"""Shared test fixtures: deterministic fake embedder so unit tests need no model."""
from __future__ import annotations

import zlib
from collections.abc import Sequence

import numpy as np
import pytest

from castor.embedding import Embedder
from castor.entailment import EntailmentChecker, EntailmentResult

DIM = 128


class FakeEmbedder(Embedder):
    """Deterministic bag-of-words embedder; records every embedded text for cache tests."""

    def __init__(self) -> None:
        self.embedded_texts: list[str] = []

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        self.embedded_texts.extend(texts)
        out = np.zeros((len(texts), DIM))
        for i, text in enumerate(texts):
            for word in text.lower().split():
                out[i, zlib.crc32(word.encode()) % DIM] += 1.0
        return out


class BrokenEmbedder(Embedder):
    """Always fails — used to prove FR-12 (Castor must never crash the pipeline)."""

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        raise RuntimeError("model exploded")


class FakeNLI(EntailmentChecker):
    """Deterministic word-overlap NLI: high overlap => entailment."""

    def check_batch(self, pairs):
        results = []
        for premise, hypothesis in pairs:
            p_words = set(premise.lower().split())
            h_words = set(hypothesis.lower().split())
            overlap = len(p_words & h_words) / max(len(h_words), 1)
            entail = min(0.95, max(0.05, overlap))
            rest = 1.0 - entail
            results.append(
                EntailmentResult(entailment=entail, neutral=rest * 0.7, contradiction=rest * 0.3)
            )
        return results


class BrokenNLI(EntailmentChecker):
    """Always fails — proves NLI degradation to drift-only mode (FR-12)."""

    def check_batch(self, pairs):
        raise OSError("nli model missing")


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()
