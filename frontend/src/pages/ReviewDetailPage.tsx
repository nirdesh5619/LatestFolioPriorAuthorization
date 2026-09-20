import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { AgentTraceEntry, DeterminationStatus, ReviewDetail } from "../api/types";
import AssessmentResult from "../components/AssessmentResult";
import AgentTraceAccordion from "../components/AgentTraceAccordion";
import { ReviewDecisionBadge, ReviewStatusBadge } from "../components/Badge";

const DETERMINATIONS: DeterminationStatus[] = ["approved", "denied", "pended"];

export default function ReviewDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const id = Number(runId);
  const navigate = useNavigate();

  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [trace, setTrace] = useState<AgentTraceEntry[]>([]);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);
  const [showTrace, setShowTrace] = useState(false);

  const [reviewerName, setReviewerName] = useState("");
  const [decision, setDecision] = useState<"uphold" | "override">("uphold");
  const [finalDetermination, setFinalDetermination] = useState<DeterminationStatus>("approved");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getReviewDetail(id)
      .then((d) => {
        setDetail(d);
        if (d.ai_response.determination) setFinalDetermination(d.ai_response.determination);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load review detail."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const toggleTrace = () => {
    const next = !showTrace;
    setShowTrace(next);
    if (next && trace.length === 0 && !traceLoading) {
      setTraceLoading(true);
      setTraceError(null);
      api
        .getTrace(id)
        .then(setTrace)
        .catch((err) => setTraceError(err instanceof ApiError ? err.message : "Failed to load agent trace."))
        .finally(() => setTraceLoading(false));
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!reviewerName.trim()) {
      setSubmitError("Reviewer name is required.");
      return;
    }
    if (decision === "override" && !notes.trim()) {
      setSubmitError("Notes are required when overriding the AI determination.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.submitReview(id, {
        reviewer_name: reviewerName.trim(),
        decision,
        final_determination: decision === "override" ? finalDetermination : undefined,
        notes: notes.trim(),
      });
      load();
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Failed to submit review.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && !detail) return <p className="loading">Loading…</p>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!detail) return null;

  return (
    <div>
      <Link to="/review">&larr; Back to review queue</Link>

      <div className="page-title" style={{ marginTop: 12 }}>
        <h2>Review determination #{detail.run_id}</h2>
        <ReviewStatusBadge status={detail.review_status} />
      </div>

      <AssessmentResult response={detail.ai_response} />

      <div className="card">
        <div className="page-title" style={{ marginBottom: 0 }}>
          <h3 style={{ margin: 0 }}>Agent trace</h3>
          <button type="button" className="secondary" onClick={toggleTrace}>
            {showTrace ? "Hide agent trace" : "Show agent trace"}
          </button>
        </div>
        <p className="muted" style={{ marginTop: 2 }}>
          The full input and output of every agent that ran for this determination, one collapsible
          section per agent.
        </p>

        {showTrace && (
          <div style={{ marginTop: 10 }}>
            {traceLoading && <p className="loading">Loading agent trace…</p>}
            {traceError && <div className="error-banner">{traceError}</div>}
            {!traceLoading && !traceError && <AgentTraceAccordion trace={trace} />}
          </div>
        )}
      </div>

      <div className="card">
        <h3>Human review</h3>

        {detail.review_status === "reviewed" ? (
          <>
            <div className="field-grid">
              <div>
                <div className="label">Reviewer</div>
                <div>{detail.reviewer_name}</div>
              </div>
              <div>
                <div className="label">Decision</div>
                <ReviewDecisionBadge decision={detail.reviewer_decision} />
              </div>
              <div>
                <div className="label">Final determination</div>
                <div>{detail.final_determination}</div>
              </div>
              <div>
                <div className="label">Reviewed at</div>
                <div>{detail.reviewed_at ? new Date(detail.reviewed_at).toLocaleString() : "—"}</div>
              </div>
            </div>
            {detail.reviewer_notes && (
              <div className="evidence-block" style={{ marginTop: 12 }}>
                <div className="label">Reviewer notes</div>
                <p style={{ margin: "4px 0 0" }}>{detail.reviewer_notes}</p>
              </div>
            )}
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div>
                <label>Reviewer name *</label>
                <input value={reviewerName} onChange={(e) => setReviewerName(e.target.value)} placeholder="Dr. Jane Smith" />
              </div>
              <div>
                <label>Decision</label>
                <select value={decision} onChange={(e) => setDecision(e.target.value as "uphold" | "override")}>
                  <option value="uphold">Uphold AI determination ({detail.ai_response.determination})</option>
                  <option value="override">Override</option>
                </select>
              </div>
              {decision === "override" && (
                <div>
                  <label>Final determination *</label>
                  <select value={finalDetermination} onChange={(e) => setFinalDetermination(e.target.value as DeterminationStatus)}>
                    {DETERMINATIONS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
              <div>
                <label>Notes {decision === "override" ? "*" : "(optional)"}</label>
                <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
              </div>
            </div>
            <button type="submit" disabled={submitting}>
              {submitting ? "Submitting…" : decision === "override" ? "Submit override" : "Uphold & submit"}
            </button>
            {submitError && (
              <div className="error-banner" style={{ marginTop: 12 }}>
                {submitError}
              </div>
            )}
          </form>
        )}
      </div>

      {detail.review_status === "reviewed" && (
        <button className="secondary" onClick={() => navigate("/review")}>
          Back to queue
        </button>
      )}
    </div>
  );
}
