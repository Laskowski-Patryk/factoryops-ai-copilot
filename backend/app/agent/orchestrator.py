from collections.abc import Callable

from app.data.factory_data import default_date
from app.llm.providers import BaseProvider
from app.models.schemas import RunRequest, RunResult
from app.tools.registry import ToolRegistry


class FactoryOpsAgent:
    def __init__(
        self,
        registry: ToolRegistry,
        provider: BaseProvider,
        history: list[RunResult] | None = None,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.history = history or []

    def run(
        self,
        request: RunRequest,
        progress: Callable[[dict], None] | None = None,
    ) -> RunResult:
        day = request.date or default_date()
        trace = []

        def emit(event: dict) -> None:
            if progress:
                progress(event)

        def execute(name: str, **kwargs):
            emit({"type": "tool_started", "name": name, "args": kwargs})
            result, call = self.registry.execute(name, **kwargs)
            trace.append(call)
            emit({"type": "tool_call", "tool": call.model_dump(mode="json")})
            return result

        emit({"type": "status", "message": "Planning tool sequence"})

        dataset_metrics = None
        dataset_profile = None
        if request.dataset_id:
            dataset_profile = execute("inspect_uploaded_dataset", dataset_id=request.dataset_id)
            dataset_metrics = execute(
                "infer_uploaded_factory_metrics", dataset_id=request.dataset_id
            )

        kpis = execute("get_production_kpis", line=request.line, day=day)
        downtime = execute("get_downtime_events", line=request.line, day=day)
        comparison = execute(
            "compare_line_performance", line=request.line, day=day, days_back=7
        )
        sop_matches = execute(
            "search_sop", query="sensor fault escalation repeated downtime"
        )
        report = execute(
            "generate_shift_report",
            line=request.line,
            date=day,
            kpis=kpis.model_dump(),
            downtime=[event.model_dump() for event in downtime],
        )
        ticket = execute(
            "create_maintenance_ticket",
            line=request.line,
            issue="Repeated sensor faults at A-CELL-04 causing output loss",
            priority="high",
            evidence=[event.evidence for event in downtime if "sensor" in event.category][:3],
        )
        flow = execute(
            "create_power_automate_flow_spec",
            trigger="When downtime category sensor_fault appears twice in one shift",
            actions=[
                "Post Teams alert to operations and maintenance channel",
                "Create Planner task linked to the mock ticket",
                "Email shift report to production leadership",
            ],
            target_users=["Shift Lead", "Maintenance Planner", "Quality Engineer"],
        )

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
        emit({"type": "status", "message": f"Calling {self.provider.name}"})
        llm = self.provider.complete(
            request.prompt,
            {
                "dataset_id": request.dataset_id,
                "dataset_profile": dataset_profile,
                "dataset_metrics": dataset_metrics,
                "conversation_history": [
                    {
                        "prompt": run.prompt,
                        "summary": run.dashboard_spec.title,
                        "answer": run.final_answer[:500],
                    }
                    for run in self.history[-5:]
                ],
                "kpis": kpis,
                "downtime": downtime,
                "comparison": comparison,
                "sop_matches": sop_matches,
                "root_cause": root_cause,
                "actions": actions,
            },
            registry=self.registry,
        )
        trace.extend(llm.tool_trace)
        for call in llm.tool_trace:
            emit({"type": "tool_call", "tool": call.model_dump(mode="json")})
        answer = llm.output
        return RunResult(
            prompt=request.prompt,
            line=request.line,
            date=day,
            provider=self.provider.name,
            final_answer=answer.markdown,
            answer_markdown=answer.markdown,
            dashboard_spec=answer.dashboard,
            dataset_id=request.dataset_id,
            conversation_id=request.conversation_id,
            root_cause=answer.root_cause or root_cause,
            recommended_actions=answer.recommended_actions or actions,
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
