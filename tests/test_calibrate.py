"""FR-5/UC-4: threshold profiles + calibration from clean trajectories."""
import pytest

from castor import ThresholdProfile, Trajectory, calibrate
from tests.conftest import FakeEmbedder


def make_trajectories():
    return [
        Trajectory.from_steps(
            [
                {"step_id": 1, "text": "alpha beta gamma"},
                {"step_id": 2, "text": "alpha beta delta"},
                {"step_id": 3, "text": "alpha gamma delta"},
            ]
        ),
        Trajectory.from_steps(
            [
                {"step_id": 1, "text": "one two three"},
                {"step_id": 2, "text": "one two four"},
            ]
        ),
    ]


def test_calibrate_recommends_percentile_threshold():
    result = calibrate(make_trajectories(), embedder=FakeEmbedder(), percentile=95.0)
    assert result.n_trajectories == 2
    assert result.n_measurements > 0
    assert 0.0 <= result.profile.drift_threshold <= 1.0
    assert result.profile.name == "calibrated"


def test_calibrate_requires_measurable_steps():
    empty = Trajectory.from_steps([{"step_id": 1, "text": "solo"}])
    with pytest.raises(ValueError, match="no measurable drift"):
        calibrate([empty], embedder=FakeEmbedder())


def test_profile_save_load_roundtrip(tmp_path):
    profile = ThresholdProfile(name="numeric", drift_threshold=0.42)
    path = tmp_path / "numeric.json"
    profile.save(path)
    loaded = ThresholdProfile.load(path)
    assert loaded == profile
