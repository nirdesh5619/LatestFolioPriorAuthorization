"""Thin wrapper around the Anthropic/OpenAI APIs for the Determination Agent's rationale text.

Design intent: the LLM never decides coverage. The approve/deny/pend
determination itself is always computed deterministically from the criteria
evaluation (see app/agents/determination_agent.py), so the platform stays
auditable even when this integration is unavailable or misconfigured. The LLM
is used purely to synthesize an already-computed decision into a clear,
professional rationale paragraph grounded in the retrieved criteria - never to
introduce new clinical claims.

Which provider is used (Anthropic or OpenAI) is picked by `settings.llm_provider`;
both are called through `_call_llm` below so the two prompt-building functions don't
need to know which SDK is active.
"""

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LlmUsage:
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LlmResult:
    text: str
    usage: LlmUsage | None
    error: str | None = None


def is_configured() -> bool:
    return get_settings().llm_enabled


def _call_llm(prompt: str, settings) -> tuple[str, LlmUsage]:
    """Sends `prompt` to whichever provider `settings.llm_provider` selects and returns
    (text, usage). Raises on a missing SDK, missing key, or any request failure - callers
    catch broadly and fall back to the deterministic template, so no fallback lives here.
    """
    if settings.llm_provider == "openai":
        import openai

        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_completion_tokens=settings.llm_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (response.choices[0].message.content or "").strip()
        usage = LlmUsage(
            model=settings.openai_model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
        return text, usage

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.llm_max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    text = "\n".join(text_parts).strip()
    usage = LlmUsage(
        model=settings.anthropic_model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    return text, usage


def generate_determination_rationale(
    *,
    requested_service: str,
    determination: str,
    criteria_evaluated: list[dict],
    patient_summary: str,
) -> LlmResult:
    """Asks Claude to write the rationale for an *already-decided* determination.

    Returns a graceful fallback (text=fallback template, usage=None, error=...)
    on any failure - missing API key, network error, SDK error - so the agent
    (and therefore the whole workflow) never crashes because of this call.
    """
    settings = get_settings()

    fallback_text = _template_rationale(requested_service, determination, criteria_evaluated)

    if not settings.llm_enabled:
        return LlmResult(text=fallback_text, usage=None, error="LLM_NOT_CONFIGURED")

    criteria_lines = "\n".join(
        f"- [{c['status']}] {c['criterion']} (patient evidence: {c.get('patient_evidence') or 'none available'})"
        for c in criteria_evaluated
    ) or "- No specific coverage criteria were retrieved."

    prompt = f"""You are drafting the rationale section of a prior authorization determination letter.

The determination has ALREADY been decided by a deterministic rules engine as: {determination.upper()}.
Do not change or second-guess this determination. Do not invent clinical facts, guideline text, or
criteria beyond what is listed below. Write 2-4 concise, professional sentences explaining WHY the
listed criteria evaluation supports this determination for the requested service.

Requested service: {requested_service}

Patient summary: {patient_summary}

Criteria evaluated (status is MET, NOT_MET, or UNKNOWN):
{criteria_lines}

Write only the rationale paragraph. No headers, no restating the determination word, no disclaimers."""

    try:
        text, usage = _call_llm(prompt, settings)
        return LlmResult(text=text or fallback_text, usage=usage)
    except ImportError as exc:
        logger.warning("%s package not installed: %s", settings.llm_provider, exc)
        return LlmResult(text=fallback_text, usage=None, error="LLM_SDK_UNAVAILABLE")
    except Exception as exc:  # noqa: BLE001 - never let an LLM outage break a determination
        logger.warning("LLM rationale generation failed, falling back to template: %s", exc)
        return LlmResult(text=fallback_text, usage=None, error=str(exc))


def generate_approval_path_suggestion(
    *,
    requested_service: str,
    determination: str,
    criteria_evaluated: list[dict],
    patient_summary: str,
) -> LlmResult:
    """For a denied/pended determination, asks Claude to describe a concrete, guideline-grounded
    scenario of what would need to be true for the request to be approved.

    Grounded strictly in the NOT_MET/UNKNOWN criteria already evaluated - the LLM may not invent
    new criteria or promise an outcome. Same graceful-fallback contract as
    generate_determination_rationale: never raises, and returns a deterministic template on any
    failure or when the LLM isn't configured.
    """
    settings = get_settings()

    blocking = [c for c in criteria_evaluated if c["status"] in ("NOT_MET", "UNKNOWN")]
    fallback_text = _template_approval_path(requested_service, blocking)

    if not settings.llm_enabled:
        return LlmResult(text=fallback_text, usage=None, error="LLM_NOT_CONFIGURED")

    if not blocking:
        return LlmResult(text=fallback_text, usage=None, error="NO_BLOCKING_CRITERIA")

    criteria_lines = "\n".join(
        f"- [{c['status']}] {c['criterion']} (patient evidence: {c.get('patient_evidence') or 'none available'})"
        for c in blocking
    )

    prompt = f"""You are drafting guidance for a prior-authorization requester whose request was
{determination.upper()}, to help them understand what a valid, approvable scenario would look like.

Base your answer ONLY on the specific criteria below that are NOT_MET or UNKNOWN for this patient.
Do not invent new coverage criteria, do not cite guideline text beyond what is implied by these
criteria, and do not guarantee that supplying this evidence will result in approval - only a
qualified reviewer can determine that. Write 2-4 concise, professional sentences describing the
concrete clinical evidence or documentation that would need to be present for each listed criterion
to be met.

Requested service: {requested_service}

Patient summary: {patient_summary}

Criteria currently blocking approval (status is NOT_MET or UNKNOWN):
{criteria_lines}

Write only the guidance paragraph. No headers, no restating the determination, no disclaimers."""

    try:
        text, usage = _call_llm(prompt, settings)
        return LlmResult(text=text or fallback_text, usage=usage)
    except ImportError as exc:
        logger.warning("%s package not installed: %s", settings.llm_provider, exc)
        return LlmResult(text=fallback_text, usage=None, error="LLM_SDK_UNAVAILABLE")
    except Exception as exc:  # noqa: BLE001 - never let an LLM outage break a determination
        logger.warning("LLM approval-path suggestion failed, falling back to template: %s", exc)
        return LlmResult(text=fallback_text, usage=None, error=str(exc))


def _template_approval_path(requested_service: str, blocking: list[dict]) -> str:
    if not blocking:
        return f"No outstanding criteria are blocking approval of '{requested_service}'."
    lines = "; ".join(c["criterion"] for c in blocking)
    return (
        f"For '{requested_service}' to be approved, documentation would need to satisfy the "
        f"following outstanding criteria: {lines}."
    )


def _template_rationale(requested_service: str, determination: str, criteria_evaluated: list[dict]) -> str:
    met = [c for c in criteria_evaluated if c["status"] == "MET"]
    not_met = [c for c in criteria_evaluated if c["status"] == "NOT_MET"]
    unknown = [c for c in criteria_evaluated if c["status"] == "UNKNOWN"]

    parts = [f"Determination for '{requested_service}': {determination.upper()}."]
    if met:
        parts.append("Criteria met: " + "; ".join(c["criterion"] for c in met) + ".")
    if not_met:
        parts.append("Criteria not met: " + "; ".join(c["criterion"] for c in not_met) + ".")
    if unknown:
        parts.append(
            "Additional documentation required to evaluate: " + "; ".join(c["criterion"] for c in unknown) + "."
        )
    return " ".join(parts)
