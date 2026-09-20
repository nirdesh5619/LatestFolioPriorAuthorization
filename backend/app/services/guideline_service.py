from app.rag.retriever import GuidelineRetriever
from app.schemas.guideline import GuidelineSearchResponse, GuidelineSearchResult


class GuidelineService:
    def __init__(self, retriever: GuidelineRetriever | None = None):
        self.retriever = retriever or GuidelineRetriever()

    def search(self, query: str, top_k: int | None = None) -> GuidelineSearchResponse:
        result = self.retriever.search(query, top_k=top_k)
        return GuidelineSearchResponse(
            query=result["query"],
            results=[GuidelineSearchResult(**r) for r in result["results"]],
        )
