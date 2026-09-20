import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { GuidelineSearchResult, GuidelineSummary } from "../api/types";

export default function GuidelineSearchPage() {
  const [guidelines, setGuidelines] = useState<GuidelineSummary[]>([]);
  const [query, setQuery] = useState("bariatric surgery BMI criteria");
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<GuidelineSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    api.listGuidelines().then(setGuidelines).catch(() => setGuidelines([]));
  }, []);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    setSearching(true);
    setError(null);
    try {
      const response = await api.searchGuidelines(query, topK);
      setResults(response.results);
      setSearched(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <div className="page-title">
        <h2>Coverage policy library</h2>
      </div>

      <div className="card">
        <div className="pill-row">
          {guidelines.map((g) => (
            <span className="pill" key={g.guideline_id} title={g.source_file}>
              {g.condition}
            </span>
          ))}
          {guidelines.length === 0 && <span className="muted">No guidelines indexed yet.</span>}
        </div>
      </div>

      <div className="card">
        <form onSubmit={handleSearch}>
          <div className="form-grid" style={{ gridTemplateColumns: "3fr 1fr" }}>
            <div>
              <label>Search query</label>
              <input value={query} onChange={(e) => setQuery(e.target.value)} required />
            </div>
            <div>
              <label>Top K</label>
              <input type="number" min={1} max={20} value={topK} onChange={(e) => setTopK(Number(e.target.value))} />
            </div>
          </div>
          <button type="submit" disabled={searching}>
            {searching ? "Searching…" : "Search guidelines"}
          </button>
        </form>
        {error && (
          <div className="error-banner" style={{ marginTop: 12 }}>
            {error}
          </div>
        )}
      </div>

      {searched && results.length === 0 && !error && (
        <p className="empty-state">No sufficiently relevant guideline content was found.</p>
      )}

      {results.map((r, idx) => (
        <div className="card" key={idx}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
            <strong>
              {r.guideline} &mdash; {r.section}
            </strong>
            <span className="muted">{(r.score * 100).toFixed(0)}% match</span>
          </div>
          <div className="evidence-block">
            <blockquote>&ldquo;{r.text}&rdquo;</blockquote>
          </div>
          <div className="muted">
            Source: {r.source} (page {r.page})
          </div>
        </div>
      ))}
    </div>
  );
}
