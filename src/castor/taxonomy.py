"""Rule-based cascade taxonomy classifier, 4 CHARM types (FR-6).

Multi-label with confidence: one cascade can carry two types at once. Scores
are heuristic signal strengths in [0, 1], not calibrated probabilities —
validation (phase 4) measures how well these rules hold up.
"""
from __future__ import annotations

from .config import DEFAULT_CLASSIFICATION_THRESHOLD, DEFAULT_DRIFT_THRESHOLD
from .report import StepSignals, TypeScore

RETRIEVAL = "retrieval"
INFERENCE = "inference"
CONTEXT_POISONING = "context_poisoning"
CONFIDENCE_INFLATION = "confidence_inflation"

_EXTERNAL_ROLES = frozenset({"tool", "memory", "retriever", "retrieval"})


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def classify(
    signals: list[StepSignals],
    roles: dict[str | int, str | None],
    drift_threshold: float = DEFAULT_DRIFT_THRESHOLD,
    entail_threshold: float | None = None,
    min_confidence: float = DEFAULT_CLASSIFICATION_THRESHOLD,
) -> tuple[TypeScore, ...]:
    """Classify a flagged trajectory into cascade types (FR-6).

    `roles` maps step_id -> role (used to spot externally injected content for
    the Context Poisoning signature). Returns all types scoring above
    `min_confidence`; if none do but drift was flagged, returns the single best
    type so the report is never silently empty.
    """
    measured = [s for s in signals if s.drift_anchor is not None]
    if not measured:
        return ()

    scores = [
        _score_retrieval(measured, drift_threshold),
        _score_inference(measured, entail_threshold),
        _score_poisoning(measured, roles, drift_threshold),
        _score_inflation(measured),
    ]
    scores = [s for s in scores if s is not None]
    above = tuple(sorted((s for s in scores if s.confidence >= min_confidence),
                         key=lambda s: -s.confidence))
    if above:
        return above
    if any(s.flagged for s in measured):
        best = max(scores, key=lambda s: s.confidence)
        return (best,) if best.confidence > 0 else ()
    return ()


def _score_retrieval(measured: list[StepSignals], threshold: float) -> TypeScore:
    """Retrieval Cascade: high drift vs anchor from the very start (H-02)."""
    early = [s.drift_anchor for s in measured[:2] if s.drift_anchor is not None]
    if not early:
        return TypeScore(RETRIEVAL, 0.0, "no early anchor drift measurable")
    early_mean = sum(early) / len(early)
    confidence = _clip((early_mean - threshold) / max(threshold * 2, 1e-9))
    return TypeScore(
        RETRIEVAL,
        confidence,
        f"anchor drift high from the first steps (mean {early_mean:.3f} vs threshold {threshold})",
    )


def _score_inference(measured: list[StepSignals], entail_threshold: float | None) -> TypeScore:
    """Inference Cascade: entailment drop on a conclusive claim + anchor drift
    climbing gradually while prev-drift stays moderate (H-05)."""
    violation = 0.0
    violating_step: str | int | None = None
    if entail_threshold is not None:
        for s in measured:
            if s.entailment is not None and s.conclusive and s.entailment < entail_threshold:
                v = (entail_threshold - s.entailment) / entail_threshold
                if v > violation:
                    violation, violating_step = v, s.step_id
    anchors = [s.drift_anchor for s in measured if s.drift_anchor is not None]
    rising = 0.0
    if len(anchors) >= 2:
        rises = sum(1 for a, b in zip(anchors, anchors[1:]) if b > a)
        rising = rises / (len(anchors) - 1)
    if entail_threshold is None:
        # Drift-only degraded mode: weaker evidence, conclusive language + rising anchor.
        conclusive_any = any(s.conclusive for s in measured)
        confidence = _clip(rising * (0.7 if conclusive_any else 0.4))
        rationale = f"drift-only mode: anchor drift rising ({rising:.0%} of transitions)"
    else:
        confidence = _clip(0.7 * violation + 0.3 * rising)
        rationale = (
            f"conclusive claim at step {violating_step} under-entailed by its premise"
            if violating_step is not None
            else f"no entailment violation on conclusive claims; anchor rising {rising:.0%}"
        )
    return TypeScore(INFERENCE, confidence, rationale)


def _score_poisoning(
    measured: list[StepSignals],
    roles: dict[str | int, str | None],
    threshold: float,
) -> TypeScore:
    """Context Poisoning: sudden anchor-drift spike mid-chain, especially on
    content entering from outside — tool or memory (H-04/H-12)."""
    best = 0.0
    best_step: str | int | None = None
    for prev, current in zip(measured, measured[1:]):
        if prev.drift_anchor is None or current.drift_anchor is None:
            continue
        jump = current.drift_anchor - prev.drift_anchor
        if jump <= 0:
            continue
        score = _clip(jump / max(threshold * 2, 1e-9))
        role = (roles.get(current.step_id) or "").lower()
        if role in _EXTERNAL_ROLES:
            score = _clip(score * 1.5)
        if score > best:
            best, best_step = score, current.step_id
    rationale = (
        f"sudden anchor-drift jump at step {best_step}"
        + (
            " on externally-sourced content"
            if best_step is not None and (roles.get(best_step) or "").lower() in _EXTERNAL_ROLES
            else ""
        )
        if best_step is not None
        else "no sudden mid-chain drift jump"
    )
    return TypeScore(CONTEXT_POISONING, best, rationale)


def _score_inflation(measured: list[StepSignals]) -> TypeScore:
    """Confidence Inflation: certainty language strengthening step over step
    while anchor drift rises — stronger claims without new grounding (H-11)."""
    inflations = [s.certainty_delta for s in measured if s.certainty_delta > 0]
    if not inflations:
        return TypeScore(CONFIDENCE_INFLATION, 0.0, "no certainty increase across steps")
    total_inflation = _clip(sum(inflations))
    anchors = [s.drift_anchor for s in measured if s.drift_anchor is not None]
    anchor_rising = len(anchors) >= 2 and anchors[-1] > anchors[0]
    confidence = _clip(total_inflation * (1.0 if anchor_rising else 0.5))
    return TypeScore(
        CONFIDENCE_INFLATION,
        confidence,
        f"certainty language strengthened (total inflation {total_inflation:.2f}"
        + (", anchor drift rising)" if anchor_rising else ", anchor drift flat)"),
    )
