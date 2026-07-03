"""FR-9 CastorObserver: live observation, flags, async, never-raise (FR-12)."""
from castor import CastorObserver, ThresholdProfile
from tests.conftest import BrokenEmbedder, FakeEmbedder, FakeNLI

PROFILE = ThresholdProfile(name="test", drift_threshold=0.3, aggregate_threshold=0.5)

STEPS = [
    {"step_id": 1, "text": "alpha beta gamma delta"},
    {"step_id": 2, "text": "alpha beta gamma epsilon"},
    {"step_id": 3, "text": "zulu yankee xray whiskey"},
]


def observer(**kwargs):
    defaults = dict(embedder=FakeEmbedder(), entailment=FakeNLI(), profile=PROFILE)
    defaults.update(kwargs)
    return CastorObserver(**defaults)


def test_observe_then_report():
    obs = observer()
    for step in STEPS:
        obs.observe(step)
    report = obs.report()
    assert len(report.steps) == 3
    assert report.verdict


def test_on_flag_fires_once_per_step():
    flagged = []
    obs = observer(on_flag=flagged.append)
    for step in STEPS:
        obs.observe(step)
    ids = [f.step_id for f in flagged]
    assert 3 in ids
    assert len(ids) == len(set(ids))  # no duplicate flags


def test_on_flag_callback_error_is_contained():
    def bad_callback(_):
        raise ValueError("user callback bug")

    obs = observer(on_flag=bad_callback)
    for step in STEPS:
        obs.observe(step)  # must not raise (FR-12)
    report = obs.report()
    assert any("on_flag callback failed" in note for note in report.notes)


def test_broken_embedder_never_crashes_host():
    obs = observer(embedder=BrokenEmbedder())
    for step in STEPS:
        obs.observe(step)  # must not raise (FR-12)
    report = obs.report()
    assert report.monitoring_failure is not None


def test_async_mode_drains_before_report():
    flagged = []
    with observer(async_mode=True, on_flag=flagged.append) as obs:
        for step in STEPS:
            obs.observe(step)
        report = obs.report()
    assert len(report.steps) == 3
    assert any(f.step_id == 3 for f in flagged)


def test_garbage_step_is_noted_not_raised():
    obs = observer()
    obs.observe(42)  # type: ignore[arg-type]
    for step in STEPS:
        obs.observe(step)
    report = obs.report()
    assert len(report.steps) == 3
    assert any("unsupported payload" in note for note in report.notes)
