from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from screenmind_todo.api.meeting_routes import meeting_router
from screenmind_todo.api.routes import router
from screenmind_todo.config import get_settings
from screenmind_todo.db import Base, engine
from screenmind_todo.services.watcher import ActivityWatcher

# important import so SQLAlchemy sees the new tables
from screenmind_todo import meeting_models  # noqa: F401

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_meeting_action_columns()
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


@app.post("/api/watcher/stop")
async def stop_watcher() -> dict[str, object]:
    watcher.pause()
    return {"message": "Watcher paused", "enabled": watcher.enabled}


@app.post("/api/watcher/start")
async def start_watcher() -> dict[str, object]:
    watcher.resume()
    return {"message": "Watcher resumed", "enabled": watcher.enabled}
