import json
from queue import Queue
from threading import Thread
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse

from app.agent.orchestrator import FactoryOpsAgent
from app.core.config import Settings, get_settings
from app.datasets.service import DatasetService
from app.db.repository import RunRepository
from app.llm.providers import build_provider, build_provider_from_request
from app.models.schemas import DatasetSummary, RunRequest, RunResult
from app.tools.factory_tools import build_registry

router = APIRouter(prefix="/api")


def get_repo(settings: Settings = Depends(get_settings)) -> RunRepository:
    return RunRepository(settings.database_path, settings.runs_jsonl_path)


def get_dataset_service(settings: Settings = Depends(get_settings)) -> DatasetService:
    return DatasetService(settings.uploads_dir)


def get_agent(settings: Settings = Depends(get_settings)) -> FactoryOpsAgent:
    return FactoryOpsAgent(build_registry(), build_provider(settings))


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config")
def config(settings: Settings = Depends(get_settings)) -> dict:
    return settings.masked_provider_config


@router.post("/runs", response_model=RunResult)
def create_run(
    request: RunRequest,
    repo: RunRepository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> RunResult:
    try:
        if not request.conversation_id:
            request = request.model_copy(update={"conversation_id": str(uuid4())})
        history = repo.list_by_conversation(request.conversation_id)
        provider = build_provider_from_request(
            settings,
            request.provider,
            request.api_key,
            request.model,
        )
        agent = FactoryOpsAgent(build_registry(dataset_service), provider, history=history)
        return repo.save(agent.run(request))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Provider run failed: {exc}",
        ) from exc


@router.post("/runs/stream")
def stream_run(
    request: RunRequest,
    repo: RunRepository = Depends(get_repo),
    settings: Settings = Depends(get_settings),
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> StreamingResponse:
    if not request.conversation_id:
        request = request.model_copy(update={"conversation_id": str(uuid4())})

    def event_stream():
        queue: Queue[dict | None] = Queue()

        def publish(event: dict) -> None:
            queue.put(event)

        def worker() -> None:
            try:
                publish({"type": "status", "message": "Starting FactoryOps agent"})
                history = repo.list_by_conversation(request.conversation_id or "")
                provider = build_provider_from_request(
                    settings,
                    request.provider,
                    request.api_key,
                    request.model,
                )
                agent = FactoryOpsAgent(
                    build_registry(dataset_service),
                    provider,
                    history=history,
                )
                run = repo.save(agent.run(request, progress=publish))
                publish({"type": "run_complete", "run": run.model_dump(mode="json")})
            except Exception as exc:
                publish({"type": "error", "message": f"Provider run failed: {exc}"})
            finally:
                queue.put(None)

        Thread(target=worker, daemon=True).start()
        while True:
            event = queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs", response_model=list[RunResult])
def list_runs(repo: RunRepository = Depends(get_repo)) -> list[RunResult]:
    return repo.list()


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str, repo: RunRepository = Depends(get_repo)) -> RunResult:
    run = repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/datasets", response_model=DatasetSummary)
def upload_dataset(
    file: UploadFile = File(...),
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> DatasetSummary:
    try:
        return dataset_service.upload(file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/datasets", response_model=list[DatasetSummary])
def list_datasets(
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> list[DatasetSummary]:
    return dataset_service.list()


@router.get("/datasets/{dataset_id}", response_model=DatasetSummary)
def get_dataset(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> DatasetSummary:
    dataset = dataset_service.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/datasets/{dataset_id}/profile")
def get_dataset_profile(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> dict:
    return dataset_service.profile(dataset_id)


@router.delete("/datasets/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> Response:
    try:
        deleted = dataset_service.delete(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return Response(status_code=204)
