"""CascadeAnalyzer orchestration: aggregation, degradation, report assembly (FR-4..FR-8, FR-12)."""
import pytest

from castor import CascadeAnalyzer, ThresholdProfile
from tests.conftest import BrokenEmbedder, BrokenNLI, FakeEmbedder, FakeNLI

STEPS = [
    {"step_id": 1, "text": "alpha beta gamma delta", "agent_name": "planner"},
    {"step_id": 2, "text": "alpha beta gamma epsilon", "agent_name": "analyst"},
    {"step_id": 3, "text": "zulu yankee xray whiskey", "agent_name": "reasoner"},
]

PROFILE = ThresholdProfile(name="test", drift_threshold=0.3, entail_threshold=0.72,
                           aggregate_threshold=0.5)


def analyzer(**kwargs):
    defaults = dict(embedder=FakeEmbedder(), entailment=FakeNLI(), profile=PROFILE)
    defaults.update(kwargs)
    return CascadeAnalyzer(**defaults)


def test_full_report_structure():
    report = analyzer().analyze(STEPS)
    assert report.monitoring_failure is None
    assert not report.degraded
    assert len(report.steps) == 3
    assert report.verdict  # step 3 is fully disjoint => high everything
    assert report.classification
    assert report.attribution
    assert report.attribution[0].method == "threshold-based"
    assert report.thresholds["profile"] == "test"
    assert report.castor_version


def test_entailment_signal_merged():
    report = analyzer().analyze(STEPS)
    assert report.steps[0].entailment is None  # first step: no transition
    assert report.steps[1].entailment is not None
    assert report.steps[2].entailment is not None
    assert report.steps[2].entailment < report.steps[1].entailment  # disjoint step


def test_nli_failure_degrades_with_warning_not_crash():
    a = analyzer(entailment=BrokenNLI())
    with pytest.warns(UserWarning, match="drift-only"):
        report = a.analyze(STEPS)
    assert report.monitoring_failure is None
    assert report.degraded
    assert report.models["nli"] is None
    assert any("drift-only" in note for note in report.notes)
    assert all(s.entailment is None for s in report.steps)
    assert report.steps[2].aggregate is not None  # renormalised, still scored


def test_nli_disabled_on_purpose_is_not_degraded():
    report = analyzer(entailment=False).analyze(STEPS)
    assert not report.degraded
    assert report.models["nli"] is None


def test_broken_embedder_never_crashes():
    report = analyzer(embedder=BrokenEmbedder()).analyze(STEPS)
    assert report.monitoring_failure is not None
    assert report.verdict is False
    assert report.steps == ()


def test_json_and_text_outputs():
    report = analyzer().analyze(STEPS)
    text = report.to_text()
    assert "verdict" in text and "CASCADE" in text
    assert "threshold-based" in text
    data = report.to_dict()
    assert data["verdict"] is True
    assert len(data["steps"]) == 3
    import json

    json.loads(report.to_json())  # round-trips


def test_clean_trajectory_no_verdict():
    same = [{"step_id": i, "text": "alpha beta gamma delta"} for i in range(1, 4)]
    report = analyzer().analyze(same)
    assert report.verdict is False
    assert report.classification == ()
    assert report.attribution == ()
