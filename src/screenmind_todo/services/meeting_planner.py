from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List

import requests

from screenmind_todo.config import get_settings


@dataclass
class PlannedAction:
    title: str
    owner: str
    priority: str
    due_date: str | None
    timeline_bucket: str
    rationale: str
    step_order: int
    estimated_minutes: int
    is_blocked: bool = False


@dataclass
class MeetingPlan:
    summary: str
    decisions: str
    priorities_overview: str
    actions: List[PlannedAction]


class MeetingPlannerService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_plan(
        self,
        title: str,
        transcript: str,
        target_end_date: str | None = None,
    ) -> MeetingPlan:
        if self.settings.ollama_enabled:
            try:
                return self._build_plan_with_ollama(title, transcript, target_end_date)
            except Exception:
                pass

        return self._build_plan_fallback(title, transcript, target_end_date)

    def _build_plan_with_ollama(
        self,
        title: str,
        transcript: str,
        target_end_date: str | None,
    ) -> MeetingPlan:
        prompt = self._make_prompt(title, transcript, target_end_date)

        response = requests.post(
            f"{self.settings.ollama_base_url}/api/chat",
            json={
                "model": self.settings.ollama_model,
                "stream": False,
                "format": "json",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a meeting follow-up planner. "
                            "Turn meeting transcript into a strict, realistic, execution-ready plan. "
                            "Return only valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
        response.raise_for_status()
        raw = response.json()["message"]["content"]
        data = json.loads(raw)

        actions: List[PlannedAction] = []
        for idx, item in enumerate(data.get("actions", []), start=1):
            actions.append(
                PlannedAction(
                    title=item.get("title", "").strip() or f"Action item {idx}",
                    owner=item.get("owner", "Unassigned").strip() or "Unassigned",
                    priority=self._normalize_priority(item.get("priority", "medium")),
                    due_date=self._clean_optional(item.get("due_date")),
                    timeline_bucket=item.get("timeline_bucket", "This week").strip() or "This week",
                    rationale=item.get("rationale", "").strip() or "Derived from meeting discussion.",
                    step_order=int(item.get("step_order", idx)),
                    estimated_minutes=max(5, int(item.get("estimated_minutes", 30))),
                    is_blocked=bool(item.get("is_blocked", False)),
                )
            )

        if not actions:
            actions = self._fallback_actions_from_text(transcript, target_end_date)

        return MeetingPlan(
            summary=(data.get("summary", "") or "").strip() or self._fallback_summary(transcript),
            decisions=(data.get("decisions", "") or "").strip() or self._fallback_decisions(transcript),
            priorities_overview=(data.get("priorities_overview", "") or "").strip()
            or self._fallback_priorities_overview(actions),
            actions=actions,
        )

    def _build_plan_fallback(
        self,
        title: str,
        transcript: str,
        target_end_date: str | None,
    ) -> MeetingPlan:
        actions = self._fallback_actions_from_text(transcript, target_end_date)
        return MeetingPlan(
            summary=self._fallback_summary(transcript),
            decisions=self._fallback_decisions(transcript),
            priorities_overview=self._fallback_priorities_overview(actions),
            actions=actions,
        )

    def _make_prompt(self, title: str, transcript: str, target_end_date: str | None) -> str:
        return f"""
Meeting title: {title}
Target completion date: {target_end_date or "Not explicitly given"}

Transcript:
{transcript[:12000]}

Return JSON in exactly this shape:
{{
  "summary": "3 to 5 sentence summary",
  "decisions": "bullet-like plain text decisions",
  "priorities_overview": "brief explanation of what is highest priority and why",
  "actions": [
    {{
      "title": "specific action item",
      "owner": "person or team or Unassigned",
      "priority": "high|medium|low",
      "due_date": "date or null",
      "timeline_bucket": "Today|Tomorrow|This week|Next week|Later",
      "rationale": "why this task matters",
      "step_order": 1,
      "estimated_minutes": 30,
      "is_blocked": false
    }}
  ]
}}

Rules:
1. Extract only realistic actions clearly implied by the transcript.
2. Prioritize deadline-sensitive and dependency-first work.
3. Make the list step-by-step and execution-ready.
4. If the transcript mentions a deadline, reflect it in due_date or timeline_bucket.
5. Keep titles concise and actionable, starting with a verb.
6. Return only valid JSON.
""".strip()

    def _fallback_actions_from_text(
        self,
        transcript: str,
        target_end_date: str | None,
    ) -> List[PlannedAction]:
        sentences = re.split(r"(?<=[.!?])\s+", transcript)
        candidates: List[str] = []

        trigger_patterns = [
            r"\bneed to\b",
            r"\bshould\b",
            r"\bmust\b",
            r"\baction item\b",
            r"\bfollow up\b",
            r"\bsend\b",
            r"\bprepare\b",
            r"\bupdate\b",
            r"\bcomplete\b",
            r"\bfinish\b",
            r"\bdeliver\b",
            r"\bsubmit\b",
        ]

        for sentence in sentences:
            sentence_clean = " ".join(sentence.split()).strip()
            if len(sentence_clean) < 15:
                continue
            lowered = sentence_clean.lower()
            if any(re.search(pattern, lowered) for pattern in trigger_patterns):
                candidates.append(sentence_clean)

        if not candidates:
            candidates = [
                "Review the meeting notes and confirm the main deliverables.",
                "Break the work into concrete follow-up tasks and assign owners.",
                "Prepare the highest-priority follow-up and send updates to stakeholders.",
            ]

        actions: List[PlannedAction] = []
        for idx, sentence in enumerate(candidates[:6], start=1):
            title = self._sentence_to_action(sentence)
            priority = "high" if idx <= 2 else "medium"
            timeline = self._timeline_bucket_for_index(idx)
            actions.append(
                PlannedAction(
                    title=title,
                    owner="Unassigned",
                    priority=priority if idx <= 3 else "low",
                    due_date=target_end_date,
                    timeline_bucket=timeline,
                    rationale="Derived from transcript language indicating a required follow-up.",
                    step_order=idx,
                    estimated_minutes=30 if idx <= 2 else 45,
                    is_blocked=False,
                )
            )

        return actions

    def _timeline_bucket_for_index(self, idx: int) -> str:
        if idx == 1:
            return "Today"
        if idx == 2:
            return "Tomorrow"
        if idx in {3, 4}:
            return "This week"
        if idx == 5:
            return "Next week"
        return "Later"

    def _sentence_to_action(self, sentence: str) -> str:
        sentence = sentence.strip().rstrip(".")
        sentence = re.sub(
            r"^(we need to|need to|we should|should|must|please)\s+",
            "",
            sentence,
            flags=re.I,
        )
        sentence = sentence[:140]
        if not sentence:
            return "Review the meeting follow-up"
        sentence = sentence[0].upper() + sentence[1:]
        return sentence

    def _fallback_summary(self, transcript: str) -> str:
        excerpt = " ".join(transcript.split())[:500]
        return (
            "This meeting covered key follow-up work, decisions, and next steps. "
            f"Primary discussion excerpt: {excerpt}"
        )

    def _fallback_decisions(self, transcript: str) -> str:
        lowered = transcript.lower()
        points = []
        if "deadline" in lowered or "due" in lowered:
            points.append("- A deadline or delivery expectation was discussed.")
        if "send" in lowered or "email" in lowered:
            points.append("- A communication follow-up is expected.")
        if "update" in lowered or "revise" in lowered:
            points.append("- Some existing work likely needs revision or update.")
        if not points:
            points.append("- Follow-up execution work is required after this meeting.")
        return "\n".join(points)

    def _fallback_priorities_overview(self, actions: List[PlannedAction]) -> str:
        if not actions:
            return "No action items were identified."
        return (
            "Highest priority goes to the earliest dependency and any deadline-sensitive follow-up. "
            "Communication blockers and deliverables should be completed first."
        )

    def _normalize_priority(self, value: str) -> str:
        lowered = (value or "").strip().lower()
        if lowered in {"high", "medium", "low"}:
            return lowered
        return "medium"

    def _clean_optional(self, value: Any) -> str | None:
        if value in {None, "", "null"}:
            return None
        return str(value).strip()