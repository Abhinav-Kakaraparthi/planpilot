from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, select

from screenmind_todo.db import SessionLocal
from screenmind_todo.meeting_models import MeetingSession
from screenmind_todo.models import ActivityEvent, TodoTask

router = APIRouter(prefix="/api", tags=["app"])


NOISE_TERMS = [
    "screenmind todo",
    "planpilot",
    "localhost",
    "127.0.0.1",
    "swagger ui",
    "system idle process",
    "response body",
    "server response",
    "no ocr text stored",
    "try it out",
    "execute",
]


class TaskCreatePayload(BaseModel):
    title: str = Field(min_length=1)
    confidence: int = 100
    reason: str = "Manually added by user"
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")
    timeline_bucket: str = "This week"


class TaskUpdatePayload(BaseModel):
    title: str = Field(min_length=1)
    priority: str = Field(pattern="^(high|medium|low)$")
    timeline_bucket: str = Field(min_length=1)
    status: str = Field(pattern="^(open|done)$")
    reason: str = Field(min_length=1)


class TaskReadPayload(BaseModel):
    id: int
    title: str
    reason: str
    source_window: str
    priority: str
    timeline_bucket: str
    status: str
    confidence: int
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    auto_created: bool

    class Config:
        from_attributes = True


class ActivityReadPayload(BaseModel):
    id: int
    window_title: str
    app_name: str
    ocr_text: str
    inferred_summary: str
    confidence: int
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardPayload(BaseModel):
    tasks: List[TaskReadPayload]
    activities: List[ActivityReadPayload]


class SessionStatusPayload(BaseModel):
    active: bool
    mode: str
    label: str


class CopilotPayload(BaseModel):
    mode: str
    speaker: str
    question: str
    answer: str
    tone: str
    follow_up: str
    screen_signal: str
    task_signal: str
    meeting_title: str
    session_active: bool


def _is_noisy_activity(activity: ActivityEvent) -> bool:
    combined = " ".join(
        [
            activity.window_title or "",
            activity.app_name or "",
            activity.ocr_text or "",
            activity.inferred_summary or "",
        ]
    ).lower()

    return any(term in combined for term in NOISE_TERMS)


def _get_filtered_activities(include_noise: bool, limit: int) -> List[ActivityEvent]:
    with SessionLocal() as db:
        activities = db.execute(
            select(ActivityEvent).order_by(desc(ActivityEvent.created_at))
        ).scalars().all()

        if not include_noise:
            activities = [a for a in activities if not _is_noisy_activity(a)]

        return activities[:limit]


def _latest_question(transcript: str) -> tuple[str, str]:
    if not transcript:
        return ("No speaker", "")

    lines = [line.strip() for line in transcript.splitlines() if line.strip()]
    for line in reversed(lines):
        if "?" not in line:
            continue

        if ":" in line:
            speaker, _, question = line.partition(":")
            return (speaker.strip() or "Meeting", question.strip())

        return ("Meeting", line)

    return ("No speaker", "")


def _truncate(value: str, max_length: int = 220) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3].rstrip()}..."


