from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select

from screenmind_todo.db import SessionLocal
from screenmind_todo.meeting_models import MeetingActionItem, MeetingSession
from screenmind_todo.meeting_schemas import (
    ActionStatusUpdate,
    MeetingListItem,
    MeetingPlanCreate,
    MeetingRead,
)
from screenmind_todo.services.meeting_planner import MeetingPlannerService

meeting_router = APIRouter(prefix="/api/meetings", tags=["meetings"])
planner = MeetingPlannerService()


@meeting_router.post("/plan", response_model=MeetingRead)
async def plan_meeting(payload: MeetingPlanCreate):
    plan = planner.build_plan(
        title=payload.title,
        transcript=payload.transcript,
        target_end_date=payload.target_end_date,
    )

    with SessionLocal() as db:
        meeting = MeetingSession(
            title=payload.title,
            transcript=payload.transcript,
            summary=plan.summary,
            decisions=plan.decisions,
            priorities_overview=plan.priorities_overview,
            target_end_date=payload.target_end_date,
        )
        db.add(meeting)
        db.flush()

        for action in plan.actions:
            db.add(
                MeetingActionItem(
                    meeting_id=meeting.id,
                    title=action.title,
                    owner=action.owner,
                    priority=action.priority,
                    due_date=action.due_date,
                    timeline_bucket=action.timeline_bucket,
                    rationale=action.rationale,
                    step_order=action.step_order,
                    estimated_minutes=action.estimated_minutes,
                    is_blocked=action.is_blocked,
                )
            )

        db.commit()
        db.refresh(meeting)

        meeting = db.execute(
            select(MeetingSession)
            .where(MeetingSession.id == meeting.id)
        ).scalar_one()

        meeting.actions  # load relationship
        return meeting


@meeting_router.get("", response_model=list[MeetingListItem])
async def list_meetings():
    with SessionLocal() as db:
        meetings = db.execute(
            select(MeetingSession).order_by(desc(MeetingSession.created_at))
        ).scalars().all()
        return meetings


@meeting_router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(meeting_id: int):
    with SessionLocal() as db:
        meeting = db.execute(
            select(MeetingSession).where(MeetingSession.id == meeting_id)
        ).scalar_one_or_none()

        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        meeting.actions
        return meeting


@meeting_router.post("/{meeting_id}/actions/{action_id}/status", response_model=MeetingRead)
async def update_action_status(meeting_id: int, action_id: int, payload: ActionStatusUpdate):
    with SessionLocal() as db:
        meeting = db.execute(
            select(MeetingSession).where(MeetingSession.id == meeting_id)
        ).scalar_one_or_none()

        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        action = db.execute(
            select(MeetingActionItem).where(
                MeetingActionItem.id == action_id,
                MeetingActionItem.meeting_id == meeting_id,
            )
        ).scalar_one_or_none()

        if not action:
            raise HTTPException(status_code=404, detail="Action item not found")

        action.status = payload.status
        action.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(meeting)
        meeting.actions
        return meeting