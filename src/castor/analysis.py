"""CascadeAnalyzer — orchestrates drift, entailment, confidence, aggregation,
classification and attribution into one CascadeReport (FR-3..FR-8, FR-12)."""
from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from typing import Any

from .aggregate import AggregatorWeights, aggregate_score
from .attribution import attribute
from .calibrate import ThresholdProfile
from .confidence import certainty_series, inflation_delta
from .config import DEFAULT_EMBEDDING_MODEL, DEFAULT_NLI_MODEL
from .drift import DriftTracker
from .embedding import Embedder
from .entailment import CrossEncoderEntailment, EntailmentChecker
from .report import CascadeReport, StepSignals
from .taxonomy import classify
from .trajectory import Trajectory, TrajectoryStep


class CascadeAnalyzer:
    """Full cascade analysis pipeline (phases 1-3). Passive: report only.

    `analyze()` never raises (FR-12). If the NLI model cannot load, the
    analyzer degrades to drift-only mode with an explicit warning — never
    silently (FR-12).

    Set `entailment=None` (default) for the local cross-encoder, pass your own
    `EntailmentChecker`, or `entailment=False` to run drift-only on purpose.
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        entailment: EntailmentChecker | bool | None = None,
        profile: ThresholdProfile | None = None,
        weights: AggregatorWeights | None = None,
        anchor: str | Sequence[str] | None = None,
    ) -> None:
        self._profile = profile if profile is not None else ThresholdProfile()
        self._weights = weights if weights is not None else AggregatorWeights()
        # Report the actual embedding model for reproducibility (FR-8).
        self._embedding_name = (
            DEFAULT_EMBEDDING_MODEL
            if embedder is None
            else getattr(embedder, "_model_name", type(embedder).__name__)
        )
        self._tracker = DriftTracker(
            embedder=embedder,
            drift_threshold=self._profile.drift_threshold,
            anchor=anchor,
        )
        if entailment is False:
            self._entailment: EntailmentChecker | None = None
            self._nli_requested = False
        else:
            self._entailment = entailment if entailment is not None else CrossEncoderEntailment()
            self._nli_requested = True
        self._nli_model_name = DEFAULT_NLI_MODEL if self._nli_requested else None

    def analyze(
        self,
        trajectory: Trajectory | Sequence[TrajectoryStep | Mapping[str, Any]],
    ) -> CascadeReport:
        """Analyse one trajectory into a full CascadeReport (FR-8). Never raises (FR-12)."""
        try:
            return self._analyze(trajectory)
        except Exception as exc:  # FR-12: never crash the host pipeline
            failure = f"{type(exc).__name__}: {exc}"
            return CascadeReport(
                verdict=False,
                steps=(),
                classification=(),
                attribution=(),
                thresholds=self._thresholds_dict(),
                models=self._models_dict(),
                castor_version=_version(),
                notes=(f"monitoring failure: {failure}",),
                degraded=True,
                monitoring_failure=failure,
            )

    def _analyze(self, trajectory) -> CascadeReport:
        drift_report = self._tracker.analyze(trajectory)
        if drift_report.monitoring_failure is not None:
            return CascadeReport(
                verdict=False,
                steps=(),
                classification=(),
                attribution=(),
                thresholds=self._thresholds_dict(),
                models=self._models_dict(),
                castor_version=_version(),
                notes=drift_report.notes,
                degraded=True,
                monitoring_failure=drift_report.monitoring_failure,
            )

        source = trajectory if isinstance(trajectory, Trajectory) else Trajectory.from_steps(trajectory)
        measurable = [step for step in source.steps if step.has_measurable_text]
        notes = list(drift_report.notes)

        entail_results = self._run_entailment(measurable, notes)
        degraded = self._nli_requested and entail_results is None
        certainty = certainty_series([step.text for step in measurable])

        signals = self._merge_signals(drift_report, measurable, entail_results, certainty)
        verdict = self._verdict(signals)
        roles = {step.step_id: step.role for step in measurable}
        entail_threshold = self._profile.entail_threshold if entail_results is not None else None
        classification = classify(
            signals,
            roles,
            drift_threshold=self._profile.drift_threshold,
            entail_threshold=entail_threshold,
        ) if verdict else ()
        candidates = attribute(
            signals, classification, self._profile.drift_threshold, entail_threshold
        ) if verdict else ()

        return CascadeReport(
            verdict=verdict,
            steps=tuple(signals),
            classification=classification,
            attribution=candidates,
            thresholds=self._thresholds_dict(),
            models=self._models_dict(degraded),
            castor_version=_version(),
            notes=tuple(notes),
            degraded=degraded,
            monitoring_failure=None,
        )

    def _run_entailment(self, measurable, notes: list[str]):
        """NLI on consecutive transitions; degrade to drift-only with an
        explicit warning when the model is unavailable (FR-4, FR-12)."""
        if self._entailment is None or len(measurable) < 2:
            return None
        pairs = [
            (previous.text, current.text)
            for previous, current in zip(measurable, measurable[1:])
        ]
        try:
            return self._entailment.check_batch(pairs)
        except Exception as exc:
            message = (
                f"NLI model unavailable ({type(exc).__name__}: {exc}) — "
                "degraded to drift-only mode"
            )
            warnings.warn(message, stacklevel=2)
            notes.append(message)
            return None

    def _merge_signals(self, drift_report, measurable, entail_results, certainty):
        """Combine drift, entailment and certainty into per-step StepSignals."""
        signals: list[StepSignals] = []
        for index, (drift, step) in enumerate(zip(drift_report.results, measurable)):
            entail = entail_results[index - 1] if entail_results is not None and index >= 1 else None
            cert = certainty[index]
            delta = inflation_delta(certainty[index - 1], cert) if index >= 1 else 0.0
            drift_for_aggregate = (
                None
                if drift.drift_prev is None and drift.drift_anchor is None
                else drift.combined_drift
            )
            aggregate = aggregate_score(
                drift=drift_for_aggregate,
                entailment_violation=(1.0 - entail.entailment) if entail is not None else None,
                confidence_inflation=delta if index >= 1 else None,
                weights=self._weights,
            )
            reasons = list(drift.flag_reasons)
            if (
                entail is not None
                and entail.entailment < self._profile.entail_threshold
            ):
                reasons.append(
                    f"entailment {entail.entailment:.3f} < threshold {self._profile.entail_threshold}"
                )
            if aggregate is not None and aggregate > self._profile.aggregate_threshold:
                reasons.append(
                    f"aggregate {aggregate:.3f} > threshold {self._profile.aggregate_threshold}"
                )
            signals.append(
                StepSignals(
                    step_id=drift.step_id,
                    agent_name=drift.agent_name,
                    drift_prev=drift.drift_prev,
                    drift_anchor=drift.drift_anchor,
                    entailment=entail.entailment if entail is not None else None,
                    contradiction=entail.contradiction if entail is not None else None,
                    certainty=cert.score,
                    certainty_delta=delta,
                    conclusive=cert.conclusive,
                    aggregate=aggregate,
                    flagged=bool(reasons),
                    flag_reasons=tuple(reasons),
                )
            )
        return signals

    def _verdict(self, signals: list[StepSignals]) -> bool:
        """Cascade verdict: any step's aggregate crosses the aggregate threshold."""
        return any(
            s.aggregate is not None and s.aggregate > self._profile.aggregate_threshold
            for s in signals
        )

    def _thresholds_dict(self) -> dict[str, Any]:
        return {
            "profile": self._profile.name,
            "drift_threshold": self._profile.drift_threshold,
            "entail_threshold": self._profile.entail_threshold,
            "aggregate_threshold": self._profile.aggregate_threshold,
            "weights": (self._weights.drift, self._weights.entailment, self._weights.confidence),
        }

    def _models_dict(self, degraded: bool = False) -> dict[str, str | None]:
        return {
            "embedding": self._embedding_name,
            "nli": None if (not self._nli_requested or degraded) else self._nli_model_name,
        }


def _version() -> str:
    from . import __version__

    return __version__
