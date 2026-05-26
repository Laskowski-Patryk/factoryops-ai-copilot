from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def override_settings():
    settings = get_settings()
    settings.database_path = "data/test-factoryops.sqlite3"
    settings.runs_jsonl_path = "data/test-runs.jsonl"
    settings.uploads_dir = "data/test-uploads"
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
    assert body["answer_markdown"].startswith("##")
    assert body["dashboard_spec"]["cards"]
    assert len(body["tool_trace"]) >= 7


def test_upload_csv_and_run_against_dataset():
    response = client.post(
        "/api/datasets",
        files={
            "file": (
                "line_metrics.csv",
                "line,date,target,actual,oee,downtime,reason\nA,2026-05-25,100,82,0.71,44,sensor\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    dataset = response.json()
    assert dataset["row_count"] == 1

    run = client.post(
        "/api/runs",
        json={
            "prompt": "Build a dashboard from this uploaded file",
            "provider": "mock",
            "dataset_id": dataset["id"],
        },
    )
    assert run.status_code == 200
    body = run.json()
    assert body["dataset_id"] == dataset["id"]
    assert "Uploaded Dataset" in body["answer_markdown"]
