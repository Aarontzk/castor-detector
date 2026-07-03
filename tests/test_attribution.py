"""FR-7: threshold-based origin attribution with mandatory honesty fields."""
from castor.attribution import attribute
from castor.report import StepSignals, TypeScore


def make_signals(step_id, drift_prev, drift_anchor, entailment=None, agent=None):
    return StepSignals(
        step_id=step_id,
        agent_name=agent,
        drift_prev=drift_prev,
        drift_anchor=drift_anchor,
        entailment=entailment,
        contradiction=None,
        certainty=0.0,
        certainty_delta=0.0,
        conclusive=False,
        aggregate=None,
        flagged=False,
        flag_reasons=(),
    )


CLASSIFICATION = (TypeScore("inference", 0.8, "test"),)


def test_first_crossing_step_is_first_candidate():
    signals = [
        make_signals(1, None, None),
        make_signals(2, 0.1, 0.1),
        make_signals(3, 0.5, 0.6, agent="reasoner"),
        make_signals(4, 0.4, 0.5),
    ]
    candidates = attribute(signals, CLASSIFICATION, drift_threshold=0.3, entail_threshold=None)
    assert candidates[0].origin_step == 3
    assert candidates[0].origin_agent == "reasoner"


def test_all_crossing_steps_reported_in_order():
    signals = [
        make_signals(1, None, None),
        make_signals(2, 0.5, 0.5),
        make_signals(3, 0.6, 0.7),
    ]
    candidates = attribute(signals, CLASSIFICATION, drift_threshold=0.3, entail_threshold=None)
    assert [c.origin_step for c in candidates] == [2, 3]


def test_method_field_always_threshold_based():
    signals = [make_signals(2, 0.9, 0.9)]
    candidates = attribute(signals, CLASSIFICATION, drift_threshold=0.3, entail_threshold=None)
    assert all(c.method == "threshold-based" for c in candidates)
    assert all(0.0 <= c.confidence <= 1.0 for c in candidates)


def test_entailment_crossing_counts_as_signal():
    signals = [make_signals(2, 0.1, 0.1, entailment=0.2)]
    candidates = attribute(signals, CLASSIFICATION, drift_threshold=0.9, entail_threshold=0.72)
    assert len(candidates) == 1
    assert candidates[0].origin_step == 2


def test_no_crossing_no_candidates():
    signals = [make_signals(2, 0.1, 0.1, entailment=0.9)]
    assert attribute(signals, CLASSIFICATION, drift_threshold=0.5, entail_threshold=0.72) == ()


def test_cascade_types_propagated():
    signals = [make_signals(2, 0.9, 0.9)]
    candidates = attribute(signals, CLASSIFICATION, drift_threshold=0.3, entail_threshold=None)
    assert candidates[0].cascade_type == ("inference",)
