import asyncio

from app.agents.base import BaseAgent
from app.orchestration.state import ClinicalWorkflowState
from app.rag.retriever import GuidelineRetriever, build_retrieval_query

MIN_RELEVANCE_SCORE = 0.15


class GuidelineRetrievalAgent(BaseAgent):
    name = "guideline_retrieval_agent"

    def __init__(self, retriever: GuidelineRetriever | None = None):
        self.retriever = retriever or GuidelineRetriever()

    def input_snapshot(self, state: ClinicalWorkflowState) -> dict:
        return {
            "requested_service": state.request.requested_service,
            "clinical_question": state.clinical_question,
            "identified_conditions": state.identified_conditions,
        }

    async def run(self, state: ClinicalWorkflowState) -> dict:
        query = build_retrieval_query(
            state.patient,
            state.clinical_question,
            requested_service=state.request.requested_service,
            diagnosis_codes=state.request.diagnosis_codes,
            prior_treatments_tried=state.request.prior_treatments_tried,
        )
        state.retrieval_query = query

        # Embedding + FAISS search is synchronous, CPU-bound work (mostly the
        # sentence-transformers model). Run it off the event loop thread so
        # streaming responses actually flush progress as agents complete,
        # instead of the whole request appearing to block until this returns.
        search_result = await asyncio.to_thread(self.retriever.search, query, top_k=None)
        results = search_result["results"]

        relevant = [r for r in results if r["score"] >= MIN_RELEVANCE_SCORE]

        state.retrieved_guidelines = relevant

        if not relevant:
            state.safety_flags.append(
                "No sufficiently relevant guideline evidence was retrieved for this clinical question."
            )

        return {
            "query": query,
            "total_results": len(results),
            "relevant_results": len(relevant),
            "results": relevant,
        }
