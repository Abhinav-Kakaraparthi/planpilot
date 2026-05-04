from types import SimpleNamespace

from screenmind_todo.services.meeting_planner import MeetingPlannerService


def test_meeting_planner_fallback_returns_plan() -> None:
    planner = MeetingPlannerService()
    plan = planner._build_plan_fallback(
        title="Weekly Sync",
        transcript=(
            "We need to send the client update by Thursday. "
            "Abhinav should revise the deck. "
            "Someone needs to prepare the implementation timeline."
        ),
        target_end_date="2026-04-25",
    )

    assert plan.summary
    assert plan.decisions
    assert plan.priorities_overview
    assert len(plan.actions) >= 1


def test_meeting_actions_have_required_fields() -> None:
    planner = MeetingPlannerService()
    plan = planner._build_plan_fallback(
        title="Project Meeting",
        transcript="We must send the report. We should update the slides.",
        target_end_date="2026-04-25",
    )

    for action in plan.actions:
        assert action.title
        assert action.owner
        assert action.priority in {"high", "medium", "low"}
        assert action.timeline_bucket in {
            "Today",
            "Tomorrow",
            "This week",
            "Next week",
            "Later",
        }
        assert action.step_order >= 1
        assert action.estimated_minutes > 0


def test_timeline_bucket_ordering() -> None:
    planner = MeetingPlannerService()

    assert planner._timeline_bucket_for_index(1) == "Today"
    assert planner._timeline_bucket_for_index(2) == "Tomorrow"
    assert planner._timeline_bucket_for_index(3) == "This week"
    assert planner._timeline_bucket_for_index(4) == "This week"
    assert planner._timeline_bucket_for_index(5) == "Next week"
    assert planner._timeline_bucket_for_index(6) == "Later"


def test_priority_assignment() -> None:
    planner = MeetingPlannerService()
    plan = planner._build_plan_fallback(
        title="Deadline Meeting",
        transcript=(
            "We need to send the report. "
            "We should update the deck. "
            "We must prepare the timeline. "
            "We need to follow up later."
        ),
        target_end_date="2026-04-25",
    )

    priorities = [action.priority for action in plan.actions]
    assert "high" in priorities
    assert all(priority in {"high", "medium", "low"} for priority in priorities)


def test_empty_or_weak_transcript_still_returns_safe_plan() -> None:
    planner = MeetingPlannerService()
    plan = planner._build_plan_fallback(
        title="Weak Meeting",
        transcript="General discussion happened.",
        target_end_date=None,
    )

    assert plan.summary
    assert len(plan.actions) >= 1


def test_fallback_planner_detects_blockers_risk_and_unblockers() -> None:
    planner = MeetingPlannerService()

    plan = planner._build_plan_fallback(
        title="Launch sync",
        transcript=(
            "Maya will prepare the launch email by tomorrow. "
            "The migration is blocked by finance approval and we need to follow up today. "
            "Jordan should update the customer FAQ after legal review."
        ),
        target_end_date="2026-05-08",
    )

    blocked_actions = [action for action in plan.actions if action.is_blocked]

    assert blocked_actions
    assert blocked_actions[0].risk_level == "high"
    assert "finance approval" in blocked_actions[0].dependency_summary.lower()
    assert blocked_actions[0].unblocker


def test_fallback_planner_extracts_owner_due_date_and_effort() -> None:
    planner = MeetingPlannerService()

    plan = planner._build_plan_fallback(
        title="Sales follow-up",
        transcript="Priya will send the enterprise pricing follow up by Friday.",
        target_end_date=None,
    )

    action = plan.actions[0]

    assert action.owner == "Priya"
    assert action.title.startswith("Send")
    assert action.due_date is not None
    assert action.timeline_bucket == "This week"
    assert action.estimated_minutes == 15
    assert action.priority == "high"


def test_fallback_planner_sequences_dependency_work_first() -> None:
    planner = MeetingPlannerService()

    plan = planner._build_plan_fallback(
        title="Sprint planning",
        transcript=(
            "We should implement the billing dashboard. "
            "We need to decide the launch scope before engineering starts."
        ),
        target_end_date=None,
    )

    assert plan.actions[0].title.startswith("Decide")


def test_adapt_plan_state_prioritizes_blocked_open_work() -> None:
    planner = MeetingPlannerService()

    state = planner.adapt_plan_state(
        [
            SimpleNamespace(
                title="Send launch recap",
                priority="high",
                due_date=None,
                timeline_bucket="Today",
                status="done",
                step_order=1,
                estimated_minutes=15,
                is_blocked=False,
                dependency_summary="",
                risk_level="high",
                unblocker="",
            ),
            SimpleNamespace(
                title="Unblock billing migration",
                priority="high",
                due_date=None,
                timeline_bucket="Today",
                status="open",
                step_order=2,
                estimated_minutes=45,
                is_blocked=True,
                dependency_summary="finance approval",
                risk_level="high",
                unblocker="Confirm finance approval.",
            ),
        ]
    )

    assert state.progress_percent == 50
    assert state.execution_health == "at_risk"
    assert state.next_recommendation.startswith("Unblock")
    assert "1/2 actions complete" in state.adaptation_note


def test_adapt_plan_state_marks_complete_when_all_done() -> None:
    planner = MeetingPlannerService()

    state = planner.adapt_plan_state(
        [
            SimpleNamespace(
                title="Send launch recap",
                priority="high",
                due_date=None,
                timeline_bucket="Today",
                status="done",
                step_order=1,
                estimated_minutes=15,
                is_blocked=False,
                dependency_summary="",
                risk_level="high",
                unblocker="",
            )
        ]
    )

    assert state.progress_percent == 100
    assert state.execution_health == "complete"
    assert "complete" in state.next_recommendation.lower()
