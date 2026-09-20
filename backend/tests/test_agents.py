import pytest

from app.agents.criteria_matching_agent import CriteriaMatchingAgent
from app.agents.determination_agent import DeterminationAgent
from app.agents.intake_agent import ClinicalIntakeAgent
from app.agents.retrieval_agent import GuidelineRetrievalAgent
from app.agents.risk_agent import RiskStratificationAgent
from app.agents.safety_agent import SafetyValidationAgent
from app.orchestration.state import ClinicalWorkflowState, PriorAuthRequest
from app.rag.retriever import GuidelineRetriever

DEMO_PATIENT = {
    "age": 56,
    "gender": "male",
    "weight_kg": 91,
    "height_cm": 172,
    "bmi": None,
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
    diagnosis_codes=["M54.5"],
    urgency="routine",
    prior_treatments_tried=[],
)


@pytest.mark.asyncio
async def test_intake_agent_computes_bmi_and_facts():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    agent = ClinicalIntakeAgent()
    trace = await agent.execute(state)

    assert trace.status == "success"
    assert state.patient["bmi"] is not None
    assert "Type 2 diabetes" in state.identified_conditions
    assert "Hypertension" in state.identified_conditions
    assert state.missing_information == []


@pytest.mark.asyncio
async def test_intake_agent_flags_missing_fields():
    incomplete = dict(DEMO_PATIENT)
    incomplete["systolic_bp"] = None
    incomplete["diastolic_bp"] = None
    incomplete["ldl"] = None

    state = ClinicalWorkflowState(patient=incomplete, clinical_question="", request=DEMO_REQUEST)
    await ClinicalIntakeAgent().execute(state)

    assert "systolic blood pressure" in state.missing_information
    assert "LDL cholesterol" in state.missing_information


@pytest.mark.asyncio
async def test_intake_agent_flags_missing_diagnosis_codes():
    state = ClinicalWorkflowState(
        patient=dict(DEMO_PATIENT),
        clinical_question="",
        request=PriorAuthRequest(requested_service="Lumbar spine MRI", diagnosis_codes=[]),
    )
    await ClinicalIntakeAgent().execute(state)

    assert any("diagnosis code" in m for m in state.missing_information)


@pytest.mark.asyncio
async def test_risk_agent_classifies_high_risk():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.patient["bmi"] = 30.8

    await RiskStratificationAgent().execute(state)

    assert state.risk_assessment["risk_category"] == "high"
    assert any("blood pressure" in f.lower() for f in state.risk_assessment["risk_factors"])


@pytest.mark.asyncio
async def test_risk_agent_low_risk_patient():
    low_risk_patient = {
        "age": 29,
        "gender": "female",
        "bmi": 21.3,
        "systolic_bp": 112,
        "diastolic_bp": 72,
        "ldl": 90,
        "hdl": 65,
        "triglycerides": 80,
        "hba1c": 5.1,
        "fasting_glucose": 85,
        "smoking_status": "never",
        "medical_history": [],
    }
    state = ClinicalWorkflowState(patient=low_risk_patient, clinical_question="", request=DEMO_REQUEST)
    await RiskStratificationAgent().execute(state)

    assert state.risk_assessment["risk_category"] == "low"
    assert state.risk_assessment["risk_factors"] == []


@pytest.mark.asyncio
async def test_retrieval_agent_filters_low_relevance(tmp_path):
    from app.rag.faiss_store import FaissStore
    from tests.fake_embeddings import fake_embed_texts

    metadata = [
        {
            "chunk_id": "IMG-001",
            "guideline_id": "IMG-DEMO",
            "guideline_title": "Demo Advanced Imaging Guideline",
            "section": "Coverage Criteria",
            "page": 1,
            "source": "pa_advanced_imaging_guideline.txt",
            "condition": "imaging",
            "text": "Criterion 2: For non-emergent lumbar spine pain, an MRI is medically necessary after six weeks of conservative therapy for the requested service.",
        },
        {
            "chunk_id": "UNRELATED-001",
            "guideline_id": "UNRELATED-DEMO",
            "guideline_title": "Unrelated Guideline",
            "section": "Unrelated Section",
            "page": 1,
            "source": "unrelated.txt",
            "condition": "unrelated",
            "text": "zzz qqq xxx completely unrelated filler text yyy www",
        },
    ]
    store = FaissStore(index_path=str(tmp_path / "index.faiss"), metadata_path=str(tmp_path / "metadata.json"))
    store.build(fake_embed_texts([m["text"] for m in metadata]), metadata)

    state = ClinicalWorkflowState(
        patient={"medical_history": ["type_2_diabetes"]},
        clinical_question="",
        request=PriorAuthRequest(requested_service="Lumbar spine MRI", diagnosis_codes=["M54.5"]),
    )
    agent = GuidelineRetrievalAgent(retriever=GuidelineRetriever(store=store))
    await agent.execute(state)

    guideline_ids = [g["guideline_id"] for g in state.retrieved_guidelines]
    assert "IMG-DEMO" in guideline_ids
    assert "UNRELATED-DEMO" not in guideline_ids


