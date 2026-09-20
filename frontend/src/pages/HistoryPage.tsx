import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ObservabilityMetrics, RecentRun } from "../api/types";

interface RunDetail extends RecentRun {
  patient_identifier?: string | null;
}

interface TraceEntry {
  agent: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  execution_time_ms: number;
  timestamp: string;
}

interface PatientStats {
  identifier: string;
  count: number;
}

export default function HistoryPage() {
  const [allRuns, setAllRuns] = useState<RunDetail[]>([]);
  const [runs, setRuns] = useState<RunDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [traceData, setTraceData] = useState<TraceEntry[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [expandedAgents, setExpandedAgents] = useState<Set<number>>(new Set());
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null);
  const [patientStats, setPatientStats] = useState<PatientStats[]>([]);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getMetrics("all")
      .then((metrics: ObservabilityMetrics) => {
        const runsData = metrics.recent_runs.map((r) => ({
          run_id: r.run_id,
          patient_id: r.patient_id,
          patient_identifier: r.patient_identifier || `Patient ${r.patient_id}`,
          requested_service: r.requested_service,
          determination: r.determination,
          status: r.status,
          created_at: r.created_at,
        }));
        
        setAllRuns(runsData);
        setRuns(runsData);
        
        // Calculate patient statistics
        const patientMap = new Map<string, number>();
        runsData.forEach((run) => {
          const identifier = run.patient_identifier || `Patient ${run.patient_id}`;
          patientMap.set(identifier, (patientMap.get(identifier) || 0) + 1);
        });
        
        const stats = Array.from(patientMap.entries())
          .map(([identifier, count]) => ({ identifier, count }))
          .sort((a, b) => b.count - a.count);
        
        setPatientStats(stats);
        setSelectedPatient(null);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load history."))
      .finally(() => setLoading(false));
  };

  const loadTrace = (runId: number) => {
    setTraceLoading(true);
    setTraceError(null);
    setSelectedRunId(runId);
    api
      .getTrace(runId)
      .then(setTraceData)
      .catch((err) => setTraceError(err instanceof ApiError ? err.message : "Failed to load trace."))
      .finally(() => setTraceLoading(false));
  };

  const toggleAgent = (index: number) => {
    const newExpanded = new Set(expandedAgents);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedAgents(newExpanded);
  };

  const downloadReport = (runId: number) => {
    const reportUrl = api.getReportUrl(runId);
    const a = document.createElement("a");
    a.href = reportUrl;
    a.download = `report-${runId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const filterByPatient = (patientIdentifier: string | null) => {
    setSelectedPatient(patientIdentifier);
    setSelectedRunId(null);
    setTraceData([]);
    
    if (patientIdentifier === null) {
      setRuns(allRuns);
    } else {
      setRuns(allRuns.filter((run) => run.patient_identifier === patientIdentifier));
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <div className="page-title">
        <h2>Request History</h2>
        <button className="secondary" onClick={load} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p className="muted" style={{ marginTop: -10 }}>
        View complete history of all prior authorization requests with all statuses. Filter by patient identifier and
        view complete stack traces with report download options.
      </p>

      {error && <div className="error-banner">{error}</div>}
      {loading && runs.length === 0 && <p className="loading">Loading request history…</p>}

      {!loading && allRuns.length === 0 && !error && (
        <p className="empty-state">No requests yet.</p>
      )}

      {!loading && allRuns.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 1fr", gap: 16 }}>
          {/* Left panel - Patient filter */}
          <div className="card" style={{ maxHeight: "80vh", overflowY: "auto" }}>
            <h3 style={{ marginTop: 0 }}>Filter by Patient</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div
                onClick={() => filterByPatient(null)}
                style={{
                  padding: 12,
                  border: selectedPatient === null ? "2px solid #0066cc" : "1px solid #ddd",
                  borderRadius: 6,
                  cursor: "pointer",
                  backgroundColor: selectedPatient === null ? "#f0f8ff" : "#fff",
                  transition: "all 0.2s",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong>All Patients</strong>
                  <span
                    className="pill"
                    style={{
                      backgroundColor: "#e3f2fd",
                      color: "#1976d2",
                      padding: "2px 8px",
                      borderRadius: 4,
                      fontSize: 12,
                    }}
                  >
                    {allRuns.length}
                  </span>
                </div>
              </div>

              {patientStats.map((patient) => (
                <div
                  key={patient.identifier}
                  onClick={() => filterByPatient(patient.identifier)}
                  style={{
                    padding: 12,
                    border: selectedPatient === patient.identifier ? "2px solid #0066cc" : "1px solid #ddd",
                    borderRadius: 6,
                    cursor: "pointer",
                    backgroundColor: selectedPatient === patient.identifier ? "#f0f8ff" : "#fff",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {patient.identifier}
                    </strong>
                    <span
                      className="pill"
                      style={{
                        backgroundColor: "#e8f5e9",
                        color: "#2e7d32",
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: 12,
                        flexShrink: 0,
                        marginLeft: 8,
                      }}
                    >
                      {patient.count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Middle panel - List of runs */}
          <div className="card" style={{ maxHeight: "80vh", overflowY: "auto" }}>
            <h3 style={{ marginTop: 0 }}>
              Requests {selectedPatient && `for ${selectedPatient}`} ({runs.length})
            </h3>
            {runs.length === 0 ? (
              <p className="empty-state">No requests for this patient.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {runs.map((run) => (
                  <div
                    key={run.run_id}
                    onClick={() => loadTrace(run.run_id)}
                    style={{
                      padding: 12,
                      border: selectedRunId === run.run_id ? "2px solid #0066cc" : "1px solid #ddd",
                      borderRadius: 6,
                      cursor: "pointer",
                      backgroundColor: selectedRunId === run.run_id ? "#f0f8ff" : "#fff",
                      transition: "all 0.2s",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong>#{run.run_id}</strong>
                      <span
                        className="pill"
                        style={{
                          backgroundColor:
                            run.status === "completed" ? "#e8f5e9" : run.status === "running" ? "#fff3e0" : "#ffebee",
                          color:
                            run.status === "completed"
                              ? "#2e7d32"
                              : run.status === "running"
                                ? "#f57c00"
                                : "#c62828",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: 12,
                        }}
                      >
                        {run.status}
                      </span>
                    </div>
                    <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                      {run.requested_service ?? "—"}
                    </div>
                    <div style={{ marginTop: 6, display: "flex", gap: 8 }}>
                      {run.determination && (
                        <span
                          className="pill"
                          style={{
                            backgroundColor:
                              run.determination === "approved"
                                ? "#c8e6c9"
                                : run.determination === "denied"
                                  ? "#ffcdd2"
                                  : "#ffe082",
                            color:
                              run.determination === "approved"
                                ? "#1b5e20"
                                : run.determination === "denied"
                                  ? "#b71c1c"
                                  : "#f57f17",
                            padding: "2px 8px",
                            borderRadius: 4,
                            fontSize: 11,
                          }}
                        >
                          {run.determination}
                        </span>
                      )}
                    </div>
                    <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
                      {new Date(run.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right panel - Stack trace */}
          <div className="card" style={{ maxHeight: "80vh", overflowY: "auto" }}>
            {selectedRunId === null ? (
              <p className="empty-state" style={{ marginTop: 0 }}>
                Select a request to view its stack trace
              </p>
            ) : (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <h3 style={{ margin: 0 }}>Stack Trace - Request #{selectedRunId}</h3>
                  <button className="primary" onClick={() => downloadReport(selectedRunId)}>
                    📥 Download Report
                  </button>
                </div>

                {traceError && <div className="error-banner">{traceError}</div>}
                {traceLoading && <p className="loading">Loading stack trace…</p>}

                {!traceLoading && traceData.length === 0 && !traceError && (
                  <p className="empty-state">No trace data available.</p>
                )}

                {!traceLoading && traceData.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {traceData.map((entry, index) => (
                      <div
                        key={index}
                        style={{
                          border: "1px solid #ddd",
                          borderRadius: 6,
                          overflow: "hidden",
                          backgroundColor: "#fafafa",
                        }}
                      >
                        <div
                          onClick={() => toggleAgent(index)}
                          style={{
                            padding: 12,
                            backgroundColor: entry.status === "success" ? "#e8f5e9" : "#ffebee",
                            cursor: "pointer",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            userSelect: "none",
                          }}
                        >
                          <div>
                            <strong>{entry.agent}</strong>
                            <span
                              style={{
                                marginLeft: 8,
                                padding: "2px 6px",
                                borderRadius: 3,
                                fontSize: 12,
                                backgroundColor: entry.status === "success" ? "#4caf50" : "#f44336",
                                color: "#fff",
                              }}
                            >
                              {entry.status}
                            </span>
                            <span className="muted" style={{ marginLeft: 12, fontSize: 12 }}>
                              {entry.execution_time_ms.toFixed(0)}ms
                            </span>
                          </div>
                          <span style={{ fontSize: 18 }}>{expandedAgents.has(index) ? "▼" : "▶"}</span>
                        </div>

                        {expandedAgents.has(index) && (
                          <div style={{ padding: 12, borderTop: "1px solid #ddd" }}>
                            <div style={{ marginBottom: 12 }}>
                              <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 12 }}>Input:</div>
                              <pre
                                style={{
                                  backgroundColor: "#fff",
                                  padding: 8,
                                  borderRadius: 4,
                                  overflow: "auto",
                                  fontSize: 11,
                                  margin: 0,
                                }}
                              >
                                {JSON.stringify(entry.input, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 12 }}>Output:</div>
                              <pre
                                style={{
                                  backgroundColor: "#fff",
                                  padding: 8,
                                  borderRadius: 4,
                                  overflow: "auto",
                                  fontSize: 11,
                                  margin: 0,
                                }}
                              >
                                {JSON.stringify(entry.output, null, 2)}
                              </pre>
                            </div>
                            <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>
                              {new Date(entry.timestamp).toLocaleString()}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
