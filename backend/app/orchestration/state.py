from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTrace:
    agent_name: str
    status: str
    input_data: dict
    output_data: dict
    execution_time_ms: float


@dataclass
class PriorAuthRequest:
    """Structured details of the requested service, distinct from free-text justification."""

    requested_service: str | None = None
    service_category: str | None = None
    diagnosis_codes: list[str] = field(default_factory=list)
    urgency: str = "routine"
    prior_treatments_tried: list[str] = field(default_factory=list)


@dataclass
class ClinicalWorkflowState:
    patient: dict[str, Any]
    clinical_question: str
    request: PriorAuthRequest = field(default_factory=PriorAuthRequest)

    extracted_facts: list[str] = field(default_factory=list)
    identified_conditions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)

    retrieval_query: str | None = None
    retrieved_guidelines: list[dict] = field(default_factory=list)

    risk_assessment: dict | None = None

    reasoning: list[dict] = field(default_factory=list)
    criteria_evaluated: list[dict] = field(default_factory=list)

    recommendations: list[dict] = field(default_factory=list)
    determination: str | None = None
    decision_rationale: str | None = None
    llm_usage: dict | None = None
    approval_path_suggestion: str | None = None
    scenario_llm_usage: dict | None = None

    safety_flags: list[str] = field(default_factory=list)
    requires_clinician_review: bool = True

    final_response: dict | None = None

    halted: bool = False
    halt_reason: str | None = None

    trace: list[AgentTrace] = field(default_factory=list)

    def add_trace(self, trace: AgentTrace) -> None:
        self.trace.append(trace)
