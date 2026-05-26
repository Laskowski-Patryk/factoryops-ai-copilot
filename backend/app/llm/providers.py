import json
import re
from time import perf_counter
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.models.schemas import AgentOutput, DashboardSpec, ToolCall, UsageMetrics
from app.tools.registry import ToolRegistry, ToolSpec


class LLMResponse(BaseModel):
    output: AgentOutput
    usage: UsageMetrics
    tool_trace: list[ToolCall] = []

    @property
    def text(self) -> str:
        return self.output.markdown


class BaseProvider:
    name = "base"
    model = "none"

    def complete(
        self,
        prompt: str,
        context: dict[str, Any],
        registry: ToolRegistry | None = None,
    ) -> LLMResponse:
        raise NotImplementedError


class MockProvider(BaseProvider):
    name = "mock"
    model = "deterministic-factoryops-v2"

    def complete(
        self,
        prompt: str,
        context: dict[str, Any],
        registry: ToolRegistry | None = None,
    ) -> LLMResponse:
        started = perf_counter()
        output = build_deterministic_output(prompt, context)
        latency = int((perf_counter() - started) * 1000) + 18
        tokens = max(100, len(prompt.split()) + 170)
        return LLMResponse(
            output=output,
            tool_trace=[],
            usage=UsageMetrics(
                provider=self.name,
                model=self.model,
                prompt_tokens=len(prompt.split()) + 140,
                completion_tokens=120,
                total_tokens=tokens,
                latency_ms=latency,
            ),
        )


class OpenRouterProvider(BaseProvider):
    name = "openrouter"

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=25.0,
        )

    def complete(
        self,
        prompt: str,
        context: dict[str, Any],
        registry: ToolRegistry | None = None,
    ) -> LLMResponse:
        started = perf_counter()
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are FactoryOps AI Copilot. Use supplied tool outputs and uploaded "
                    "dataset summaries only. Return one JSON object matching this schema: "
                    "{markdown:string, summary:string, root_cause:string, "
                    "recommended_actions:string[], dashboard:{title:string, cards:"
                    "{label:string,value:string,detail:string,tone:string}[], insights:string[], "
                    "tables:{title:string,columns:string[],rows:string[][]}[], "
                    "chart_hints:object[]}}. "
                    "The markdown field must be concise GitHub-flavored markdown. No extra text."
                ),
            },
            {"role": "user", "content": f"Prompt: {prompt}\nContext JSON: {safe_json(context)}"},
        ]
        total_prompt_tokens = 0
        total_completion_tokens = 0
        provider_tool_trace: list[ToolCall] = []

        if registry:
            first = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=[_tool_spec_to_openai(tool) for tool in registry.specs()],
                tool_choice="auto",
                temperature=0.1,
            )
            total_prompt_tokens += getattr(first.usage, "prompt_tokens", 0) if first.usage else 0
            total_completion_tokens += (
                getattr(first.usage, "completion_tokens", 0) if first.usage else 0
            )
            message = first.choices[0].message
            messages.append(message.model_dump(exclude_none=True))
            for tool_call in message.tool_calls or []:
                args = json.loads(tool_call.function.arguments or "{}")
                result, trace = registry.execute(tool_call.function.name, **args)
                provider_tool_trace.append(trace)
                tool_payload = {
                    "status": trace.status,
                    "tool": trace.name,
                    "args": trace.args,
                    "duration_ms": trace.duration_ms,
                    "result": result if trace.status == "ok" else None,
                    "error": trace.result_preview if trace.status != "ok" else None,
                }
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": safe_json(tool_payload),
                    }
                )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        total_prompt_tokens += getattr(response.usage, "prompt_tokens", 0) if response.usage else 0
        total_completion_tokens += (
            getattr(response.usage, "completion_tokens", 0) if response.usage else 0
        )
        content = response.choices[0].message.content or "{}"
        try:
            output = AgentOutput.model_validate_json(_extract_json(content))
        except (ValidationError, ValueError):
            output = build_deterministic_output(prompt, context)
            output.markdown = (
                "## Provider Response Fallback\n\n"
                "OpenRouter returned a response that did not match the dashboard schema. "
                "The app used the deterministic structured fallback.\n\n"
                f"{output.markdown}"
            )
        latency = int((perf_counter() - started) * 1000)
        return LLMResponse(
            output=output,
            tool_trace=provider_tool_trace,
            usage=UsageMetrics(
                provider=self.name,
                model=self.model,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                total_tokens=total_prompt_tokens + total_completion_tokens,
                latency_ms=latency,
            ),
        )


def build_provider(settings: Settings) -> BaseProvider:
    provider = settings.llm_provider.lower()
    if provider == "openrouter" and settings.openrouter_api_key:
        return OpenRouterProvider(settings.openrouter_model, settings.openrouter_api_key)
    return MockProvider()


def build_provider_from_request(
    settings: Settings,
    provider: str | None,
    api_key: str | None,
    model: str | None,
) -> BaseProvider:
    selected = (provider or settings.llm_provider).lower()
    if selected == "openrouter" and api_key:
        return OpenRouterProvider(model or settings.openrouter_model, api_key)
    if selected == "openrouter" and settings.openrouter_api_key:
        return OpenRouterProvider(settings.openrouter_model, settings.openrouter_api_key)
    return MockProvider()


