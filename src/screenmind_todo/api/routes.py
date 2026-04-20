from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from screenmind_todo.db import get_db
from screenmind_todo.models import ActivityEvent, TodoTask
from screenmind_todo.schemas import ActivityRead, DashboardRead, TaskCreate, TaskRead

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db)) -> DashboardRead:
    tasks = db.execute(select(TodoTask).order_by(desc(TodoTask.created_at)).limit(50)).scalars().all()
    activities = (
        db.execute(select(ActivityEvent).order_by(desc(ActivityEvent.created_at)).limit(50))
        .scalars()
        .all()
    )
    return DashboardRead(tasks=tasks, activities=activities)


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(db: Session = Depends(get_db)) -> list[TodoTask]:
    return db.execute(select(TodoTask).order_by(desc(TodoTask.created_at))).scalars().all()


@router.post("/tasks", response_model=TaskRead)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> TodoTask:
    task = TodoTask(
        title=payload.title,
        reason=payload.reason,
        confidence=payload.confidence,
        auto_created=False,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/complete", response_model=TaskRead)
def complete_task(task_id: int, db: Session = Depends(get_db)) -> TodoTask:
    task = db.get(TodoTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "done"
    task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.get("/activities", response_model=list[ActivityRead])
def list_activities(db: Session = Depends(get_db)) -> list[ActivityEvent]:
    return db.execute(select(ActivityEvent).order_by(desc(ActivityEvent.created_at))).scalars().all()

