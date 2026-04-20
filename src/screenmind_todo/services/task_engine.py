from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from screenmind_todo.models import TodoTask


class TaskEngine:
    def __init__(self, cooldown_minutes: int) -> None:
        self.cooldown = timedelta(minutes=cooldown_minutes)

    def maybe_create_tasks(
        self,
        db: Session,
        source_window: str,
        suggested_tasks: list[dict[str, str | int]],
    ) -> list[TodoTask]:
        created: list[TodoTask] = []
        for suggestion in suggested_tasks:
            title = str(suggestion["title"])
            existing = self._recent_matching_task(db, title)
            if existing:
                continue

            task = TodoTask(
                title=title,
                reason=str(suggestion["reason"]),
                source_window=source_window,
                confidence=int(suggestion["confidence"]),
                auto_created=True,
            )
            db.add(task)
            created.append(task)

        if created:
            db.commit()
            for task in created:
                db.refresh(task)
        return created

    def _recent_matching_task(self, db: Session, title: str) -> TodoTask | None:
        since = datetime.utcnow() - self.cooldown
        stmt = (
            select(TodoTask)
            .where(TodoTask.title == title)
            .where(TodoTask.created_at >= since)
            .where(TodoTask.status == "open")
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

