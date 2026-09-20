from app.agents.base import BaseAgent
from app.orchestration.determination_rules import expected_determination
from app.orchestration.state import ClinicalWorkflowState


class SafetyValidationAgent(BaseAgent):
    """Cross-checks the determination against retrieved evidence and flags anything unsupported.

    This is the last line of defense: it independently re-derives what the
    determination *should* be from the criteria evaluation and flags a
    mismatch, and verifies every cited criterion actually appears in text the
    retrieval agent returned (catching extraction bugs, not just LLM issues -
    there is no LLM in the decision path itself).
    """

    name = "safety_validation_agent"

    def input_snapshot(self, state: ClinicalWorkflowState) -> dict:
        return {
            "determination": state.determination,
            "criteria_count": len(state.criteria_evaluated),
            "retrieved_chunk_count": len(state.retrieved_guidelines),
            "missing_information": state.missing_information,
        }

    async def run(self, state: ClinicalWorkflowState) -> dict:
        flags: list[str] = list(state.safety_flags)
        retrieved_texts = [g["text"] for g in state.retrieved_guidelines]

        unsupported = [
            c["criterion"] for c in state.criteria_evaluated if not any(c["criterion"] in text for text in retrieved_texts)
        ]
        if unsupported:
            flags.append(
                f"{len(unsupported)} evaluated criterion/criteria could not be traced back to retrieved policy "
                "text and were flagged as unsupported."
            )

        expected = expected_determination(state.criteria_evaluated)
        if state.determination and state.determination != expected:
            flags.append(
                f"Determination '{state.determination}' does not match what the criteria evaluation implies "
                f"('{expected}') - flagged for manual review."
            )

        if not state.criteria_evaluated:
            flags.append("No specific coverage criteria could be evaluated from retrieved policy evidence.")

        if state.missing_information:
            flags.append(
                "Missing information: " + ", ".join(state.missing_information) + ". Determination completeness may be limited."
            )

        risk_category = (state.risk_assessment or {}).get("risk_category")
        if risk_category == "high":
            flags.append("Patient risk stratification is HIGH - prioritize clinical reviewer attention.")

        seen = set()
        deduped_flags = []
        for flag in flags:
            if flag not in seen:
                deduped_flags.append(flag)
                seen.add(flag)

        state.safety_flags = deduped_flags
        state.requires_clinician_review = True

        return {
            "safety_flags": deduped_flags,
            "unsupported_criteria": unsupported,
            "expected_determination": expected,
            "requires_clinician_review": True,
        }
