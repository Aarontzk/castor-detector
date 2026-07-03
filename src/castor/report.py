"""Report data structures: per-step signals, classification, attribution, report (FR-8)."""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class StepSignals:
    """All measured signals for one step."""

    step_id: str | int
    agent_name: str | None
    drift_prev: float | None
    drift_anchor: float | None
    entailment: float | None  # P(step entailed by its predecessor); None = first step or NLI off
    contradiction: float | None
    certainty: float  # certainty-language score of this step, [-1, 1]
    certainty_delta: float  # positive certainty increase vs previous step, [0, 1]
    conclusive: bool  # step makes a conclusive claim (therefore/maka/...)
    aggregate: float | None  # weighted anomaly score, [0, 1]
    flagged: bool
    flag_reasons: tuple[str, ...]


@dataclass(frozen=True)
class TypeScore:
    """One cascade-type classification with confidence (FR-6, multi-label)."""

    cascade_type: str  # retrieval | inference | context_poisoning | confidence_inflation
    confidence: float
    rationale: str


@dataclass(frozen=True)
class OriginCandidate:
    """Candidate origin step (FR-7). `method` is mandatory and always
    "threshold-based" in v0.x — this is candidate identification, NOT causal proof."""

    origin_step: str | int
    origin_agent: str | None
    cascade_type: tuple[str, ...]
    drift_scores: Mapping[str, float | None]
    confidence: float
    method: str = "threshold-based"


@dataclass(frozen=True)
class CascadeReport:
    """Full analysis result (FR-8): machine-readable + human-readable."""

    verdict: bool  # cascade detected?
    steps: tuple[StepSignals, ...]
    classification: tuple[TypeScore, ...]
    attribution: tuple[OriginCandidate, ...]
    thresholds: Mapping[str, Any]
    models: Mapping[str, str | None]
    castor_version: str
    notes: tuple[str, ...] = ()
    degraded: bool = False  # drift-only mode (NLI unavailable, FR-12)
    monitoring_failure: str | None = None

    @property
    def flagged_steps(self) -> tuple[StepSignals, ...]:
        return tuple(step for step in self.steps if step.flagged)

    def to_dict(self) -> dict[str, Any]:
        """Machine-readable report for CI and storage (FR-8)."""
        data = asdict(self)
        data["thresholds"] = dict(self.thresholds)
        data["models"] = dict(self.models)
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_text(self) -> str:
        """Human-readable terminal summary (FR-8)."""
        lines = [
            f"Castor {self.castor_version} — cascade analysis",
            f"verdict: {'CASCADE DETECTED' if self.verdict else 'no cascade detected'}"
            + (" [degraded: drift-only mode]" if self.degraded else ""),
            "",
            f"{'step':>8}  {'agent':<12} {'d_prev':>7} {'d_anchor':>8} {'entail':>7} {'aggr':>6}  flags",
        ]
        for s in self.steps:
            fmt = lambda v: f"{v:.3f}" if v is not None else "  -  "
            lines.append(
                f"{str(s.step_id):>8}  {(s.agent_name or '-'):<12} {fmt(s.drift_prev):>7}"
                f" {fmt(s.drift_anchor):>8} {fmt(s.entailment):>7} {fmt(s.aggregate):>6}"
                f"  {'; '.join(s.flag_reasons) if s.flagged else ''}"
            )
        if self.classification:
            lines.append("")
            lines.append("classification (rule-based, multi-label):")
            for t in self.classification:
                lines.append(f"  - {t.cascade_type} (confidence {t.confidence:.2f}): {t.rationale}")
        if self.attribution:
            lines.append("")
            lines.append("origin candidates (method: threshold-based — NOT causal proof):")
            for c in self.attribution:
                lines.append(
                    f"  - step {c.origin_step} (agent {c.origin_agent or '-'}), "
                    f"confidence {c.confidence:.2f}"
                )
        if self.notes:
            lines.append("")
            lines.append("notes:")
            lines.extend(f"  - {note}" for note in self.notes)
        lines.append("")
        lines.append(
            f"thresholds: {dict(self.thresholds)} | models: {dict(self.models)}"
        )
        return "\n".join(lines)
