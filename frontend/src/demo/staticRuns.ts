import type { RunResult } from "../types/run";

export const samplePrompt = "Why did Line A underperform yesterday and what should we do next?";

export const staticRuns: RunResult[] = [
  {
    id: "STATIC-DEMO-RUN",
    created_at: "2026-05-26T06:00:00Z",
    prompt: samplePrompt,
    line: "Line A",
    date: "2026-05-25",
    provider: "mock",
    final_answer:
      "Line A underperformed because repeated sensor faults created 94 minutes of downtime, pushing output below the previous 7-day baseline. The strongest evidence is repeated A-CELL-04 faults, manual resets, and SOP guidance for sensor escalation. Inspect and recalibrate sensors, verify cabling and PLC timestamps, hold first-hour quality containment, and review the mock maintenance ticket at handover.",
    root_cause:
      "Repeated Line A sensor faults, concentrated at A-CELL-04 and the infeed station, created abnormal downtime and recovery starvation.",
    recommended_actions: [
      "Inspect, clean, align, and recalibrate A-CELL-04 and infeed sensors.",
      "Validate PLC fault timestamps and cable continuity with maintenance controls owner.",
      "Run first-hour containment and confirm OEE recovery before closing the ticket.",
      "Activate the escalation flow when repeated sensor faults occur in one shift."
    ],
    kpis: {
      line: "Line A",
      date: "2026-05-25",
      target_units: 5000,
      actual_units: 4210,
      oee: 0.681,
      scrap_rate: 0.034,
      downtime_minutes: 94
    },
    downtime: [
      {
        start_time: "06:42",
        duration_minutes: 21,
        category: "sensor_fault",
        reason: "Repeated photoeye misread at infeed station",
        station: "A-INFEED-02"
      },
      {
        start_time: "10:18",
        duration_minutes: 34,
        category: "sensor_fault",
        reason: "Proximity sensor alignment drift after changeover",
        station: "A-CELL-04"
      },
      {
        start_time: "13:57",
        duration_minutes: 24,
        category: "sensor_fault",
        reason: "Intermittent cable signal on conveyor guard sensor",
        station: "A-CELL-04"
      }
    ],
    comparison: {
      avg_actual_units: 4726.1,
      avg_oee: 0.838,
      avg_downtime_minutes: 31.7,
      actual_delta_units: -516.1,
      oee_delta: -0.157,
      downtime_delta_minutes: 62.3
    },
    sop_matches: [
      {
        id: "SOP-QA-014",
        title: "Sensor Fault Escalation",
        body: "Repeated sensor faults require inspection, cleaning, bracket alignment, calibration check, and maintenance escalation."
      }
    ],
    shift_report: {
      title: "Line A Shift Performance Report - 2026-05-25",
      summary: "Line A produced 4210 of 5000 target units with OEE 68.1%.",
      downtime_summary: "Primary loss categories: sensor_fault, minor_stop.",
      recommended_actions: ["Recalibrate sensors", "Validate PLC timestamps", "Contain quality risk"]
    },
    maintenance_ticket: {
      id: "MOCK-A184F29C",
      line: "Line A",
      issue: "Repeated sensor faults at A-CELL-04 causing output loss",
      priority: "high",
      evidence: ["Three stops cleared by manual sensor reset"],
      status: "mock-created"
    },
    flow_spec: {
      name: "Line A Sensor Fault Escalation",
      trigger: "When downtime category sensor_fault appears twice in one shift",
      actions: ["Post Teams alert", "Create Planner task", "Email shift report"],
      target_users: ["Shift Lead", "Maintenance Planner", "Quality Engineer"],
      connectors: ["SharePoint", "Teams", "Outlook", "Planner"]
    },
    tool_trace: [
      { name: "get_production_kpis", args: {}, status: "ok", duration_ms: 4, result_preview: "Line A KPI snapshot loaded" },
      { name: "get_downtime_events", args: {}, status: "ok", duration_ms: 5, result_preview: "4 downtime events loaded" },
      { name: "compare_line_performance", args: {}, status: "ok", duration_ms: 7, result_preview: "7-day baseline compared" },
      { name: "search_sop", args: {}, status: "ok", duration_ms: 3, result_preview: "SOP-QA-014 matched" },
      { name: "generate_shift_report", args: {}, status: "ok", duration_ms: 9, result_preview: "Shift report generated" },
      { name: "create_maintenance_ticket", args: {}, status: "ok", duration_ms: 6, result_preview: "MOCK-A184F29C" },
      { name: "create_power_automate_flow_spec", args: {}, status: "ok", duration_ms: 5, result_preview: "Flow spec generated" }
    ],
    usage: {
      provider: "mock",
      model: "deterministic-factoryops-v1",
      prompt_tokens: 132,
      completion_tokens: 96,
      total_tokens: 228,
      latency_ms: 22
    }
  }
];
