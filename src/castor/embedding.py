"""Embedding engine behind a pluggable interface (FR-2)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

import numpy as np

from .config import DEFAULT_EMBEDDING_MODEL


class Embedder(ABC):
    """Pluggable embedding interface (FR-2).

    Swap implementations (e.g. a multilingual model for Indonesian pipelines)
    without touching the drift core.
    """

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Return an array of shape (len(texts), dim)."""


class SentenceTransformerEmbedder(Embedder):
    """Default embedder: all-mpnet-base-v2 via sentence-transformers (FR-2).

    Local and free — no paid API. The model loads lazily on first use so that
    constructing a tracker never blocks or fails on model download.
    """

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL, device: str | None = None) -> None:
        self._model_name = model_name
        self._device = device
        self._model = None

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name, device=self._device)
        return np.asarray(self._model.encode(list(texts)))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity via numpy (FR-2). Returns 0.0 when either vector is all-zero."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)
