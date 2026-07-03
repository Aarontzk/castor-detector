"""FR-1: trajectory data model and ingestion (list, JSON/JSONL, stream)."""
import json

import pytest

from castor import Trajectory, TrajectoryStep


def test_step_defaults_include_multimodal_fields():
    step = TrajectoryStep(step_id=1, text="hello")
    assert step.modality == "text"
    assert step.raw_ref is None
    assert step.agent_name is None
    assert step.confidence_raw is None
    assert step.metadata is None


def test_step_is_immutable():
    step = TrajectoryStep(step_id=1, text="hello")
    with pytest.raises(AttributeError):
        step.text = "mutated"


def test_from_steps_accepts_dicts_and_dataclasses():
    trajectory = Trajectory.from_steps(
        [
            {"step_id": 1, "text": "first", "agent_name": "planner"},
            TrajectoryStep(step_id=2, text="second"),
        ]
    )
    assert len(trajectory) == 2
    assert trajectory.steps[0].agent_name == "planner"
    assert trajectory.steps[1].step_id == 2


def test_unknown_dict_keys_go_to_metadata():
    trajectory = Trajectory.from_steps([{"step_id": 1, "text": "x", "custom": 42}])
    assert trajectory.steps[0].metadata == {"custom": 42}


def test_missing_step_id_is_assigned_with_note():
    trajectory = Trajectory.from_steps([{"text": "no id here"}])
    assert trajectory.steps[0].step_id == 0
    assert any("missing step_id" in note for note in trajectory.notes)


def test_missing_text_noted_not_raised():
    trajectory = Trajectory.from_steps([{"step_id": 1}])
    assert trajectory.steps[0].text == ""
    assert any("missing text" in note for note in trajectory.notes)


def test_non_string_text_noted_not_raised():
    trajectory = Trajectory.from_steps([{"step_id": 1, "text": 123}])
    assert trajectory.steps[0].text == ""
    assert any("non-string text" in note for note in trajectory.notes)


def test_garbage_payload_noted_not_raised():
    trajectory = Trajectory.from_steps([42, {"step_id": 1, "text": "ok"}])
    assert len(trajectory) == 1
    assert any("unsupported payload" in note for note in trajectory.notes)


def test_add_step_stream_style():
    trajectory = Trajectory()
    trajectory.add_step({"step_id": "a", "text": "one"})
    trajectory.add_step({"step_id": "b", "text": "two"})
    assert [s.step_id for s in trajectory.steps] == ["a", "b"]


def test_from_json_array(tmp_path):
    path = tmp_path / "run.json"
    path.write_text(json.dumps([{"step_id": 1, "text": "a"}, {"step_id": 2, "text": "b"}]))
    trajectory = Trajectory.from_json(path)
    assert len(trajectory) == 2


def test_from_jsonl(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_text('{"step_id": 1, "text": "a"}\n{"step_id": 2, "text": "b"}\n')
    trajectory = Trajectory.from_json(path)
    assert len(trajectory) == 2


def test_from_json_rejects_non_array(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"step_id": 1}')
    with pytest.raises(ValueError, match="expected a JSON array"):
        Trajectory.from_json(path)