@pytest.mark.asyncio
async def test_criteria_matching_agent_evaluates_bmi_criterion():
    state = ClinicalWorkflowState(
        patient={"age": 45, "gender": "female", "bmi": 42.0, "medical_history": []},
        clinical_question="",
        request=PriorAuthRequest(requested_service="Bariatric surgery", diagnosis_codes=["E66.01"]),
    )
    state.retrieved_guidelines = [
        {
            "guideline": "Demo Bariatric Surgery Guideline",
            "guideline_id": "BARIATRIC-DEMO",
            "section": "Coverage Criteria",
            "text": "Criterion 1: Bariatric surgery is considered medically necessary for adults with a body mass index (BMI) of 40 or greater, regardless of comorbidities.",
            "score": 0.7,
            "source": "pa_bariatric_surgery_guideline.txt",
            "page": 1,
        }
    ]

    trace = await CriteriaMatchingAgent().execute(state)

    assert trace.status == "success"
    assert len(state.criteria_evaluated) == 1
    assert state.criteria_evaluated[0]["status"] == "MET"
    assert "42.0" in state.criteria_evaluated[0]["patient_evidence"]


@pytest.mark.asyncio
async def test_criteria_matching_agent_not_met_bmi():
    state = ClinicalWorkflowState(
        patient={"age": 45, "gender": "female", "bmi": 32.0, "medical_history": []},
        clinical_question="",
        request=PriorAuthRequest(requested_service="Bariatric surgery"),
    )
    state.retrieved_guidelines = [
        {
            "guideline": "Demo Bariatric Surgery Guideline",
            "guideline_id": "BARIATRIC-DEMO",
            "section": "Coverage Criteria",
            "text": "Criterion 1: Bariatric surgery is considered medically necessary for adults with a body mass index (BMI) of 40 or greater, regardless of comorbidities.",
            "score": 0.7,
            "source": "pa_bariatric_surgery_guideline.txt",
            "page": 1,
        }
    ]

    await CriteriaMatchingAgent().execute(state)

    assert state.criteria_evaluated[0]["status"] == "NOT_MET"


