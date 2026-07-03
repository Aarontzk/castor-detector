"""Dual-reference drift tracking, thresholds and flagging (FR-3, FR-5 subset, FR-12)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import DEFAULT_CACHE_WINDOW, DEFAULT_DRIFT_THRESHOLD
from .embedding import Embedder, SentenceTransformerEmbedder, cosine_similarity
from .trajectory import Trajectory, TrajectoryStep


@dataclass(frozen=True)
class StepDrift:
    """Drift measurements for one step (FR-3)."""

    step_id: str | int
    agent_name: str | None
    drift_prev: float | None
    drift_anchor: float | None
    flagged: bool
    flag_reasons: tuple[str, ...]

    @property
    def combined_drift(self) -> float:
        """Mean of both references — used for ranking steps, not for flagging.

        Dual-reference ranking separates the step that left the trajectory
        (high prev AND high anchor) from the step after it that returns to
        course (high prev, low anchor). The weighted CHARM aggregator arrives
        with the phase 2 signals.
        """
        values = [v for v in (self.drift_prev, self.drift_anchor) if v is not None]
        return sum(values) / len(values) if values else 0.0


@dataclass(frozen=True)
class DriftReport:
    """Result of analysing one trajectory (FR-3, FR-5, FR-12)."""

    results: tuple[StepDrift, ...]
    notes: tuple[str, ...]
    drift_threshold: float
    anchor_description: str
    monitoring_failure: str | None = None

    @property
    def flagged_steps(self) -> tuple[StepDrift, ...]:
        """Steps whose drift exceeded the threshold on any reference (FR-5)."""
        return tuple(result for result in self.results if result.flagged)

    def max_drift_step(self) -> StepDrift | None:
        """The measured step with the highest combined drift, if any."""
        measured = [
            result
            for result in self.results
            if result.drift_prev is not None or result.drift_anchor is not None
        ]
        if not measured:
            return None
        return max(measured, key=lambda result: result.combined_drift)


class DriftTracker:
    """Dual-reference drift tracker (FR-3).

    For every measurable step i>=2:
    ``drift_prev = 1 - cos(e_i, e_{i-1})`` and
    ``drift_anchor = 1 - cos(e_i, e_anchor)``.

    The anchor defaults to the first measurable step and can be overridden
    with a text (e.g. the source document, H-02) or a list of texts —
    a consensus anchor built as the mean embedding (FR-3). The drift
    threshold is configurable per instance (FR-5). Embeddings are computed
    once per step and cached (FR-1). ``analyze()`` never raises (FR-12).
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        drift_threshold: float = DEFAULT_DRIFT_THRESHOLD,
        anchor: str | Sequence[str] | None = None,
        cache_window: int = DEFAULT_CACHE_WINDOW,
    ) -> None:
        self._embedder = embedder if embedder is not None else SentenceTransformerEmbedder()
        self._drift_threshold = float(drift_threshold)
        self._anchor_override = anchor
        self._cache: dict[int, tuple[str, np.ndarray]] = {}
        self._anchor_cache: np.ndarray | None = None
        # FR-11: sliding window for very long trajectories — the anchor
        # embedding is always retained, plus the most recent `cache_window`
        # steps. Evicted steps are re-embedded on demand (correctness kept).
        self._cache_window = int(cache_window)
        self._anchor_position: int | None = None

    def analyze(
        self,
        trajectory: Trajectory | Sequence[TrajectoryStep | Mapping[str, Any]],
    ) -> DriftReport:
        """Analyse a trajectory (FR-3, FR-5).

        Never raises — internal failures are returned as a report with
        ``monitoring_failure`` set, so Castor can never crash the host
        pipeline (FR-12).
        """
        try:
            return self._analyze(self._coerce(trajectory))
        except Exception as exc:  # FR-12: never crash the host pipeline
            failure = f"{type(exc).__name__}: {exc}"
            return DriftReport(
                results=(),
                notes=(f"monitoring failure: {failure}",),
                drift_threshold=self._drift_threshold,
                anchor_description=self._describe_anchor(),
                monitoring_failure=failure,
            )

    def _coerce(
        self, trajectory: Trajectory | Sequence[TrajectoryStep | Mapping[str, Any]]
    ) -> Trajectory:
        if isinstance(trajectory, Trajectory):
            return trajectory
        return Trajectory.from_steps(trajectory)

    def _analyze(self, trajectory: Trajectory) -> DriftReport:
        notes = list(trajectory.notes)
        measurable: list[tuple[int, TrajectoryStep]] = []
        for position, step in enumerate(trajectory.steps):
            if step.has_measurable_text:
                measurable.append((position, step))
            else:
                notes.append(f"step {step.step_id!r} skipped: empty or non-text content")

        if not measurable:
            notes.append("no measurable steps in trajectory")
            return DriftReport(
                (), tuple(notes), self._drift_threshold, self._describe_anchor(), None
            )

        embeddings = self._embed_steps(measurable)
        anchor_vector = self._anchor_vector(embeddings[0])

        results: list[StepDrift] = []
        for index, (_, step) in enumerate(measurable):
            if index == 0 and self._anchor_override is None:
                # First measurable step IS the anchor — nothing to measure against.
                results.append(StepDrift(step.step_id, step.agent_name, None, None, False, ()))
                continue
            drift_prev = (
                1.0 - cosine_similarity(embeddings[index], embeddings[index - 1])
                if index > 0
                else None
            )
            drift_anchor = 1.0 - cosine_similarity(embeddings[index], anchor_vector)
            reasons: list[str] = []
            if drift_prev is not None and drift_prev > self._drift_threshold:
                reasons.append(
                    f"drift_prev {drift_prev:.3f} > threshold {self._drift_threshold}"
                )
            if drift_anchor > self._drift_threshold:
                reasons.append(
                    f"drift_anchor {drift_anchor:.3f} > threshold {self._drift_threshold}"
                )
            results.append(
                StepDrift(
                    step_id=step.step_id,
                    agent_name=step.agent_name,
                    drift_prev=drift_prev,
                    drift_anchor=drift_anchor,
                    flagged=bool(reasons),
                    flag_reasons=tuple(reasons),
                )
            )

        return DriftReport(
            results=tuple(results),
            notes=tuple(notes),
            drift_threshold=self._drift_threshold,
            anchor_description=self._describe_anchor(),
            monitoring_failure=None,
        )

    def _embed_steps(self, measurable: list[tuple[int, TrajectoryStep]]) -> list[np.ndarray]:
        """Embed steps, computing each step's embedding exactly once (FR-1 cache)."""
        to_embed = [
            (position, step.text)
            for position, step in measurable
            if self._cache.get(position, (None,))[0] != step.text
        ]
        if to_embed:
            vectors = np.atleast_2d(np.asarray(self._embedder.embed([text for _, text in to_embed])))
            for (position, text), vector in zip(to_embed, vectors):
                self._cache[position] = (text, np.asarray(vector))
        embeddings = [self._cache[position][1] for position, _ in measurable]
        self._anchor_position = measurable[0][0]
        self._evict_beyond_window()
        return embeddings

    def _evict_beyond_window(self) -> None:
        """FR-11: cap cache memory — keep anchor + most recent window."""
        if len(self._cache) <= self._cache_window + 1:
            return
        evictable = sorted(pos for pos in self._cache if pos != self._anchor_position)
        for position in evictable[: len(evictable) - self._cache_window]:
            del self._cache[position]

    def _anchor_vector(self, first_step_embedding: np.ndarray) -> np.ndarray:
        if self._anchor_override is None:
            return first_step_embedding
        if self._anchor_cache is None:
            texts = (
                [self._anchor_override]
                if isinstance(self._anchor_override, str)
                else list(self._anchor_override)
            )
            vectors = np.atleast_2d(np.asarray(self._embedder.embed(texts)))
            # FR-3 consensus anchor: mean embedding of the reference texts.
            self._anchor_cache = vectors.mean(axis=0)
        return self._anchor_cache

    def _describe_anchor(self) -> str:
        if self._anchor_override is None:
            return "first measurable step"
        if isinstance(self._anchor_override, str):
            return "custom anchor text"
        return f"consensus of {len(list(self._anchor_override))} anchor texts"
