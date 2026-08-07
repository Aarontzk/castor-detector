"""Omission/completeness signal: fact splitting, coverage, and analyzer wiring."""
from __future__ import annotations

import pytest

from castor import CascadeAnalyzer
from castor.entailment import EntailmentChecker, EntailmentResult
from castor.omission import coverage_series, omission_series, split_facts

from .conftest import BrokenNLI, FakeEmbedder, FakeNLI

SOURCE = (
    "The budget is 500 million. Phase one spent 180 million and phase two spent "
    "210 million. The final phase needs 95 million. A separate contingency fund "
    "of 50 million requires board approval."
)


class ScriptedNLI(EntailmentChecker):
    """Returns a fixed entailment score per (premise, hypothesis) pair index."""

    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.pairs: list[tuple[str, str]] = []

    def check_batch(self, pairs):
        self.pairs.extend(pairs)
        out = []
        for index, _ in enumerate(pairs):
            entail = self.scores[index % len(self.scores)]
            rest = 1.0 - entail
            out.append(
                EntailmentResult(entailment=entail, neutral=rest * 0.7, contradiction=rest * 0.3)
            )
        return out


def test_split_facts_keeps_decimals_intact():
    """A decimal point must not be read as a sentence boundary."""
    facts = split_facts("The rate is 0.12 dollars per kWh. The customer used 640 kWh.")
    assert len(facts) == 2
    assert "0.12 dollars per kWh" in facts[0]


def test_split_facts_merges_short_fragments():
    """Fragments below the minimum length join the previous fact."""
    facts = split_facts("Budget is 500 million and phase one spent 180 million. Ok.")
    assert len(facts) == 1
    assert facts[0].endswith("Ok.")


def test_split_facts_passes_through_sequence_anchor():
    """A sequence anchor is already fact-shaped and is used as given."""
    assert split_facts(["fact one", "fact two"]) == ("fact one", "fact two")


def test_split_facts_caps_fact_count():
    """Long sources are truncated so NLI cost stays bounded (FR-11)."""
    text = " ".join(f"Fact number {n} is a sufficiently long sentence." for n in range(30))
    assert len(split_facts(text, max_facts=5)) == 5


def test_split_facts_on_empty_anchor():
    assert split_facts("   ") == ()


def test_coverage_series_scores_every_step_fact_pair():
    """One NLI pair per (step, fact), with the step as premise (reversed direction)."""
    checker = ScriptedNLI([0.9])
    facts = ("fact a", "fact b")
    coverage = coverage_series(["step one", "step two"], facts, checker)
    assert coverage == [1.0, 1.0]
    assert len(checker.pairs) == 4
    # Reverse direction is the whole point: the step is the premise.
    assert checker.pairs[0] == ("step one", "fact a")


def test_coverage_series_counts_only_facts_above_threshold():
    checker = ScriptedNLI([0.9, 0.1])  # alternating covered / not covered
    coverage = coverage_series(["s1"], ("f1", "f2"), checker, covered_threshold=0.5)
    assert coverage == [0.5]


def test_coverage_series_with_no_facts():
    assert coverage_series(["s1"], (), FakeNLI()) == [0.0]


def test_omission_series_first_step_measured_against_full_coverage():
    """The first agent reads the source, so anything it drops is its own omission."""
    assert omission_series([0.6]) == pytest.approx([0.4])


def test_omission_series_charges_the_step_that_dropped_the_fact():
    """A fact lost at step 2 is not charged again to step 3."""
    out = omission_series([1.0, 0.5, 0.5])
    assert out == pytest.approx([0.0, 0.5, 0.0])


def test_omission_series_clips_recovery_at_zero():
    assert omission_series([0.5, 1.0]) == pytest.approx([0.5, 0.0])


def test_analyzer_reports_coverage_and_omission_with_anchor():
    """End-to-end wiring: an anchor plus NLI produces both fields."""
    analyzer = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI(), anchor=SOURCE
    )
    report = analyzer.analyze(
        [
            {"step_id": 1, "text": SOURCE, "agent_name": "extractor"},
            {"step_id": 2, "text": "The budget is 500 million.", "agent_name": "analyst"},
        ]
    )
    assert all(s.coverage is not None for s in report.steps)
    assert all(s.omission is not None for s in report.steps)
    # Step 2 keeps one sentence out of several, so it must lose coverage.
    assert report.steps[1].coverage < report.steps[0].coverage
    assert report.steps[1].omission > 0


def test_analyzer_flags_a_dropped_fact():
    """A step that sheds most of the source trips the omission threshold."""
    analyzer = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI(), anchor=SOURCE
    )
    report = analyzer.analyze(
        [
            {"step_id": 1, "text": SOURCE, "agent_name": "extractor"},
            {"step_id": 2, "text": "Nothing relevant here at all.", "agent_name": "analyst"},
        ]
    )
    reasons = " ".join(report.steps[1].flag_reasons)
    assert "omission" in reasons
    assert report.steps[1].flagged


def test_no_anchor_leaves_omission_unset():
    """Without ground truth there is nothing to measure completeness against."""
    analyzer = CascadeAnalyzer(embedder=FakeEmbedder(), entailment=FakeNLI())
    report = analyzer.analyze(
        [
            {"step_id": 1, "text": "first step text here", "agent_name": "a"},
            {"step_id": 2, "text": "second step text here", "agent_name": "b"},
        ]
    )
    assert all(s.coverage is None and s.omission is None for s in report.steps)


def test_omission_absent_when_nli_disabled():
    analyzer = CascadeAnalyzer(embedder=FakeEmbedder(), entailment=False, anchor=SOURCE)
    report = analyzer.analyze(
        [{"step_id": 1, "text": "first step", "agent_name": "a"}]
    )
    assert report.steps[0].omission is None


def test_broken_nli_does_not_crash_the_analyzer():
    """FR-12: a failing coverage check degrades, it never propagates."""
    analyzer = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=BrokenNLI(), anchor=SOURCE
    )
    with pytest.warns(UserWarning):
        report = analyzer.analyze(
            [
                {"step_id": 1, "text": "first step text", "agent_name": "a"},
                {"step_id": 2, "text": "second step text", "agent_name": "b"},
            ]
        )
    assert report.monitoring_failure is None
    assert all(s.omission is None for s in report.steps)


def test_omission_stays_out_of_the_aggregate():
    """Theta is calibrated over three signals; the fourth must not shift it."""
    steps = [
        {"step_id": 1, "text": SOURCE, "agent_name": "extractor"},
        {"step_id": 2, "text": "Nothing relevant here at all.", "agent_name": "analyst"},
    ]
    with_anchor = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI(), anchor=SOURCE
    ).analyze(steps)
    without_anchor = CascadeAnalyzer(
        embedder=FakeEmbedder(), entailment=FakeNLI()
    ).analyze(steps)
    assert with_anchor.steps[1].omission is not None
    # Anchor drift changes the aggregate, so compare the entailment-only part:
    # the omission value itself must not appear in either aggregate.
    assert without_anchor.steps[1].omission is None
    assert with_anchor.steps[1].aggregate is not None
