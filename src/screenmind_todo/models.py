from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from screenmind_todo.db import Base


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    window_title: Mapped[str] = mapped_column(String(500), default="")
    app_name: Mapped[str] = mapped_column(String(255), default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    inferred_summary: Mapped[str] = mapped_column(String(500), default="")
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TodoTask(Base):
    __tablename__ = "todo_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    source_window: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(50), default="open", index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_created: Mapped[bool] = mapped_column(Boolean, default=True)

