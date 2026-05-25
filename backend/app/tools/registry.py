from collections.abc import Callable
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.schemas import ToolCall


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class RegisteredTool(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    spec: ToolSpec
    handler: Callable[..., Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: Callable[..., Any]) -> None:
        self._tools[spec.name] = RegisteredTool(spec=spec, handler=handler)

    def specs(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    def execute(self, name: str, **kwargs: Any) -> tuple[Any, ToolCall]:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        started = perf_counter()
        try:
            result = self._tools[name].handler(**kwargs)
            duration = int((perf_counter() - started) * 1000)
            return result, ToolCall(
                name=name,
                args=kwargs,
                status="ok",
                duration_ms=duration,
                result_preview=_preview(result),
            )
        except Exception as exc:
            duration = int((perf_counter() - started) * 1000)
            return None, ToolCall(
                name=name,
                args=kwargs,
                status="error",
                duration_ms=duration,
                result_preview=str(exc),
            )


def _preview(result: Any) -> str:
    text = str(result.model_dump()) if hasattr(result, "model_dump") else str(result)
    return text[:280]
