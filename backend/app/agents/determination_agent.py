import asyncio

from app.agents.base import BaseAgent
from app.orchestration.determination_rules import blocking_not_met_criteria
from app.orchestration.state import ClinicalWorkflowState
from app.services import llm_client


def _build_patient_summary(state: ClinicalWorkflowState) -> str:
    patient = state.patient
    risk = state.risk_assessment or {}
    parts = [f"{patient.get('age')}-year-old {patient.get('gender')} patient"]
    if state.identified_conditions:
        parts.append("with " + ", ".join(state.identified_conditions))
    if risk.get("risk_category"):
        parts.append(f"(overall risk: {risk['risk_category']})")
    return " ".join(parts)


class DeterminationAgent(BaseAgent):
    """Decides approve / deny / pend from the criteria evaluation, deterministically,
    then asks an LLM (if configured) to write the rationale explaining that decision. When the
    outcome is denied or pended, a second LLM call describes a concrete, guideline-grounded
    scenario of what would need to be true for the request to be approved.

    The LLM never makes or changes the coverage decision - it only phrases the
    already-computed outcome and, for non-approvals, the evidence that would close the gap. This
    keeps the actual determination logic auditable and reproducible even when the LLM is
    unavailable or disabled, while still demonstrating a real, metered LLM integration for the
    observability layer.
    """

    name = "determination_agent"

    def input_snapshot(self, state: ClinicalWorkflowState) -> dict:
        return {
            "requested_service": state.request.requested_service,
            "criteria_evaluated_count": len(state.criteria_evaluated),
        }

    async def run(self, state: ClinicalWorkflowState) -> dict:
        criteria = state.criteria_evaluated
        met = [c for c in criteria if c["status"] == "MET"]
        not_met = blocking_not_met_criteria(criteria)
        unknown = [c for c in criteria if c["status"] == "UNKNOWN"]

        if not_met:
            determination = "denied"
        elif unknown:
            determination = "pended"
        elif met:
            determination = "approved"
        else:
            determination = "pended"

        allergies = [a.lower() for a in (state.patient.get("allergies") or [])]
        medications = [m.lower() for m in (state.patient.get("current_medications") or [])]
        for allergy in allergies:
            for medication in medications:
                if allergy and (allergy in medication or medication in allergy):
                    state.safety_flags.append(
                        f"Documented allergy '{allergy}' overlaps with current medication '{medication}'."
                    )

        patient_summary = _build_patient_summary(state)
        requested_service = state.request.requested_service or "the requested service"

        llm_result = await asyncio.to_thread(
            llm_client.generate_determination_rationale,
            requested_service=requested_service,
            determination=determination,
            criteria_evaluated=criteria,
            patient_summary=patient_summary,
        )

        state.determination = determination
        state.decision_rationale = llm_result.text
        state.llm_usage = (
            {
                "model": llm_result.usage.model,
                "input_tokens": llm_result.usage.input_tokens,
                "output_tokens": llm_result.usage.output_tokens,
            }
            if llm_result.usage
            else None
        )

        scenario_result = None
        if determination in ("denied", "pended"):
            scenario_result = await asyncio.to_thread(
                llm_client.generate_approval_path_suggestion,
                requested_service=requested_service,
                determination=determination,
                criteria_evaluated=criteria,
                patient_summary=patient_summary,
            )
            state.approval_path_suggestion = scenario_result.text
            state.scenario_llm_usage = (
                {
                    "model": scenario_result.usage.model,
                    "input_tokens": scenario_result.usage.input_tokens,
                    "output_tokens": scenario_result.usage.output_tokens,
                }
                if scenario_result.usage
                else None
            )

        return {
            "determination": determination,
            "met_count": len(met),
            "not_met_count": len(not_met),
            "unknown_count": len(unknown),
            "rationale": llm_result.text,
            "rationale_source": "llm" if llm_result.usage else "template",
            "llm_error": llm_result.error,
            "llm_usage": state.llm_usage,
            "approval_path_suggestion": state.approval_path_suggestion,
            "scenario_rationale_source": "llm" if scenario_result and scenario_result.usage else ("template" if scenario_result else None),
            "scenario_llm_error": scenario_result.error if scenario_result else None,
            "scenario_llm_usage": state.scenario_llm_usage,
        }
