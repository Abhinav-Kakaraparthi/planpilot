from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MeetingPlanCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    transcript: str = Field(..., min_length=20)
    target_end_date: Optional[str] = None


class MeetingActionRead(BaseModel):
    id: int
    title: str
    owner: str
    priority: str
    due_date: Optional[str]
    timeline_bucket: str
    rationale: str
    status: str
    step_order: int
    estimated_minutes: int
    is_blocked: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MeetingRead(BaseModel):
    id: int
    title: str
    transcript: str
    summary: str
    decisions: str
    priorities_overview: str
    target_end_date: Optional[str]
    created_at: datetime
    updated_at: datetime
    actions: List[MeetingActionRead]

    class Config:
        from_attributes = True


class MeetingListItem(BaseModel):
    id: int
    title: str
    summary: str
    target_end_date: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|done)$")