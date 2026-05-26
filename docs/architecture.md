# Architecture

FactoryOps AI Copilot is intentionally deterministic for the main demo path. The agent uses a known orchestration plan for factory performance questions, executes tools sequentially, records trace metadata, and only then asks the selected provider to summarize tool results.

## Backend

- FastAPI exposes `/api/health`, `/api/config`, `/api/runs`, and `/api/runs/{run_id}`.
- Pydantic v2 models define run requests, KPI snapshots, downtime events, tickets, flow specs, tool calls, and usage metrics.
- SQLite stores full run payloads. JSONL mirrors runs for inspection and export.
- The provider layer supports `mock` and `openrouter`.

## Agent Flow

1. Resolve date, defaulting to yesterday.
2. If a dataset is selected, profile the uploaded CSV/XLSX/SQLite data and infer dashboard cards.
3. Fetch the deterministic factory KPI baseline.
4. Fetch downtime events.
5. Compare previous 7 days.
6. Search SOP guidance.
7. Generate shift report.
8. Create mock maintenance ticket.
9. Create Power Automate flow spec.
10. Generate structured markdown plus dashboard JSON.
11. Persist run.

## Tooling Shape

The registry is MCP-shaped: every tool has a name, description, input schema, handler, and trace entry. OpenRouter receives the registry as OpenAI-compatible tool definitions, can call tools, and the backend validates/executes those calls. The repository does not claim full MCP protocol support; `backend/app/mcp_server.py` lists the available tool manifest for inspection.

## Uploaded Data

CSV, XLSX/XLSM, and SQLite files are stored under `data/uploads` and converted to a local SQLite copy. Dataset SQL tools reject write/admin statements and return only limited SELECT results. The agent emits `answer_markdown` plus `dashboard_spec` so the frontend can build cards and tables without scraping prose.

## Frontend

The React dashboard loads live API runs when available. If the backend is unavailable, it switches to `frontend/src/demo/staticRuns.ts`, which makes the repository presentable as a static demo.