@pytest.mark.asyncio
async def test_criteria_matching_agent_step_therapy_unknown_when_undocumented():
    state = ClinicalWorkflowState(
        patient={"age": 40, "gender": "male", "medical_history": []},
        clinical_question="",
        request=PriorAuthRequest(requested_service="Lumbar spine MRI", prior_treatments_tried=[]),
    )
    state.retrieved_guidelines = [
        {
            "guideline": "Demo Advanced Imaging Guideline",
            "guideline_id": "IMG-DEMO",
            "section": "Coverage Criteria",
            "text": (
                "Criterion 2: For non-emergent back, neck, or joint pain without red-flag symptoms, "
                "advanced imaging is considered medically necessary only after at least six weeks of "
                "documented conservative therapy, such as physical therapy, without adequate improvement."
            ),
            "score": 0.7,
            "source": "pa_advanced_imaging_guideline.txt",
            "page": 1,
        }
    ]

    await CriteriaMatchingAgent().execute(state)

    assert state.criteria_evaluated[0]["status"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_criteria_matching_agent_step_therapy_met_when_documented():
    state = ClinicalWorkflowState(
        patient={"age": 40, "gender": "male", "medical_history": []},
        clinical_question="",
        request=PriorAuthRequest(
            requested_service="Lumbar spine MRI",
            prior_treatments_tried=["physical therapy for 8 weeks"],
        ),
    )
    state.retrieved_guidelines = [
        {
            "guideline": "Demo Advanced Imaging Guideline",
            "guideline_id": "IMG-DEMO",
            "section": "Coverage Criteria",
            "text": (
                "Criterion 2: For non-emergent back, neck, or joint pain without red-flag symptoms, "
                "advanced imaging is considered medically necessary only after at least six weeks of "
                "documented conservative therapy, such as physical therapy, without adequate improvement."
            ),
            "score": 0.7,
            "source": "pa_advanced_imaging_guideline.txt",
            "page": 1,
        }
    ]

    await CriteriaMatchingAgent().execute(state)

    assert state.criteria_evaluated[0]["status"] == "MET"


@pytest.mark.asyncio
async def test_criteria_matching_agent_exclusion_criteria_never_asserts_not_met():
    """Regression test: exclusion criteria are phrased as negations ("requests
    WITHOUT documented improvement are not necessary"). Lexical overlap can't
    reliably resolve the negation direction, so this tier must never confidently
    deny (NOT_MET) - only flag for human review (UNKNOWN) or stay silent."""
    state = ClinicalWorkflowState(
        patient={"age": 60, "gender": "male", "medical_history": []},
        clinical_question="",
        request=PriorAuthRequest(
            requested_service="Extended physical therapy",
            prior_treatments_tried=["initial course with documented improvement in range of motion"],
        ),
    )
    state.retrieved_guidelines = [
        {
            "guideline": "Demo Extended Physical Therapy Guideline",
            "guideline_id": "PT-DEMO",
            "section": "Exclusions",
            "text": (
                "Criterion 3: Extension requests without documentation of measurable improvement "
                "from the prior course of therapy are not considered medically necessary, as continued "
                "treatment without progress does not meet medical necessity criteria."
            ),
            "score": 0.7,
            "source": "pa_physical_therapy_guideline.txt",
            "page": 1,
        }
    ]

    await CriteriaMatchingAgent().execute(state)

    statuses = [c["status"] for c in state.criteria_evaluated]
    assert "NOT_MET" not in statuses


@pytest.mark.asyncio
async def test_determination_agent_approves_when_all_criteria_met():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.criteria_evaluated = [
        {
            "criterion": "Criterion 1: Example.",
            "status": "MET",
            "patient_evidence": "matches",
            "guideline": "Demo Guideline",
            "section": "Coverage Criteria",
            "source": "demo.txt",
        }
    ]

    trace = await DeterminationAgent().execute(state)

    assert trace.status == "success"
    assert state.determination == "approved"
    assert state.decision_rationale
    assert state.llm_usage is None  # no API key configured in tests -> deterministic fallback


@pytest.mark.asyncio
async def test_determination_agent_denies_when_any_criterion_not_met():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.criteria_evaluated = [
        {"criterion": "A", "status": "MET", "patient_evidence": None, "guideline": "G", "section": "S", "source": "s"},
        {"criterion": "B", "status": "NOT_MET", "patient_evidence": None, "guideline": "G", "section": "S", "source": "s"},
    ]

    trace = await DeterminationAgent().execute(state)

    assert state.determination == "denied"
    assert state.approval_path_suggestion  # scenario suggestion is generated for non-approvals
    assert "B" in state.approval_path_suggestion
    assert state.scenario_llm_usage is None  # no API key configured in tests -> deterministic fallback
    assert trace.output_data["approval_path_suggestion"] == state.approval_path_suggestion


@pytest.mark.asyncio
async def test_determination_agent_skips_scenario_suggestion_when_approved():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.criteria_evaluated = [
        {"criterion": "A", "status": "MET", "patient_evidence": None, "guideline": "G", "section": "S", "source": "s"},
    ]

    trace = await DeterminationAgent().execute(state)

    assert state.determination == "approved"
    assert state.approval_path_suggestion is None
    assert trace.output_data["approval_path_suggestion"] is None


@pytest.mark.asyncio
async def test_determination_agent_approves_alternative_bmi_band_even_if_other_band_not_met():
    """Regression test: BMI criteria are alternative qualifying bands (e.g. >=40 OR
    35-39.9 with a comorbidity), not a checklist every band must pass. Failing one
    band must not block approval when another band is met."""
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.criteria_evaluated = [
        {
            "criterion": "BMI of 40 or greater.",
            "status": "NOT_MET",
            "patient_evidence": "Patient BMI 39.8 is below the 40.0 threshold.",
            "guideline": "G",
            "section": "S",
            "source": "s",
        },
        {
            "criterion": "BMI of 35 to 39.9 with a comorbidity.",
            "status": "MET",
            "patient_evidence": "Patient BMI 39.8 falls within 35.0-39.9.",
            "guideline": "G",
            "section": "S",
            "source": "s",
        },
    ]

    await DeterminationAgent().execute(state)

    assert state.determination == "approved"


@pytest.mark.asyncio
async def test_determination_agent_pends_when_unknown_present():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.criteria_evaluated = [
        {"criterion": "A", "status": "MET", "patient_evidence": None, "guideline": "G", "section": "S", "source": "s"},
        {"criterion": "B", "status": "UNKNOWN", "patient_evidence": None, "guideline": "G", "section": "S", "source": "s"},
    ]

    await DeterminationAgent().execute(state)

    assert state.determination == "pended"


@pytest.mark.asyncio
async def test_safety_agent_flags_missing_information():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.missing_information = ["LDL cholesterol"]
    state.criteria_evaluated = []
    state.retrieved_guidelines = []
    state.risk_assessment = {"risk_category": "high"}

    await SafetyValidationAgent().execute(state)

    assert state.requires_clinician_review is True
    assert any("Missing information" in f for f in state.safety_flags)
    assert any("HIGH" in f for f in state.safety_flags)


@pytest.mark.asyncio
async def test_safety_agent_flags_unsupported_criteria():
    state = ClinicalWorkflowState(patient=dict(DEMO_PATIENT), clinical_question="", request=DEMO_REQUEST)
    state.retrieved_guidelines = [
        {
            "guideline": "G",
            "guideline_id": "G-1",
            "section": "S",
            "text": "Some actually retrieved text.",
            "score": 0.5,
            "source": "s.txt",
            "page": 1,
        }
    ]
    state.criteria_evaluated = [
        {
            "criterion": "This exact sentence was never retrieved.",
            "status": "MET",
            "patient_evidence": None,
            "guideline": "G",
            "section": "S",
            "source": "s.txt",
        }
    ]
    state.determination = "approved"

    await SafetyValidationAgent().execute(state)

    assert any("unsupported" in f for f in state.safety_flags)