def _build_copilot_payload(mode: str, session_active: bool) -> CopilotPayload:
    normalized_mode = mode if mode in {"answer", "summary", "tasks"} else "answer"

    with SessionLocal() as db:
        meeting = db.execute(
            select(MeetingSession).order_by(desc(MeetingSession.created_at)).limit(1)
        ).scalar_one_or_none()
        if meeting:
            meeting.actions
        tasks = db.execute(select(TodoTask).order_by(desc(TodoTask.created_at))).scalars().all()
        activities = db.execute(
            select(ActivityEvent).order_by(desc(ActivityEvent.created_at))
        ).scalars().all()

    tasks = list(tasks)
    activities = [activity for activity in activities if not _is_noisy_activity(activity)][:20]

    speaker, question = _latest_question(meeting.transcript if meeting else "")
    screen_signal = (
        _truncate(
            (activities[0].inferred_summary or activities[0].ocr_text or "").strip()
            or f"{activities[0].app_name} {activities[0].window_title}",
            120,
        )
        if activities
        else "No recent screen activity."
    )
    open_tasks = [task for task in tasks if task.status != "done"]
    task_signal = (
        _truncate("; ".join(task.title for task in open_tasks[:2]), 120)
        if open_tasks
        else "No open tasks available."
    )

    if not meeting:
        return CopilotPayload(
            mode=normalized_mode,
            speaker=speaker,
            question="No meeting question detected yet.",
            answer="Load a meeting plan to generate a response.",
            tone="Concise",
            follow_up="Open a meeting plan to unlock the copilot context.",
            screen_signal=screen_signal,
            task_signal=task_signal,
            meeting_title="None loaded",
            session_active=session_active,
        )

    tone = "Executive" if normalized_mode == "summary" else "Directive" if normalized_mode == "tasks" else "Concise"
    question_text = question or "No meeting question detected yet."

    if normalized_mode == "summary":
        answer = _truncate(
            f"{meeting.summary} Right now the plan health is {meeting.execution_health.replace('_', ' ')} and the next move is {meeting.next_recommendation}.",
            320,
        )
        follow_up = meeting.adaptation_note or meeting.next_recommendation
    elif normalized_mode == "tasks":
        action_titles = [f"{action.title} ({action.timeline_bucket})" for action in meeting.actions[:3]]
        answer = (
            f"Focus the room on these next actions: {'; '.join(action_titles)}."
            if action_titles
            else "No saved action items yet. Generate a plan from a transcript first."
        )
        follow_up = "Ask whether the room agrees on owners and due windows."
    else:
        answer = _truncate(
            " ".join(
                [
                    f"Answer the question directly: {question}" if question else "Lead with the core product point.",
                    meeting.summary,
                    f"Ground the response in the current signal: {screen_signal}",
                ]
            ),
            320,
        )
        follow_up = meeting.next_recommendation or "Close by proposing the next concrete step."

    return CopilotPayload(
        mode=normalized_mode,
        speaker=speaker,
        question=question_text,
        answer=answer,
        tone=tone,
        follow_up=follow_up,
        screen_signal=screen_signal,
        task_signal=task_signal,
        meeting_title=meeting.title,
        session_active=session_active,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/tasks", response_model=list[TaskReadPayload])
def list_tasks() -> list[TodoTask]:
    with SessionLocal() as db:
        tasks = db.execute(
            select(TodoTask).order_by(desc(TodoTask.created_at))
        ).scalars().all()
        return list(tasks)


@router.post("/tasks", response_model=TaskReadPayload)
def create_task(payload: TaskCreatePayload) -> TodoTask:
    with SessionLocal() as db:
        task = TodoTask(
            title=payload.title,
            reason=payload.reason,
            source_window="Manual",
            priority=payload.priority,
            timeline_bucket=payload.timeline_bucket,
            status="open",
            confidence=payload.confidence,
            auto_created=False,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task


@router.put("/tasks/{task_id}", response_model=TaskReadPayload)
def update_task(task_id: int, payload: TaskUpdatePayload) -> TodoTask:
    with SessionLocal() as db:
        task = db.execute(
            select(TodoTask).where(TodoTask.id == task_id)
        ).scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task.title = payload.title.strip()
        task.priority = payload.priority
        task.timeline_bucket = payload.timeline_bucket.strip()
        task.status = payload.status
        task.reason = payload.reason.strip()
        task.completed_at = datetime.utcnow() if payload.status == "done" else None
        db.commit()
        db.refresh(task)
        return task


@router.post("/tasks/{task_id}/complete", response_model=TaskReadPayload)
def complete_task(task_id: int) -> TodoTask:
    with SessionLocal() as db:
        task = db.execute(
            select(TodoTask).where(TodoTask.id == task_id)
        ).scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task.status = "done"
        task.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task


@router.get("/activities", response_model=list[ActivityReadPayload])
def list_activities(
    include_noise: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
) -> list[ActivityEvent]:
    return _get_filtered_activities(include_noise=include_noise, limit=limit)


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: int) -> dict[str, str]:
    with SessionLocal() as db:
        activity = db.execute(
            select(ActivityEvent).where(ActivityEvent.id == activity_id)
        ).scalar_one_or_none()

        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        db.delete(activity)
        db.commit()
        return {"status": "deleted"}


@router.post("/activities/clear")
def clear_activities() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(delete(ActivityEvent))
        db.commit()
        return {"status": "cleared"}


@router.get("/dashboard", response_model=DashboardPayload)
def dashboard(
    include_noise: bool = Query(False),
    activity_limit: int = Query(20, ge=1, le=100),
) -> dict:
    with SessionLocal() as db:
        tasks = db.execute(
            select(TodoTask).order_by(desc(TodoTask.created_at))
        ).scalars().all()

    activities = _get_filtered_activities(
        include_noise=include_noise,
        limit=activity_limit,
    )

    return {
        "tasks": list(tasks),
        "activities": list(activities),
    }


@router.get("/copilot/context", response_model=CopilotPayload)
def copilot_context(mode: str = Query("answer")) -> CopilotPayload:
    return _build_copilot_payload(mode=mode, session_active=False)
