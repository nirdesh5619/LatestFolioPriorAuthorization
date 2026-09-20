import json
import os

import numpy as np

from app.core.config import get_settings
from app.core.exceptions import VectorStoreUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


class FaissStore:
    """Thin wrapper around a FAISS flat inner-product index plus a JSON metadata sidecar."""

    def __init__(self, index_path: str | None = None, metadata_path: str | None = None):
        settings = get_settings()
        self.index_path = index_path or settings.faiss_index_path
        self.metadata_path = metadata_path or settings.faiss_metadata_path
        self._index = None
        self._metadata: list[dict] = []

    def exists(self) -> bool:
        return os.path.exists(self.index_path) and os.path.exists(self.metadata_path)

    def build(self, vectors: np.ndarray, metadata: list[dict]) -> None:
        import faiss

        if vectors.shape[0] != len(metadata):
            raise ValueError("Vector count and metadata count must match")

        dimension = vectors.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(vectors)

        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        faiss.write_index(index, self.index_path)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        self._index = index
        self._metadata = metadata
        logger.info("Built FAISS index with %d vectors (dim=%d)", vectors.shape[0], dimension)

    def load(self) -> None:
        if not self.exists():
            raise VectorStoreUnavailableError(
                f"FAISS index not found at '{self.index_path}'. Run guideline ingestion first."
            )
        try:
            import faiss

            self._index = faiss.read_index(self.index_path)
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.error("Failed to load FAISS index: %s", exc)
            raise VectorStoreUnavailableError(f"Failed to load FAISS index: {exc}") from exc

    def is_ready(self) -> bool:
        return self._index is not None and len(self._metadata) > 0

    def ensure_loaded(self) -> None:
        if not self.is_ready():
            self.load()

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[dict]:
        self.ensure_loaded()
        query = np.asarray(query_vector, dtype="float32").reshape(1, -1)
        scores, indices = self._index.search(query, min(top_k, len(self._metadata)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            entry = dict(self._metadata[idx])
            entry["score"] = float(score)
            results.append(entry)
        return results

    @property
    def size(self) -> int:
        return len(self._metadata)


_store: FaissStore | None = None


def get_faiss_store() -> FaissStore:
    global _store
    if _store is None:
        _store = FaissStore()
    return _store
