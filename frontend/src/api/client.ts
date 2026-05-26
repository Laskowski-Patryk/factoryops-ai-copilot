import type { DatasetSummary, RunResult, ToolCall } from "../types/run";

export type ProviderSession = {
  provider: "mock" | "openrouter";
  apiKey: string;
  model: string;
};

export async function fetchConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) throw new Error("config unavailable");
  return response.json();
}

export async function fetchRuns(): Promise<RunResult[]> {
  const response = await fetch("/api/runs");
  if (!response.ok) throw new Error("runs unavailable");
  return response.json();
}

export async function createRun(
  prompt: string,
  session: ProviderSession,
  datasetId?: string
): Promise<RunResult> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      line: "Line A",
      provider: session.provider,
      api_key: session.provider === "mock" ? undefined : session.apiKey,
      model: session.provider === "mock" ? undefined : session.model,
      dataset_id: datasetId || undefined
    })
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Run failed with HTTP ${response.status}`);
  }
  return response.json();
}

export type RunStreamEvent =
  | { type: "status"; message: string }
  | { type: "tool_started"; name: string; args: Record<string, unknown> }
  | { type: "tool_call"; tool: ToolCall }
  | { type: "run_complete"; run: RunResult }
  | { type: "error"; message: string };

export async function streamRun(
  prompt: string,
  session: ProviderSession,
  conversationId: string,
  datasetId: string | undefined,
  onEvent: (event: RunStreamEvent) => void
): Promise<RunResult> {
  const response = await fetch("/api/runs/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      line: "Line A",
      provider: session.provider,
      api_key: session.provider === "mock" ? undefined : session.apiKey,
      model: session.provider === "mock" ? undefined : session.model,
      dataset_id: datasetId || undefined,
      conversation_id: conversationId
    })
  });
  if (!response.ok || !response.body) {
    const detail = await response.text();
    throw new Error(detail || `Run failed with HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completedRun: RunResult | null = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      const event = JSON.parse(line.replace("data: ", "")) as RunStreamEvent;
      onEvent(event);
      if (event.type === "run_complete") completedRun = event.run;
      if (event.type === "error") throw new Error(event.message);
    }
  }
  if (!completedRun) throw new Error("Run stream ended without result");
  return completedRun;
}

export async function uploadDataset(file: File): Promise<DatasetSummary> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/datasets", {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Upload failed with HTTP ${response.status}`);
  }
  return response.json();
}

export async function fetchDatasets(): Promise<DatasetSummary[]> {
  const response = await fetch("/api/datasets");
  if (!response.ok) throw new Error("datasets unavailable");
  return response.json();
}
