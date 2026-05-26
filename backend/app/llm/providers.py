from time import perf_counter
from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import Settings
from app.models.schemas import UsageMetrics


class LLMResponse(BaseModel):
    text: str
    usage: UsageMetrics


class BaseProvider:
    name = "base"
    model = "none"

    def complete(self, prompt: str, context: dict[str, Any]) -> LLMResponse:
        raise NotImplementedError


class MockProvider(BaseProvider):
    name = "mock"
    model = "deterministic-factoryops-v1"

    def complete(self, prompt: str, context: dict[str, Any]) -> LLMResponse:
        started = perf_counter()
        kpis = context["kpis"]
        comparison = context["comparison"]
        text = (
            f"{kpis.line} underperformed because repeated sensor faults created "
            f"{kpis.downtime_minutes} minutes of downtime, pushing output "
            f"{abs(int(comparison['actual_delta_units']))} units below the 7-day average. "
            "The strongest evidence is the repeated A-CELL-04 fault pattern, manual resets, "
            "and matching SOP guidance for sensor fault escalation. Next: inspect and recalibrate "
            "the sensor set, verify cabling and PLC timestamps, hold quality containment, "
            "and review the maintenance ticket at shift handover."
        )
        latency = int((perf_counter() - started) * 1000) + 18
        tokens = max(80, len(prompt.split()) + 140)
        return LLMResponse(
            text=text,
            usage=UsageMetrics(
                provider=self.name,
                model=self.model,
                prompt_tokens=len(prompt.split()) + 120,
                completion_tokens=96,
                total_tokens=tokens,
                latency_ms=latency,
            ),
        )


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, name: str, model: str, api_key: str, base_url: str | None = None) -> None:
        self.name = name
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, prompt: str, context: dict[str, Any]) -> LLMResponse:
        started = perf_counter()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize deterministic manufacturing tool results. "
                        "Do not invent facts."
                    ),
                },
                {"role": "user", "content": f"Prompt: {prompt}\nContext: {context}"},
            ],
            temperature=0.2,
        )
        latency = int((perf_counter() - started) * 1000)
        usage = response.usage
        return LLMResponse(
            text=response.choices[0].message.content or "",
            usage=UsageMetrics(
                provider=self.name,
                model=self.model,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
                latency_ms=latency,
            ),
        )


def build_provider(settings: Settings) -> BaseProvider:
    provider = settings.llm_provider.lower()
    if provider == "openai" and settings.openai_api_key:
        return OpenAICompatibleProvider("openai", settings.openai_model, settings.openai_api_key)
    if provider == "openrouter" and settings.openrouter_api_key:
        return OpenAICompatibleProvider(
            "openrouter",
            settings.openrouter_model,
            settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    return MockProvider()


def build_provider_from_request(
    settings: Settings,
    provider: str | None,
    api_key: str | None,
    model: str | None,
) -> BaseProvider:
    selected = (provider or settings.llm_provider).lower()
    if selected == "openai" and api_key:
        return OpenAICompatibleProvider(
            "openai",
            model or settings.openai_model,
            api_key,
        )
    if selected == "openrouter" and api_key:
        return OpenAICompatibleProvider(
            "openrouter",
            model or settings.openrouter_model,
            api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    if selected in {"openai", "openrouter"}:
        env_provider = build_provider(settings)
        if env_provider.name == selected:
            return env_provider
    return MockProvider()
