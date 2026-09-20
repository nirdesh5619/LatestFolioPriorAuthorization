from collections.abc import AsyncIterator

from app.agents.criteria_matching_agent import CriteriaMatchingAgent
from app.agents.determination_agent import DeterminationAgent
from app.agents.intake_agent import ClinicalIntakeAgent
from app.agents.retrieval_agent import GuidelineRetrievalAgent
from app.agents.risk_agent import RiskStratificationAgent
from app.agents.safety_agent import SafetyValidationAgent
from app.orchestration.state import AgentTrace, ClinicalWorkflowState
from app.rag.retriever import GuidelineRetriever

CRITICAL_FIELDS = {"age", "gender"}
INSUFFICIENT_DATA_THRESHOLD = 6


class ClinicalWorkflow:
    """Runs the sequential multi-agent pipeline with conditional routing.

    Routing rules:
      - If critical patient fields are missing, or too many clinical fields are
        missing, the workflow halts after intake and returns an
        "insufficient information" state instead of guessing.
      - Safety conflicts never halt the workflow; they are surfaced as flags and
        always force `requires_clinician_review = True` on the final response.
    """

    def __init__(self, retriever: GuidelineRetriever | None = None):
        self.intake_agent = ClinicalIntakeAgent()
        self.retrieval_agent = GuidelineRetrievalAgent(retriever)
        self.risk_agent = RiskStratificationAgent()
        self.criteria_matching_agent = CriteriaMatchingAgent()
        self.determination_agent = DeterminationAgent()
        self.safety_agent = SafetyValidationAgent()

    async def run_steps(self, state: ClinicalWorkflowState) -> AsyncIterator[AgentTrace]:
        """Runs each agent in turn, yielding its trace the moment it completes.

        This is the single source of truth for the pipeline sequence and routing
        rules; both the synchronous `run()` and the streaming API consume it, so
        the two can never drift apart.
        """
        yield await self.intake_agent.execute(state)

        critical_missing = {f for f in CRITICAL_FIELDS if state.patient.get(f) is None}
        if critical_missing or len(state.missing_information) >= INSUFFICIENT_DATA_THRESHOLD:
            state.halted = True
            state.halt_reason = "insufficient_information"
            state.safety_flags.append(
                "Workflow halted: insufficient patient information to safely proceed with "
                "guideline-based assessment."
            )
            state.requires_clinician_review = True
            return

        yield await self.retrieval_agent.execute(state)
        yield await self.risk_agent.execute(state)
        yield await self.criteria_matching_agent.execute(state)
        yield await self.determination_agent.execute(state)
        yield await self.safety_agent.execute(state)

    async def run(self, state: ClinicalWorkflowState) -> ClinicalWorkflowState:
        async for _ in self.run_steps(state):
            pass
        return state
