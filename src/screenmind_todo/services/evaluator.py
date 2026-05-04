from __future__ import annotations

from dataclasses import dataclass
from typing import List

from screenmind_todo.services.meeting_planner import MeetingPlan


@dataclass
class EvaluationResult:
    total_score: float
    summary_score: float
    actionability_score: float
    priority_score: float
    timeline_score: float
    coverage_score: float
    issues: List[str]


class PlanEvaluator:
    def evaluate(self, transcript: str, plan: MeetingPlan) -> EvaluationResult:
        issues: List[str] = []
        summary_score = self._score_summary(plan, issues)
        actionability_score = self._score_actionability(plan, issues)
        priority_score = self._score_priorities(plan, issues)
        timeline_score = self._score_timeline(plan, issues)
        coverage_score = self._score_coverage(transcript, plan, issues)
        total_score = round(
            (
                summary_score * 0.20
                + actionability_score * 0.30
                + priority_score * 0.20
                + timeline_score * 0.15
                + coverage_score * 0.15
            ),
            2,
        )

        return EvaluationResult(
            total_score=total_score,
            summary_score=summary_score,
            actionability_score=actionability_score,
            priority_score=priority_score,
            timeline_score=timeline_score,
            coverage_score=coverage_score,
            issues=issues,
        )

    def _score_summary(self, plan: MeetingPlan, issues: List[str]) -> float:
        if not plan.summary:
            issues.append("Missing summary.")
            return 0.0
        if len(plan.summary.split()) < 10:
            issues.append("Summary is too short.")
            return 50.0
        return 100.0

    def _score_actionability(self, plan: MeetingPlan, issues: List[str]) -> float:
        if not plan.actions:
            issues.append("No action items generated.")
            return 0.0

        score = 100.0
        for action in plan.actions:
            if len(action.title.split()) < 2:
                score -= 10
                issues.append(f"Action title too vague: {action.title}")
            if not action.rationale:
                score -= 5
                issues.append(f"Missing rationale for: {action.title}")

        return max(score, 0.0)

    def _score_priorities(self, plan: MeetingPlan, issues: List[str]) -> float:
        if not plan.actions:
            return 0.0

        valid = {"high", "medium", "low"}
        score = 100.0
        for action in plan.actions:
            if action.priority not in valid:
                score -= 20
                issues.append(f"Invalid priority: {action.priority}")

        if not any(action.priority == "high" for action in plan.actions):
            score -= 15
            issues.append("No high-priority action found.")

        return max(score, 0.0)

    def _score_timeline(self, plan: MeetingPlan, issues: List[str]) -> float:
        valid = {"Today", "Tomorrow", "This week", "Next week", "Later"}
        score = 100.0
        for action in plan.actions:
            if action.timeline_bucket not in valid:
                score -= 20
                issues.append(f"Invalid timeline bucket: {action.timeline_bucket}")
            if action.estimated_minutes <= 0:
                score -= 10
                issues.append(f"Invalid estimate for: {action.title}")

        return max(score, 0.0)

    def _score_coverage(
        self,
        transcript: str,
        plan: MeetingPlan,
        issues: List[str],
    ) -> float:
        transcript_lower = transcript.lower()
        action_text = " ".join(action.title.lower() for action in plan.actions)
        trigger_words = [
            "need to",
            "should",
            "must",
            "send",
            "prepare",
            "update",
            "complete",
            "follow up",
            "submit",
        ]
        triggers_found = [word for word in trigger_words if word in transcript_lower]
        if not triggers_found:
            return 80.0

        covered = 0
        for word in triggers_found:
            simplified = word.replace("need to", "").replace("should", "").strip()
            if simplified and simplified in action_text:
                covered += 1

        coverage = covered / max(len(triggers_found), 1)
        if coverage < 0.4:
            issues.append("Action items may not cover enough transcript commitments.")

        return round(coverage * 100, 2)
