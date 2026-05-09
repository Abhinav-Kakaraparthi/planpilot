from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select, text

from screenmind_todo.api.meeting_routes import meeting_router
from screenmind_todo.api.routes import router
from screenmind_todo.config import get_settings
from screenmind_todo.db import Base, SessionLocal, engine
from screenmind_todo.models import ActivityEvent, TodoTask
from screenmind_todo.services.watcher import ActivityWatcher

# important import so SQLAlchemy sees the new tables
from screenmind_todo import meeting_models  # noqa: F401
from screenmind_todo.meeting_models import MeetingActionItem, MeetingSession

settings = get_settings()
watcher = ActivityWatcher(settings)


def ensure_meeting_action_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_columns = {
        "meeting_action_items": {
            "dependency_summary": "TEXT NOT NULL DEFAULT ''",
            "risk_level": "VARCHAR(20) NOT NULL DEFAULT 'medium'",
            "unblocker": "TEXT NOT NULL DEFAULT ''",
        },
        "meeting_sessions": {
            "progress_percent": "INTEGER NOT NULL DEFAULT 0",
            "execution_health": "VARCHAR(40) NOT NULL DEFAULT 'needs_start'",
            "next_recommendation": "TEXT NOT NULL DEFAULT ''",
            "adaptation_note": "TEXT NOT NULL DEFAULT ''",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in table_columns.items():
            if not inspector.has_table(table_name):
                continue

            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {definition}"))


def ensure_task_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if not inspector.has_table("todo_tasks"):
        return

    existing = {column["name"] for column in inspector.get_columns("todo_tasks")}
    missing = {
        "priority": "VARCHAR(20) NOT NULL DEFAULT 'medium'",
        "timeline_bucket": "VARCHAR(64) NOT NULL DEFAULT 'This week'",
    }

    with engine.begin() as connection:
        for name, definition in missing.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE todo_tasks ADD COLUMN {name} {definition}"))


def seed_demo_content() -> None:
    with SessionLocal() as db:
        has_tasks = db.execute(select(TodoTask.id).limit(1)).scalar_one_or_none() is not None
        has_activities = db.execute(select(ActivityEvent.id).limit(1)).scalar_one_or_none() is not None
        has_meetings = db.execute(select(MeetingSession.id).limit(1)).scalar_one_or_none() is not None

        if has_tasks or has_activities or has_meetings:
            return

        demo_tasks = [
            TodoTask(
                title="Refine the investor pitch story for PlanPilot",
                reason="Tighten the product narrative around session-based execution assistance.",
                source_window="Demo Seed",
                priority="high",
                timeline_bucket="Today",
                status="open",
                confidence=96,
                auto_created=False,
            ),
            TodoTask(
                title="Review the seeded meeting action plan before demo",
                reason="Make sure the meeting planner output looks polished for first-run demos.",
                source_window="Demo Seed",
                priority="medium",
                timeline_bucket="This week",
                status="open",
                confidence=92,
                auto_created=False,
            ),
            TodoTask(
                title="Prepare follow-up email template for pilot users",
                reason="Use a clean follow-up workflow after product walkthroughs.",
                source_window="Demo Seed",
                priority="low",
                timeline_bucket="Later",
                status="open",
                confidence=88,
                auto_created=False,
            ),
        ]

        demo_activities = [
            ActivityEvent(
                window_title="Investor Pitch Deck",
                app_name="PowerPoint",
                ocr_text="The product turns meetings and screen context into structured execution plans with priorities and timeline guidance.",
                inferred_summary="Pitch deck focused on positioning the product as an execution assistant.",
                confidence=94,
            ),
            ActivityEvent(
                window_title="Customer Notes",
                app_name="Notion",
                ocr_text="Investors want editable tasks, cleaner signal quality, and a more intentional session mode.",
                inferred_summary="Captured investor feedback about control, clarity, and session flow.",
                confidence=91,
            ),
            ActivityEvent(
                window_title="Product Roadmap",
                app_name="Linear",
                ocr_text="Next milestone: session mode, transcript-first copilot, task editing, launch-ready experience.",
                inferred_summary="Roadmap is centered on session mode and product polish.",
                confidence=90,
            ),
        ]

        meeting = MeetingSession(
            title="PlanPilot investor prep",
            transcript=(
                "Ava: What makes PlanPilot different from transcript tools?\n"
                "Founder: PlanPilot converts discussion into a sequence of actions.\n"
                "Ava: How do we prove this feels like a product instead of a prototype?\n"
                "Founder: We need a tighter first-run story, editable tasks, and session mode.\n"
            ),
            summary="The team aligned on turning PlanPilot from a passive watcher into a sharper execution product for demos and investor meetings.",
            decisions="Prioritize demo readiness. Ship editable tasks. Replace always-on capture with session mode for intentional workflows.",
            priorities_overview="High priority is demo polish and user control. Medium priority is a clearer session flow for watcher capture.",
            progress_percent=42,
            execution_health="on_track",
            next_recommendation="Lead the pitch with session mode and editable execution plans, then demo the copilot surface.",
            adaptation_note="The product story is shifting from background OCR to guided execution assistance.",
            target_end_date="2026-05-16",
        )
        db.add(meeting)
        db.flush()

        demo_actions = [
            MeetingActionItem(
                meeting_id=meeting.id,
                title="Present the product as a session-based execution assistant",
                owner="Founder",
                priority="high",
                due_date="2026-05-12",
                timeline_bucket="Today",
                rationale="Investors need the strategic repositioning to understand why PlanPilot is differentiated.",
                step_order=1,
                estimated_minutes=30,
                is_blocked=False,
                dependency_summary="Pitch story must be aligned with current UI and workflow.",
                risk_level="low",
                unblocker="Use the investor prep notes in the seeded dataset.",
            ),
            MeetingActionItem(
                meeting_id=meeting.id,
                title="Demo editable tasks with priority and timeline control",
                owner="Founder",
                priority="high",
                due_date="2026-05-12",
                timeline_bucket="This week",
                rationale="Direct control is expected immediately in a productivity product demo.",
                step_order=2,
                estimated_minutes=20,
                is_blocked=False,
                dependency_summary="Task editing must be visible in the dashboard.",
                risk_level="medium",
                unblocker="Use the task cards in the Signals view.",
            ),
            MeetingActionItem(
                meeting_id=meeting.id,
                title="Run a live session instead of leaving the watcher always on",
                owner="Founder",
                priority="medium",
                due_date="2026-05-13",
                timeline_bucket="This week",
                rationale="A session-based demo feels deliberate and reduces OCR noise.",
                step_order=3,
                estimated_minutes=15,
                is_blocked=False,
                dependency_summary="Session controls must be visible before the demo starts.",
                risk_level="low",
                unblocker="Use the new session controls in the sidebar.",
            ),
        ]

        db.add_all(demo_tasks + demo_activities + demo_actions)
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_meeting_action_columns()
    ensure_task_columns()
    seed_demo_content()
    await watcher.start()
    try:
        yield
    finally:
        await watcher.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
app.include_router(meeting_router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(static_dir / "favicon.svg", media_type="image/svg+xml")


@app.post("/api/scan-once")
async def scan_once() -> dict[str, str]:
    await watcher.scan_once(force=True)
    return {"status": "queued"}


@app.get("/api/watcher/status")
async def watcher_status() -> dict[str, bool]:
    return {"enabled": watcher.enabled}


@app.get("/api/session/status")
async def session_status() -> dict[str, object]:
    return {
        "active": watcher.enabled,
        "mode": "session",
        "label": watcher.session_label,
    }


@app.post("/api/session/start")
async def start_session() -> dict[str, object]:
    watcher.resume()
    return {"message": "Session started", "active": watcher.enabled, "label": watcher.session_label}


@app.post("/api/session/stop")
async def stop_session() -> dict[str, object]:
    watcher.pause()
    return {"message": "Session stopped", "active": watcher.enabled, "label": watcher.session_label}


@app.post("/api/watcher/stop")
async def stop_watcher() -> dict[str, object]:
    watcher.pause()
    return {"message": "Watcher paused", "enabled": watcher.enabled}


@app.post("/api/watcher/start")
async def start_watcher() -> dict[str, object]:
    watcher.resume()
    return {"message": "Watcher resumed", "enabled": watcher.enabled}
