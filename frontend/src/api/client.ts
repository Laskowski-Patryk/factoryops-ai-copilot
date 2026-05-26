import type { DatasetSummary, RunResult } from "../types/run";

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
