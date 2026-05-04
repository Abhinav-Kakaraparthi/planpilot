from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, List, Protocol

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
    dependency_summary: str = ""
    risk_level: str = "medium"
    unblocker: str = ""


@dataclass
class MeetingPlan:
    summary: str
    decisions: str
    priorities_overview: str
    actions: List[PlannedAction]


class ActionState(Protocol):
    title: str
    priority: str
    due_date: str | None
    timeline_bucket: str
    status: str
    step_order: int
    estimated_minutes: int
    is_blocked: bool
    dependency_summary: str
    risk_level: str
    unblocker: str


@dataclass
class PlanState:
    progress_percent: int
    execution_health: str
    next_recommendation: str
    adaptation_note: str
    priorities_overview: str


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
                    dependency_summary=(item.get("dependency_summary", "") or "").strip(),
                    risk_level=self._normalize_risk(item.get("risk_level", "medium")),
                    unblocker=(item.get("unblocker", "") or "").strip(),
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

    def adapt_plan_state(self, actions: list[ActionState]) -> PlanState:
        total = len(actions)
        if total == 0:
            return PlanState(
                progress_percent=0,
                execution_health="empty",
                next_recommendation="Create at least one action before tracking execution.",
                adaptation_note="No actions exist for this plan yet.",
                priorities_overview="No action items were identified.",
            )

        done_actions = [action for action in actions if self._is_done(action)]
        open_actions = [action for action in actions if not self._is_done(action)]
        progress_percent = round((len(done_actions) / total) * 100)

        if not open_actions:
            return PlanState(
                progress_percent=100,
                execution_health="complete",
                next_recommendation="Plan complete. Capture learnings and close the loop with stakeholders.",
                adaptation_note=f"All {total} actions are complete.",
                priorities_overview="All planned follow-up work is complete.",
            )

        blocked_actions = [action for action in open_actions if action.is_blocked]
        overdue_actions = [action for action in open_actions if self._is_due_or_overdue(action.due_date)]
        high_risk_actions = [
            action for action in open_actions if (action.risk_level or "").lower() == "high"
        ]

        next_action = self._choose_next_action(open_actions)
        execution_health = self._execution_health(
            progress_percent=progress_percent,
            blocked_count=len(blocked_actions),
            overdue_count=len(overdue_actions),
            high_risk_count=len(high_risk_actions),
        )

        next_recommendation = self._next_recommendation(next_action)
        adaptation_note = (
            f"{len(done_actions)}/{total} actions complete. "
            f"{len(blocked_actions)} blocked, {len(high_risk_actions)} high risk, "
            f"{sum(action.estimated_minutes for action in open_actions)} minutes estimated remaining."
        )

        priorities_overview = (
            f"Current plan health is {execution_health.replace('_', ' ')}. "
            f"Focus next on: {next_action.title}. "
            "Blocked and deadline-sensitive work should be handled before lower-risk tasks."
        )

        return PlanState(
            progress_percent=progress_percent,
            execution_health=execution_health,
            next_recommendation=next_recommendation,
            adaptation_note=adaptation_note,
            priorities_overview=priorities_overview,
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
      "is_blocked": false,
      "dependency_summary": "what this action depends on, or empty string",
      "risk_level": "high|medium|low",
      "unblocker": "specific next unblocker if blocked, or empty string"
    }}
  ]
}}

