from screenmind_todo.services.analyzer import ActivityAnalyzer, ActivityContext


def test_analyzer_suggests_bugfix_task() -> None:
    analyzer = ActivityAnalyzer()
    result = analyzer.analyze(
        ActivityContext(
            window_title="main.py - Traceback in terminal",
            app_name="Code",
            ocr_text="ValueError exception stack trace failed",
        )
    )

    titles = [task["title"] for task in result.suggested_tasks]
    assert "Fix the current application error" in titles
    assert result.confidence >= 85

