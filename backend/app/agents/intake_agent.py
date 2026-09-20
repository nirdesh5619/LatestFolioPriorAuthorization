from app.agents.base import BaseAgent
from app.orchestration.state import ClinicalWorkflowState
from app.utils.validators import compute_bmi, find_missing_fields

CONDITION_LABELS = {
    "type_2_diabetes": "Type 2 diabetes",
    "type_1_diabetes": "Type 1 diabetes",
    "hypertension": "Hypertension",
    "dyslipidemia": "Dyslipidemia",
    "obesity": "Obesity",
    "coronary_artery_disease": "Coronary artery disease",
    "chronic_kidney_disease": "Chronic kidney disease",
    "atrial_fibrillation": "Atrial fibrillation",
    "heart_failure": "Heart failure",
    "stroke": "History of stroke",
}


class ClinicalIntakeAgent(BaseAgent):
    name = "clinical_intake_agent"

    async def run(self, state: ClinicalWorkflowState) -> dict:
        patient = state.patient

        if not patient.get("bmi") and patient.get("weight_kg") and patient.get("height_cm"):
            patient["bmi"] = compute_bmi(patient["weight_kg"], patient["height_cm"])

        facts: list[str] = [
            f"{patient.get('age')}-year-old {patient.get('gender')} patient",
        ]
        if patient.get("bmi"):
            facts.append(f"BMI {patient['bmi']}")
        if patient.get("systolic_bp") and patient.get("diastolic_bp"):
            facts.append(f"Blood pressure {patient['systolic_bp']}/{patient['diastolic_bp']} mmHg")
        if patient.get("hba1c"):
            facts.append(f"HbA1c {patient['hba1c']}%")
        if patient.get("fasting_glucose"):
            facts.append(f"Fasting glucose {patient['fasting_glucose']} mg/dL")
        if patient.get("ldl"):
            facts.append(f"LDL {patient['ldl']} mg/dL")
        if patient.get("hdl"):
            facts.append(f"HDL {patient['hdl']} mg/dL")
        if patient.get("triglycerides"):
            facts.append(f"Triglycerides {patient['triglycerides']} mg/dL")
        if patient.get("smoking_status"):
            facts.append(f"Smoking status: {patient['smoking_status']}")

        conditions = [
            CONDITION_LABELS.get(c, c.replace("_", " ").title())
            for c in (patient.get("medical_history") or [])
        ]

        request = state.request
        if request.requested_service:
            facts.append(f"Requesting: {request.requested_service} ({request.service_category})")
        if request.prior_treatments_tried:
            facts.append("Prior treatments tried: " + ", ".join(request.prior_treatments_tried))

        missing = find_missing_fields(patient)
        if not request.diagnosis_codes:
            missing.append("diagnosis code(s) supporting the request")

        state.extracted_facts = facts
        state.identified_conditions = conditions
        state.missing_information = missing

        return {
            "extracted_facts": facts,
            "identified_conditions": conditions,
            "missing_information": missing,
            "bmi_computed": patient.get("bmi"),
        }
