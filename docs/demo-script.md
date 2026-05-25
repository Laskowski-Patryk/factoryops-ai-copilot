# Demo Script

1. Start the app:

```bash
docker compose up --build
```

2. Open http://localhost:5173.

3. Ask:

```text
Why did Line A underperform yesterday and what should we do next?
```

4. Walk through the dashboard:

- KPI cards show output gap, OEE, downtime, and scrap.
- Final answer explains the repeated sensor fault pattern.
- Root cause and recommended actions are separated from the narrative answer.
- Tool trace proves the agent used structured steps instead of guessing.
- Tokens and latency panel shows provider observability.
- Shift report, maintenance ticket, and Power Automate flow spec show automation handoff artifacts.
- Run history shows persistence.

5. Stop the backend and refresh the frontend to show static demo mode.
