"""Trajectory data model and ingestion (FR-1).

Steps carry `modality` and `raw_ref` from day one (multimodal-ready), but
measurement in v0.x is text-only (PRD 4.2): a multimodal step is measured via
its text representation (caption / extraction result) when present.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

_KNOWN_FIELDS = (
    "step_id",
    "text",
    "agent_name",
    "role",
    "timestamp",
    "modality",
    "raw_ref",
    "confidence_raw",
    "metadata",
)


@dataclass(frozen=True)
class TrajectoryStep:
    """One step of a multi-agent trajectory (FR-1)."""

    step_id: str | int
    text: str
    agent_name: str | None = None
    role: str | None = None
    timestamp: float | str | None = None
    modality: str = "text"
    raw_ref: str | None = None
    confidence_raw: float | None = None
    metadata: Mapping[str, Any] | None = None

    @property
    def has_measurable_text(self) -> bool:
        """True when this step carries text that drift measurement can use."""
        return isinstance(self.text, str) and bool(self.text.strip())


class Trajectory:
    """Ordered store of ALL steps in a run (FR-1).

    Accepts steps from a Python list (`from_steps`), JSON/JSONL files
    (`from_json`), or one at a time (`add_step`, stream/callback style).
    Ingestion never raises on malformed steps — problems are recorded as
    notes so the host pipeline is never crashed (FR-12).
    """

    def __init__(self) -> None:
        self._steps: list[TrajectoryStep] = []
        self._notes: list[str] = []

    @property
    def steps(self) -> tuple[TrajectoryStep, ...]:
        return tuple(self._steps)

    @property
    def notes(self) -> tuple[str, ...]:
        return tuple(self._notes)

    def __len__(self) -> int:
        return len(self._steps)

    def add_step(self, raw: TrajectoryStep | Mapping[str, Any]) -> TrajectoryStep | None:
        """Add one step (stream ingestion, FR-1). Never raises (FR-12).

        Returns the stored step, or None when the payload was unusable
        (recorded as a note either way).
        """
        position = len(self._steps)
        if isinstance(raw, TrajectoryStep):
            step = raw
        elif isinstance(raw, Mapping):
            step = self._from_mapping(raw, position)
        else:
            self._notes.append(
                f"step at position {position} skipped: unsupported payload type "
                f"{type(raw).__name__}"
            )
            return None
        if not isinstance(step.text, str):
            self._notes.append(
                f"step {step.step_id!r}: non-string text replaced with empty text "
                "(will be skipped in measurement)"
            )
            step = replace(step, text="")
        self._steps.append(step)
        return step

    def _from_mapping(self, raw: Mapping[str, Any], position: int) -> TrajectoryStep:
        data = dict(raw)
        known = {key: data.pop(key) for key in _KNOWN_FIELDS if key in data}
        if "step_id" not in known:
            known["step_id"] = position
            self._notes.append(f"step at position {position}: missing step_id, assigned {position}")
        if "text" not in known:
            known["text"] = ""
            self._notes.append(
                f"step {known['step_id']!r}: missing text (will be skipped in measurement)"
            )
        if data:
            merged = dict(known.get("metadata") or {})
            merged.update(data)
            known["metadata"] = merged
        return TrajectoryStep(**known)

    @classmethod
    def from_steps(cls, steps: Iterable[TrajectoryStep | Mapping[str, Any]]) -> "Trajectory":
        """Build a trajectory from a Python list/iterable of steps (FR-1)."""
        trajectory = cls()
        for step in steps:
            trajectory.add_step(step)
        return trajectory

    @classmethod
    def from_json(cls, path: str | Path) -> "Trajectory":
        """Load a trajectory from a .json (array of step objects) or .jsonl file (FR-1)."""
        file_path = Path(path)
        raw = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() == ".jsonl":
            items = [json.loads(line) for line in raw.splitlines() if line.strip()]
        else:
            items = json.loads(raw)
            if not isinstance(items, list):
                raise ValueError(
                    f"{file_path}: expected a JSON array of step objects, got "
                    f"{type(items).__name__}"
                )
        return cls.from_steps(items)
