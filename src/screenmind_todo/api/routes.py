from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, desc, select

from screenmind_todo.db import SessionLocal
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
    title: str
    confidence: int = 100
    reason: str = "Manually added by user"


class TaskReadPayload(BaseModel):
    id: int
    title: str
    reason: str
    source_window: str
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
            status="open",
            confidence=payload.confidence,
            auto_created=False,
        )
        db.add(task)
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