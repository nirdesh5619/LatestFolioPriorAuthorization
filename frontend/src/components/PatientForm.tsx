import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import type { PatientCreatePayload } from "../api/types";

interface Props {
  onSubmit: (payload: PatientCreatePayload) => Promise<void>;
  onCancel: () => void;
}

type FormState = {
  patient_identifier: string;
  age: string;
  gender: string;
  weight_kg: string;
  height_cm: string;
  smoking_status: string;
  systolic_bp: string;
  diastolic_bp: string;
  heart_rate: string;
  total_cholesterol: string;
  ldl: string;
  hdl: string;
  triglycerides: string;
  hba1c: string;
  fasting_glucose: string;
  medical_history: string;
  current_medications: string;
  allergies: string;
};

const EMPTY_FORM: FormState = {
  patient_identifier: "",
  age: "",
  gender: "female",
  weight_kg: "",
  height_cm: "",
  smoking_status: "never",
  systolic_bp: "",
  diastolic_bp: "",
  heart_rate: "",
  total_cholesterol: "",
  ldl: "",
  hdl: "",
  triglycerides: "",
  hba1c: "",
  fasting_glucose: "",
  medical_history: "",
  current_medications: "",
  allergies: "",
};

function toNumberOrNull(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function toList(value: string): string[] {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export default function PatientForm({ onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (field: keyof FormState) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        patient_identifier: form.patient_identifier,
        age: Number(form.age),
        gender: form.gender,
        weight_kg: toNumberOrNull(form.weight_kg),
        height_cm: toNumberOrNull(form.height_cm),
        bmi: null,
        smoking_status: form.smoking_status || null,
        systolic_bp: toNumberOrNull(form.systolic_bp),
        diastolic_bp: toNumberOrNull(form.diastolic_bp),
        heart_rate: toNumberOrNull(form.heart_rate),
        total_cholesterol: toNumberOrNull(form.total_cholesterol),
        ldl: toNumberOrNull(form.ldl),
        hdl: toNumberOrNull(form.hdl),
        triglycerides: toNumberOrNull(form.triglycerides),
        hba1c: toNumberOrNull(form.hba1c),
        fasting_glucose: toNumberOrNull(form.fasting_glucose),
        medical_history: toList(form.medical_history),
        current_medications: toList(form.current_medications),
        allergies: toList(form.allergies),
      });
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create patient.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h3>New synthetic patient</h3>
      {error && <div className="error-banner">{error}</div>}

      <div className="form-grid">
        <div>
          <label>Patient identifier</label>
          <input required value={form.patient_identifier} onChange={update("patient_identifier")} placeholder="DEMO-011" />
        </div>
        <div>
          <label>Age</label>
          <input required type="number" min={0} max={130} value={form.age} onChange={update("age")} />
        </div>
        <div>
          <label>Gender</label>
          <select value={form.gender} onChange={update("gender")}>
            <option value="female">female</option>
            <option value="male">male</option>
            <option value="other">other</option>
          </select>
        </div>
        <div>
          <label>Smoking status</label>
          <select value={form.smoking_status} onChange={update("smoking_status")}>
            <option value="never">never</option>
            <option value="former">former</option>
            <option value="current">current</option>
          </select>
        </div>
        <div>
          <label>Weight (kg)</label>
          <input type="number" value={form.weight_kg} onChange={update("weight_kg")} />
        </div>
        <div>
          <label>Height (cm)</label>
          <input type="number" value={form.height_cm} onChange={update("height_cm")} />
        </div>
        <div>
          <label>Systolic BP</label>
          <input type="number" value={form.systolic_bp} onChange={update("systolic_bp")} />
        </div>
        <div>
          <label>Diastolic BP</label>
          <input type="number" value={form.diastolic_bp} onChange={update("diastolic_bp")} />
        </div>
        <div>
          <label>Heart rate</label>
          <input type="number" value={form.heart_rate} onChange={update("heart_rate")} />
        </div>
        <div>
          <label>Total cholesterol</label>
          <input type="number" value={form.total_cholesterol} onChange={update("total_cholesterol")} />
        </div>
        <div>
          <label>LDL</label>
          <input type="number" value={form.ldl} onChange={update("ldl")} />
        </div>
        <div>
          <label>HDL</label>
          <input type="number" value={form.hdl} onChange={update("hdl")} />
        </div>
        <div>
          <label>Triglycerides</label>
          <input type="number" value={form.triglycerides} onChange={update("triglycerides")} />
        </div>
        <div>
          <label>HbA1c</label>
          <input type="number" step="0.1" value={form.hba1c} onChange={update("hba1c")} />
        </div>
        <div>
          <label>Fasting glucose</label>
          <input type="number" value={form.fasting_glucose} onChange={update("fasting_glucose")} />
        </div>
      </div>

      <div className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
        <div>
          <label>Medical history (comma-separated, e.g. type_2_diabetes, hypertension)</label>
          <input value={form.medical_history} onChange={update("medical_history")} />
        </div>
        <div>
          <label>Current medications (comma-separated)</label>
          <input value={form.current_medications} onChange={update("current_medications")} />
        </div>
        <div>
          <label>Allergies (comma-separated)</label>
          <input value={form.allergies} onChange={update("allergies")} />
        </div>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Create patient"}
        </button>
        <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  );
}
