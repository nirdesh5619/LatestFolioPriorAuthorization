import numpy as np

from app.core.config import get_settings
from app.core.exceptions import EmbeddingModelUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

_model_cache: dict[str, object] = {}


def _load_model():
    settings = get_settings()
    model_name = settings.embedding_model
    if model_name in _model_cache:
        return _model_cache[model_name]

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.error("Failed to load embedding model %s: %s", model_name, exc)
        raise EmbeddingModelUnavailableError(
            f"Embedding model '{model_name}' could not be loaded: {exc}"
        ) from exc

    _model_cache[model_name] = model
    return model


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, get_embedding_dimension()), dtype="float32")
    model = _load_model()
    vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return np.asarray(vectors, dtype="float32")


def embed_query(query: str) -> np.ndarray:
    return embed_texts([query])[0]


def get_embedding_dimension() -> int:
    model = _load_model()
    return int(model.get_sentence_embedding_dimension())
