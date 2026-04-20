from __future__ import annotations

import asyncio
import logging
import re
from contextlib import suppress

from sqlalchemy import desc, select

from screenmind_todo.config import Settings
from screenmind_todo.db import SessionLocal
from screenmind_todo.models import ActivityEvent
from screenmind_todo.services.active_window import get_active_window_title
from screenmind_todo.services.analyzer import ActivityAnalyzer, ActivityContext
from screenmind_todo.services.capture import ScreenCaptureService
from screenmind_todo.services.ocr import OCRService
from screenmind_todo.services.ollama import OllamaService
from screenmind_todo.services.task_engine import TaskEngine

logger = logging.getLogger(__name__)


class ActivityWatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.capture_service = ScreenCaptureService(
            save_screenshots=settings.save_screenshots,
            captures_dir=settings.captures_dir,
        )
        self.ocr_service = OCRService()
        self.analyzer = ActivityAnalyzer()
        self.task_engine = TaskEngine(settings.task_cooldown_minutes)
        self.ollama = (
            OllamaService(settings.ollama_base_url, settings.ollama_model)
            if settings.ollama_enabled
            else None
        )
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._enabled = True

        self._blocked_window_terms = [
            "screenmind todo",
            "127.0.0.1",
            "localhost",
            "swagger ui",
            "/docs",
        ]

        self._blocked_text_terms = [
            "screenmind todo",
            "local ai screen watcher",
            "scan now",
            "recent activity",
            "add manual task",
            "complete",
            "stop watching",
            "start watching",
            "localhost",
            "127.0.0.1",
            "swagger ui",
            "response body",
            "server response",
            "try it out",
            "execute",
        ]

    @property
    def enabled(self) -> bool:
        return self._enabled

    def pause(self) -> None:
        self._enabled = False
        logger.info("Activity watcher paused")

    def resume(self) -> None:
        self._enabled = True
        logger.info("Activity watcher resumed")

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def scan_once(self, force: bool = False) -> None:
        if not self._enabled and not force:
            logger.info("Skipping scan because watcher is paused")
            return

        window_title, app_name = get_active_window_title()

        if self._should_skip_window(window_title, app_name):
            logger.info("Skipping blocked window: %s | %s", window_title, app_name)
            return

        image, _ = await asyncio.to_thread(self.capture_service.capture_primary_display)
        ocr_text = await asyncio.to_thread(self.ocr_service.extract_text, image)

        cleaned_text = self._clean_ocr_text(ocr_text)

        if not self._has_meaningful_content(window_title, cleaned_text):
            logger.info("Skipping weak or noisy OCR for window: %s", window_title)
            return

        context = ActivityContext(
            window_title=window_title,
            app_name=app_name,
            ocr_text=cleaned_text,
        )
        analysis = self.analyzer.analyze(context)

        if self.ollama:
            with suppress(Exception):
                analysis.summary, analysis.confidence = await self.ollama.summarize(
                    self._build_llm_prompt(window_title, app_name, cleaned_text)
                )

        if self._should_skip_analysis(window_title, cleaned_text, analysis.summary):
            logger.info("Skipping low-value activity: %s", window_title)
            return

        with SessionLocal() as db:
            previous = db.execute(
                select(ActivityEvent).order_by(desc(ActivityEvent.created_at)).limit(1)
            ).scalar_one_or_none()

            if previous and self._is_duplicate(previous, window_title, app_name, cleaned_text):
                logger.info("Skipping duplicate activity: %s", window_title)
                return

            event = ActivityEvent(
                window_title=window_title,
                app_name=app_name,
                ocr_text=cleaned_text[:2000],
                inferred_summary=analysis.summary,
                confidence=analysis.confidence,
            )
            db.add(event)
            db.commit()

            filtered_tasks = self._filter_suggested_tasks(analysis.suggested_tasks)
            if filtered_tasks:
                self.task_engine.maybe_create_tasks(db, window_title, filtered_tasks)

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self._enabled:
                    await self.scan_once()
            except Exception as exc:
                logger.exception("Activity watcher iteration failed: %s", exc)

            await asyncio.sleep(self.settings.capture_interval_seconds)

    def _is_duplicate(
        self,
        previous: ActivityEvent,
        window_title: str,
        app_name: str,
        ocr_text: str,
    ) -> bool:
        return (
            previous.window_title == window_title
            and previous.app_name == app_name
            and (previous.ocr_text or "")[:250] == ocr_text[:250]
        )

    def _should_skip_window(self, window_title: str, app_name: str) -> bool:
        combined = f"{window_title} {app_name}".lower()
        return any(term in combined for term in self._blocked_window_terms)

    def _clean_ocr_text(self, text: str) -> str:
        if not text:
            return ""

        text = " ".join(text.split())
        lowered = text.lower()

        for term in self._blocked_text_terms:
            lowered = lowered.replace(term, " ")

        tokens = lowered.split()
        cleaned_tokens = []

        for token in tokens:
            token = re.sub(r"[^a-zA-Z0-9@:/._-]", "", token)

            if len(token) <= 1:
                continue
            if token.isdigit():
                continue
            if len(set(token)) == 1 and len(token) > 3:
                continue

            cleaned_tokens.append(token)

        deduped = []
        prev = None
        for token in cleaned_tokens:
            if token != prev:
                deduped.append(token)
            prev = token

        return " ".join(deduped[:300]).strip()

    def _has_meaningful_content(self, window_title: str, cleaned_text: str) -> bool:
        if len(cleaned_text) < self.settings.ocr_min_text_length:
            return False

        words = cleaned_text.split()
        if len(words) < 5:
            return False

        long_words = [w for w in words if len(w) >= 4]
        if len(long_words) < 3:
            return False

        return True

    def _should_skip_analysis(self, window_title: str, cleaned_text: str, summary: str) -> bool:
        combined = f"{window_title} {cleaned_text} {summary}".lower()

        low_value_patterns = [
            "system idle process",
            "screenmind todo",
            "localhost",
            "127.0.0.1",
            "swagger ui",
        ]

        return any(pattern in combined for pattern in low_value_patterns)

    def _filter_suggested_tasks(self, suggested_tasks: list[str]) -> list[str]:
        filtered = []
        blocked_task_terms = [
            "review and update the current task list",
            "use screenmind",
            "scan the screen",
            "review recent activity",
            "system idle process",
        ]

        for task in suggested_tasks:
            task_clean = task.strip()
            if not task_clean:
                continue

            lowered = task_clean.lower()
            if any(term in lowered for term in blocked_task_terms):
                continue

            filtered.append(task_clean)

        return filtered[:5]

    def _build_llm_prompt(self, window_title: str, app_name: str, cleaned_text: str) -> str:
        return (
            "You are an assistant that creates useful todo tasks from active screen work.\n\n"
            "Rules:\n"
            "1. Ignore OCR noise, browser chrome text, localhost pages, and app UI labels.\n"
            "2. Ignore the ScreenMind Todo app itself.\n"
            "3. Only infer tasks when there is strong evidence from the visible work.\n"
            "4. If evidence is weak or noisy, return a low-confidence summary.\n"
            "5. Prefer concrete actions such as replying to an email, fixing an error, "
            "completing a form, updating a resume, or submitting an application.\n"
            "6. Do not invent tasks from random words.\n\n"
            f"Window: {window_title}\n"
            f"App: {app_name}\n"
            f"Visible text: {cleaned_text[:1500]}"
        )