import { api } from "../api/client";
import type { FinalClinicalResponse } from "../api/types";
import { CriterionStatusBadge, DeterminationBadge, RiskBadge } from "./Badge";

interface Props {
  response: FinalClinicalResponse;
}

export default function AssessmentResult({ response }: Props) {
  return (
    <div className="card">
      <div className="page-title">
        <h3 style={{ margin: 0 }}>Determination #{response.run_id}</h3>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <DeterminationBadge determination={response.determination} />
          <a
            className="btn secondary"
            href={api.getReportUrl(response.run_id)}
            target="_blank"
            rel="noopener noreferrer"
          >
            Download PDF report
          </a>
        </div>
      </div>

      {response.requested_service && (
        <p className="muted" style={{ marginTop: -8 }}>
          Requested service: <strong>{response.requested_service}</strong>
        </p>
      )}

      <p>{response.summary}</p>

      {response.decision_rationale && (
        <div className="evidence-block">
          <div className="label">Rationale</div>
          <p style={{ margin: "4px 0 0" }}>{response.decision_rationale}</p>
          <div className="muted" style={{ marginTop: 6 }}>
            {response.llm_usage
              ? `Drafted by ${response.llm_usage.model} (${response.llm_usage.input_tokens} input + ${response.llm_usage.output_tokens} output tokens)`
              : "Drafted from a deterministic template (no LLM configured for this run)"}
          </div>
        </div>
      )}

      {response.approval_path_suggestion && (
        <div className="evidence-block">
          <div className="label">Path to approval</div>
          <p style={{ margin: "4px 0 0" }}>{response.approval_path_suggestion}</p>
          <div className="muted" style={{ marginTop: 6 }}>
            {response.scenario_llm_usage
              ? `Drafted by ${response.scenario_llm_usage.model} (${response.scenario_llm_usage.input_tokens} input + ${response.scenario_llm_usage.output_tokens} output tokens)`
              : "Drafted from a deterministic template (no LLM configured for this run)"}
          </div>
        </div>
      )}

      {response.requires_clinician_review && (
        <p style={{ fontWeight: 600, color: "var(--color-danger)" }}>
          Requires clinical reviewer sign-off before this determination is communicated.
        </p>
      )}

      <div className="field-grid" style={{ marginTop: 10 }}>
        <div>
          <div className="label">Clinical risk</div>
          <RiskBadge level={response.risk_category} />
        </div>
      </div>

      {response.identified_conditions.length > 0 && (
        <>
          <div className="label" style={{ marginTop: 10 }}>
            Identified conditions
          </div>
          <div className="pill-row">
            {response.identified_conditions.map((c) => (
              <span className="pill" key={c}>
                {c}
              </span>
            ))}
          </div>
        </>
      )}

      {response.risk_factors.length > 0 && (
        <>
          <div className="label" style={{ marginTop: 10 }}>
            Risk factors
          </div>
          <ul>
            {response.risk_factors.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </>
      )}

      {response.missing_information.length > 0 && (
        <>
          <div className="label" style={{ marginTop: 10 }}>
            Missing information
          </div>
          <ul className="flag-list">
            {response.missing_information.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </>
      )}

      {response.safety_flags.length > 0 && (
        <>
          <div className="label" style={{ marginTop: 10 }}>
            Safety flags
          </div>
          <ul className="flag-list">
            {response.safety_flags.map((f, idx) => (
              <li key={idx}>{f}</li>
            ))}
          </ul>
        </>
      )}

      {response.criteria_evaluated.length > 0 && (
        <>
          <h4>Criteria evaluated</h4>
          {response.criteria_evaluated.map((c, idx) => (
            <div key={idx} className="evidence-block">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>{c.criterion}</strong>
                <CriterionStatusBadge status={c.status} />
              </div>
              {c.patient_evidence && <p style={{ margin: "6px 0" }}>{c.patient_evidence}</p>}
              <div className="muted">
                {c.guideline} &mdash; {c.section}
              </div>
            </div>
          ))}
        </>
      )}

      {response.guideline_evidence.length > 0 && (
        <>
          <h4>Retrieved policy evidence</h4>
          {response.guideline_evidence.map((ev, idx) => (
            <div key={idx} className="evidence-block">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>
                  {ev.guideline} &mdash; {ev.section}
                </strong>
                <span className="muted">{(ev.relevance_score * 100).toFixed(0)}% relevant</span>
              </div>
              <blockquote>&ldquo;{ev.evidence}&rdquo;</blockquote>
              <div className="muted">Source: {ev.source}</div>
            </div>
          ))}
        </>
      )}

      <div className="disclaimer">{response.disclaimer}</div>
    </div>
  );
}
