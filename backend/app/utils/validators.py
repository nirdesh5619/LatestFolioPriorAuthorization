REQUIRED_CLINICAL_FIELDS = [
    "age",
    "gender",
    "systolic_bp",
    "diastolic_bp",
    "total_cholesterol",
    "ldl",
    "hdl",
    "hba1c",
    "fasting_glucose",
    "bmi",
]

FIELD_LABELS = {
    "age": "age",
    "gender": "gender",
    "weight_kg": "weight",
    "height_cm": "height",
    "bmi": "BMI",
    "smoking_status": "smoking status",
    "systolic_bp": "systolic blood pressure",
    "diastolic_bp": "diastolic blood pressure",
    "heart_rate": "heart rate",
    "total_cholesterol": "total cholesterol",
    "ldl": "LDL cholesterol",
    "hdl": "HDL cholesterol",
    "triglycerides": "triglycerides",
    "hba1c": "HbA1c",
    "fasting_glucose": "fasting glucose",
}


def compute_bmi(weight_kg: float | None, height_cm: float | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100
    if height_m <= 0:
        return None
    return round(weight_kg / (height_m**2), 1)


def find_missing_fields(patient_data: dict) -> list[str]:
    missing = []
    for field in REQUIRED_CLINICAL_FIELDS:
        value = patient_data.get(field)
        if value is None:
            missing.append(FIELD_LABELS.get(field, field))
    return missing
