"""FR-4: entailment interface + real cross-encoder integration."""
import pytest

from castor.entailment import CrossEncoderEntailment, EntailmentResult
from tests.conftest import FakeNLI


def test_result_label():
    assert EntailmentResult(0.8, 0.1, 0.1).label == "entailment"
    assert EntailmentResult(0.1, 0.2, 0.7).label == "contradiction"


def test_fake_nli_interface():
    checker = FakeNLI()
    result = checker.check("the cat sat on the mat", "the cat sat")
    assert result.entailment > 0.5


def test_real_cross_encoder_directional():
    """Integration test with the real local NLI model (FR-4)."""
    checker = CrossEncoderEntailment()
    entailed = checker.check("Revenue grew ten percent this quarter.", "Revenue increased.")
    leap = checker.check(
        "Revenue grew ten percent this quarter.",
        "The office coffee machine causes the company's success.",
    )
    assert entailed.entailment > 0.7
    assert leap.entailment < 0.3
    probs = (entailed.entailment, entailed.neutral, entailed.contradiction)
    assert abs(sum(probs) - 1.0) < 1e-5
