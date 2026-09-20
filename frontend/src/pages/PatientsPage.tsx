import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Patient, PatientCreatePayload } from "../api/types";
import PatientForm from "../components/PatientForm";

function conditionSummary(patient: Patient): string {
  if (patient.medical_history.length === 0) return "No documented conditions";
  return patient.medical_history.map((c) => c.replace(/_/g, " ")).join(", ");
}

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();

  const loadPatients = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listPatients();
      setPatients(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load patients.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPatients();
  }, []);

  const handleCreate = async (payload: PatientCreatePayload) => {
    await api.createPatient(payload);
    setShowForm(false);
    await loadPatients();
  };

  return (
    <div>
      <div className="page-title">
        <h2>Patients</h2>
        <button onClick={() => setShowForm((prev) => !prev)}>{showForm ? "Close" : "+ Add patient"}</button>
      </div>

      {showForm && <PatientForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />}

      {error && <div className="error-banner">{error}</div>}
      {loading && <p className="loading">Loading patients…</p>}

      {!loading && patients.length === 0 && !error && (
        <p className="empty-state">No patients yet. Add one above to get started.</p>
      )}

      <div className="grid">
        {patients.map((p) => (
          <div className="card patient-card" key={p.id} onClick={() => navigate(`/patients/${p.id}`)}>
            <h3>{p.patient_identifier}</h3>
            <div className="muted">
              {p.age}-year-old {p.gender}
              {p.bmi ? ` · BMI ${p.bmi}` : ""}
            </div>
            <div className="muted">{conditionSummary(p)}</div>
            {(p.systolic_bp || p.hba1c) && (
              <div className="pill-row">
                {p.systolic_bp && p.diastolic_bp && (
                  <span className="pill">
                    BP {p.systolic_bp}/{p.diastolic_bp}
                  </span>
                )}
                {p.hba1c && <span className="pill">HbA1c {p.hba1c}%</span>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
