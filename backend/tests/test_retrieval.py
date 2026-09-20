import pytest

from app.core.exceptions import VectorStoreUnavailableError
from app.rag.faiss_store import FaissStore
from app.rag.retriever import GuidelineRetriever, build_retrieval_query
from tests.fake_embeddings import fake_embed_texts

SAMPLE_METADATA = [
    {
        "chunk_id": "DM-001",
        "guideline_id": "DM-DEMO",
        "guideline_title": "Demo Diabetes Guideline",
        "section": "Glycemic Assessment",
        "page": 1,
        "source": "diabetes_guideline.txt",
        "condition": "diabetes",
        "text": "Assess glycemic control using HbA1c and fasting glucose for diabetes.",
    },
    {
        "chunk_id": "HTN-001",
        "guideline_id": "HTN-DEMO",
        "guideline_title": "Demo Hypertension Guideline",
        "section": "Blood Pressure Classification",
        "page": 1,
        "source": "hypertension_guideline.txt",
        "condition": "hypertension",
        "text": "Blood pressure of 140/90 or higher is consistent with hypertension.",
    },
]


def _build_store(tmp_path) -> FaissStore:
    store = FaissStore(index_path=str(tmp_path / "index.faiss"), metadata_path=str(tmp_path / "metadata.json"))
    vectors = fake_embed_texts([m["text"] for m in SAMPLE_METADATA])
    store.build(vectors, SAMPLE_METADATA)
    return store


def test_faiss_store_build_and_search(tmp_path):
    store = _build_store(tmp_path)
    assert store.exists()
    assert store.size == 2

    query_vector = fake_embed_texts(["patient with elevated HbA1c and glucose"])[0]
    results = store.search(query_vector, top_k=2)

    assert len(results) == 2
    assert results[0]["chunk_id"] == "DM-001"


def test_faiss_store_missing_raises(tmp_path):
    store = FaissStore(index_path=str(tmp_path / "missing.faiss"), metadata_path=str(tmp_path / "missing.json"))
    with pytest.raises(VectorStoreUnavailableError):
        store.load()


def test_guideline_retriever_search(tmp_path):
    store = _build_store(tmp_path)
    retriever = GuidelineRetriever(store=store)

    result = retriever.search("hypertension blood pressure classification", top_k=1)

    assert result["query"]
    assert len(result["results"]) == 1
    assert result["results"][0]["guideline_id"] == "HTN-DEMO"


def test_build_retrieval_query_includes_conditions():
    query = build_retrieval_query(
        {"medical_history": ["type_2_diabetes", "hypertension"]},
        "Assess cardiovascular risk",
    )
    assert "Assess cardiovascular risk" in query
    assert "type_2_diabetes" in query
