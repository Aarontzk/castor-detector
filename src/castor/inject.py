"""Synthetic error injection toolkit (FR-10).

Injects controlled errors into clean trajectories to build labeled validation
datasets without real hallucination data (cuts the circular dependency —
arXiv:2410.12278). Used internally for validation (PRD Section 12) AND exposed
to users for their own regression suites (UC-3). Deterministic under `seed`.

Kinds: numeric_fabrication, entity_distortion, causal_leap,
certainty_inflation, context_swap.
"""
from __future__ import annotations

import dataclasses
import random
import re
from dataclasses import dataclass

from .trajectory import Trajectory, TrajectoryStep

NUMERIC_FABRICATION = "numeric_fabrication"
ENTITY_DISTORTION = "entity_distortion"
CAUSAL_LEAP = "causal_leap"
CERTAINTY_INFLATION = "certainty_inflation"
CONTEXT_SWAP = "context_swap"

INJECTION_KINDS = (
    NUMERIC_FABRICATION,
    ENTITY_DISTORTION,
    CAUSAL_LEAP,
    CERTAINTY_INFLATION,
    CONTEXT_SWAP,
)

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
# Capitalised token NOT at sentence start — a rough proper-noun heuristic.
_ENTITY_RE = re.compile(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]{2,})\b")

_ENTITY_POOL = ("Jakarta", "Berlin", "Osaka", "Nairobi", "Toronto", "Zurich")
_LEAP_POOL = (
    "Therefore, this clearly proves the entire industry will collapse within a year.",
    "Thus, it is now certain that the original data source was fabricated by competitors.",
    "Maka sudah pasti seluruh strategi perusahaan harus dibatalkan segera.",
    "Consequently, the only logical conclusion is to triple the budget immediately.",
)
_SWAP_POOL = (
    "The migration patterns of arctic terns cover more than seventy thousand kilometers each year.",
    "Baking sourdough bread requires maintaining a fermented starter culture at room temperature.",
    "Resep rendang tradisional membutuhkan santan kelapa dan waktu memasak lebih dari empat jam.",
    "The 1969 lunar landing module weighed roughly fifteen thousand kilograms at launch.",
)
_HEDGE_TO_CERTAIN = {
    "might": "definitely",
    "may": "certainly",
    "possibly": "certainly",
    "perhaps": "surely",
    "maybe": "definitely",
    "likely": "certainly",
    "probably": "undoubtedly",
    "could": "must",
    "suggests": "proves",
    "mungkin": "pasti",
    "kemungkinan": "kepastian",
    "sepertinya": "jelas",
    "tampaknya": "terbukti",
    "diduga": "dipastikan",
    "diperkirakan": "dipastikan",
}


@dataclass(frozen=True)
class InjectionRecord:
    """Ground-truth label for one injection (FR-10): where and what."""

    step_index: int  # position in trajectory.steps
    step_id: str | int
    kind: str
    original_text: str
    injected_text: str


def inject(
    trajectory: Trajectory,
    kind: str,
    step_index: int | None = None,
    seed: int = 0,
) -> tuple[Trajectory, InjectionRecord]:
    """Return a NEW trajectory with one controlled error injected (FR-10).

    `step_index` defaults to a mid-chain step (never the first — the anchor
    must stay clean so the injected error is measurable downstream).
    """
    if kind not in INJECTION_KINDS:
        raise ValueError(f"unknown injection kind {kind!r}; choose from {INJECTION_KINDS}")
    steps = list(trajectory.steps)
    if len(steps) < 3:
        raise ValueError("need at least 3 steps to inject a mid-chain error")
    rng = random.Random(seed)
    if step_index is None:
        step_index = rng.randrange(1, len(steps) - 1)
    if not 0 < step_index < len(steps):
        raise ValueError(f"step_index {step_index} out of range (must be 1..{len(steps) - 1})")

    target = steps[step_index]
    injected_text = _INJECTORS[kind](target.text, rng)
    steps[step_index] = dataclasses.replace(target, text=injected_text)
    record = InjectionRecord(
        step_index=step_index,
        step_id=target.step_id,
        kind=kind,
        original_text=target.text,
        injected_text=injected_text,
    )
    return Trajectory.from_steps(steps), record


def _inject_numeric(text: str, rng: random.Random) -> str:
    """Fabricated number: perturb an existing figure, or append one (H-06)."""
    match = _NUMBER_RE.search(text)
    if match is None:
        return text + f" The measured figure is exactly {rng.randrange(1000, 9999)} units."
    original = match.group()
    fabricated = str(int(float(original.replace(",", "."))) * rng.randrange(3, 9) + rng.randrange(7, 97))
    return text[: match.start()] + fabricated + text[match.end() :]


def _inject_entity(text: str, rng: random.Random) -> str:
    """Distorted entity: swap a proper noun for a wrong one (H-06)."""
    match = _ENTITY_RE.search(text)
    if match is None:
        return text + f" This was originally reported in {rng.choice(_ENTITY_POOL)}."
    replacement = rng.choice([e for e in _ENTITY_POOL if e != match.group(1)])
    return text[: match.start(1)] + replacement + text[match.end(1) :]


def _inject_leap(text: str, rng: random.Random) -> str:
    """Causal leap: append a conclusive non-sequitur (H-05)."""
    return text + " " + rng.choice(_LEAP_POOL)


def _inject_certainty(text: str, rng: random.Random) -> str:
    """Certainty inflation: hedges become absolutes (H-11)."""
    replaced = False

    def swap(match: re.Match) -> str:
        nonlocal replaced
        replaced = True
        return _HEDGE_TO_CERTAIN[match.group(0).lower()]

    pattern = re.compile(
        r"\b(" + "|".join(map(re.escape, _HEDGE_TO_CERTAIN)) + r")\b", re.IGNORECASE
    )
    result = pattern.sub(swap, text)
    if not replaced:
        result = "It is absolutely certain and proven that " + text[0].lower() + text[1:]
    return result


def _inject_swap(text: str, rng: random.Random) -> str:
    """Context swap: replace the step content with off-domain material (H-04)."""
    return rng.choice(_SWAP_POOL)


_INJECTORS = {
    NUMERIC_FABRICATION: _inject_numeric,
    ENTITY_DISTORTION: _inject_entity,
    CAUSAL_LEAP: _inject_leap,
    CERTAINTY_INFLATION: _inject_certainty,
    CONTEXT_SWAP: _inject_swap,
}
