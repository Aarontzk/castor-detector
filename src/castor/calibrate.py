"""Threshold profiles per task category + calibration from clean trajectories (FR-5, UC-4).

Single global thresholds are unfair across task types (heteroskedastic
signals, PRD 3.3) — users calibrate per domain from their own clean runs.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np

from .config import (
    DEFAULT_AGGREGATE_THRESHOLD,
    DEFAULT_COVERAGE_THRESHOLD,
    DEFAULT_DRIFT_COLLAPSE,
    DEFAULT_DRIFT_THRESHOLD,
    DEFAULT_ENTAIL_COLLAPSE,
    DEFAULT_ENTAILMENT_THRESHOLD,
    DEFAULT_OMISSION_COLLAPSE,
    DEFAULT_OMISSION_THRESHOLD,
)
from .drift import DriftTracker
from .embedding import Embedder
from .trajectory import Trajectory


@dataclass(frozen=True)
class ThresholdProfile:
    """Named threshold set for one task category (FR-5), e.g. "numeric", "narrative"."""

    name: str = "default"
    drift_threshold: float = DEFAULT_DRIFT_THRESHOLD
    entail_threshold: float = DEFAULT_ENTAILMENT_THRESHOLD
    aggregate_threshold: float = DEFAULT_AGGREGATE_THRESHOLD
    # v1 item 1 (omission signal). Defaulted so profiles saved before the
    # coverage check existed still load unchanged.
    coverage_threshold: float = DEFAULT_COVERAGE_THRESHOLD
    omission_threshold: float = DEFAULT_OMISSION_THRESHOLD
    # v1 item 3 (verdict rework). Collapse-grade trigger levels for the
    # trajectory verdict, stricter than the per-step flag thresholds above.
    # `None` disables that trigger. Defaulted for the same reason as the two
    # above: profiles saved earlier still load unchanged.
    entail_collapse: float | None = DEFAULT_ENTAIL_COLLAPSE
    omission_collapse: float | None = DEFAULT_OMISSION_COLLAPSE
    drift_collapse: float | None = DEFAULT_DRIFT_COLLAPSE

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ThresholdProfile":
        """Load a saved profile (FR-5). Unknown keys are ignored and missing
        keys fall back to defaults, so profiles survive schema growth."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})


@dataclass(frozen=True)
class CalibrationResult:
    """Recommended thresholds derived from a user's clean trajectories (UC-4)."""

    profile: ThresholdProfile
    n_trajectories: int
    n_measurements: int
    drift_mean: float
    drift_std: float
    drift_percentile_used: float


def calibrate(
    trajectories: Iterable[Trajectory],
    embedder: Embedder | None = None,
    percentile: float = 95.0,
    profile_name: str = "calibrated",
) -> CalibrationResult:
    """Compute the drift distribution of CLEAN trajectories and recommend a
    drift threshold at the given percentile (FR-5, UC-4).

    Steps drifting beyond what `percentile`% of the user's normal, correct
    runs exhibit are then treated as anomalous. Entailment/aggregate
    thresholds keep their defaults in v0.x (drift calibration first).
    """
    if embedder is None:
        from .embedding import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()
    drifts: list[float] = []
    n_trajectories = 0
    for trajectory in trajectories:
        n_trajectories += 1
        # Fresh tracker (cache) per trajectory; the embedder — and its loaded
        # model — is shared across all of them.
        report = DriftTracker(embedder=embedder).analyze(trajectory)
        for result in report.results:
            for value in (result.drift_prev, result.drift_anchor):
                if value is not None:
                    drifts.append(value)
    if not drifts:
        raise ValueError("no measurable drift values found — need trajectories with >=2 text steps")
    values = np.asarray(drifts)
    recommended = float(np.percentile(values, percentile))
    profile = ThresholdProfile(name=profile_name, drift_threshold=round(recommended, 4))
    return CalibrationResult(
        profile=profile,
        n_trajectories=n_trajectories,
        n_measurements=len(drifts),
        drift_mean=round(float(values.mean()), 4),
        drift_std=round(float(values.std()), 4),
        drift_percentile_used=percentile,
    )
