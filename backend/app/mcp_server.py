from app.datasets.service import DatasetService
from app.tools.factory_tools import build_registry


def list_tools() -> list[dict]:
    """MCP-shaped tool manifest for demos without requiring a full MCP runtime."""
    return [
        spec.model_dump()
        for spec in build_registry(DatasetService("data/uploads")).specs()
    ]


if __name__ == "__main__":
    for tool in list_tools():
        print(tool)
