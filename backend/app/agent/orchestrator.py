from app.data.factory_data import default_date
from app.llm.providers import BaseProvider
from app.models.schemas import RunRequest, RunResult
from app.tools.registry import ToolRegistry


class FactoryOpsAgent:
    def __init__(self, registry: ToolRegistry, provider: BaseProvider) -> None:
        self.registry = registry
        self.provider = provider

    def run(self, request: RunRequest) -> RunResult:
        day = request.date or default_date()
        trace = []

        kpis, call = self.registry.execute("get_production_kpis", line=request.line, day=day)
        trace.append(call)
        downtime, call = self.registry.execute("get_downtime_events", line=request.line, day=day)
        trace.append(call)
        comparison, call = self.registry.execute(
            "compare_line_performance", line=request.line, day=day, days_back=7
        )
        trace.append(call)
        sop_matches, call = self.registry.execute(
            "search_sop", query="sensor fault escalation repeated downtime"
        )
        trace.append(call)
        report, call = self.registry.execute(
            "generate_shift_report",
            line=request.line,
            date=day,
            kpis=kpis.model_dump(),
            downtime=[event.model_dump() for event in downtime],
        )
        trace.append(call)
        ticket, call = self.registry.execute(
            "create_maintenance_ticket",
            line=request.line,
            issue="Repeated sensor faults at A-CELL-04 causing output loss",
            priority="high",
            evidence=[event.evidence for event in downtime if "sensor" in event.category][:3],
        )
        trace.append(call)
        flow, call = self.registry.execute(
            "create_power_automate_flow_spec",
            trigger="When downtime category sensor_fault appears twice in one shift",
            actions=[
                "Post Teams alert to operations and maintenance channel",
                "Create Planner task linked to the mock ticket",
                "Email shift report to production leadership",
            ],
            target_users=["Shift Lead", "Maintenance Planner", "Quality Engineer"],
        )
        trace.append(call)

        root_cause = (
            "Repeated Line A sensor faults, concentrated at A-CELL-04 and the infeed station, "
            "created abnormal downtime and recovery starvation."
        )
        actions = [
            "Inspect, clean, align, and recalibrate A-CELL-04 and infeed sensors.",
            "Validate PLC fault timestamps and cable continuity with maintenance controls owner.",
            "Run first-hour containment and confirm OEE recovery before closing the ticket.",
            "Activate the escalation flow when repeated sensor faults occur in one shift.",
        ]
        llm = self.provider.complete(
            request.prompt,
            {
                "kpis": kpis,
                "downtime": downtime,
                "comparison": comparison,
                "sop_matches": sop_matches,
                "root_cause": root_cause,
                "actions": actions,
            },
        )
        return RunResult(
            prompt=request.prompt,
            line=request.line,
            date=day,
            provider=self.provider.name,
            final_answer=llm.text,
            root_cause=root_cause,
            recommended_actions=actions,
            kpis=kpis,
            downtime=downtime,
            comparison=comparison,
            sop_matches=sop_matches,
            shift_report=report,
            maintenance_ticket=ticket,
            flow_spec=flow,
            tool_trace=trace,
            usage=llm.usage,
        )
