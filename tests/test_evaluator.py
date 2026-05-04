from screenmind_todo.services.evaluator import PlanEvaluator
from screenmind_todo.services.meeting_planner import MeetingPlannerService


def test_plan_evaluator_scores_valid_plan() -> None:
    planner = MeetingPlannerService()
    evaluator = PlanEvaluator()
    transcript = (
        "We need to send the client update by Thursday. "
        "Abhinav should revise the deck. "
        "Someone needs to prepare the implementation timeline."
    )
    plan = planner._build_plan_fallback(
        title="Weekly Sync",
        transcript=transcript,
        target_end_date="2026-04-25",
    )

    result = evaluator.evaluate(transcript, plan)

    assert result.total_score >= 50
    assert result.actionability_score > 0
    assert result.timeline_score > 0
