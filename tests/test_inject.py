"""FR-10: synthetic error injection toolkit."""
import pytest

from castor import INJECTION_KINDS, Trajectory, inject
from castor.inject import (
    CAUSAL_LEAP,
    CERTAINTY_INFLATION,
    CONTEXT_SWAP,
    ENTITY_DISTORTION,
    NUMERIC_FABRICATION,
)

CLEAN = Trajectory.from_steps(
    [
        {"step_id": 1, "text": "The March report from Jakarta shows sales of 120 units."},
        {"step_id": 2, "text": "Sales might increase because the Jakarta team hired 5 staff."},
        {"step_id": 3, "text": "The team plans to open a second office next year."},
    ]
)


@pytest.mark.parametrize("kind", INJECTION_KINDS)
def test_each_kind_changes_target_step_only(kind):
    corrupted, record = inject(CLEAN, kind, step_index=1, seed=7)
    assert record.kind == kind
    assert record.step_index == 1
    assert corrupted.steps[1].text != CLEAN.steps[1].text
    assert corrupted.steps[0].text == CLEAN.steps[0].text
    assert corrupted.steps[2].text == CLEAN.steps[2].text


def test_original_trajectory_untouched():
    before = [s.text for s in CLEAN.steps]
    inject(CLEAN, CAUSAL_LEAP, step_index=1, seed=1)
    assert [s.text for s in CLEAN.steps] == before  # immutability


def test_deterministic_under_seed():
    a, _ = inject(CLEAN, NUMERIC_FABRICATION, step_index=1, seed=42)
    b, _ = inject(CLEAN, NUMERIC_FABRICATION, step_index=1, seed=42)
    assert a.steps[1].text == b.steps[1].text


def test_numeric_fabrication_changes_number():
    corrupted, _ = inject(CLEAN, NUMERIC_FABRICATION, step_index=1, seed=3)
    assert "5" not in corrupted.steps[1].text or corrupted.steps[1].text != CLEAN.steps[1].text


def test_entity_distortion_swaps_proper_noun():
    corrupted, _ = inject(CLEAN, ENTITY_DISTORTION, step_index=1, seed=3)
    assert corrupted.steps[1].text != CLEAN.steps[1].text


def test_certainty_inflation_removes_hedge():
    corrupted, _ = inject(CLEAN, CERTAINTY_INFLATION, step_index=1, seed=3)
    assert "might" not in corrupted.steps[1].text.lower()


def test_context_swap_replaces_content():
    corrupted, _ = inject(CLEAN, CONTEXT_SWAP, step_index=1, seed=3)
    assert "jakarta" not in corrupted.steps[1].text.lower()


def test_never_injects_into_anchor_step():
    for seed in range(10):
        _, record = inject(CLEAN, CAUSAL_LEAP, seed=seed)
        assert record.step_index >= 1


def test_unknown_kind_rejected():
    with pytest.raises(ValueError, match="unknown injection kind"):
        inject(CLEAN, "nonsense")
