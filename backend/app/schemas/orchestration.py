from datetime import datetime

from pydantic import BaseModel, Field


class OrchestrationRunRequest(BaseModel):
    patient_id: int
    requested_service: str = Field(min_length=1, description="The procedure, medication, or service being requested")
    service_category: str = Field(default="other", description="e.g. imaging, surgery, medication, therapy, dme")
    diagnosis_codes: list[str] = Field(default_factory=list, description="ICD-10 codes or free-text diagnoses")
    urgency: str = Field(default="routine", description="routine | urgent | emergent")
    prior_treatments_tried: list[str] = Field(default_factory=list)
    clinical_question: str = Field(
        default="", description="Optional free-text clinical justification or additional context"
    )


class AgentTraceEntry(BaseModel):
    agent: str
    status: str
    input: dict
    output: dict
    execution_time_ms: float
    timestamp: datetime


class OrchestrationRunSummary(BaseModel):
    run_id: int
    patient_id: int
    status: str
    requested_service: str | None = None
    determination: str | None = None
    clinical_question: str
    created_at: datetime
    completed_at: datetime | None = None
