import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CostMetrics, CostPeriod, MetricsPeriod, ObservabilityMetrics } from "../api/types";
import { AgentLatencyChart } from "../charts/AgentLatencyChart";
import { AgentReliabilityChart } from "../charts/AgentReliabilityChart";
import { DETERMINATION_COLORS, REVIEW_DECISION_COLORS } from "../charts/colors";
import { CostTrendChart } from "../charts/CostTrendChart";
import { StackedOutcomeBar } from "../charts/StackedOutcomeBar";

const COST_PERIOD_LABELS: Record<CostPeriod, string> = {
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  month: "This month",
  year: "This year",
  custom: "Custom range",
};

const METRICS_PERIOD_LABELS: Record<MetricsPeriod, string> = {
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  month: "Last 1 month",
  year: "Last 1 year",
  all: "All time",
};

const LLM_PROVIDER_ENV_VAR: Record<string, string> = {
  anthropic: "ANTHROPIC_API_KEY",
  openai: "OPENAI_API_KEY",
};

function formatUsd(v: number): string {
  return `$${v.toFixed(4)}`;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function StatTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="stat-tile">
      <div className="stat-tile-value">{value}</div>
      <div className="stat-tile-label">{label}</div>
      {sub && <div className="stat-tile-sub">{sub}</div>}
    </div>
  );
}

function HealthPill({ label, ok, text }: { label: string; ok: boolean; text: string }) {
  return (
    <div className="health-pill">
      <span className={`health-dot ${ok ? "health-dot-up" : "health-dot-down"}`} />
      <span className="label" style={{ margin: 0 }}>
        {label}
      </span>
      <strong>{text}</strong>
    </div>
  );
}

