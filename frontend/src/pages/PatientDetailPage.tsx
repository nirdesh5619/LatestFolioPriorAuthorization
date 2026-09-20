import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, runOrchestrationStream } from "../api/client";
import type { AgentTraceEntry, FinalClinicalResponse, Patient, PriorAuthRequestPayload } from "../api/types";
import AssessmentResult from "../components/AssessmentResult";
import AgentPipeline from "../components/AgentPipeline";
import AgentTraceView from "../components/AgentTraceView";
import { applyAgentEvent, buildInitialPipeline, finalizePipeline, type PipelineState } from "../agentPipeline";

const SERVICE_CATEGORIES = ["imaging", "surgery", "medication", "therapy", "dme", "other"];

// Maps the controlled medical_history vocabulary (see backend/data/patients) to a
// representative ICD-10 code, so the request form can pre-fill diagnosis codes
// instead of asking the user to recall/type them from scratch. Unrecognized
// history entries fall back to their own (de-underscored) label so nothing is
// silently dropped.
const CONDITION_ICD10: Record<string, string> = {
  type_2_diabetes: "E11.9",
  hypertension: "I10",
  dyslipidemia: "E78.5",
  obesity: "E66.9",
  coronary_artery_disease: "I25.10",
  chronic_kidney_disease: "N18.9",
  atrial_fibrillation: "I48.91",
  heart_failure: "I50.9",
};

function conditionsToIcdCodes(conditions: string[]): string {
  return conditions.map((c) => CONDITION_ICD10[c] ?? c.replace(/_/g, " ")).join(", ");
}

interface RequestForm {
  requestedService: string;
  serviceCategory: string;
  diagnosisCodes: string;
  urgency: string;
  priorTreatments: string;
  clinicalQuestion: string;
}

const DEFAULT_REQUEST_FORM: RequestForm = {
  requestedService: "",
  serviceCategory: "imaging",
  diagnosisCodes: "",
  urgency: "routine",
  priorTreatments: "",
  clinicalQuestion: "",
};

