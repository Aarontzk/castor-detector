"""Confidence-language (hedging vs certainty) tracking, bilingual EN+ID (FR-6 signal).

Known limitation (PRD 3.3 / CLAUDE.md): lexicon-based confidence signals are
brittle across writing styles and LLM self-reported confidence is unreliable —
this signal is SECONDARY only (smallest aggregator weight), never a primary
gate.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Multi-word phrases are matched (and consumed) before single tokens so that
# e.g. Indonesian "belum pasti" (hedge) never counts its "pasti" as certainty.
_HEDGE_PHRASES = (
    "belum pasti",
    "belum tentu",
    "kemungkinan besar",
    "bisa jadi",
    "not sure",
    "not certain",
    "might be",
    "may be",
)
_CERTAINTY_PHRASES = (
    "sudah pasti",
    "tanpa keraguan",
    "tidak diragukan",
    "without a doubt",
    "beyond doubt",
    "for certain",
)
_HEDGE_WORDS = frozenset(
    {
        # EN
        "might", "may", "possibly", "perhaps", "maybe", "likely", "unlikely",
        "probably", "seemingly", "apparently", "unclear", "uncertain",
        "could", "suggests", "estimated", "roughly", "approximately",
        # ID
        "mungkin", "kemungkinan", "barangkali", "sepertinya", "tampaknya",
        "diduga", "diperkirakan", "kira-kira", "sekitar", "agaknya",
    }
)
_CERTAINTY_WORDS = frozenset(
    {
        # EN
        "definitely", "certainly", "clearly", "obviously", "undoubtedly",
        "surely", "proves", "proven", "confirmed", "guaranteed", "absolutely",
        "unquestionably",
        # ID
        "pasti", "yakin", "jelas", "terbukti", "tentu", "dipastikan",
        "niscaya", "mutlak",
    }
)
# Conclusive-claim markers — used by the taxonomy classifier (FR-6) to
# separate a legitimate topic change from a leap claimed as a conclusion (H-05).
_CONCLUSIVE_PHRASES = ("oleh karena itu", "dengan demikian", "as a result", "this proves")
_CONCLUSIVE_WORDS = frozenset(
    {
        # EN
        "therefore", "thus", "hence", "consequently", "proves",
        # ID
        "maka", "jadi", "sehingga", "kesimpulannya", "berarti",
    }
)

_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ɏ-]+")


@dataclass(frozen=True)
class CertaintySignal:
    """Certainty-language measurement for one step's text."""

    score: float  # (certainty - hedge) hits, length-normalised, in [-1, 1]
    hedge_hits: int
    certainty_hits: int
    conclusive: bool


def _count_phrases(text: str, phrases: tuple[str, ...]) -> tuple[str, int]:
    hits = 0
    for phrase in phrases:
        occurrences = text.count(phrase)
        if occurrences:
            hits += occurrences
            text = text.replace(phrase, " ")
    return text, hits


def certainty_signal(text: str) -> CertaintySignal:
    """Measure hedging vs certainty language in one text, EN+ID (FR-6 signal)."""
    lowered = text.lower()
    remaining, conclusive_phrase_hits = _count_phrases(lowered, _CONCLUSIVE_PHRASES)
    remaining, hedge_hits = _count_phrases(remaining, _HEDGE_PHRASES)
    remaining, certainty_hits = _count_phrases(remaining, _CERTAINTY_PHRASES)
    tokens = _TOKEN_RE.findall(remaining)
    hedge_hits += sum(1 for token in tokens if token in _HEDGE_WORDS)
    certainty_hits += sum(1 for token in tokens if token in _CERTAINTY_WORDS)
    conclusive = conclusive_phrase_hits > 0 or any(token in _CONCLUSIVE_WORDS for token in tokens)
    n_tokens = max(len(tokens), 1)
    # Scale by 5 so that one marker in a ~20-token sentence registers clearly,
    # then clip to [-1, 1]. Crude by design — secondary signal only.
    raw = (certainty_hits - hedge_hits) / n_tokens * 5.0
    score = max(-1.0, min(1.0, raw))
    return CertaintySignal(
        score=score,
        hedge_hits=hedge_hits,
        certainty_hits=certainty_hits,
        conclusive=conclusive,
    )


def certainty_series(texts: list[str]) -> list[CertaintySignal]:
    """Per-step certainty signals for a sequence of step texts (FR-6 signal)."""
    return [certainty_signal(text) for text in texts]


def inflation_delta(previous: CertaintySignal, current: CertaintySignal) -> float:
    """Positive certainty increase between consecutive steps, in [0, 1].

    The Confidence Inflation signature (H-11): certainty language strengthening
    step over step without new evidence.
    """
    return max(0.0, min(1.0, current.score - previous.score))
