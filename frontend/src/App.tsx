import {
  Activity,
  Bot,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Gauge,
  History,
  KeyRound,
  Play,
  ShieldCheck,
  TicketCheck,
  Trash2,
  Upload,
  Workflow
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  deleteDataset,
  fetchConfig,
  fetchDatasets,
  fetchRuns,
  streamRun,
  type ProviderSession,
  uploadDataset
} from "./api/client";
import { samplePrompt, staticRuns } from "./demo/staticRuns";
import type { DatasetSummary, RunResult } from "./types/run";

const prompts = [
  samplePrompt,
  "Generate a shift handover summary for Line A.",
  "Create an escalation plan for repeated sensor faults.",
  "What automation flow should notify maintenance after recurring downtime?"
];

const SESSION_STORAGE_KEY = "factoryops-provider-session";
const CONVERSATION_STORAGE_KEY = "factoryops-conversation-id";

function safeGetItem(key: string) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Some browsers block localStorage on LAN/private modes. The app can still run without persistence.
  }
}

function createLocalId() {
  if (
    globalThis.crypto &&
    "randomUUID" in globalThis.crypto &&
    typeof globalThis.crypto.randomUUID === "function"
  ) {
    return globalThis.crypto.randomUUID();
  }
  return `thread-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function loadStoredSession(): ProviderSession {
  try {
    const stored = safeGetItem(SESSION_STORAGE_KEY);
    if (!stored) return { provider: "mock", apiKey: "", model: "openai/gpt-4o-mini" };
    const parsed = JSON.parse(stored) as ProviderSession;
    return {
      provider: parsed.provider === "openrouter" ? "openrouter" : "mock",
      apiKey: parsed.apiKey ?? "",
      model: parsed.model || "openai/gpt-4o-mini"
    };
  } catch {
    return { provider: "mock", apiKey: "", model: "openai/gpt-4o-mini" };
  }
}

export function App() {
  const [prompt, setPrompt] = useState(samplePrompt);
  const [runs, setRuns] = useState<RunResult[]>(staticRuns);
  const [activeId, setActiveId] = useState(staticRuns[0].id);
  const [provider, setProvider] = useState("mock");
  const [session, setSession] = useState<ProviderSession>(loadStoredSession);
  const [sessionReady, setSessionReady] = useState(false);
  const [offline, setOffline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingDatasetId, setDeletingDatasetId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [liveTrace, setLiveTrace] = useState<RunResult["tool_trace"]>([]);
  const [conversationId] = useState(() => {
    const existing = safeGetItem(CONVERSATION_STORAGE_KEY);
    if (existing) return existing;
    const next = createLocalId();
    safeSetItem(CONVERSATION_STORAGE_KEY, next);
    return next;
  });

  const active = useMemo(
    () => runs.find((run) => run.id === activeId) ?? runs[0],
    [activeId, runs]
  );

  useEffect(() => {
    Promise.all([fetchConfig(), fetchRuns(), fetchDatasets()])
      .then(([config, apiRuns, apiDatasets]) => {
        setProvider(config.provider ?? "mock");
        if (apiRuns.length) {
          setRuns(apiRuns);
          setActiveId(apiRuns[0].id);
        }
        setDatasets(apiDatasets);
        if (apiDatasets.length) setSelectedDatasetId(apiDatasets[0].id);
        setOffline(false);
      })
      .catch(() => setOffline(true));
  }, []);

  function updateSession(next: ProviderSession) {
    setSession(next);
    safeSetItem(SESSION_STORAGE_KEY, JSON.stringify(next));
  }

  async function handleDatasetUpload(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    setStatusMessage(`Uploading ${file.name}...`);
    try {
      const dataset = await uploadDataset(file);
      setDatasets((current) => [dataset, ...current.filter((item) => item.id !== dataset.id)]);
      setSelectedDatasetId(dataset.id);
      setStatusMessage(
        `Dataset uploaded: ${dataset.name} (${dataset.row_count} rows, ${dataset.tables.length} table/s).`
      );
      await runAnalysis(
        "Create a dashboard and root-cause report from my uploaded dataset.",
        dataset.id
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown upload error";
      setStatusMessage(`Run failed: ${message}`);
    } finally {
      setUploading(false);
    }
  }

  async function handleDatasetDelete(datasetId: string) {
    if (!datasetId) return;
    const dataset = datasets.find((item) => item.id === datasetId);
    const name = dataset?.name ?? "selected dataset";
    const confirmed = window.confirm(
      `Delete "${name}" from local uploads? Existing run history will stay, but this file will no longer be available for new analysis.`
    );
    if (!confirmed) return;

    setDeletingDatasetId(datasetId);
    setStatusMessage(`Deleting dataset: ${name}...`);
    try {
      await deleteDataset(datasetId);
      setDatasets((current) => current.filter((item) => item.id !== datasetId));
      setSelectedDatasetId((current) => (current === datasetId ? "" : current));
      setStatusMessage(`Dataset deleted: ${name}.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown delete error";
      setStatusMessage(`Delete failed: ${message}`);
    } finally {
      setDeletingDatasetId(null);
    }
  }

  async function submitRun() {
    await runAnalysis(prompt, selectedDatasetId || undefined);
  }

  async function runAnalysis(promptText: string, datasetId?: string) {
    setLoading(true);
    setLiveTrace([]);
    setStatusMessage(`Running analysis with ${session.provider}...`);
    try {
      const run = await streamRun(promptText, session, conversationId, datasetId, (event) => {
        if (event.type === "status") setStatusMessage(event.message);
        if (event.type === "tool_started") {
          setStatusMessage(`Running tool: ${event.name}`);
        }
        if (event.type === "tool_call") {
          setLiveTrace((current) => [...current, event.tool]);
          setStatusMessage(`Tool completed: ${event.tool.name}`);
        }
        if (event.type === "error") setStatusMessage(`Run failed: ${event.message}`);
      });
      setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
      setActiveId(run.id);
      setProvider(run.provider);
      setOffline(false);
      setStatusMessage(`Run completed with ${run.provider} in ${run.usage.latency_ms} ms.`);
    } catch (error) {
      setOffline(true);
      const message = error instanceof Error ? error.message : "Unknown run error";
      setStatusMessage(`Run failed: ${message}`);
    } finally {
      setLoading(false);
    }
  }

  const outputGap = active.kpis.target_units - active.kpis.actual_units;
  const downtimeDelta = Number(active.comparison.downtime_delta_minutes ?? 0);
  const isFailureStatus =
    statusMessage?.startsWith("Run failed") || statusMessage?.startsWith("Delete failed");

  return (
    <main className="min-h-screen bg-ink text-slate-100">
      {!sessionReady && (
        <ProviderGate
          session={session}
          onChange={updateSession}
          onStart={() => {
            safeSetItem(SESSION_STORAGE_KEY, JSON.stringify(session));
            setProvider(session.provider);
            setSessionReady(true);
          }}
        />
      )}
      <div className="border-b border-white/10 bg-panel">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-signal">FactoryOps AI Copilot</p>
            <h1 className="mt-1 text-2xl font-semibold">Manufacturing Performance Triage</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge icon={<Bot size={16} />} text={`Provider: ${provider}`} />
          <Badge icon={<Database size={16} />} text={`Thread: ${conversationId.slice(0, 8)}`} />
            <button
              className="inline-flex items-center gap-2 border border-white/10 bg-steel px-3 py-1.5 hover:border-signal"
              onClick={() => setSessionReady(false)}
            >
              <KeyRound size={16} />
              Provider setup
            </button>
            <Badge icon={<ShieldCheck size={16} />} text={offline ? "Static demo" : "API online"} />
            <Badge icon={<Clock3 size={16} />} text={`${active.usage.latency_ms} ms`} />
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl gap-5 px-4 py-5 xl:grid-cols-[1.4fr_0.8fr]">
        <section className="space-y-5">
          {statusMessage && (
            <div
              className={`border px-4 py-3 text-sm ${
                isFailureStatus
                  ? "border-danger bg-danger/10 text-rose-100"
                  : "border-signal bg-signal/10 text-emerald-100"
              }`}
            >
              {statusMessage}
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-4">
            {(active.dashboard_spec?.cards?.length
              ? active.dashboard_spec.cards
              : [
                  {
                    label: "Output Gap",
                    value: `${outputGap}`,
                    detail: "units below target",
                    tone: "danger" as const
                  },
                  {
                    label: "OEE",
                    value: `${(active.kpis.oee * 100).toFixed(1)}%`,
                    detail: "current shift",
                    tone: "signal" as const
                  },
                  {
                    label: "Downtime",
                    value: `${active.kpis.downtime_minutes}m`,
                    detail: `+${downtimeDelta}m vs 7d`,
                    tone: "warning" as const
                  },
                  {
                    label: "Scrap",
                    value: `${(active.kpis.scrap_rate * 100).toFixed(1)}%`,
                    detail: "synthetic KPI",
                    tone: "neutral" as const
                  }
                ]).map((card) => (
              <Metric
                key={`${card.label}-${card.value}`}
                label={card.label}
                value={card.value}
                detail={card.detail}
                tone={card.tone}
              />
            ))}
          </div>

          <Panel title="Upload Operational Data" icon={<Upload size={18} />}>
            <div className="grid gap-3 md:grid-cols-[1fr_0.8fr]">
              <label className="flex cursor-pointer items-center justify-center gap-2 border border-dashed border-white/20 bg-steel px-4 py-6 text-sm hover:border-signal">
                <Upload size={18} />
                {uploading ? "Uploading..." : "Upload CSV, XLSX or SQLite"}
                <input
                  className="hidden"
                  type="file"
                  accept=".csv,.xlsx,.xlsm,.sqlite,.sqlite3,.db"
                  onChange={(event) => handleDatasetUpload(event.target.files?.[0])}
                />
              </label>
              <div className="block">
                <span className="text-xs uppercase text-slate-400">Active dataset</span>
                <div className="mt-2 flex gap-2">
                  <select
                    className="min-w-0 flex-1 border border-white/10 bg-steel px-3 py-2 text-sm outline-none focus:border-signal"
                    value={selectedDatasetId}
                    onChange={(event) => setSelectedDatasetId(event.target.value)}
                  >
                    <option value="">Fake factory demo data</option>
                    {datasets.map((dataset) => (
                      <option key={dataset.id} value={dataset.id}>
                        {dataset.name} - {dataset.row_count} rows
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    title="Delete selected uploaded dataset"
                    className="inline-flex shrink-0 items-center justify-center gap-2 border border-white/10 px-3 py-2 text-sm text-slate-200 hover:border-danger hover:text-rose-100 disabled:cursor-not-allowed disabled:opacity-40"
                    disabled={!selectedDatasetId || deletingDatasetId === selectedDatasetId}
                    onClick={() => handleDatasetDelete(selectedDatasetId)}
                  >
                    <Trash2 size={16} />
                    {deletingDatasetId === selectedDatasetId ? "Deleting" : "Delete"}
                  </button>
                </div>
                <p className="mt-2 text-xs text-slate-400">
                  CSV, XLSX/XLSM, and SQLite are converted into local read-only SQLite.
                  Any column names are accepted; clear metric names improve inference.
                </p>
              </div>
            </div>
          </Panel>

          <Panel title="Ask The Copilot" icon={<Play size={18} />}>
            <textarea
              className="min-h-24 w-full resize-none border border-white/10 bg-steel p-3 text-sm outline-none focus:border-signal"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                className="inline-flex items-center gap-2 bg-signal px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
                onClick={submitRun}
                disabled={loading}
              >
                <Play size={16} />
                {loading ? "Running" : "Run Analysis"}
              </button>
              {prompts.map((item) => (
                <button
                  key={item}
                  className="border border-white/10 px-3 py-2 text-xs text-slate-300 hover:border-signal"
                  onClick={() => setPrompt(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="Final Answer" icon={<CheckCircle2 size={18} />}>
            <MarkdownBlock markdown={active.answer_markdown || active.final_answer} />
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold text-white">Root Cause</h3>
                <p className="mt-2 text-sm leading-6 text-slate-300">{active.root_cause}</p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Recommended Actions</h3>
                <ul className="mt-2 space-y-2 text-sm text-slate-300">
                  {active.recommended_actions.map((action) => (
                    <li key={action} className="flex gap-2">
                      <CheckCircle2 className="mt-0.5 shrink-0 text-signal" size={15} />
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Panel>

          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Generated Shift Report" icon={<FileText size={18} />}>
              <h3 className="text-sm font-semibold">{active.shift_report.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-300">{active.shift_report.summary}</p>
              <p className="mt-3 text-sm text-slate-400">{active.shift_report.downtime_summary}</p>
            </Panel>
            <Panel title="Ticket And Flow" icon={<TicketCheck size={18} />}>
              <p className="text-sm font-semibold">{active.maintenance_ticket.id}</p>
              <p className="mt-1 text-sm text-slate-300">{active.maintenance_ticket.issue}</p>
              <div className="mt-4 border-t border-white/10 pt-4">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <Workflow size={16} /> {active.flow_spec.name}
                </p>
                <p className="mt-2 text-sm text-slate-300">{active.flow_spec.trigger}</p>
              </div>
            </Panel>
          </div>

          {!!active.dashboard_spec?.tables?.length && (
            <div className="grid gap-5">
              {active.dashboard_spec.tables.map((table) => (
                <Panel key={table.title} title={table.title} icon={<Database size={18} />}>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse text-left text-xs">
                      <thead className="text-slate-400">
                        <tr>
                          {table.columns.map((column) => (
                            <th key={column} className="border-b border-white/10 px-2 py-2">
                              {column}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {table.rows.slice(0, 8).map((row, index) => (
                          <tr key={`${table.title}-${index}`} className="border-b border-white/5">
                            {row.map((cell, cellIndex) => (
                              <td key={`${cell}-${cellIndex}`} className="px-2 py-2 text-slate-300">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Panel>
              ))}
            </div>
          )}
        </section>

        <aside className="space-y-5">
          <Panel title="Tool Trace" icon={<Activity size={18} />}>
            <div className="space-y-3">
              {(loading && liveTrace.length ? liveTrace : active.tool_trace).map((tool, index) => (
                <div key={`${tool.name}-${index}`} className="border-l-2 border-signal pl-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-semibold">{tool.name}</span>
                    <span className="text-xs text-slate-400">{tool.duration_ms} ms</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-slate-400">{tool.result_preview}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Tokens And Latency" icon={<Gauge size={18} />}>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Stat label="Model" value={active.usage.model} />
              <Stat label="Provider" value={active.usage.provider} />
              <Stat label="Prompt Tokens" value={active.usage.prompt_tokens.toString()} />
              <Stat label="Total Tokens" value={active.usage.total_tokens.toString()} />
            </div>
          </Panel>

          <Panel title="Run History" icon={<History size={18} />}>
            <div className="space-y-2">
              {runs.map((run) => (
                <button
                  key={run.id}
                  className={`block w-full border px-3 py-2 text-left text-sm ${
                    run.id === active.id ? "border-signal bg-signal/10" : "border-white/10"
                  }`}
                  onClick={() => setActiveId(run.id)}
                >
                  <span className="block font-semibold">{run.line} - {run.provider}</span>
                  <span className="line-clamp-1 text-xs text-slate-400">{run.prompt}</span>
                </button>
              ))}
            </div>
          </Panel>
        </aside>
      </div>
    </main>
  );
}

function Badge({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <span className="inline-flex items-center gap-2 border border-white/10 bg-steel px-3 py-1.5">
      {icon}
      {text}
    </span>
  );
}

function MarkdownBlock({ markdown }: { markdown: string }) {
  return (
    <div className="space-y-2 text-sm leading-6 text-slate-200">
      {markdown.split("\n").map((line, index) => {
        if (!line.trim()) return <div key={index} className="h-1" />;
        if (line.startsWith("### ")) {
          return (
            <h3 key={index} className="pt-2 text-sm font-semibold text-white">
              {line.replace("### ", "")}
            </h3>
          );
        }
        if (line.startsWith("## ")) {
          return (
            <h2 key={index} className="pt-2 text-base font-semibold text-white">
              {line.replace("## ", "")}
            </h2>
          );
        }
        if (line.startsWith("- ")) {
          return (
            <p key={index} className="pl-3 text-slate-300">
              <span className="text-signal">• </span>
              <InlineMarkdown text={line.replace("- ", "")} />
            </p>
          );
        }
        if (/^\d+\.\s/.test(line)) {
          return (
            <p key={index} className="pl-3 text-slate-300">
              <InlineMarkdown text={line} />
            </p>
          );
        }
        return (
          <p key={index}>
            <InlineMarkdown text={line} />
          </p>
        );
      })}
    </div>
  );
}

function InlineMarkdown({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, index) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={index} className="font-semibold text-white">
            {part.slice(2, -2)}
          </strong>
        ) : (
          <span key={index}>{part}</span>
        )
      )}
    </>
  );
}

function ProviderGate({
  session,
  onChange,
  onStart
}: {
  session: ProviderSession;
  onChange: (session: ProviderSession) => void;
  onStart: () => void;
}) {
  const needsKey = session.provider !== "mock";
  const defaultModel =
    session.provider === "openrouter" ? "openai/gpt-4o-mini" : "gpt-4o-mini";
  const canStart = !needsKey || session.apiKey.trim().length > 8;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/95 px-4">
      <section className="w-full max-w-2xl border border-white/10 bg-panel p-5 shadow-2xl">
        <div className="flex items-center gap-3 border-b border-white/10 pb-4">
          <Bot className="text-signal" size={24} />
          <div>
            <p className="text-xs uppercase tracking-wider text-signal">FactoryOps AI Copilot</p>
            <h2 className="text-xl font-semibold">Choose Runtime Provider</h2>
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {(["mock", "openrouter"] as ProviderSession["provider"][]).map((item) => (
            <button
              key={item}
              className={`border p-4 text-left ${
                session.provider === item ? "border-signal bg-signal/10" : "border-white/10"
              }`}
              onClick={() =>
                onChange({
                  provider: item,
                  apiKey: item === "mock" ? "" : session.apiKey,
                  model:
                    item === "mock"
                      ? ""
                      : "openai/gpt-4o-mini"
                })
              }
            >
              <span className="block text-sm font-semibold uppercase">{item}</span>
              <span className="mt-2 block text-xs leading-5 text-slate-400">
                {item === "mock"
                  ? "Deterministic, free, no API key."
                  : "Uses your key for this browser session only."}
              </span>
            </button>
          ))}
        </div>

        {needsKey && (
          <div className="mt-5 grid gap-3 md:grid-cols-[1fr_0.7fr]">
            <label className="block">
              <span className="text-xs uppercase text-slate-400">API key</span>
              <input
                className="mt-2 w-full border border-white/10 bg-steel px-3 py-2 text-sm outline-none focus:border-signal"
                type="password"
                placeholder="OPENROUTER_API_KEY"
                value={session.apiKey}
                onChange={(event) => onChange({ ...session, apiKey: event.target.value })}
              />
            </label>
            <label className="block">
              <span className="text-xs uppercase text-slate-400">Model</span>
              <input
                className="mt-2 w-full border border-white/10 bg-steel px-3 py-2 text-sm outline-none focus:border-signal"
                value={session.model || defaultModel}
                onChange={(event) => onChange({ ...session, model: event.target.value })}
              />
            </label>
          </div>
        )}

        <div className="mt-5 flex flex-col gap-3 border-t border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-slate-400">
            The OpenRouter key and model are saved in this browser's localStorage for convenience.
            They are not stored in SQLite, JSONL, git, or backend files.
          </p>
          <button
            className="inline-flex shrink-0 items-center justify-center gap-2 bg-signal px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
            disabled={!canStart}
            onClick={onStart}
          >
            <Play size={16} />
            Enter Dashboard
          </button>
        </div>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  tone = "signal"
}: {
  label: string;
  value: string;
  detail: string;
  tone?: "signal" | "warning" | "danger" | "neutral";
}) {
  const color =
    tone === "danger"
      ? "text-danger"
      : tone === "warning"
        ? "text-warning"
        : tone === "signal"
          ? "text-signal"
          : "text-slate-100";
  return (
    <div className="border border-white/10 bg-panel p-4">
      <p className="text-xs uppercase text-slate-400">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${color}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-400">{detail}</p>
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="border border-white/10 bg-panel p-4">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
        {icon}
        {title}
      </div>
      {children}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-white/10 bg-steel p-3">
      <p className="text-xs uppercase text-slate-400">{label}</p>
      <p className="mt-1 break-words font-semibold text-slate-100">{value}</p>
    </div>
  );
}
