"""Completeness (omission) signal via reverse entailment (STATUS.md v1 item 1).

Drift and forward entailment share a blind spot: a step that silently drops a
fact from the source is a *faithful subset* of its predecessor. It contradicts
nothing, so entailment scores high, and it stays semantically close, so drift
stays low. Organic validation found this mode at the origin of a large share of
cascades, invisible to both existing signals.

This module inverts the entailment direction. Forward entailment asks "is this
step supported by its predecessor?". Coverage asks "does this step still carry
the source's facts?", scoring (premise=step_text, hypothesis=source_fact) for
every fact in the anchor document.

Two numbers come out per step:

- `coverage`: the fraction of anchor facts the step still entails.
- `omission`: how much of that coverage this step lost relative to the step
  before it. The first measured step is compared against the anchor itself,
  because an extractor that reads the source is expected to carry it.

Known limitation, kept explicit rather than smoothed over: condensing roles
(a writer that compresses four sentences into one) legitimately shed coverage,
so a raw coverage drop over-flags them. This is the same role-aware threshold
problem the PRD flags in Section 3.3 for heteroskedastic signals. Coverage is
reported per step so a role-aware threshold can use it later; it is deliberately
NOT folded into the weighted aggregate, whose theta is calibrated over three
signals only.

No training, no new model: the existing NLI cross-encoder is reused with its
inputs reversed.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from .config import (
    DEFAULT_COVERAGE_THRESHOLD,
    DEFAULT_MAX_ANCHOR_FACTS,
    DEFAULT_MIN_FACT_CHARS,
)
from .entailment import EntailmentChecker

# Split on sentence-final punctuation followed by whitespace. A decimal point
# ("0.12 dollars") is followed by a digit rather than whitespace, so numeric
# sources survive intact.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_facts(
    anchor: str | Sequence[str],
    max_facts: int = DEFAULT_MAX_ANCHOR_FACTS,
    min_chars: int = DEFAULT_MIN_FACT_CHARS,
) -> tuple[str, ...]:
    """Split an anchor document into atomic fact candidates (FR-4, v1 item 1).

    A sequence anchor is already a list of facts and is passed through. A string
    anchor is segmented on sentence boundaries; fragments shorter than
    `min_chars` are merged into the previous fact so that stray abbreviations do
    not become their own hypothesis. The result is capped at `max_facts` to keep
    NLI cost bounded on long sources (FR-11).
    """
    if not isinstance(anchor, str):
        parts = [str(item).strip() for item in anchor if str(item).strip()]
        return tuple(parts[:max_facts])

    text = anchor.strip()
    if not text:
        return ()

    facts: list[str] = []
    for chunk in _SENTENCE_SPLIT.split(text):
        chunk = chunk.strip()
        if not chunk:
            continue
        if facts and len(chunk) < min_chars:
            facts[-1] = f"{facts[-1]} {chunk}"
        else:
            facts.append(chunk)
    return tuple(facts[:max_facts])


def coverage_series(
    step_texts: Sequence[str],
    facts: Sequence[str],
    checker: EntailmentChecker,
    covered_threshold: float = DEFAULT_COVERAGE_THRESHOLD,
) -> list[float]:
    """Fraction of anchor facts each step still entails (v1 item 1).

    Scores every (step, fact) pair in a single batched NLI call and counts a
    fact as covered when the step entails it at or above `covered_threshold`.
    Returns one value in [0, 1] per step, in step order.
    """
    if not facts or not step_texts:
        return [0.0 for _ in step_texts]

    pairs = [(text, fact) for text in step_texts for fact in facts]
    results = checker.check_batch(pairs)

    coverages: list[float] = []
    width = len(facts)
    for index in range(len(step_texts)):
        window = results[index * width : (index + 1) * width]
        covered = sum(1 for r in window if r.entailment >= covered_threshold)
        coverages.append(covered / width)
    return coverages


def omission_series(coverages: Sequence[float]) -> list[float]:
    """Per-step loss of source-fact coverage (v1 item 1).

    Step 0 is measured against full coverage of the anchor, since the first
    agent reads the source directly and is expected to carry it. Later steps are
    measured against the step before them, so a fact already lost upstream is
    not charged again to every step downstream: omission marks *where* coverage
    dropped, which is what origin attribution needs.

    Values are clipped at zero. A step that recovers coverage (by restating
    something its predecessor dropped) scores 0, not a negative omission.
    """
    out: list[float] = []
    for index, coverage in enumerate(coverages):
        previous = 1.0 if index == 0 else coverages[index - 1]
        out.append(max(0.0, previous - coverage))
    return out
