import type { RunResult } from "../types/run";

export type ProviderSession = {
  provider: "mock" | "openai" | "openrouter";
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

export async function createRun(prompt: string, session: ProviderSession): Promise<RunResult> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      line: "Line A",
      provider: session.provider,
      api_key: session.provider === "mock" ? undefined : session.apiKey,
      model: session.provider === "mock" ? undefined : session.model
    })
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Run failed with HTTP ${response.status}`);
  }
  return response.json();
}
