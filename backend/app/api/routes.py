from fastapi import APIRouter, Depends, HTTPException

from app.agent.orchestrator import FactoryOpsAgent
from app.core.config import Settings, get_settings
from app.db.repository import RunRepository
from app.llm.providers import build_provider
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
    agent: FactoryOpsAgent = Depends(get_agent),
    repo: RunRepository = Depends(get_repo),
) -> RunResult:
    return repo.save(agent.run(request))


@router.get("/runs", response_model=list[RunResult])
def list_runs(repo: RunRepository = Depends(get_repo)) -> list[RunResult]:
    return repo.list()


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str, repo: RunRepository = Depends(get_repo)) -> RunResult:
    run = repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
