"""Transition-validity (entailment) checking behind a pluggable interface (FR-4)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .config import DEFAULT_NLI_MODEL

# Standard label order for cross-encoder/nli-deberta-v3-base; overridden at
# runtime from the model config when available.
_FALLBACK_LABELS = ("contradiction", "entailment", "neutral")


@dataclass(frozen=True)
class EntailmentResult:
    """Entail/neutral/contradiction probabilities for one transition (FR-4)."""

    entailment: float
    neutral: float
    contradiction: float

    @property
    def label(self) -> str:
        scores = {
            "entailment": self.entailment,
            "neutral": self.neutral,
            "contradiction": self.contradiction,
        }
        return max(scores, key=scores.get)


class EntailmentChecker(ABC):
    """Pluggable NLI interface (FR-4). Swap models without touching the core."""

    @abstractmethod
    def check_batch(self, pairs: Sequence[tuple[str, str]]) -> list[EntailmentResult]:
        """Score (premise, hypothesis) pairs."""

    def check(self, premise: str, hypothesis: str) -> EntailmentResult:
        """Score one transition: is `hypothesis` entailed by `premise`? (FR-4)"""
        return self.check_batch([(premise, hypothesis)])[0]


class CrossEncoderEntailment(EntailmentChecker):
    """Default NLI checker: cross-encoder/nli-deberta-v3-base, local and free (FR-4).

    Loads lazily on first use. Load/inference failures propagate to the caller,
    where the analyzer degrades to drift-only mode with an explicit warning
    (FR-12) — this class stays honest and simple.
    """

    def __init__(self, model_name: str = DEFAULT_NLI_MODEL, device: str | None = None) -> None:
        self._model_name = model_name
        self._device = device
        self._model = None
        self._labels: tuple[str, ...] = _FALLBACK_LABELS

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name, device=self._device)
            id2label = getattr(getattr(self._model.model, "config", None), "id2label", None)
            if id2label:
                self._labels = tuple(id2label[i].lower() for i in sorted(id2label))
        return self._model

    def check_batch(self, pairs: Sequence[tuple[str, str]]) -> list[EntailmentResult]:
        model = self._load()
        logits = np.atleast_2d(np.asarray(model.predict(list(pairs))))
        exp = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = exp / exp.sum(axis=1, keepdims=True)
        results = []
        for row in probs:
            by_label = dict(zip(self._labels, (float(v) for v in row)))
            results.append(
                EntailmentResult(
                    entailment=by_label.get("entailment", 0.0),
                    neutral=by_label.get("neutral", 0.0),
                    contradiction=by_label.get("contradiction", 0.0),
                )
            )
        return results
