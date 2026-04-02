from fastapi.testclient import TestClient

from app.main import app
from app.services.generation_service import generation_service


client = TestClient(app)


def test_generation_trigger_and_status(monkeypatch):
    def fake_run_task(task_id: str):
        generation_service._update_task(task_id, "succeeded", "mock completed")

    monkeypatch.setattr(generation_service, "run_task", fake_run_task)

    trigger_response = client.post(
        "/api/v1/generation/trigger",
        json={"rss_source": "default", "topic": "daily-news"},
    )
    assert trigger_response.status_code == 200
    trigger_payload = trigger_response.json()
    assert trigger_payload["status"] in {"queued", "succeeded"}
    task_id = trigger_payload["task_id"]

    status_response = client.get(f"/api/v1/generation/{task_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["task_id"] == task_id
    assert status_payload["status"] == "succeeded"
