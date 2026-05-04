from fastapi.testclient import TestClient

from screenmind_todo.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_meeting_plan() -> None:
    payload = {
        "title": "Weekly project sync",
        "transcript": (
            "We need to send the client update by Thursday. "
            "Abhinav should revise the deck. "
            "Someone needs to prepare the implementation timeline."
        ),
        "target_end_date": "2026-04-25",
    }

    response = client.post("/api/meetings/plan", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"]
    assert data["title"] == payload["title"]
    assert data["summary"]
    assert data["decisions"]
    assert data["priorities_overview"]
    assert len(data["actions"]) >= 1


def test_list_meetings() -> None:
    response = client.get("/api/meetings")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_dashboard_endpoint() -> None:
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "activities" in data
