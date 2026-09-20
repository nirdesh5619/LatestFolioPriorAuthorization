from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    patient_identifier: str
    age: int = Field(ge=0, le=130)
    gender: str
    weight_kg: float | None = None
    height_cm: float | None = None
    bmi: float | None = None
    smoking_status: str | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    heart_rate: float | None = None
    total_cholesterol: float | None = None
    ldl: float | None = None
    hdl: float | None = None
    triglycerides: float | None = None
    hba1c: float | None = None
    fasting_glucose: float | None = None
    medical_history: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_row(cls, row) -> "PatientRead":
        import json

        return cls(
            id=row.id,
            patient_identifier=row.patient_identifier,
            age=row.age,
            gender=row.gender,
            weight_kg=row.weight_kg,
            height_cm=row.height_cm,
            bmi=row.bmi,
            smoking_status=row.smoking_status,
            systolic_bp=row.systolic_bp,
            diastolic_bp=row.diastolic_bp,
            heart_rate=row.heart_rate,
            total_cholesterol=row.total_cholesterol,
            ldl=row.ldl,
            hdl=row.hdl,
            triglycerides=row.triglycerides,
            hba1c=row.hba1c,
            fasting_glucose=row.fasting_glucose,
            medical_history=json.loads(row.medical_history or "[]"),
            current_medications=json.loads(row.current_medications or "[]"),
            allergies=json.loads(row.allergies or "[]"),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
