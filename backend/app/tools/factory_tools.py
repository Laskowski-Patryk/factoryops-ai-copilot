import re
from uuid import uuid4

from app.data.factory_data import compare_performance, get_downtime, get_kpis, search_sops
from app.models.schemas import FlowSpec, MaintenanceTicket, ShiftReport
from app.tools.registry import ToolRegistry, ToolSpec

BLOCKED_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|PRAGMA|ATTACH|DETACH|REPLACE|CREATE)\b",
    re.I,
)


def query_factory_db(sql: str) -> list[dict]:
    normalized = sql.strip()
    if not normalized.lower().startswith("select") or BLOCKED_SQL.search(normalized):
        raise ValueError(
            "Only read-only SELECT statements are allowed in the demo factory database."
        )
    return [{"note": "Demo SELECT accepted", "sql": normalized[:160]}]


def generate_shift_report(line: str, date: str, kpis: dict, downtime: list[dict]) -> ShiftReport:
    top_categories = sorted({event["category"] for event in downtime})
    return ShiftReport(
        title=f"{line} Shift Performance Report - {date}",
        summary=(
            f"{line} produced {kpis['actual_units']} of {kpis['target_units']} target units "
            f"with OEE {kpis['oee']:.1%} and {kpis['downtime_minutes']} downtime minutes."
        ),
        metrics=kpis,
        downtime_summary=f"Primary loss categories: {', '.join(top_categories)}.",
        recommended_actions=[
            "Inspect and recalibrate A-CELL-04 sensors before next shift start.",
            "Review PLC fault trend with maintenance and controls owner.",
            "Add first-hour quality containment until stable restart is confirmed.",
        ],
    )


def create_maintenance_ticket(
    line: str, issue: str, priority: str, evidence: list[str]
) -> MaintenanceTicket:
    return MaintenanceTicket(
        id=f"MOCK-{str(uuid4())[:8].upper()}",
        line=line,
        issue=issue,
        priority=priority,
        evidence=evidence,
    )


def create_power_automate_flow_spec(
    trigger: str, actions: list[str], target_users: list[str]
) -> FlowSpec:
    return FlowSpec(
        name="Line A Sensor Fault Escalation",
        trigger=trigger,
        actions=actions,
        target_users=target_users,
        connectors=["SharePoint", "Teams", "Outlook", "Planner"],
    )


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="get_production_kpis",
            description="Fetch line KPI snapshot.",
            input_schema={"line": "str", "date": "YYYY-MM-DD"},
        ),
        get_kpis,
    )
    registry.register(
        ToolSpec(
            name="get_downtime_events",
            description="Fetch downtime events.",
            input_schema={"line": "str", "date": "YYYY-MM-DD"},
        ),
        get_downtime,
    )
    registry.register(
        ToolSpec(
            name="compare_line_performance",
            description="Compare against previous days.",
            input_schema={"line": "str", "date": "YYYY-MM-DD", "days_back": "int"},
        ),
        compare_performance,
    )
    registry.register(
        ToolSpec(
            name="search_sop",
            description="Search SOP documents.",
            input_schema={"query": "str"},
        ),
        search_sops,
    )
    registry.register(
        ToolSpec(
            name="generate_shift_report",
            description="Create a shift report.",
            input_schema={
                "line": "str",
                "date": "YYYY-MM-DD",
                "kpis": "object",
                "downtime": "array",
            },
        ),
        generate_shift_report,
    )
    registry.register(
        ToolSpec(
            name="create_maintenance_ticket",
            description="Create a mock maintenance ticket.",
            input_schema={
                "line": "str",
                "issue": "str",
                "priority": "str",
                "evidence": "array",
            },
        ),
        create_maintenance_ticket,
    )
    registry.register(
        ToolSpec(
            name="create_power_automate_flow_spec",
            description="Draft automation flow specification.",
            input_schema={
                "trigger": "str",
                "actions": "array",
                "target_users": "array",
            },
        ),
        create_power_automate_flow_spec,
    )
    registry.register(
        ToolSpec(
            name="query_factory_db",
            description="Run safe SELECT-only demo query.",
            input_schema={"sql": "SELECT ..."},
        ),
        query_factory_db,
    )
    return registry
