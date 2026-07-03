"""CastorObserver — generic Python integration surface (FR-9 #1).

Passive, framework-agnostic live observation (UC-2): feed steps as they
happen, get drift warnings via callback, pull a full report at the end.
Never blocks, never raises into the host pipeline (FR-12); optional async
mode runs embedding work on a background thread (FR-11).
"""
from __future__ import annotations

import dataclasses
import warnings
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from .analysis import CascadeAnalyzer
from .calibrate import ThresholdProfile
from .drift import DriftTracker, StepDrift
from .embedding import Embedder
from .entailment import EntailmentChecker
from .report import CascadeReport
from .trajectory import Trajectory, TrajectoryStep


class CastorObserver:
    """Owns one trajectory; observe steps live, report at the end (FR-9).

    - ``observe(step)`` — record a step; cheap drift check runs immediately
      (or on a background thread in async mode) and fires ``on_flag`` when a
      threshold is crossed. NLI is NOT run per step (too heavy for the hot
      path); it runs once in ``report()``.
    - ``report()`` — full cascade analysis (drift + NLI + classification +
      attribution).

    All observation errors are swallowed and surfaced as report notes —
    Castor must never crash the host pipeline (FR-12).
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        entailment: EntailmentChecker | bool | None = None,
        profile: ThresholdProfile | None = None,
        anchor: str | Sequence[str] | None = None,
        async_mode: bool = False,
        on_flag: Callable[[StepDrift], None] | None = None,
    ) -> None:
        self._profile = profile if profile is not None else ThresholdProfile()
        self._trajectory = Trajectory()
        self._tracker = DriftTracker(
            embedder=embedder,
            drift_threshold=self._profile.drift_threshold,
            anchor=anchor,
        )
        self._analyzer = CascadeAnalyzer(
            embedder=embedder, entailment=entailment, profile=self._profile, anchor=anchor
        )
        self._on_flag = on_flag
        self._already_flagged: set[str | int] = set()
        self._notes: list[str] = []
        self._executor = ThreadPoolExecutor(max_workers=1) if async_mode else None
        self._pending: list[Future] = []

    def observe(self, step: TrajectoryStep | Mapping[str, Any]) -> None:
        """Record one step (FR-9). Never raises (FR-12)."""
        try:
            stored = self._trajectory.add_step(step)
            if stored is None:
                return
            if self._executor is not None:
                self._pending.append(self._executor.submit(self._check_drift))
            else:
                self._check_drift()
        except Exception as exc:  # FR-12
            self._notes.append(f"observe failed: {type(exc).__name__}: {exc}")

    def report(self) -> CascadeReport:
        """Full cascade analysis of everything observed so far (FR-8, FR-9)."""
        self._drain()
        report = self._analyzer.analyze(self._trajectory)
        if self._notes:
            report = dataclasses.replace(
                report, notes=tuple(report.notes) + tuple(self._notes)
            )
        return report

    def _check_drift(self) -> None:
        """Cheap incremental drift check; fires on_flag once per step (UC-2)."""
        try:
            drift_report = self._tracker.analyze(self._trajectory)
            for result in drift_report.results:
                if result.flagged and result.step_id not in self._already_flagged:
                    self._already_flagged.add(result.step_id)
                    self._emit_flag(result)
        except Exception as exc:  # FR-12
            self._notes.append(f"drift check failed: {type(exc).__name__}: {exc}")

    def _emit_flag(self, result: StepDrift) -> None:
        if self._on_flag is None:
            warnings.warn(
                f"castor: step {result.step_id!r} crossed drift threshold "
                f"({'; '.join(result.flag_reasons)})",
                stacklevel=2,
            )
            return
        try:
            self._on_flag(result)
        except Exception as exc:  # user callback must not break observation (FR-12)
            self._notes.append(f"on_flag callback failed: {type(exc).__name__}: {exc}")

    def _drain(self) -> None:
        for future in self._pending:
            try:
                future.result(timeout=60)
            except Exception as exc:  # FR-12
                self._notes.append(f"async drift check failed: {type(exc).__name__}: {exc}")
        self._pending.clear()

    def close(self) -> None:
        """Shut down the async worker (if any)."""
        self._drain()
        if self._executor is not None:
            self._executor.shutdown(wait=True)

    def __enter__(self) -> "CastorObserver":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