def build_deterministic_output(prompt: str, context: dict[str, Any]) -> AgentOutput:
    dataset = context.get("dataset_metrics")
    if dataset:
        cards = [
            {
                "label": card.get("label", "Metric"),
                "value": str(card.get("value", "n/a")),
                "detail": str(card.get("detail", "")),
                "tone": "neutral",
            }
            for card in dataset.get("cards", [])
        ]
        insights = dataset.get("insights", [])
        markdown = (
            "## Uploaded Dataset Analysis\n\n"
            f"**Question:** {prompt}\n\n"
            + "\n".join(f"- {item}" for item in insights)
            + "\n\n### Next Actions\n"
            "- Validate detected column roles.\n"
            "- Ask a follow-up question against the uploaded dataset.\n"
            "- Use SELECT-only SQL for precise drilldowns."
        )
        return AgentOutput(
            markdown=markdown,
            summary="Uploaded dataset profiled and converted into dashboard-ready signals.",
            root_cause=insights[0] if insights else "No single root cause inferred yet.",
            recommended_actions=[
                "Validate detected columns and business meaning.",
                "Ask a targeted follow-up question about a line, date, or loss category.",
                "Use uploaded dataset SQL drilldowns for evidence.",
            ],
            dashboard=DashboardSpec(
                title="Uploaded Dataset Dashboard",
                cards=cards,
                insights=insights,
                tables=[],
                chart_hints=[],
            ),
        )

    kpis = context["kpis"]
    comparison = context["comparison"]
    downtime = context["downtime"]
    actions = context["actions"]
    downtime_lines = "\n".join(
        f"- **{event.start_time}**: {event.reason} ({event.duration_minutes} min)"
        for event in downtime
    )
    markdown = (
        "## Line A Underperformance\n\n"
        f"**{kpis.line}** produced **{kpis.actual_units} / {kpis.target_units} units** "
        f"with **{kpis.oee:.1%} OEE** and **{kpis.downtime_minutes} minutes** of downtime.\n\n"
        "### Evidence\n"
        f"{downtime_lines}\n\n"
        "### Recommendation\n"
        + "\n".join(f"{idx + 1}. {action}" for idx, action in enumerate(actions))
    )
    root_cause = (
        "Repeated sensor faults concentrated around A-CELL-04 and infeed sensing caused "
        "excess downtime and recovery starvation."
    )
    return AgentOutput(
        markdown=markdown,
        summary=(
            f"{kpis.line} missed target by {kpis.target_units - kpis.actual_units} units "
            f"with {kpis.downtime_minutes} downtime minutes."
        ),
        root_cause=root_cause,
        recommended_actions=actions,
        dashboard=DashboardSpec(
            title="Factory Performance Triage",
            cards=[
                {
                    "label": "Output Gap",
                    "value": str(kpis.target_units - kpis.actual_units),
                    "detail": "units below target",
                    "tone": "danger",
                },
                {
                    "label": "OEE",
                    "value": f"{kpis.oee:.1%}",
                    "detail": "current shift",
                    "tone": "signal",
                },
                {
                    "label": "Downtime",
                    "value": f"{kpis.downtime_minutes}m",
                    "detail": f"+{comparison['downtime_delta_minutes']}m vs 7d",
                    "tone": "warning",
                },
                {
                    "label": "Scrap",
                    "value": f"{kpis.scrap_rate:.1%}",
                    "detail": "synthetic KPI",
                    "tone": "neutral",
                },
            ],
            insights=[
                root_cause,
                "SOP-QA-014 matches the repeated sensor fault escalation path.",
                "A maintenance ticket and Power Automate escalation spec were generated.",
            ],
            tables=[
                {
                    "title": "Downtime Evidence",
                    "columns": ["Time", "Station", "Reason", "Minutes"],
                    "rows": [
                        [
                            event.start_time,
                            event.station,
                            event.reason,
                            str(event.duration_minutes),
                        ]
                        for event in downtime
                    ],
                }
            ],
            chart_hints=[
                {
                    "type": "bar",
                    "title": "Downtime by Event",
                    "x": "start_time",
                    "y": "duration_minutes",
                }
            ],
        ),
    )


def safe_json(value: Any) -> str:
    def default(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return str(obj)

    return json.dumps(value, default=default, ensure_ascii=True)[:20000]


def _extract_json(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return text[start : end + 1]


def _tool_spec_to_openai(spec: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": {
                "type": "object",
                "properties": {
                    key: {"type": _schema_type(value), "description": str(value)}
                    for key, value in spec.input_schema.items()
                },
                "required": list(spec.input_schema.keys()),
            },
        },
    }


def _schema_type(value: Any) -> str:
    text = str(value).lower()
    if "int" in text or "number" in text:
        return "integer"
    if "array" in text or "list" in text:
        return "array"
    if "object" in text:
        return "object"
    return "string"
