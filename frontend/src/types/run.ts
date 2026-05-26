export type ToolCall = {
  name: string;
  args: Record<string, unknown>;
  status: "ok" | "error";
  duration_ms: number;
  result_preview: string;
};

export type KpiSnapshot = {
  line: string;
  date: string;
  target_units: number;
  actual_units: number;
  oee: number;
  scrap_rate: number;
  downtime_minutes: number;
};

export type RunResult = {
  id: string;
  created_at: string;
  prompt: string;
  line: string;
  date: string;
  provider: string;
  final_answer: string;
  answer_markdown?: string;
  dashboard_spec?: DashboardSpec;
  dataset_id?: string | null;
  conversation_id?: string | null;
  root_cause: string;
  recommended_actions: string[];
  kpis: KpiSnapshot;
  downtime: Array<Record<string, string | number>>;
  comparison: Record<string, unknown>;
  sop_matches: Array<Record<string, string>>;
  shift_report: {
    title: string;
    summary: string;
    downtime_summary: string;
    recommended_actions: string[];
  };
  maintenance_ticket: {
    id: string;
    line: string;
    issue: string;
    priority: string;
    evidence: string[];
    status: string;
  };
  flow_spec: {
    name: string;
    trigger: string;
    actions: string[];
    target_users: string[];
    connectors: string[];
  };
  tool_trace: ToolCall[];
  usage: {
    provider: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    latency_ms: number;
  };
};

export type DashboardCard = {
  label: string;
  value: string;
  detail: string;
  tone: "signal" | "warning" | "danger" | "neutral";
};

export type DashboardTable = {
  title: string;
  columns: string[];
  rows: string[][];
};

export type DashboardSpec = {
  title: string;
  cards: DashboardCard[];
  insights: string[];
  tables: DashboardTable[];
  chart_hints: Array<Record<string, unknown>>;
};

export type DatasetSummary = {
  id: string;
  name: string;
  kind: "csv" | "excel" | "sqlite";
  created_at: string;
  tables: string[];
  row_count: number;
  columns: string[];
};
