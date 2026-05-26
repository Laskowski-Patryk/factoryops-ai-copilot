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


def test_delete_uploaded_dataset():
    response = client.post(
        "/api/datasets",
        files={
            "file": (
                "delete_me.csv",
                "line,date,target,actual\nA,2026-05-25,100,88\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    dataset_id = response.json()["id"]

    assert client.get(f"/api/datasets/{dataset_id}").status_code == 200

    deleted = client.delete(f"/api/datasets/{dataset_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 404

    deleted_again = client.delete(f"/api/datasets/{dataset_id}")
    assert deleted_again.status_code == 404


def test_uploaded_dataset_with_arbitrary_columns_gets_generic_cards():
    response = client.post(
        "/api/datasets",
        files={
            "file": (
                "custom_columns.csv",
                "batch,widget_score,shift_loss\nA1,72,8\nA2,81,5\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    dataset_id = response.json()["id"]

    run = client.post(
        "/api/runs",
        json={
            "prompt": "Analyze this custom operations file",
            "provider": "mock",
            "dataset_id": dataset_id,
        },
    )
    assert run.status_code == 200
    cards = run.json()["dashboard_spec"]["cards"]
    labels = {card["label"] for card in cards}
    assert "Widget Score" in labels
    assert "Shift Loss" in labels


def test_stream_mock_run_returns_tool_events():
    response = client.post(
        "/api/runs/stream",
        json={
            "prompt": "Why did Line A underperform yesterday?",
            "provider": "mock",
            "conversation_id": "test-thread",
        },
    )
    assert response.status_code == 200
    text = response.text
    assert "tool_call" in text
    assert "run_complete" in text
