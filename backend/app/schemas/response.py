from pydantic import BaseModel, Field

CLINICAL_SAFETY_NOTICE = (
    "This platform is a prior-authorization decision-support demonstration using "
    "synthetic data and synthetic payer policies. It is not a substitute "
    "for professional clinical or utilization-management judgment. "
    "Final coverage decisions must be made by an appropriately qualified "
    "clinical reviewer using authoritative, current payer policy."
)


class GuidelineEvidence(BaseModel):
    guideline: str
    guideline_id: str
    section: str
    evidence: str
    relevance_score: float
    source: str


class CriterionEvaluation(BaseModel):
    criterion: str
    status: str  # MET | NOT_MET | UNKNOWN
    patient_evidence: str | None = None
    guideline: str
    section: str
    source: str


class LlmUsageInfo(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int


class FinalClinicalResponse(BaseModel):
    run_id: int
    patient_id: int
    summary: str

    requested_service: str | None = None
    determination: str | None = None  # approved | denied | pended
    decision_rationale: str | None = None
    llm_usage: LlmUsageInfo | None = None
    approval_path_suggestion: str | None = None
    scenario_llm_usage: LlmUsageInfo | None = None

    identified_conditions: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    risk_category: str | None = None
    missing_information: list[str] = Field(default_factory=list)

    guideline_evidence: list[GuidelineEvidence] = Field(default_factory=list)
    criteria_evaluated: list[CriterionEvaluation] = Field(default_factory=list)

    safety_flags: list[str] = Field(default_factory=list)
    requires_clinician_review: bool = True
    disclaimer: str = CLINICAL_SAFETY_NOTICE
