"""Threshold-based origin attribution (FR-7).

Honest by construction: every candidate carries `method: "threshold-based"`
and a confidence score. This identifies CANDIDATE origin steps, never causal
proof (PRD 3.3; causal upgrades are v2).
"""
from __future__ import annotations

from .report import OriginCandidate, StepSignals, TypeScore


def attribute(
    signals: list[StepSignals],
    classification: tuple[TypeScore, ...],
    drift_threshold: float,
    entail_threshold: float | None,
) -> tuple[OriginCandidate, ...]:
    """Identify candidate origin steps (FR-7).

    A candidate is any step crossing a threshold on ANY signal. All candidates
    are reported in trajectory order (never forced to a single answer — PRD
    FR-7). Confidence = fraction of signals crossed, weighted by how far the
    strongest signal exceeds its threshold; the FIRST crossing step gets a
    small boost since cascades propagate forward.
    """
    cascade_types = tuple(t.cascade_type for t in classification)
    candidates: list[OriginCandidate] = []
    for s in signals:
        crossed: list[tuple[str, float]] = []  # (signal name, margin in threshold units)
        if s.drift_prev is not None and s.drift_prev > drift_threshold:
            crossed.append(("drift_prev", (s.drift_prev - drift_threshold) / drift_threshold))
        if s.drift_anchor is not None and s.drift_anchor > drift_threshold:
            crossed.append(("drift_anchor", (s.drift_anchor - drift_threshold) / drift_threshold))
        if (
            entail_threshold is not None
            and s.entailment is not None
            and s.entailment < entail_threshold
        ):
            crossed.append(("entailment", (entail_threshold - s.entailment) / entail_threshold))
        if not crossed:
            continue
        n_signals = 3 if entail_threshold is not None else 2
        strongest = max(margin for _, margin in crossed)
        confidence = 0.6 * (len(crossed) / n_signals) + 0.4 * min(1.0, strongest)
        if not candidates:  # first crossing step: cascades propagate forward
            confidence = min(1.0, confidence + 0.1)
        candidates.append(
            OriginCandidate(
                origin_step=s.step_id,
                origin_agent=s.agent_name,
                cascade_type=cascade_types,
                drift_scores={
                    "drift_prev": s.drift_prev,
                    "drift_anchor": s.drift_anchor,
                    "entailment": s.entailment,
                    "aggregate": s.aggregate,
                },
                confidence=round(confidence, 3),
                method="threshold-based",
            )
        )
    return tuple(candidates)
