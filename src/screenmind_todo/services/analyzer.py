from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ActivityContext:
    window_title: str
    app_name: str
    ocr_text: str


@dataclass
class ActivityAnalysis:
    summary: str
    confidence: int
    suggested_tasks: list[dict[str, str | int]]


class ActivityAnalyzer:
    KEYWORD_TASKS = [
        (
            ("traceback", "exception", "stack trace", "error", "failed", "bug"),
            "Fix the current application error",
            "Repeated error-related text suggests debugging work.",
            85,
        ),
        (
            ("gmail", "inbox", "draft", "follow up", "reply", "outlook"),
            "Send the pending email reply",
            "Email activity suggests a message needs follow-up.",
            75,
        ),
        (
            ("resume", "job description", "linkedin", "cover letter", "application"),
            "Tailor resume or complete the job application",
            "Job-search related activity is visible on screen.",
            78,
        ),
        (
            ("assignment", "rubric", "deadline", "submit", "canvas", "blackboard"),
            "Complete and submit the current assignment",
            "School-related instructions suggest a deliverable is pending.",
            80,
        ),
        (
            ("meeting notes", "agenda", "calendar", "zoom", "teams"),
            "Prepare for or follow up on the current meeting",
            "Meeting-related content usually implies prep or follow-up.",
            65,
        ),
        (
            ("todo", "task", "checklist", "notion", "trello", "jira"),
            "Review and update the current task list",
            "Task management activity is already in focus.",
            60,
        ),
        (
            ("invoice", "payment", "billing", "receipt"),
            "Review and complete the pending payment task",
            "Billing-related content suggests a money task is pending.",
            70,
        ),
    ]

    def analyze(self, context: ActivityContext) -> ActivityAnalysis:
        combined = " ".join(
            part for part in [context.window_title, context.app_name, context.ocr_text] if part
        ).lower()
        summary = self._build_summary(context)
        tasks: list[dict[str, str | int]] = []
        max_confidence = 30 if combined else 0

        for keywords, title, reason, confidence in self.KEYWORD_TASKS:
            if any(keyword in combined for keyword in keywords):
                tasks.append(
                    {
                        "title": title,
                        "reason": reason,
                        "confidence": confidence,
                    }
                )
                max_confidence = max(max_confidence, confidence)

        return ActivityAnalysis(summary=summary, confidence=max_confidence, suggested_tasks=tasks)

    def _build_summary(self, context: ActivityContext) -> str:
        if context.window_title and context.app_name:
            return f"Active in {context.app_name}: {context.window_title}"
        if context.window_title:
            return f"Active window: {context.window_title}"
        if context.ocr_text:
            snippet = context.ocr_text[:120]
            return f"Visible screen text: {snippet}"
        return "No meaningful screen activity detected"

