from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

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
        provider = build_provider_from_request(
            settings,
            request.provider,
            request.api_key,
            request.model,
        )
        agent = FactoryOpsAgent(build_registry(dataset_service), provider)
        return repo.save(agent.run(request))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Provider run failed: {exc}",
        ) from exc


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
