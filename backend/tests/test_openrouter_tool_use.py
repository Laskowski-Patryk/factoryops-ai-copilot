from types import SimpleNamespace

from app.llm.providers import OpenRouterProvider
from app.tools.factory_tools import build_registry


class FakeMessage:
    def __init__(self, content: str | None = None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none: bool = True):
        payload = {"role": "assistant"}
        if self.content:
            payload["content"] = self.content
        if self.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ]
        return payload


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "tools" in kwargs:
            tool_call = SimpleNamespace(
                id="tool-1",
                function=SimpleNamespace(
                    name="get_production_kpis",
                    arguments='{"line":"Line A","day":"2026-05-25"}',
                ),
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=FakeMessage(tool_calls=[tool_call]))],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=FakeMessage(
                        content=(
                            '{"markdown":"## OK","summary":"ok","root_cause":"tool used",'
                            '"recommended_actions":["act"],"dashboard":{"title":"Demo",'
                            '"cards":[],"insights":[],"tables":[],"chart_hints":[]}}'
                        )
                    )
                )
            ],
            usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3),
        )


def test_openrouter_provider_executes_native_tool_call():
    fake_completions = FakeCompletions()
    provider = OpenRouterProvider("test-model", "test-key")
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))

    response = provider.complete(
        "Use tools",
        {"kpis": "context"},
        registry=build_registry(),
    )

    assert fake_completions.calls[0]["tools"]
    assert fake_completions.calls[0]["tool_choice"] == "auto"
    assert response.output.root_cause == "tool used"
    assert [tool.name for tool in response.tool_trace] == ["get_production_kpis"]
