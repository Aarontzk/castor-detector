"""Trajectory-level verdict rule: per-signal disjunction (v1 item 3).

The rule these tests pin down: the verdict fires when the aggregate crosses
theta OR any single signal collapses on its own. The motivating defect is that
the aggregate is a weighted MEAN, so one collapsed signal averaged against two
calm ones lands under theta — measured on the organic set, the aggregate-only
rule returned False on all 24 annotated cascades.
"""
from __future__ import annotations

import pytest

from castor import CascadeAnalyzer, ThresholdProfile
from castor.entailment import EntailmentChecker, EntailmentResult
from tests.conftest import FakeEmbedder, FakeNLI

# Collapse levels far from the flag thresholds so each test isolates one trigger.
PROFILE = ThresholdProfile(
    name="verdict-test",
    drift_threshold=0.3,
    entail_threshold=0.72,
    aggregate_threshold=0.9,   # high: the aggregate must not fire incidentally
    omission_threshold=0.25,
    entail_collapse=0.01,
    omission_collapse=0.5,
    drift_collapse=0.9,
)

NEAR_STEPS = [
    {"step_id": 1, "text": "alpha beta gamma delta", "agent_name": "one"},
    {"step_id": 2, "text": "alpha beta gamma delta epsilon", "agent_name": "two"},
]


class ConstantNLI(EntailmentChecker):
    """Returns one fixed entailment probability for every transition."""

    def __init__(self, entailment: float) -> None:
        self._entailment = entailment

    def check_batch(self, pairs):
        rest = 1.0 - self._entailment
        return [
            EntailmentResult(
                entailment=self._entailment,
                neutral=rest * 0.7,
                contradiction=rest * 0.3,
            )
            for _ in pairs
        ]


def analyzer(**kwargs):
    defaults = dict(embedder=FakeEmbedder(), entailment=FakeNLI(), profile=PROFILE)
    defaults.update(kwargs)
    return CascadeAnalyzer(**defaults)


def test_entailment_collapse_fires_verdict_alone():
    """The regression this rework exists for: one collapsed signal is enough."""
    report = analyzer(entailment=ConstantNLI(0.001)).analyze(NEAR_STEPS)
    assert report.verdict
    assert any("entailment collapse" in r for r in report.verdict_reasons)
    # It really was the entailment trigger, not the aggregate sneaking through.
    assert not any("aggregate" in r for r in report.verdict_reasons)


def test_entailment_just_above_collapse_does_not_fire():
    """Boundary: below the per-step flag threshold, above collapse grade."""
    report = analyzer(entailment=ConstantNLI(0.05)).analyze(NEAR_STEPS)
    assert not report.verdict
    assert report.verdict_reasons == ()
    # Still worth flagging the step — collapse grade is stricter than flag grade.
    assert report.steps[1].flagged


def test_aggregate_trigger_still_fires():
    """The original rule survives as one disjunct, so old behaviour is preserved."""
    profile = ThresholdProfile(
        name="low-theta", drift_threshold=0.3, entail_threshold=0.72,
        aggregate_threshold=0.1, entail_collapse=0.0,
        omission_collapse=1.01, drift_collapse=1.01,
    )
    steps = [
        {"step_id": 1, "text": "alpha beta gamma", "agent_name": "one"},
        {"step_id": 2, "text": "zulu yankee xray", "agent_name": "two"},
    ]
    report = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI(), profile=profile
    ).analyze(steps)
    assert report.verdict
    assert any("aggregate" in r for r in report.verdict_reasons)


def test_drift_collapse_fires_verdict():
    profile = ThresholdProfile(
        name="drift-only-trigger", drift_threshold=0.3, entail_threshold=0.72,
        aggregate_threshold=0.99, entail_collapse=0.0,
        omission_collapse=1.01, drift_collapse=0.5,
    )
    steps = [
        {"step_id": 1, "text": "alpha beta gamma", "agent_name": "one"},
        {"step_id": 2, "text": "zulu yankee xray", "agent_name": "two"},
    ]
    report = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI(), profile=profile
    ).analyze(steps)
    assert report.verdict
    assert any("anchor drift" in r for r in report.verdict_reasons)


def test_clean_trajectory_stays_clean():
    """No trigger crosses => no verdict, and no reasons invented."""
    profile = ThresholdProfile(
        name="strict", drift_threshold=0.9, entail_threshold=0.1,
        aggregate_threshold=0.99, entail_collapse=0.0,
        omission_collapse=1.01, drift_collapse=1.01,
    )
    report = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI(), profile=profile
    ).analyze(NEAR_STEPS)
    assert not report.verdict
    assert report.verdict_reasons == ()
    assert report.classification == ()
    assert report.attribution == ()


def test_verdict_reasons_name_the_step():
    """A verdict that does not say where is not actionable (FR-7 spirit)."""
    report = analyzer(entailment=ConstantNLI(0.001)).analyze(NEAR_STEPS)
    assert any("at step" in r for r in report.verdict_reasons)


def test_verdict_reasons_serialise():
    report = analyzer(entailment=ConstantNLI(0.001)).analyze(NEAR_STEPS)
    assert report.to_dict()["verdict_reasons"]
    assert "triggered by:" in report.to_text()


def test_verdict_survives_missing_signals():
    """Drift-only mode: entailment/omission are None and must not raise (FR-12)."""
    report = analyzer(entailment=False).analyze(NEAR_STEPS)
    assert report.monitoring_failure is None
    assert isinstance(report.verdict, bool)


def test_collapse_thresholds_reported():
    """Thresholds are configuration, so they belong in the report (FR-8)."""
    report = analyzer().analyze(NEAR_STEPS)
    assert report.thresholds["entail_collapse"] == PROFILE.entail_collapse
    assert report.thresholds["omission_collapse"] == PROFILE.omission_collapse
    assert report.thresholds["drift_collapse"] == PROFILE.drift_collapse


def test_profile_without_collapse_fields_still_loads(tmp_path):
    """Profiles saved before this rework must keep working (forward compat)."""
    path = tmp_path / "old-profile.json"
    path.write_text(
        '{"name": "old", "drift_threshold": 0.8, "entail_threshold": 0.72,'
        ' "aggregate_threshold": 0.71}',
        encoding="utf-8",
    )
    profile = ThresholdProfile.load(path)
    assert profile.name == "old"
    assert profile.entail_collapse == pytest.approx(0.01)
    assert profile.drift_collapse == pytest.approx(0.9)
    # Measured default: omission cannot separate broken chains from healthy
    # ones at trajectory level, so it ships disabled as a verdict trigger.
    assert profile.omission_collapse is None


def test_none_level_disables_a_trigger():
    """A None collapse level must switch that trigger off, not crash on compare."""
    steps = [
        {"step_id": 1, "text": "alpha beta gamma", "agent_name": "one"},
        {"step_id": 2, "text": "zulu yankee xray", "agent_name": "two"},
    ]
    off = ThresholdProfile(
        name="all-off", drift_threshold=0.3, entail_threshold=0.72,
        aggregate_threshold=0.99, entail_collapse=None,
        omission_collapse=None, drift_collapse=None,
    )
    report = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI(), profile=off
    ).analyze(steps)
    assert not report.verdict
    assert report.verdict_reasons == ()


def test_omission_disabled_by_default_in_shipped_profile():
    """Regression guard for the measured decision, at the default profile."""
    assert ThresholdProfile().omission_collapse is None
