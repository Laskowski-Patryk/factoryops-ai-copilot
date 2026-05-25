# Architecture

FactoryOps AI Copilot is intentionally deterministic for the main demo path. The agent uses a known orchestration plan for factory performance questions, executes tools sequentially, records trace metadata, and only then asks the selected provider to summarize tool results.

## Backend

- FastAPI exposes `/api/health`, `/api/config`, `/api/runs`, and `/api/runs/{run_id}`.
- Pydantic v2 models define run requests, KPI snapshots, downtime events, tickets, flow specs, tool calls, and usage metrics.
- SQLite stores full run payloads. JSONL mirrors runs for inspection and export.
- The provider layer supports `mock`, `openrouter`, and `openai`.

## Agent Flow

1. Resolve date, defaulting to yesterday.
2. Fetch KPI snapshot.
3. Fetch downtime events.
4. Compare previous 7 days.
5. Search SOP guidance.
6. Generate shift report.
7. Create mock maintenance ticket.
8. Create Power Automate flow spec.
9. Generate final response.
10. Persist run.

## Tooling Shape

The registry is MCP-shaped: every tool has a name, description, input schema, handler, and trace entry. The repository does not claim full MCP protocol support; `backend/app/mcp_server.py` lists the available tool manifest for inspection.

## Frontend

The React dashboard loads live API runs when available. If the backend is unavailable, it switches to `frontend/src/demo/staticRuns.ts`, which makes the repository presentable as a static demo.