Rules:
1. Extract only realistic actions clearly implied by the transcript.
2. Prioritize deadline-sensitive and dependency-first work.
3. Make the list step-by-step and execution-ready.
4. If the transcript mentions a deadline, reflect it in due_date or timeline_bucket.
5. Keep titles concise and actionable, starting with a verb.
6. Mark blocked actions when they are waiting on a person, decision, asset, access, or prior task.
7. Surface risk when timing, unclear ownership, missing inputs, or customer impact could derail execution.
8. Return only valid JSON.
""".strip()

    def _fallback_actions_from_text(
        self,
        transcript: str,
        target_end_date: str | None,
    ) -> List[PlannedAction]:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", transcript)
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
            r"\bassign\b",
            r"\bdecide\b",
            r"\bapprove\b",
            r"\bblocked\b",
            r"\bwaiting on\b",
            r"\bdepends on\b",
            r"\bonce\b",
            r"\bafter\b",
        ]

        for sentence in sentences:
            sentence_clean = " ".join(sentence.split()).strip()
            if len(sentence_clean) < 15:
                continue
            sentence_clean = self._strip_speaker(sentence_clean)
            lowered = sentence_clean.lower()
            if any(re.search(pattern, lowered) for pattern in trigger_patterns):
                candidates.append(sentence_clean)

        if not candidates:
            candidates = [
                "Review the meeting notes and confirm the main deliverables.",
                "Break the work into concrete follow-up tasks and assign owners.",
                "Prepare the highest-priority follow-up and send updates to stakeholders.",
            ]

        normalized_candidates = self._dedupe_candidates(candidates)[:8]
        actions: List[PlannedAction] = []
        for idx, sentence in enumerate(normalized_candidates, start=1):
            title = self._sentence_to_action(sentence)
            due_date = self._extract_due_date(sentence, target_end_date)
            is_blocked = self._is_blocked(sentence)
            risk_level = self._infer_risk(sentence, due_date, is_blocked)
            priority = self._infer_priority(sentence, idx, due_date, is_blocked, risk_level)
            timeline = self._infer_timeline_bucket(sentence, idx, due_date)
            actions.append(
                PlannedAction(
                    title=title,
                    owner=self._extract_owner(sentence),
                    priority=priority,
                    due_date=due_date,
                    timeline_bucket=timeline,
                    rationale=self._make_action_rationale(sentence, due_date, is_blocked),
                    step_order=idx,
                    estimated_minutes=self._estimate_minutes(sentence),
                    is_blocked=is_blocked,
                    dependency_summary=self._dependency_summary(sentence),
                    risk_level=risk_level,
                    unblocker=self._unblocker(sentence) if is_blocked else "",
                )
            )

        return self._sequence_actions(actions)

    def _is_done(self, action: ActionState) -> bool:
        return (action.status or "").lower() == "done"

    def _is_due_or_overdue(self, due_date: str | None) -> bool:
        if not due_date:
            return False
        try:
            return date.fromisoformat(due_date) <= date.today()
        except ValueError:
            return False

    def _choose_next_action(self, actions: list[ActionState]) -> ActionState:
        def rank(action: ActionState) -> tuple[int, int, int, int]:
            blocked_rank = 0 if action.is_blocked else 1
            due_rank = 0 if self._is_due_or_overdue(action.due_date) else 1
            risk_rank = {"high": 0, "medium": 1, "low": 2}.get(
                (action.risk_level or "").lower(), 1
            )
            return (blocked_rank, due_rank, risk_rank, action.step_order)

        return sorted(actions, key=rank)[0]

    def _execution_health(
        self,
        progress_percent: int,
        blocked_count: int,
        overdue_count: int,
        high_risk_count: int,
    ) -> str:
        if blocked_count or overdue_count:
            return "at_risk"
        if progress_percent == 0 and high_risk_count:
            return "needs_start"
        return "on_track"

    def _next_recommendation(self, action: ActionState) -> str:
        if action.is_blocked:
            unblocker = action.unblocker or "confirm the missing dependency or decision"
            return f"Unblock '{action.title}' first: {unblocker}"

        due_context = f" due {action.due_date}" if action.due_date else ""
        return (
            f"Do '{action.title}' next{due_context}. "
            f"It is {action.priority} priority and estimated at {action.estimated_minutes} minutes."
        )

    def _dedupe_candidates(self, candidates: List[str]) -> List[str]:
        seen: set[str] = set()
        unique: List[str] = []
        for candidate in candidates:
            key = re.sub(r"\W+", " ", candidate.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    def _strip_speaker(self, sentence: str) -> str:
        return re.sub(r"^[A-Za-z][A-Za-z .'-]{1,40}:\s*", "", sentence).strip()

    def _extract_owner(self, sentence: str) -> str:
        patterns = [
            r"\b([A-Z][a-z]+)\s+(?:will|should|must|needs to|need to|to)\b",
            r"\bassign(?:ed)?\s+to\s+([A-Z][a-z]+)\b",
            r"\bowner\s*(?:is|:)\s*([A-Z][a-z]+)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, sentence)
            if match:
                return match.group(1)
        return "Unassigned"

    def _extract_due_date(self, sentence: str, target_end_date: str | None) -> str | None:
        lowered = sentence.lower()
        today = date.today()
        if re.search(r"\btoday\b|\beod\b|\bend of day\b", lowered):
            return today.isoformat()
        if "tomorrow" in lowered:
            return (today + timedelta(days=1)).isoformat()

        weekday_offsets = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        for weekday, target_weekday in weekday_offsets.items():
            if re.search(fr"\b(?:by|before|on)?\s*{weekday}\b", lowered):
                offset = (target_weekday - today.weekday()) % 7
                offset = 7 if offset == 0 else offset
                return (today + timedelta(days=offset)).isoformat()

        explicit = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", sentence)
        if explicit:
            return explicit.group(1)

        month_day = re.search(
            r"\b(?:by|before|on)\s+((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})\b",
            lowered,
        )
        if month_day:
            return month_day.group(1).title()

        if re.search(r"\bdeadline\b|\bdue\b|\bby\b|\bbefore\b", lowered):
            return target_end_date

        return target_end_date if target_end_date and "target" in lowered else None

    def _is_blocked(self, sentence: str) -> bool:
        return bool(
            re.search(
                r"\b(blocked|waiting on|depends on|dependent on|need approval|needs approval|"
                r"once we have|after we get|after legal|after approval|cannot|can't|missing)\b",
                sentence.lower(),
            )
        )

    def _dependency_summary(self, sentence: str) -> str:
        patterns = [
            r"\bdepends on\s+(.+)",
            r"\bwaiting on\s+(.+)",
            r"\bafter\s+(.+)",
            r"\bonce\s+(.+)",
            r"\bblocked by\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, sentence, flags=re.I)
            if match:
                return self._trim_clause(match.group(1))
        return ""

    def _unblocker(self, sentence: str) -> str:
        dependency = self._dependency_summary(sentence)
        if dependency:
            return f"Confirm or obtain {dependency.lower()}."
        return "Identify the missing input, decision, or owner blocking this action."

    def _infer_risk(self, sentence: str, due_date: str | None, is_blocked: bool) -> str:
        lowered = sentence.lower()
        if is_blocked or re.search(r"\burgent|critical|risk|customer|launch|deadline|today|eod\b", lowered):
            return "high"
        if due_date or re.search(r"\bapproval|review|legal|security|finance|stakeholder\b", lowered):
            return "medium"
        return "low"

    def _infer_priority(
        self,
        sentence: str,
        idx: int,
        due_date: str | None,
        is_blocked: bool,
        risk_level: str,
    ) -> str:
        lowered = sentence.lower()
        if (
            is_blocked
            or risk_level == "high"
            or due_date
            or re.search(r"\bmust|urgent|critical|customer|launch|deadline|today|eod\b", lowered)
        ):
            return "high"
        if idx <= 3 or re.search(r"\bshould|follow up|prepare|update|review|decide\b", lowered):
            return "medium"
        return "low"

    def _infer_timeline_bucket(self, sentence: str, idx: int, due_date: str | None) -> str:
        lowered = sentence.lower()
        if re.search(r"\btoday\b|\beod\b|\bend of day\b", lowered):
            return "Today"
        if "tomorrow" in lowered:
            return "Tomorrow"
        if re.search(r"\bthis week\b|\bfriday\b|\bby\s+\w+day\b", lowered):
            return "This week"
        if re.search(r"\bnext week\b", lowered):
            return "Next week"
        if due_date:
            return "This week"
        return self._timeline_bucket_for_index(idx)

    def _estimate_minutes(self, sentence: str) -> int:
        lowered = sentence.lower()
        if re.search(r"\bquick|confirm|reply|send|follow up|approve\b", lowered):
            return 15
        if re.search(r"\breview|update|revise|prepare|draft|decide\b", lowered):
            return 45
        if re.search(r"\bbuild|implement|complete|deliver|migrate|analyze|launch\b", lowered):
            return 90
        return 30

    def _make_action_rationale(self, sentence: str, due_date: str | None, is_blocked: bool) -> str:
        pieces = ["Transcript language indicates this is required follow-up work."]
        if due_date:
            pieces.append(f"Timing is constrained by {due_date}.")
        if is_blocked:
            pieces.append("The wording shows a dependency or missing input that must be unblocked.")
        return " ".join(pieces)

    def _sequence_actions(self, actions: List[PlannedAction]) -> List[PlannedAction]:
        def rank(action: PlannedAction) -> tuple[int, int, int]:
            title = action.title.lower()
            dependency_first = 0 if re.search(r"\bdecide|approve|confirm|review|assign|unblock\b", title) else 1
            priority_rank = {"high": 0, "medium": 1, "low": 2}.get(action.priority, 1)
            blocked_rank = 0 if action.is_blocked else 1
            return (dependency_first, priority_rank, blocked_rank)

        sequenced = sorted(actions, key=rank)
        for idx, action in enumerate(sequenced, start=1):
            action.step_order = idx
        return sequenced

    def _trim_clause(self, value: str) -> str:
        value = re.split(
            r"[.;!?]|\band\s+(?:we\s+)?(?:need|should|must|will)\b",
            value,
            maxsplit=1,
            flags=re.I,
        )[0]
        return value.strip().strip(",")[:140]

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
        sentence = self._strip_speaker(sentence).strip().rstrip(".")
        blocked_match = re.search(r"^(?:the\s+)?(.+?)\s+is\s+blocked\s+by\s+(.+)$", sentence, flags=re.I)
        if blocked_match:
            subject = blocked_match.group(1).strip()
            blocker = self._trim_clause(blocked_match.group(2))
            return f"Unblock {subject} by resolving {blocker}"

        sentence = re.sub(
            r"^(we need to|need to|we should|should|must|please|action item:?)\s+",
            "",
            sentence,
            flags=re.I,
        )
        sentence = re.sub(
            r"^[A-Z][a-z]+\s+(?:will|should|must|needs to|need to|to)\s+",
            "",
            sentence,
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

    def _normalize_risk(self, value: str) -> str:
        lowered = (value or "").strip().lower()
        if lowered in {"high", "medium", "low"}:
            return lowered
        return "medium"

    def _clean_optional(self, value: Any) -> str | None:
        if value in {None, "", "null"}:
            return None
        return str(value).strip()
