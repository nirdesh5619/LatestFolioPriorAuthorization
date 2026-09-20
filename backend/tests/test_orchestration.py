import json

import pytest

from app.orchestration.orchestrator import FinalResponseOrchestrator
from app.orchestration.state import PriorAuthRequest
from app.rag.faiss_store import FaissStore
from app.rag.ingestion import ingest_guidelines
from app.rag.retriever import GuidelineRetriever

DEMO_PATIENT = {
    "age": 56,
    "gender": "male",
    "weight_kg": 91,
    "height_cm": 172,
    "bmi": 30.8,
    "smoking_status": "former",
    "systolic_bp": 148,
    "diastolic_bp": 92,
    "heart_rate": 78,
    "total_cholesterol": 225,
    "ldl": 148,
    "hdl": 39,
    "triglycerides": 210,
    "hba1c": 7.8,
    "fasting_glucose": 158,
    "medical_history": ["type_2_diabetes", "hypertension"],
    "current_medications": ["metformin"],
    "allergies": [],
}

DEMO_REQUEST = PriorAuthRequest(
    requested_service="Lumbar spine MRI",
    service_category="imaging",
    diagnosis_codes=["M54.5 - low back pain"],
    urgency="routine",
    prior_treatments_tried=["physical therapy for 8 weeks", "oral anti-inflammatory medication"],
)

EXPECTED_AGENT_SEQUENCE = [
    "clinical_intake_agent",
    "guideline_retrieval_agent",
    "risk_stratification_agent",
    "criteria_matching_agent",
    "determination_agent",
    "safety_validation_agent",
]


@pytest.fixture()
def real_guideline_store(db_session, tmp_path) -> FaissStore:
    store = FaissStore(index_path=str(tmp_path / "index.faiss"), metadata_path=str(tmp_path / "metadata.json"))
    ingest_guidelines(db_session, "./data/guidelines", store)
    return store


@pytest.mark.asyncio
async def test_full_workflow_produces_a_well_formed_determination(real_guideline_store):
    orchestrator = FinalResponseOrchestrator(retriever=GuidelineRetriever(store=real_guideline_store))

    state = await orchestrator.run(dict(DEMO_PATIENT), "", DEMO_REQUEST)

    assert not state.halted
    response = state.final_response

    assert response["requires_clinician_review"] is True
    assert response["requested_service"] == "Lumbar spine MRI"
    assert response["determination"] in ("approved", "denied", "pended")
    assert response["decision_rationale"]
    assert "Type 2 diabetes" in response["identified_conditions"]
    assert response["risk_category"] == "high"
    assert len(response["guideline_evidence"]) > 0

    # Every evaluated criterion must cite text actually present in retrieved evidence.
    retrieved_texts = [e["evidence"] for e in response["guideline_evidence"]]
    for criterion in response["criteria_evaluated"]:
        assert any(criterion["criterion"] in text for text in retrieved_texts)

    agent_names = [t.agent_name for t in state.trace]
    assert agent_names == EXPECTED_AGENT_SEQUENCE

    # No API key configured in tests -> deterministic template rationale, no token usage.
    assert response["llm_usage"] is None


@pytest.mark.asyncio
async def test_workflow_halts_on_insufficient_information(real_guideline_store):
    orchestrator = FinalResponseOrchestrator(retriever=GuidelineRetriever(store=real_guideline_store))

    incomplete_patient = {"age": None, "gender": None, "medical_history": []}
    state = await orchestrator.run(incomplete_patient, "", PriorAuthRequest(requested_service="Lumbar spine MRI"))

    assert state.halted
    assert state.final_response["requires_clinician_review"] is True
    assert state.final_response["determination"] == "pended"
    assert state.final_response["criteria_evaluated"] == []
    assert len(state.trace) == 1  # only the intake agent ran


@pytest.mark.asyncio
async def test_workflow_survives_missing_vector_store(tmp_path):
    empty_store = FaissStore(
        index_path=str(tmp_path / "missing_index.faiss"),
        metadata_path=str(tmp_path / "missing_metadata.json"),
    )
    orchestrator = FinalResponseOrchestrator(retriever=GuidelineRetriever(store=empty_store))

    state = await orchestrator.run(dict(DEMO_PATIENT), "", DEMO_REQUEST)

    assert not state.halted
    retrieval_trace = next(t for t in state.trace if t.agent_name == "guideline_retrieval_agent")
    assert retrieval_trace.status == "error"

    assert state.final_response["criteria_evaluated"] == []
    assert state.final_response["determination"] == "pended"
    assert state.final_response["requires_clinician_review"] is True
    assert any("No specific coverage criteria" in f for f in state.final_response["safety_flags"])


@pytest.mark.asyncio
async def test_run_streaming_yields_one_event_per_agent_then_final(real_guideline_store):
    orchestrator = FinalResponseOrchestrator(retriever=GuidelineRetriever(store=real_guideline_store))

    kinds = []
    async for kind, payload in orchestrator.run_streaming(dict(DEMO_PATIENT), "", DEMO_REQUEST):
        kinds.append(kind)
        if kind == "agent":
            assert payload.agent_name
            assert payload.status in ("success", "error")
        else:
            assert payload.final_response is not None

    assert kinds == ["agent"] * 6 + ["final"]


def test_orchestration_run_stream_api(client, db_session):
    # Relies on the app's own startup bootstrap having already populated the
    # process-wide FAISS index (same singleton the other client-based tests use).
    patient_resp = client.post(
        "/api/v1/patients",
        json={
            "patient_identifier": "STREAM-001",
            "age": 56,
            "gender": "male",
            "systolic_bp": 148,
            "diastolic_bp": 92,
            "hba1c": 7.8,
            "medical_history": ["type_2_diabetes", "hypertension"],
        },
    )
    assert patient_resp.status_code == 201
    patient_id = patient_resp.json()["id"]

    resp = client.post(
        "/api/v1/orchestration/run/stream",
        json={
            "patient_id": patient_id,
            "requested_service": "Lumbar spine MRI",
            "service_category": "imaging",
            "diagnosis_codes": ["M54.5"],
            "prior_treatments_tried": ["physical therapy for 8 weeks"],
        },
    )
    assert resp.status_code == 200

    lines = [line for line in resp.text.strip().split("\n") if line]
    events = [json.loads(line) for line in lines]

    agent_events = [e for e in events if e["type"] == "agent"]
    final_events = [e for e in events if e["type"] == "final"]

    assert len(final_events) == 1
    assert [e["agent"] for e in agent_events] == EXPECTED_AGENT_SEQUENCE

    final = final_events[0]
    assert final["patient_id"] == patient_id
    assert final["requires_clinician_review"] is True
    assert final["determination"] in ("approved", "denied", "pended")
    assert "run_id" in final


def test_orchestration_run_stream_missing_patient_returns_error(client):
    resp = client.post(
        "/api/v1/orchestration/run/stream",
        json={"patient_id": 999999, "requested_service": "Lumbar spine MRI"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "PATIENT_NOT_FOUND"


def test_orchestration_run_rejects_blank_requested_service(client):
    resp = client.post(
        "/api/v1/orchestration/run",
        json={"patient_id": 1, "requested_service": ""},
    )
    assert resp.status_code == 422
