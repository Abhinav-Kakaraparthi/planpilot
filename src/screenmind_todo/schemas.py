from datetime import datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    reason: str = ""
    confidence: int = 50


class TaskRead(BaseModel):
    id: int
    title: str
    reason: str
    source_window: str
    status: str
    confidence: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    auto_created: bool

    model_config = {"from_attributes": True}


class ActivityRead(BaseModel):
    id: int
    window_title: str
    app_name: str
    ocr_text: str
    inferred_summary: str
    confidence: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardRead(BaseModel):
    tasks: list[TaskRead]
    activities: list[ActivityRead]

