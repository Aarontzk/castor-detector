"""FR-3 (dual-reference drift), FR-5 (thresholds/flagging), FR-12 (never crash)."""
import numpy as np
import pytest

from castor import DriftTracker, Trajectory, cosine_similarity
from tests.conftest import BrokenEmbedder, FakeEmbedder

STEPS = [
    {"step_id": 1, "text": "alpha beta gamma", "agent_name": "planner"},
    {"step_id": 2, "text": "alpha beta delta", "agent_name": "reasoner"},
    {"step_id": 3, "text": "zulu yankee xray", "agent_name": "reasoner"},
]


def expected_drift(embedder_cls, text_a: str, text_b: str) -> float:
    vectors = embedder_cls().embed([text_a, text_b])
    return 1.0 - cosine_similarity(vectors[0], vectors[1])


def test_dual_reference_drift_values(fake_embedder):
    report = DriftTracker(embedder=fake_embedder).analyze(STEPS)
    assert report.monitoring_failure is None
    first, second, third = report.results

    # Step 1 is the anchor: nothing to measure.
    assert first.drift_prev is None and first.drift_anchor is None

    assert second.drift_prev == pytest.approx(
        expected_drift(FakeEmbedder, STEPS[0]["text"], STEPS[1]["text"])
    )
    assert second.drift_anchor == pytest.approx(second.drift_prev)  # anchor == step 1

    assert third.drift_prev == pytest.approx(
        expected_drift(FakeEmbedder, STEPS[1]["text"], STEPS[2]["text"])
    )
    assert third.drift_anchor == pytest.approx(
        expected_drift(FakeEmbedder, STEPS[0]["text"], STEPS[2]["text"])
    )


def test_disjoint_step_gets_highest_drift(fake_embedder):
    report = DriftTracker(embedder=fake_embedder).analyze(STEPS)
    assert report.max_drift_step().step_id == 3


def test_anchor_override_text(fake_embedder):
    report = DriftTracker(embedder=fake_embedder, anchor="alpha beta gamma").analyze(STEPS)
    # With an override, step 1 is also measured against the anchor.
    first = report.results[0]
    assert first.drift_anchor == pytest.approx(0.0)
    assert first.drift_prev is None
    assert report.anchor_description == "custom anchor text"


def test_consensus_anchor_is_mean_embedding(fake_embedder):
    texts = ["alpha beta gamma", "alpha beta delta"]
    report = DriftTracker(embedder=fake_embedder, anchor=texts).analyze(STEPS)
    vectors = FakeEmbedder().embed(texts)
    consensus = vectors.mean(axis=0)
    step3_vector = FakeEmbedder().embed([STEPS[2]["text"]])[0]
    expected = 1.0 - cosine_similarity(step3_vector, consensus)
    assert report.results[2].drift_anchor == pytest.approx(expected)
    assert "consensus of 2" in report.anchor_description


def test_embeddings_cached_across_analyze_calls(fake_embedder):
    tracker = DriftTracker(embedder=fake_embedder)
    tracker.analyze(STEPS)
    tracker.analyze(STEPS)
    # Each step text embedded exactly once despite two analyze() calls (FR-1).
    assert sorted(fake_embedder.embedded_texts) == sorted(s["text"] for s in STEPS)


def test_threshold_configurable_per_instance(fake_embedder):
    strict = DriftTracker(embedder=fake_embedder, drift_threshold=0.0).analyze(STEPS)
    lax = DriftTracker(embedder=FakeEmbedder(), drift_threshold=1.0).analyze(STEPS)
    assert len(strict.flagged_steps) > 0
    assert len(lax.flagged_steps) == 0
    assert strict.drift_threshold == 0.0
    assert lax.drift_threshold == 1.0


def test_flag_reasons_name_the_signal(fake_embedder):
    report = DriftTracker(embedder=fake_embedder, drift_threshold=0.0).analyze(STEPS)
    third = report.results[2]
    assert third.flagged
    assert any("drift_prev" in reason for reason in third.flag_reasons)
    assert any("drift_anchor" in reason for reason in third.flag_reasons)


def test_empty_step_skipped_with_note(fake_embedder):
    steps = [STEPS[0], {"step_id": "empty", "text": "   "}, STEPS[1], STEPS[2]]
    report = DriftTracker(embedder=fake_embedder).analyze(steps)
    assert report.monitoring_failure is None
    measured_ids = [r.step_id for r in report.results]
    assert "empty" not in measured_ids
    assert measured_ids == [1, 2, 3]
    assert any("skipped" in note for note in report.notes)


def test_broken_embedder_never_crashes():
    report = DriftTracker(embedder=BrokenEmbedder()).analyze(STEPS)
    assert report.monitoring_failure is not None
    assert "RuntimeError" in report.monitoring_failure
    assert report.results == ()


def test_all_empty_trajectory_reports_not_crashes(fake_embedder):
    report = DriftTracker(embedder=fake_embedder).analyze([{"step_id": 1, "text": ""}])
    assert report.monitoring_failure is None
    assert report.results == ()
    assert any("no measurable steps" in note for note in report.notes)


def test_sliding_window_keeps_anchor_and_recent(fake_embedder):
    # FR-11: >window steps — cache capped at anchor + window, results still full.
    steps = [{"step_id": i, "text": f"word{i} alpha beta"} for i in range(1, 31)]
    tracker = DriftTracker(embedder=fake_embedder, cache_window=10)
    report = tracker.analyze(steps)
    assert len(report.results) == 30
    assert len(tracker._cache) <= 11  # anchor + 10
    assert 0 in tracker._cache  # anchor position always retained


def test_accepts_trajectory_object(fake_embedder):
    trajectory = Trajectory.from_steps(STEPS)
    report = DriftTracker(embedder=fake_embedder).analyze(trajectory)
    assert len(report.results) == 3
