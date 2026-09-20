from app.core.config import get_settings
from app.rag.embeddings import embed_query
from app.rag.faiss_store import FaissStore, get_faiss_store


class GuidelineRetriever:
    def __init__(self, store: FaissStore | None = None):
        self.store = store or get_faiss_store()

    def search(self, query: str, top_k: int | None = None) -> dict:
        settings = get_settings()
        top_k = top_k or settings.top_k

        query_vector = embed_query(query)
        raw_results = self.store.search(query_vector, top_k=top_k)

        results = [
            {
                "score": r["score"],
                "text": r["text"],
                "guideline": r["guideline_title"],
                "guideline_id": r["guideline_id"],
                "section": r["section"],
                "source": r["source"],
                "page": r["page"],
            }
            for r in raw_results
        ]

        return {"query": query, "results": results}


def build_retrieval_query(
    patient_data: dict,
    clinical_question: str,
    requested_service: str | None = None,
    diagnosis_codes: list[str] | None = None,
    prior_treatments_tried: list[str] | None = None,
) -> str:
    conditions = patient_data.get("medical_history") or []
    parts: list[str] = []

    if requested_service:
        parts.append(f"Requested service: {requested_service}")
    if diagnosis_codes:
        parts.append("Diagnoses: " + ", ".join(diagnosis_codes))
    if clinical_question:
        parts.append(clinical_question)
    if conditions:
        parts.append("Relevant conditions: " + ", ".join(conditions))
    if prior_treatments_tried:
        parts.append("Prior treatments tried: " + ", ".join(prior_treatments_tried))

    return " ".join(parts) if parts else (clinical_question or "prior authorization request")