function toList(value: string): string[] {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div>{value === null || value === undefined || value === "" ? "—" : value}</div>
    </div>
  );
}

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const patientId = Number(id);

  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<RequestForm>(DEFAULT_REQUEST_FORM);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [requestedServiceInvalid, setRequestedServiceInvalid] = useState(false);
  const requestedServiceRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<FinalClinicalResponse | null>(null);

  const [trace, setTrace] = useState<AgentTraceEntry[]>([]);
  const [pipeline, setPipeline] = useState<PipelineState | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getPatient(patientId)
      .then((p) => {
        if (!cancelled) {
          setPatient(p);
          setForm((prev) => ({ ...prev, diagnosisCodes: conditionsToIcdCodes(p.medical_history) }));
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load patient.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  const handleRun = async () => {
    if (!form.requestedService.trim()) {
      setRunError("Requested service is required.");
      setRequestedServiceInvalid(true);
      requestedServiceRef.current?.focus();
      return;
    }

    setRunning(true);
    setRunError(null);
    setRequestedServiceInvalid(false);
    setResult(null);
    setTrace([]);
    setPipeline(buildInitialPipeline());

    const payload: PriorAuthRequestPayload = {
      patient_id: patientId,
      requested_service: form.requestedService.trim(),
      service_category: form.serviceCategory,
      diagnosis_codes: toList(form.diagnosisCodes),
      urgency: form.urgency,
      prior_treatments_tried: toList(form.priorTreatments),
      clinical_question: form.clinicalQuestion.trim(),
    };

    try {
      for await (const event of runOrchestrationStream(payload)) {
        if (event.type === "agent") {
          setPipeline((prev) => applyAgentEvent(prev ?? buildInitialPipeline(), event));
          setTrace((prev) => [
            ...prev,
            {
              agent: event.agent,
              status: event.status,
              input: event.input,
              output: event.output,
              execution_time_ms: event.execution_time_ms,
              timestamp: new Date().toISOString(),
            },
          ]);
        } else {
          const { type: _type, ...response } = event;
          setResult(response as FinalClinicalResponse);
          setPipeline((prev) => finalizePipeline(prev ?? buildInitialPipeline()));
        }
      }
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Failed to run orchestration.");
      setPipeline((prev) => (prev ? finalizePipeline(prev) : prev));
    } finally {
      setRunning(false);
    }
  };

  const runningAgent = pipeline
    ? Object.entries(pipeline).find(([, s]) => s.status === "running")?.[0] ?? null
    : null;

  if (loading) return <p className="loading">Loading patient…</p>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!patient) return null;

  return (
    <div>
      <Link to="/">&larr; Back to patients</Link>

      <div className="page-title" style={{ marginTop: 12 }}>
        <h2>{patient.patient_identifier}</h2>
      </div>

      <div className="card">
        <h3>Demographics</h3>
        <div className="field-grid">
          <Field label="Age" value={patient.age} />
          <Field label="Gender" value={patient.gender} />
          <Field label="BMI" value={patient.bmi} />
          <Field label="Smoking status" value={patient.smoking_status} />
        </div>

        <h3>Vitals & labs</h3>
        <div className="field-grid">
          <Field
            label="Blood pressure"
            value={patient.systolic_bp && patient.diastolic_bp ? `${patient.systolic_bp}/${patient.diastolic_bp} mmHg` : null}
          />
          <Field label="Heart rate" value={patient.heart_rate} />
          <Field label="Total cholesterol" value={patient.total_cholesterol} />
          <Field label="LDL" value={patient.ldl} />
          <Field label="HDL" value={patient.hdl} />
          <Field label="Triglycerides" value={patient.triglycerides} />
          <Field label="HbA1c" value={patient.hba1c} />
          <Field label="Fasting glucose" value={patient.fasting_glucose} />
        </div>

        <h3>History</h3>
        <div className="pill-row">
          {patient.medical_history.length === 0 && <span className="muted">None documented</span>}
          {patient.medical_history.map((c) => (
            <span className="pill" key={c}>
              {c.replace(/_/g, " ")}
            </span>
          ))}
        </div>

        <h3>Current medications</h3>
        <div className="pill-row">
          {patient.current_medications.length === 0 && <span className="muted">None documented</span>}
          {patient.current_medications.map((m) => (
            <span className="pill" key={m}>
              {m.replace(/_/g, " ")}
            </span>
          ))}
        </div>

        <h3>Allergies</h3>
        <div className="pill-row">
          {patient.allergies.length === 0 && <span className="muted">None documented</span>}
          {patient.allergies.map((a) => (
            <span className="pill" key={a}>
              {a}
            </span>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>New prior authorization request</h3>
        <div className="form-grid">
          <div>
            <label>Requested service *</label>
            <input
              ref={requestedServiceRef}
              required
              aria-invalid={requestedServiceInvalid}
              className={requestedServiceInvalid ? "input-error" : undefined}
              value={form.requestedService}
              onChange={(e) => {
                setForm((prev) => ({ ...prev, requestedService: e.target.value }));
                if (requestedServiceInvalid && e.target.value.trim()) setRequestedServiceInvalid(false);
              }}
              placeholder="e.g. Lumbar spine MRI, Bariatric surgery, Adalimumab"
            />
          </div>
          <div>
            <label>Service category</label>
            <select
              value={form.serviceCategory}
              onChange={(e) => setForm((prev) => ({ ...prev, serviceCategory: e.target.value }))}
            >
              {SERVICE_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label>Urgency</label>
            <select value={form.urgency} onChange={(e) => setForm((prev) => ({ ...prev, urgency: e.target.value }))}>
              <option value="routine">routine</option>
              <option value="urgent">urgent</option>
              <option value="emergent">emergent</option>
            </select>
          </div>
        </div>

        <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
          <div>
            <label>Diagnosis codes (comma-separated)</label>
            <input
              value={form.diagnosisCodes}
              onChange={(e) => setForm((prev) => ({ ...prev, diagnosisCodes: e.target.value }))}
              placeholder="e.g. M54.5, E66.01"
            />
            <div className="muted" style={{ marginTop: 4, fontSize: 12 }}>
              {patient.medical_history.length > 0
                ? "Auto-filled from this patient's documented history — add or remove codes for this specific request."
                : "No documented history to auto-fill from — enter ICD-10 codes for this request."}
            </div>
          </div>
          <div>
            <label>Prior treatments tried (comma-separated)</label>
            <input
              value={form.priorTreatments}
              onChange={(e) => setForm((prev) => ({ ...prev, priorTreatments: e.target.value }))}
              placeholder="e.g. physical therapy for 8 weeks, methotrexate"
            />
          </div>
          <div>
            <label>Additional clinical justification (optional)</label>
            <textarea
              rows={2}
              value={form.clinicalQuestion}
              onChange={(e) => setForm((prev) => ({ ...prev, clinicalQuestion: e.target.value }))}
            />
          </div>
        </div>

        <button onClick={handleRun} disabled={running}>
          {running ? "Running multi-agent determination…" : "Submit for determination"}
        </button>
        {runError && (
          <div className="error-banner" style={{ marginTop: 12 }}>
            {runError}
          </div>
        )}
      </div>

      {pipeline && (
        <div className="card">
          <h3>Multi-agent orchestration</h3>
          <p className="muted" style={{ marginTop: -6 }}>
            {running
              ? "Running — each step lights up live as that agent actually completes on the backend."
              : "Pipeline for this run. Dashed/faded steps were skipped by the workflow's routing rules."}
          </p>
          <AgentPipeline pipeline={pipeline} />

          <h4 style={{ marginBottom: 4 }}>Live agent details</h4>
          <p className="muted" style={{ marginTop: 0 }}>
            Each row appears the instant that agent finishes — full input and output it received/produced.
          </p>
          <AgentTraceView trace={trace} runningAgent={runningAgent} />
        </div>
      )}

      {result && (
        <>
          <div className="card" style={{ background: "#eef3f7", border: "1px dashed var(--color-border)" }}>
            This AI determination has been queued for human review and is not yet final.{" "}
            <Link to={`/review/${result.run_id}`}>Go to review &rarr;</Link>
          </div>
          <AssessmentResult response={result} />
        </>
      )}
    </div>
  );
}
