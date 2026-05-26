from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ProviderName = Literal["mock", "openrouter"]


class RunRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    line: str = "Line A"
    date: str | None = None
    provider: ProviderName | None = None
    api_key: str | None = Field(default=None, max_length=400)
    model: str | None = Field(default=None, max_length=120)
    dataset_id: str | None = None
    conversation_id: str | None = None


class KpiSnapshot(BaseModel):
    line: str
    date: str
    target_units: int
    actual_units: int
    oee: float
    scrap_rate: float
    downtime_minutes: int


class DowntimeEvent(BaseModel):
    line: str
    date: str
    start_time: str
    duration_minutes: int
    category: str
    reason: str
    station: str
    evidence: str


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any]
    status: Literal["ok", "error"]
    duration_ms: int
    result_preview: str


class MaintenanceTicket(BaseModel):
    id: str
    line: str
    issue: str
    priority: Literal["low", "medium", "high", "critical"]
    evidence: list[str]
    status: str = "mock-created"


class FlowSpec(BaseModel):
    name: str
    trigger: str
    actions: list[str]
    target_users: list[str]
    connectors: list[str]


class ShiftReport(BaseModel):
    title: str
    summary: str
    metrics: dict[str, Any]
    downtime_summary: str
    recommended_actions: list[str]


class UsageMetrics(BaseModel):
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int


class DashboardCard(BaseModel):
    label: str
    value: str
    detail: str = ""
    tone: Literal["signal", "warning", "danger", "neutral"] = "neutral"


class DashboardTable(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str]]


class DashboardSpec(BaseModel):
    title: str
    cards: list[DashboardCard] = []
    insights: list[str] = []
    tables: list[DashboardTable] = []
    chart_hints: list[dict[str, Any]] = []


class AgentOutput(BaseModel):
    markdown: str
    summary: str
    root_cause: str
    recommended_actions: list[str]
    dashboard: DashboardSpec


class DatasetSummary(BaseModel):
    id: str
    name: str
    kind: Literal["csv", "excel", "sqlite"]
    created_at: datetime
    tables: list[str]
    row_count: int
    columns: list[str]


class RunResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt: str
    line: str
    date: str
    provider: str
    final_answer: str
    answer_markdown: str = ""
    dashboard_spec: DashboardSpec = Field(
        default_factory=lambda: DashboardSpec(title="FactoryOps Run")
    )
    dataset_id: str | None = None
    conversation_id: str | None = None
    root_cause: str
    recommended_actions: list[str]
    kpis: KpiSnapshot
    downtime: list[DowntimeEvent]
    comparison: dict[str, Any]
    sop_matches: list[dict[str, str]]
    shift_report: ShiftReport
    maintenance_ticket: MaintenanceTicket
    flow_spec: FlowSpec
    tool_trace: list[ToolCall]
    usage: UsageMetrics
