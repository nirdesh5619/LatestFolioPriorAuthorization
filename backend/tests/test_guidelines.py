from app.db.repositories import GuidelineRepository
from app.rag.faiss_store import FaissStore
from app.rag.ingestion import ingest_guidelines

GUIDELINES_DIR = "./data/guidelines"


def test_ingest_guidelines_creates_chunks_and_index(db_session, tmp_path):
    store = FaissStore(
        index_path=str(tmp_path / "index.faiss"),
        metadata_path=str(tmp_path / "metadata.json"),
    )

    result = ingest_guidelines(db_session, GUIDELINES_DIR, store)

    assert result["files_processed"] >= 4
    assert result["chunks_indexed"] > 0

    repo = GuidelineRepository(db_session)
    assert len(repo.list()) == result["files_processed"]
    assert repo.count_chunks() == result["chunks_indexed"]
    assert store.exists()


def test_guideline_api_list_and_search(client, db_session, tmp_path):
    # Seed guidelines directly into the same isolated session the overridden
    # `get_db` dependency uses, independent of the app's real bootstrap DB.
    # Ingest into a throwaway FAISS store so we don't disturb the process-wide
    # FAISS singleton that /guidelines/search relies on (already populated by
    # the app's own startup bootstrap).
    scratch_store = FaissStore(
        index_path=str(tmp_path / "index.faiss"), metadata_path=str(tmp_path / "metadata.json")
    )
    ingest_guidelines(db_session, GUIDELINES_DIR, scratch_store)

    list_resp = client.get("/api/v1/guidelines")
    assert list_resp.status_code == 200
    titles = [g["condition"] for g in list_resp.json()]
    assert len(titles) >= 4

    search_resp = client.post(
        "/api/v1/guidelines/search",
        json={"query": "diabetes hypertension cardiovascular risk", "top_k": 3},
    )
    assert search_resp.status_code == 200
    body = search_resp.json()
    assert body["query"]
    assert len(body["results"]) <= 3
    for result in body["results"]:
        assert "section" in result
        assert "guideline" in result
        assert "score" in result
