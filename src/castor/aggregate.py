"""Weighted signal aggregation (CHARM-style), configurable weights.

Known limitation (PRD 3.3): the default weights 0.4/0.4/0.2 are inherited from
CHARM as reasonable manual defaults, NOT learned values. Recalibration from
synthetic data is a v1 goal.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_AGGREGATOR_WEIGHTS


@dataclass(frozen=True)
class AggregatorWeights:
    """Weights for (drift, entailment-violation, confidence-inflation)."""

    drift: float = DEFAULT_AGGREGATOR_WEIGHTS[0]
    entailment: float = DEFAULT_AGGREGATOR_WEIGHTS[1]
    confidence: float = DEFAULT_AGGREGATOR_WEIGHTS[2]


def aggregate_score(
    drift: float | None,
    entailment_violation: float | None,
    confidence_inflation: float | None,
    weights: AggregatorWeights = AggregatorWeights(),
) -> float | None:
    """Weighted mean of the available signals, each in [0, 1].

    Missing signals (e.g. NLI unavailable in drift-only degraded mode, FR-12)
    drop out and the remaining weights are renormalised, so the score stays on
    the same [0, 1] scale instead of silently shrinking.
    """
    parts = [
        (weights.drift, drift),
        (weights.entailment, entailment_violation),
        (weights.confidence, confidence_inflation),
    ]
    available = [(w, v) for w, v in parts if v is not None and w > 0]
    if not available:
        return None
    total_weight = sum(w for w, _ in available)
    return sum(w * v for w, v in available) / total_weight
