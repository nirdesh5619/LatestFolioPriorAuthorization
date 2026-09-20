from collections.abc import AsyncIterator
from typing import Literal

from app.orchestration.state import AgentTrace, ClinicalWorkflowState, PriorAuthRequest
from app.orchestration.workflow import ClinicalWorkflow
from app.schemas.response import CLINICAL_SAFETY_NOTICE
from app.rag.retriever import GuidelineRetriever

StreamEvent = tuple[Literal["agent"], AgentTrace] | tuple[Literal["final"], ClinicalWorkflowState]


class FinalResponseOrchestrator:
    """Combines all agent outputs into the final structured prior-authorization determination."""

    def __init__(self, retriever: GuidelineRetriever | None = None):
        self.workflow = ClinicalWorkflow(retriever)

    async def run(self, patient: dict, clinical_question: str, request: PriorAuthRequest | None = None) -> ClinicalWorkflowState:
        state = ClinicalWorkflowState(patient=patient, clinical_question=clinical_question, request=request or PriorAuthRequest())
        await self.workflow.run(state)
        state.final_response = self._build_final_response(state)
        return state

    async def run_streaming(
        self, patient: dict, clinical_question: str, request: PriorAuthRequest | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Same pipeline as `run`, but yields each agent's trace the instant it completes.

        Lets a caller (e.g. an SSE/NDJSON API endpoint) surface live, real
        multi-agent progress instead of only the final combined response.
        """
        state = ClinicalWorkflowState(patient=patient, clinical_question=clinical_question, request=request or PriorAuthRequest())
        async for trace in self.workflow.run_steps(state):
            yield ("agent", trace)

        state.final_response = self._build_final_response(state)
        yield ("final", state)

    def _build_final_response(self, state: ClinicalWorkflowState) -> dict:
        requested_service = state.request.requested_service

        if state.halted:
            return {
                "summary": (
                    f"Insufficient information was submitted to complete a determination for "
                    f"'{requested_service or 'the requested service'}'."
                ),
                "requested_service": requested_service,
                "determination": "pended",
                "decision_rationale": (
                    "This request was pended before evidence retrieval because required information "
                    "was missing: " + ", ".join(state.missing_information) + "."
                    if state.missing_information
                    else "This request was pended due to missing required information."
                ),
                "llm_usage": None,
                "approval_path_suggestion": (
                    "Submit the missing information listed below, then resubmit the request for a "
                    "full guideline-based evaluation."
                    if state.missing_information
                    else None
                ),
                "scenario_llm_usage": None,
                "identified_conditions": state.identified_conditions,
                "risk_factors": [],
                "risk_category": None,
                "missing_information": state.missing_information,
                "guideline_evidence": [],
                "criteria_evaluated": [],
                "safety_flags": state.safety_flags,
                "requires_clinician_review": True,
                "disclaimer": CLINICAL_SAFETY_NOTICE,
            }

        guideline_evidence = [
            {
                "guideline": g["guideline"],
                "guideline_id": g["guideline_id"],
                "section": g["section"],
                "evidence": g["text"],
                "relevance_score": g["score"],
                "source": g["source"],
            }
            for g in state.retrieved_guidelines
        ]

        criteria_evaluated = [
            {
                "criterion": c["criterion"],
                "status": c["status"],
                "patient_evidence": c.get("patient_evidence"),
                "guideline": c["guideline"],
                "section": c["section"],
                "source": c["source"],
            }
            for c in state.criteria_evaluated
        ]

        risk_assessment = state.risk_assessment or {}

        summary_parts = [
            f"Prior authorization determination for '{requested_service or 'the requested service'}': "
            f"{(state.determination or 'pended').upper()}.",
            f"Patient: {state.patient.get('age')}-year-old {state.patient.get('gender')}.",
        ]
        if state.identified_conditions:
            summary_parts.append("Documented conditions: " + ", ".join(state.identified_conditions) + ".")
        if risk_assessment.get("risk_category"):
            summary_parts.append(f"Overall clinical risk: {risk_assessment['risk_category']}.")

        return {
            "summary": " ".join(summary_parts),
            "requested_service": requested_service,
            "determination": state.determination,
            "decision_rationale": state.decision_rationale,
            "llm_usage": state.llm_usage,
            "approval_path_suggestion": state.approval_path_suggestion,
            "scenario_llm_usage": state.scenario_llm_usage,
            "identified_conditions": state.identified_conditions,
            "risk_factors": risk_assessment.get("risk_factors", []),
            "risk_category": risk_assessment.get("risk_category"),
            "missing_information": state.missing_information,
            "guideline_evidence": guideline_evidence,
            "criteria_evaluated": criteria_evaluated,
            "safety_flags": state.safety_flags,
            "requires_clinician_review": True,
            "disclaimer": CLINICAL_SAFETY_NOTICE,
        }
