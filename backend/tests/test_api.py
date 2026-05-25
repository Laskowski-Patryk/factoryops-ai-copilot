from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def override_settings():
    settings = get_settings()
    settings.database_path = "data/test-factoryops.sqlite3"
    settings.runs_jsonl_path = "data/test-runs.jsonl"
    settings.llm_provider = "mock"
    return settings


app.dependency_overrides[get_settings] = override_settings
client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_mock_run():
    response = client.post(
        "/api/runs",
        json={"prompt": "Why did Line A underperform yesterday and what should we do next?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert "sensor faults" in body["final_answer"]
    assert len(body["tool_trace"]) >= 7
