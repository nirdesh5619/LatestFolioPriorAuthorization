from app.agents.base import BaseAgent
from app.orchestration.state import ClinicalWorkflowState


def _classify_blood_pressure(systolic: float | None, diastolic: float | None) -> tuple[str, list[str]]:
    if systolic is None or diastolic is None:
        return "unknown", []
    factors = []
    if systolic >= 140 or diastolic >= 90:
        factors.append(f"Elevated blood pressure ({systolic}/{diastolic} mmHg) consistent with hypertension")
        return "high", factors
    if systolic >= 130 or diastolic >= 80:
        factors.append(f"Blood pressure ({systolic}/{diastolic} mmHg) in elevated/stage 1 range")
        return "moderate", factors
    return "normal", []


def _classify_lipids(ldl: float | None, hdl: float | None, triglycerides: float | None) -> tuple[str, list[str]]:
    factors = []
    level = "normal"
    if ldl is not None and ldl >= 160:
        factors.append(f"Elevated LDL cholesterol ({ldl} mg/dL)")
        level = "high"
    elif ldl is not None and ldl >= 130:
        factors.append(f"Borderline-high LDL cholesterol ({ldl} mg/dL)")
        level = "moderate"

    if hdl is not None and hdl < 40:
        factors.append(f"Low HDL cholesterol ({hdl} mg/dL)")
        level = "high" if level != "high" else level
        level = "moderate" if level == "normal" else level

    if triglycerides is not None and triglycerides >= 200:
        factors.append(f"Elevated triglycerides ({triglycerides} mg/dL)")
        level = "high" if level != "high" else level
        level = "moderate" if level == "normal" else level

    return level, factors


def _classify_glycemic(hba1c: float | None, fasting_glucose: float | None) -> tuple[str, list[str]]:
    factors = []
    if hba1c is not None and hba1c >= 6.5:
        factors.append(f"HbA1c {hba1c}% consistent with diabetes range")
        return "high", factors
    if hba1c is not None and hba1c >= 5.7:
        factors.append(f"HbA1c {hba1c}% consistent with prediabetes range")
        return "moderate", factors
    if fasting_glucose is not None and fasting_glucose >= 126:
        factors.append(f"Fasting glucose {fasting_glucose} mg/dL consistent with diabetes range")
        return "high", factors
    if fasting_glucose is not None and fasting_glucose >= 100:
        factors.append(f"Fasting glucose {fasting_glucose} mg/dL consistent with prediabetes range")
        return "moderate", factors
    return "normal", []


def _classify_bmi(bmi: float | None) -> tuple[str, list[str]]:
    if bmi is None:
        return "unknown", []
    if bmi >= 30:
        return "high", [f"BMI {bmi} in the obesity range"]
    if bmi >= 25:
        return "moderate", [f"BMI {bmi} in the overweight range"]
    return "normal", []


LEVEL_SCORE = {"unknown": 0, "normal": 0, "moderate": 1, "high": 2}


class RiskStratificationAgent(BaseAgent):
    name = "risk_stratification_agent"

    def input_snapshot(self, state: ClinicalWorkflowState) -> dict:
        return {"patient_vitals_and_labs": {k: v for k, v in state.patient.items() if k not in (
            "medical_history", "current_medications", "allergies")}}

    async def run(self, state: ClinicalWorkflowState) -> dict:
        patient = state.patient
        factors: list[str] = []

        bp_level, bp_factors = _classify_blood_pressure(patient.get("systolic_bp"), patient.get("diastolic_bp"))
        lipid_level, lipid_factors = _classify_lipids(patient.get("ldl"), patient.get("hdl"), patient.get("triglycerides"))
        glycemic_level, glycemic_factors = _classify_glycemic(patient.get("hba1c"), patient.get("fasting_glucose"))
        bmi_level, bmi_factors = _classify_bmi(patient.get("bmi"))

        factors.extend(bp_factors)
        factors.extend(lipid_factors)
        factors.extend(glycemic_factors)
        factors.extend(bmi_factors)

        if patient.get("smoking_status") == "current":
            factors.append("Current tobacco use")

        history = patient.get("medical_history") or []
        cardiovascular_history_conditions = {
            "coronary_artery_disease",
            "heart_failure",
            "stroke",
            "atrial_fibrillation",
        }
        if any(c in cardiovascular_history_conditions for c in history):
            factors.append("Documented cardiovascular history")

        max_level = max(
            LEVEL_SCORE[bp_level],
            LEVEL_SCORE[lipid_level],
            LEVEL_SCORE[glycemic_level],
            LEVEL_SCORE[bmi_level],
        )
        if patient.get("smoking_status") == "current" or any(
            c in cardiovascular_history_conditions for c in history
        ):
            max_level = max(max_level, 2)

        risk_category = {0: "low", 1: "moderate", 2: "high"}[max_level]

        assessment = {
            "risk_category": risk_category,
            "blood_pressure_level": bp_level,
            "lipid_level": lipid_level,
            "glycemic_level": glycemic_level,
            "bmi_level": bmi_level,
            "risk_factors": factors,
        }
        state.risk_assessment = assessment
        return assessment
