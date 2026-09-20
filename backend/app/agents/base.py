import time
from abc import ABC, abstractmethod

from app.core.logging import get_logger
from app.orchestration.state import AgentTrace, ClinicalWorkflowState

logger = get_logger(__name__)


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    async def run(self, state: ClinicalWorkflowState) -> dict:
        """Perform the agent's task, mutate state as needed, and return a structured output dict."""
        raise NotImplementedError

    def input_snapshot(self, state: ClinicalWorkflowState) -> dict:
        """Subclasses may override to record a more targeted input snapshot for tracing."""
        return {"clinical_question": state.clinical_question}

    async def execute(self, state: ClinicalWorkflowState) -> AgentTrace:
        start = time.perf_counter()
        input_data = self.input_snapshot(state)
        status = "success"
        output: dict = {}

        try:
            output = await self.run(state)
        except Exception as exc:  # noqa: BLE001 - agents must not crash the workflow
            status = "error"
            output = {"error": str(exc)}
            logger.exception("Agent %s failed", self.name)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000

        trace = AgentTrace(
            agent_name=self.name,
            status=status,
            input_data=input_data,
            output_data=output,
            execution_time_ms=round(elapsed_ms, 3),
        )
        state.add_trace(trace)
        return trace
