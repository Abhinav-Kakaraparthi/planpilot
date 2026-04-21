from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from screenmind_todo.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MeetingSession(Base):
    __tablename__ = "meeting_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    transcript = Column(Text, nullable=False)
    summary = Column(Text, nullable=False, default="")
    decisions = Column(Text, nullable=False, default="")
    priorities_overview = Column(Text, nullable=False, default="")
    target_end_date = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    actions = relationship(
        "MeetingActionItem",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="MeetingActionItem.step_order",
    )


class MeetingActionItem(Base):
    __tablename__ = "meeting_action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meeting_sessions.id"), nullable=False, index=True)

    title = Column(String(300), nullable=False)
    owner = Column(String(120), nullable=False, default="Unassigned")
    priority = Column(String(20), nullable=False, default="medium")
    due_date = Column(String(64), nullable=True)
    timeline_bucket = Column(String(64), nullable=False, default="This week")
    rationale = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="open")
    step_order = Column(Integer, nullable=False, default=1)
    estimated_minutes = Column(Integer, nullable=False, default=30)
    is_blocked = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    meeting = relationship("MeetingSession", back_populates="actions")