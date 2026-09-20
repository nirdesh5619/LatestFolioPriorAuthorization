import re

from app.agents.base import BaseAgent
from app.orchestration.state import ClinicalWorkflowState

# Matches each individual numbered criterion inside a retrieved policy chunk,
# e.g. "Criterion 2: Extension of physical therapy ... functional goal."
CRITERION_PATTERN = re.compile(r"Criterion\s+\d+:\s*(.*?)(?=(?:\s*Criterion\s+\d+:)|$)", re.DOTALL)

STEP_THERAPY_HINTS = [
    "conservative therapy",
    "conservative treatment",
    "physical therapy",
    "weight-management program",
    "weight management program",
    "conventional therapy",
    "trialed",
    "step therapy",
    "prior treatment",
    "documented participation",
    "documented attempts",
    "screening",
    "face-to-face evaluation",
    "supervised diet",
    "prior equipment",
]

EXCLUSION_HINTS = ["not considered medically necessary", "is not considered"]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _extract_criteria(chunk_text: str) -> list[str]:
    matches = CRITERION_PATTERN.findall(chunk_text)
    cleaned = []
    for m in matches:
        text = m.strip()
        if not text:
            continue
        if not text.endswith("."):
            text += "."
        cleaned.append(text)
    return cleaned


def _evaluate_bmi(criterion_text: str, patient_bmi: float | None) -> tuple[str, str | None]:
    if patient_bmi is None:
        return "UNKNOWN", "Patient BMI is not documented on this request."

    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", criterion_text)]
    if not numbers:
        return "UNKNOWN", None

    lowered = criterion_text.lower()
    if "or greater" in lowered or "or higher" in lowered or "or more" in lowered:
        threshold = numbers[0]
        if patient_bmi >= threshold:
            return "MET", f"Patient BMI {patient_bmi} meets the {threshold}+ threshold."
        return "NOT_MET", f"Patient BMI {patient_bmi} is below the {threshold} threshold."

    if len(numbers) >= 2:
        low, high = numbers[0], numbers[1]
        if low <= patient_bmi <= high:
            return "MET", f"Patient BMI {patient_bmi} falls within {low}-{high}."
        return "NOT_MET", f"Patient BMI {patient_bmi} falls outside {low}-{high}."

    threshold = numbers[0]
    if patient_bmi >= threshold:
        return "MET", f"Patient BMI {patient_bmi} meets the {threshold} threshold."
    return "NOT_MET", f"Patient BMI {patient_bmi} is below the {threshold} threshold."


