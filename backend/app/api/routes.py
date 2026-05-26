from fastapi import APIRouter, Depends, HTTPException

from app.agent.orchestrator import FactoryOpsAgent
from app.core.config import Settings, get_settings
from app.db.repository import RunRepository
from app.llm.providers import build_provider, build_provider_from_request
from app.models.schemas import RunRequest, RunResult
from app.tools.factory_tools import build_registry

router = APIRouter(prefix="/api")


def get_repo(settings: Settings = Depends(get_settings)) -> RunRepository:
    return RunRepository(settings.database_path, settings.runs_jsonl_path)


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
) -> RunResult:
    try:
        provider = build_provider_from_request(
            settings,
            request.provider,
            request.api_key,
            request.model,
        )
        agent = FactoryOpsAgent(build_registry(), provider)
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
