import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { ReviewQueueItem } from "../api/types";
import { DeterminationBadge } from "../components/Badge";

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getReviewQueue()
      .then(setQueue)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load review queue."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <div className="page-title">
        <h2>Review queue</h2>
        <button className="secondary" onClick={() => load()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p className="muted" style={{ marginTop: -10 }}>
        Every determination requires a clinical reviewer's sign-off before it is final. This queue lists
        completed determinations awaiting that review, oldest first.
      </p>

      {error && <div className="error-banner">{error}</div>}
      {loading && queue.length === 0 && <p className="loading">Loading queue…</p>}

      {!loading && queue.length === 0 && !error && (
        <p className="empty-state">Nothing pending review right now.</p>
      )}

      <div className="grid">
        {queue.map((item) => (
          <div className="card patient-card" key={item.run_id} onClick={() => navigate(`/review/${item.run_id}`)}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <h3 style={{ margin: 0 }}>#{item.run_id}</h3>
              <DeterminationBadge determination={item.determination} />
            </div>
            <div className="muted">{item.patient_identifier ?? `Patient ${item.patient_id}`}</div>
            <div style={{ margin: "8px 0" }}>{item.requested_service ?? "—"}</div>
            <div className="pill-row">
              <span className="pill">{item.urgency}</span>
              <span className="pill">{item.status.replace(/_/g, " ")}</span>
            </div>
            <div className="muted" style={{ marginTop: 8 }}>
              Submitted {new Date(item.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