export default function ObservabilityPage() {
  const [metrics, setMetrics] = useState<ObservabilityMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [metricsPeriod, setMetricsPeriod] = useState<MetricsPeriod>("all");

  const [costPeriod, setCostPeriod] = useState<CostPeriod>("30d");
  const [customStart, setCustomStart] = useState(todayIso());
  const [customEnd, setCustomEnd] = useState(todayIso());
  const [costMetrics, setCostMetrics] = useState<CostMetrics | null>(null);
  const [costError, setCostError] = useState<string | null>(null);
  const [costLoading, setCostLoading] = useState(true);

  const load = (period: MetricsPeriod = metricsPeriod) => {
    setLoading(true);
    setError(null);
    api
      .getMetrics(period)
      .then(setMetrics)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load metrics."))
      .finally(() => setLoading(false));
  };

  const loadCosts = (period: CostPeriod, startDate?: string, endDate?: string) => {
    setCostLoading(true);
    setCostError(null);
    api
      .getCostMetrics({ period, startDate, endDate })
      .then(setCostMetrics)
      .catch((err) => setCostError(err instanceof ApiError ? err.message : "Failed to load cost metrics."))
      .finally(() => setCostLoading(false));
  };

  useEffect(() => {
    load(metricsPeriod);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metricsPeriod]);

  useEffect(() => {
    if (costPeriod !== "custom") {
      loadCosts(costPeriod);
    }
    // Custom range is applied explicitly via the "Apply" button below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [costPeriod]);

  const applyCustomRange = () => {
    loadCosts("custom", `${customStart}T00:00:00`, `${customEnd}T23:59:59`);
  };

  return (
    <div>
      <div className="page-title">
        <h2>Observability</h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <select value={metricsPeriod} onChange={(e) => setMetricsPeriod(e.target.value as MetricsPeriod)}>
            {(Object.keys(METRICS_PERIOD_LABELS) as MetricsPeriod[]).map((p) => (
              <option key={p} value={p}>
                {METRICS_PERIOD_LABELS[p]}
              </option>
            ))}
          </select>
          <button className="secondary" onClick={() => load()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>
      <p className="muted" style={{ marginTop: -8 }}>
        Health, volume, outcomes, per-agent stats, and recent requests below are scoped to{" "}
        {METRICS_PERIOD_LABELS[metricsPeriod].toLowerCase()}.
      </p>

      {error && <div className="error-banner">{error}</div>}
      {loading && !metrics && <p className="loading">Loading metrics…</p>}

      {metrics && (
        <>
          <div className="card">
            <h3>System health</h3>
            <div className="health-row">
              <HealthPill label="Database" ok={metrics.health.database === "UP"} text={metrics.health.database} />
              <HealthPill label="Vector store" ok={metrics.health.vector_store === "UP"} text={metrics.health.vector_store} />
              <HealthPill
                label="LLM"
                ok={metrics.health.llm_configured}
                text={metrics.health.llm_configured ? "configured" : "not configured"}
              />
            </div>
          </div>

          <div className="card">
            <h3>Volume &amp; value</h3>
            <div className="stat-grid">
              <StatTile label="Total requests" value={metrics.total_requests} />
              <StatTile label="Completed" value={metrics.completed_requests} />
              <StatTile label="Pended (insufficient info)" value={metrics.insufficient_information_requests} />
              <StatTile
                label="Avg end-to-end latency"
                value={metrics.avg_end_to_end_latency_ms != null ? `${metrics.avg_end_to_end_latency_ms.toFixed(0)} ms` : "—"}
              />
              <StatTile
                label="Clinician review rate"
                value={`${(metrics.requires_clinician_review_rate * 100).toFixed(0)}%`}
                sub="Every completed run requires sign-off, by design"
              />
            </div>

            <h4 style={{ marginTop: 18, marginBottom: 0 }}>Determination outcomes</h4>
            <StackedOutcomeBar
              emptyMessage="No completed determinations yet."
              segments={[
                { key: "approved", label: "Approved", value: metrics.determination_breakdown.approved, color: DETERMINATION_COLORS.approved },
                { key: "denied", label: "Denied", value: metrics.determination_breakdown.denied, color: DETERMINATION_COLORS.denied },
                { key: "pended", label: "Pended", value: metrics.determination_breakdown.pended, color: DETERMINATION_COLORS.pended },
              ]}
            />
          </div>

          <div className="card">
            <div className="page-title" style={{ marginBottom: 0 }}>
              <h3 style={{ margin: 0 }}>Human-in-the-loop review</h3>
              <Link to="/review">Open review queue &rarr;</Link>
            </div>
            <div className="stat-grid">
              <StatTile label="Pending review" value={metrics.review.pending_count} />
              <StatTile label="Reviewed" value={metrics.review.reviewed_count} />
              <StatTile
                label="Avg time to review"
                value={metrics.review.avg_time_to_review_ms != null ? `${(metrics.review.avg_time_to_review_ms / 1000).toFixed(1)} s` : "—"}
              />
            </div>

            <h4 style={{ marginTop: 18, marginBottom: 0 }}>Reviewer decisions</h4>
            <p className="muted" style={{ marginTop: 2 }}>
              Override rate is a trust metric: how often a human actually disagreed with the AI.
            </p>
            <StackedOutcomeBar
              emptyMessage="Nothing reviewed yet."
              segments={[
                { key: "upheld", label: "Upheld", value: metrics.review.upheld_count, color: REVIEW_DECISION_COLORS.upheld },
                { key: "overridden", label: "Overridden", value: metrics.review.overridden_count, color: REVIEW_DECISION_COLORS.overridden },
              ]}
            />
          </div>

          <div className="card">
            <h3>Per-agent latency (avg vs. p95)</h3>
            <p className="muted" style={{ marginTop: -6 }}>
              Log scale — guideline retrieval's embedding call can be orders of magnitude slower than the
              other agents on a cold start.
            </p>
            <AgentLatencyChart agentStats={metrics.agent_stats} />
          </div>

          <div className="card">
            <h3>Per-agent reliability</h3>
            <AgentReliabilityChart agentStats={metrics.agent_stats} />

            {metrics.agent_stats.length > 0 && (
              <div style={{ overflowX: "auto", marginTop: 16 }}>
                <table className="trace-table">
                  <thead>
                    <tr>
                      <th>Agent</th>
                      <th>Calls</th>
                      <th>Success</th>
                      <th>Error</th>
                      <th>Avg time</th>
                      <th>P95 time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.agent_stats.map((a) => (
                      <tr key={a.agent}>
                        <td>{a.agent}</td>
                        <td>{a.total_calls}</td>
                        <td>{a.success_count}</td>
                        <td>{a.error_count}</td>
                        <td>{a.avg_execution_time_ms.toFixed(2)} ms</td>
                        <td>{a.p95_execution_time_ms.toFixed(2)} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <h3>LLM usage &amp; token cost</h3>
            {!metrics.llm_usage.enabled ? (
              <p className="muted">
                No LLM is configured (
                <code>{LLM_PROVIDER_ENV_VAR[metrics.health.llm_provider] ?? "API key"}</code> unset for provider{" "}
                <code>{metrics.health.llm_provider}</code>) — the Determination Agent is using a deterministic
                templated rationale for every run, so there is no token usage to report.
                {metrics.llm_usage.fallback_count > 0 && ` (${metrics.llm_usage.fallback_count} run(s) used the template.)`}
              </p>
            ) : (
              <div className="stat-grid">
                <StatTile label="Provider" value={metrics.health.llm_provider} />
                <StatTile label="Model" value={metrics.llm_usage.model ?? "—"} />
                <StatTile label="LLM calls" value={metrics.llm_usage.total_calls} />
                <StatTile label="Input tokens" value={metrics.llm_usage.total_input_tokens.toLocaleString()} />
                <StatTile label="Output tokens" value={metrics.llm_usage.total_output_tokens.toLocaleString()} />
                <StatTile label="Total tokens" value={metrics.llm_usage.total_tokens.toLocaleString()} />
                <StatTile label="Avg tokens/call" value={metrics.llm_usage.avg_tokens_per_call} />
                <StatTile label="Estimated cost (all-time)" value={formatUsd(metrics.llm_usage.estimated_cost_usd)} sub="Illustrative list pricing, not billing-accurate" />
                {metrics.llm_usage.fallback_count > 0 && (
                  <StatTile label="Fallback (LLM unavailable)" value={metrics.llm_usage.fallback_count} />
                )}
              </div>
            )}
            {metrics.llm_usage.enabled && (
              <>
                <h4 style={{ marginTop: 18, marginBottom: 0 }}>Spend at a glance</h4>
                <div className="stat-grid">
                  <StatTile label="Last 7 days" value={formatUsd(metrics.llm_usage.cost_last_7_days_usd)} />
                  <StatTile label="This month" value={formatUsd(metrics.llm_usage.cost_this_month_usd)} />
                  <StatTile label="This year" value={formatUsd(metrics.llm_usage.cost_this_year_usd)} />
                </div>
              </>
            )}
          </div>

          <div className="card">
            <div className="page-title" style={{ marginBottom: 0 }}>
              <h3 style={{ margin: 0 }}>Cost per execution</h3>
            </div>
            <p className="muted" style={{ marginTop: 2 }}>
              Filter LLM spend by period to see the trend and the cost of each individual run
              (rationale + approval-path-suggestion calls combined).
            </p>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end", marginTop: 10 }}>
              <div style={{ minWidth: 160 }}>
                <div className="label">Period</div>
                <select value={costPeriod} onChange={(e) => setCostPeriod(e.target.value as CostPeriod)}>
                  {(Object.keys(COST_PERIOD_LABELS) as CostPeriod[]).map((p) => (
                    <option key={p} value={p}>
                      {COST_PERIOD_LABELS[p]}
                    </option>
                  ))}
                </select>
              </div>
              {costPeriod === "custom" && (
                <>
                  <div>
                    <div className="label">From</div>
                    <input type="date" value={customStart} max={customEnd} onChange={(e) => setCustomStart(e.target.value)} />
                  </div>
                  <div>
                    <div className="label">To</div>
                    <input type="date" value={customEnd} min={customStart} onChange={(e) => setCustomEnd(e.target.value)} />
                  </div>
                  <button onClick={applyCustomRange} disabled={costLoading}>
                    Apply
                  </button>
                </>
              )}
            </div>

            {costError && <div className="error-banner" style={{ marginTop: 12 }}>{costError}</div>}
            {costLoading && !costMetrics && <p className="loading">Loading cost metrics…</p>}

            {costMetrics && (
              <>
                <div className="stat-grid" style={{ marginTop: 14 }}>
                  <StatTile label="Total cost" value={formatUsd(costMetrics.total_cost_usd)} sub={COST_PERIOD_LABELS[costMetrics.filters.period]} />
                  <StatTile label="Avg cost / execution" value={formatUsd(costMetrics.avg_cost_per_execution)} />
                  <StatTile label="LLM calls" value={costMetrics.total_calls} />
                  <StatTile label="Tokens" value={costMetrics.total_tokens.toLocaleString()} />
                </div>

                {costMetrics.by_call_type.some((c) => c.calls > 0) && (
                  <div className="stat-grid" style={{ marginTop: 10 }}>
                    {costMetrics.by_call_type.map((c) => (
                      <StatTile
                        key={c.call_type}
                        label={c.call_type === "rationale" ? "Rationale calls" : "Approval-path suggestion calls"}
                        value={formatUsd(c.cost_usd)}
                        sub={`${c.calls} call(s), ${(c.input_tokens + c.output_tokens).toLocaleString()} tokens`}
                      />
                    ))}
                  </div>
                )}

                <h4 style={{ marginTop: 18, marginBottom: 0 }}>Cost trend</h4>
                <CostTrendChart timeseries={costMetrics.timeseries} />

                <h4 style={{ marginTop: 18, marginBottom: 0 }}>Cost per execution</h4>
                {costMetrics.per_run.length === 0 ? (
                  <p className="empty-state">No executions with LLM spend in this range.</p>
                ) : (
                  <div style={{ overflowX: "auto" }}>
                    <table className="trace-table">
                      <thead>
                        <tr>
                          <th>Run</th>
                          <th>Requested service</th>
                          <th>Determination</th>
                          <th>Calls</th>
                          <th>Tokens</th>
                          <th>Cost</th>
                          <th>Created</th>
                        </tr>
                      </thead>
                      <tbody>
                        {costMetrics.per_run.slice(0, 50).map((r) => (
                          <tr key={r.run_id}>
                            <td>#{r.run_id}</td>
                            <td>{r.requested_service ?? "—"}</td>
                            <td>{r.determination ?? "—"}</td>
                            <td>{r.calls}</td>
                            <td>{r.tokens.toLocaleString()}</td>
                            <td>{formatUsd(r.cost_usd)}</td>
                            <td>{new Date(r.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {costMetrics.per_run.length > 50 && (
                      <p className="muted" style={{ marginTop: 6 }}>
                        Showing the 50 most recent of {costMetrics.per_run.length} executions with LLM spend in this range.
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="card">
            <h3>Recent requests</h3>
            {metrics.recent_runs.length === 0 ? (
              <p className="empty-state">No requests yet.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="trace-table">
                  <thead>
                    <tr>
                      <th>Run</th>
                      <th>Patient</th>
                      <th>Requested service</th>
                      <th>Determination</th>
                      <th>Status</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.recent_runs.map((r) => (
                      <tr key={r.run_id}>
                        <td>#{r.run_id}</td>
                        <td>{r.patient_id}</td>
                        <td>{r.requested_service ?? "—"}</td>
                        <td>{r.final_determination ?? r.determination ?? "—"}</td>
                        <td>{r.status}</td>
                        <td>{new Date(r.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <p className="muted">Last refreshed: {new Date(metrics.generated_at).toLocaleString()}</p>
        </>
      )}
    </div>
  );
}
