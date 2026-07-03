"""FR-6: rule-based taxonomy classifier on crafted signal patterns."""
from castor.report import StepSignals
from castor.taxonomy import (
    CONFIDENCE_INFLATION,
    CONTEXT_POISONING,
    INFERENCE,
    RETRIEVAL,
    classify,
)


def make_signals(step_id, drift_prev, drift_anchor, entailment=None, certainty=0.0,
                 certainty_delta=0.0, conclusive=False, agent=None, flagged=True):
    return StepSignals(
        step_id=step_id,
        agent_name=agent,
        drift_prev=drift_prev,
        drift_anchor=drift_anchor,
        entailment=entailment,
        contradiction=None,
        certainty=certainty,
        certainty_delta=certainty_delta,
        conclusive=conclusive,
        aggregate=0.6,
        flagged=flagged,
        flag_reasons=("test",),
    )


THRESHOLD = 0.2


def test_retrieval_cascade_high_anchor_from_start():
    signals = [
        make_signals(1, None, None, flagged=False),
        make_signals(2, 0.6, 0.65),
        make_signals(3, 0.3, 0.7),
    ]
    result = classify(signals, {}, drift_threshold=THRESHOLD, entail_threshold=0.72)
    types = {t.cascade_type for t in result}
    assert RETRIEVAL in types


def test_inference_cascade_entailment_drop_on_conclusive_claim():
    signals = [
        make_signals(1, None, None, flagged=False),
        make_signals(2, 0.1, 0.15, entailment=0.9, flagged=False),
        make_signals(3, 0.15, 0.3, entailment=0.2, conclusive=True),
        make_signals(4, 0.1, 0.4, entailment=0.8),
    ]
    result = classify(signals, {}, drift_threshold=THRESHOLD, entail_threshold=0.72)
    assert result
    assert result[0].cascade_type == INFERENCE


def test_context_poisoning_sudden_jump_on_tool_content():
    signals = [
        make_signals(1, None, None, flagged=False),
        make_signals(2, 0.05, 0.05, flagged=False),
        make_signals(3, 0.6, 0.65, agent="fetcher"),
        make_signals(4, 0.1, 0.6),
    ]
    roles = {3: "tool"}
    result = classify(signals, roles, drift_threshold=THRESHOLD, entail_threshold=0.72)
    types = {t.cascade_type for t in result}
    assert CONTEXT_POISONING in types


def test_confidence_inflation_rising_certainty_and_anchor():
    signals = [
        make_signals(1, None, None, flagged=False),
        make_signals(2, 0.1, 0.2, certainty=0.2, certainty_delta=0.4),
        make_signals(3, 0.1, 0.35, certainty=0.8, certainty_delta=0.6),
    ]
    result = classify(signals, {}, drift_threshold=THRESHOLD, entail_threshold=0.72)
    types = {t.cascade_type for t in result}
    assert CONFIDENCE_INFLATION in types


def test_multi_label_possible():
    # High early anchor drift AND certainty inflation at once.
    signals = [
        make_signals(1, None, None, flagged=False),
        make_signals(2, 0.6, 0.7, certainty_delta=0.5),
        make_signals(3, 0.4, 0.8, certainty_delta=0.6),
    ]
    result = classify(signals, {}, drift_threshold=THRESHOLD, entail_threshold=0.72)
    types = {t.cascade_type for t in result}
    assert RETRIEVAL in types and CONFIDENCE_INFLATION in types


def test_flagged_but_weak_signals_returns_best_single_type():
    signals = [
        make_signals(1, None, None, flagged=False),
        make_signals(2, 0.22, 0.23),
    ]
    result = classify(signals, {}, drift_threshold=THRESHOLD, entail_threshold=0.72)
    assert len(result) >= 1  # never silently empty when something was flagged


def test_all_confidences_in_range():
    signals = [
        make_signals(1, None, None, flagged=False),
        make_signals(2, 0.9, 0.95, entailment=0.05, conclusive=True, certainty_delta=1.0),
    ]
    result = classify(signals, {2: "tool"}, drift_threshold=THRESHOLD, entail_threshold=0.72)
    assert all(0.0 <= t.confidence <= 1.0 for t in result)