class CriteriaMatchingAgent(BaseAgent):
    """Evaluates each individual numbered criterion retrieved from payer policy
    documents against this specific request, producing a MET / NOT_MET / UNKNOWN
    verdict with the patient-side evidence used to reach it.

    This agent never invents criteria - every entry is a criterion sentence that
    was actually present in a chunk returned by the retrieval agent. It also
    never fabricates patient facts - numeric criteria (e.g. BMI thresholds) are
    checked against the patient's actual recorded values, and documentation-style
    criteria are checked against what the requester actually submitted.
    """

    name = "criteria_matching_agent"

    def input_snapshot(self, state: ClinicalWorkflowState) -> dict:
        return {
            "requested_service": state.request.requested_service,
            "prior_treatments_tried": state.request.prior_treatments_tried,
            "retrieved_chunk_count": len(state.retrieved_guidelines),
        }

    async def run(self, state: ClinicalWorkflowState) -> dict:
        request = state.request
        patient = state.patient

        patient_fact_text = " ".join(
            [
                request.requested_service or "",
                " ".join(request.diagnosis_codes),
                " ".join(request.prior_treatments_tried),
                " ".join(state.identified_conditions),
                " ".join((state.risk_assessment or {}).get("risk_factors", [])),
                state.clinical_question,
            ]
        )
        patient_fact_tokens = _tokenize(patient_fact_text)
        step_therapy_tokens = _tokenize(" ".join(request.prior_treatments_tried))

        # A prior-auth request is evaluated against the ONE policy that actually
        # applies to it, not every policy that happened to score above the
        # retrieval threshold. Without this, criteria from an unrelated policy
        # (e.g. durable medical equipment) can leak into an imaging request just
        # because a chunk of it scored reasonably well. Restrict evaluation to
        # the guideline whose best-matching chunk scored highest.
        best_score_by_guideline: dict[str, float] = {}
        for chunk in state.retrieved_guidelines:
            gid = chunk["guideline_id"]
            best_score_by_guideline[gid] = max(best_score_by_guideline.get(gid, 0.0), chunk["score"])
        dominant_guideline_id = max(best_score_by_guideline, key=best_score_by_guideline.get) if best_score_by_guideline else None

        evaluated: list[dict] = []
        seen = set()

        for chunk in state.retrieved_guidelines:
            if chunk["guideline_id"] != dominant_guideline_id:
                continue
            for criterion_text in _extract_criteria(chunk["text"]):
                if criterion_text in seen:
                    continue
                seen.add(criterion_text)

                status, evidence = self._evaluate(criterion_text, patient, patient_fact_tokens, step_therapy_tokens, request)
                if status is None:
                    continue  # not relevant enough to this request to surface

                evaluated.append(
                    {
                        "criterion": criterion_text,
                        "status": status,
                        "patient_evidence": evidence,
                        "guideline": chunk["guideline"],
                        "guideline_id": chunk["guideline_id"],
                        "section": chunk["section"],
                        "source": chunk["source"],
                    }
                )

        state.criteria_evaluated = evaluated

        met = sum(1 for e in evaluated if e["status"] == "MET")
        not_met = sum(1 for e in evaluated if e["status"] == "NOT_MET")
        unknown = sum(1 for e in evaluated if e["status"] == "UNKNOWN")

        return {
            "dominant_guideline_id": dominant_guideline_id,
            "criteria_evaluated": evaluated,
            "met_count": met,
            "not_met_count": not_met,
            "unknown_count": unknown,
        }

    def _evaluate(
        self,
        criterion_text: str,
        patient: dict,
        patient_fact_tokens: set[str],
        step_therapy_tokens: set[str],
        request,
    ) -> tuple[str | None, str | None]:
        lowered = criterion_text.lower()
        criterion_tokens = _tokenize(criterion_text)

        if "bmi" in lowered:
            return _evaluate_bmi(criterion_text, patient.get("bmi"))

        if any(hint in lowered for hint in EXCLUSION_HINTS):
            # These criteria are phrased as negations ("requests WITHOUT X are not
            # necessary"). Lexical overlap alone can't reliably tell whether the
            # patient's facts satisfy X or fall into the excluded gap - and
            # guessing wrong here means confidently DENYING care that should have
            # been approved. Flag for human review instead of ever asserting
            # NOT_MET from this tier.
            overlap = criterion_tokens & patient_fact_tokens
            if len(overlap) >= 2:
                return (
                    "UNKNOWN",
                    f"This exclusion may be relevant (overlapping terms: {', '.join(sorted(overlap))}) "
                    "- requires reviewer judgment to confirm whether it actually applies.",
                )
            return None, None

        if any(hint in lowered for hint in STEP_THERAPY_HINTS):
            overlap = criterion_tokens & step_therapy_tokens
            if overlap:
                return "MET", f"Prior treatments documented: {', '.join(request.prior_treatments_tried)}."
            return "UNKNOWN", "No matching prior treatment or documentation was submitted with this request."

        overlap = criterion_tokens & patient_fact_tokens
        if len(overlap) >= 2:
            return "MET", f"Request/patient details match this criterion ({', '.join(sorted(overlap))})."
        if len(overlap) == 1:
            return "UNKNOWN", f"Only a weak match was found on: {', '.join(sorted(overlap))}."
        return None, None
