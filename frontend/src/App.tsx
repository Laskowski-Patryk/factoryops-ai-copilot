import {
  Activity,
  Bot,
  CheckCircle2,
  Clock3,
  KeyRound,
  FileText,
  Gauge,
  History,
  Play,
  ShieldCheck,
  TicketCheck,
  Workflow
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createRun, fetchConfig, fetchRuns, type ProviderSession } from "./api/client";
import { samplePrompt, staticRuns } from "./demo/staticRuns";
import type { RunResult } from "./types/run";

const prompts = [
  samplePrompt,
  "Generate a shift handover summary for Line A.",
  "Create an escalation plan for repeated sensor faults.",
  "What automation flow should notify maintenance after recurring downtime?"
];

export function App() {
  const [prompt, setPrompt] = useState(samplePrompt);
  const [runs, setRuns] = useState<RunResult[]>(staticRuns);
  const [activeId, setActiveId] = useState(staticRuns[0].id);
  const [provider, setProvider] = useState("mock");
  const [session, setSession] = useState<ProviderSession>({
    provider: "mock",
    apiKey: "",
    model: ""
  });
  const [sessionReady, setSessionReady] = useState(false);
  const [offline, setOffline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const active = useMemo(
    () => runs.find((run) => run.id === activeId) ?? runs[0],
    [activeId, runs]
  );

  useEffect(() => {
    Promise.all([fetchConfig(), fetchRuns()])
      .then(([config, apiRuns]) => {
        setProvider(config.provider ?? "mock");
        if (apiRuns.length) {
          setRuns(apiRuns);
          setActiveId(apiRuns[0].id);
        }
        setOffline(false);
      })
      .catch(() => setOffline(true));
  }, []);

  async function submitRun() {
    setLoading(true);
    setStatusMessage(`Running analysis with ${session.provider}...`);
    try {
      const run = await createRun(prompt, session);
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

  return (
    <main className="min-h-screen bg-ink text-slate-100">
      {!sessionReady && (
        <ProviderGate
          session={session}
          onChange={setSession}
          onStart={() => {
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
                statusMessage.startsWith("Run failed")
                  ? "border-danger bg-danger/10 text-rose-100"
                  : "border-signal bg-signal/10 text-emerald-100"
              }`}
            >
              {statusMessage}
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-4">
            <Metric label="Output Gap" value={`${outputGap}`} detail="units below target" tone="danger" />
            <Metric label="OEE" value={`${(active.kpis.oee * 100).toFixed(1)}%`} detail="current shift" />
            <Metric label="Downtime" value={`${active.kpis.downtime_minutes}m`} detail={`+${downtimeDelta}m vs 7d`} tone="warning" />
            <Metric label="Scrap" value={`${(active.kpis.scrap_rate * 100).toFixed(1)}%`} detail="synthetic KPI" />
          </div>

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
            <p className="text-sm leading-6 text-slate-200">{active.final_answer}</p>
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
        </section>

        <aside className="space-y-5">
          <Panel title="Tool Trace" icon={<Activity size={18} />}>
            <div className="space-y-3">
              {active.tool_trace.map((tool, index) => (
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
          {(["mock", "openai", "openrouter"] as ProviderSession["provider"][]).map((item) => (
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
                      : item === "openrouter"
                        ? "openai/gpt-4o-mini"
                        : "gpt-4o-mini"
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
                placeholder={
                  session.provider === "openrouter" ? "OPENROUTER_API_KEY" : "OPENAI_API_KEY"
                }
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
            Keys are sent only to the local backend for the selected run and are not stored in
            SQLite, JSONL, git, or browser storage.
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
  tone?: "signal" | "warning" | "danger";
}) {
  const color = tone === "danger" ? "text-danger" : tone === "warning" ? "text-warning" : "text-signal";
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
