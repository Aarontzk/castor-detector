"""FR-9 #3: CLI analyze/calibrate. Uses the real embedding model (cached)."""
import json

from castor.cli import main

CLEAN_STEPS = [
    {"step_id": 1, "text": "The quarterly report shows revenue grew ten percent."},
    {"step_id": 2, "text": "Revenue growth came mostly from the subscription plan."},
    {"step_id": 3, "text": "Subscription renewals were also higher than last year."},
]


def write_trajectory(path, steps):
    path.write_text(json.dumps(steps), encoding="utf-8")


def test_analyze_exit_codes_and_output(tmp_path, capsys):
    trajectory_file = tmp_path / "run.json"
    write_trajectory(trajectory_file, CLEAN_STEPS)
    json_out = tmp_path / "report.json"
    code = main(
        ["analyze", str(trajectory_file), "--no-nli", "--json-out", str(json_out)]
    )
    output = capsys.readouterr().out
    assert code in (0, 1)  # verdict-dependent, never a monitoring failure
    assert "verdict" in output
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert "steps" in report and len(report["steps"]) == 3
    assert report["thresholds"]["drift_threshold"] > 0


def test_analyze_threshold_override(tmp_path, capsys):
    trajectory_file = tmp_path / "run.json"
    write_trajectory(trajectory_file, CLEAN_STEPS)
    code = main(["analyze", str(trajectory_file), "--no-nli", "--threshold", "0.99"])
    assert code in (0, 1)
    assert "0.99" in capsys.readouterr().out


def test_calibrate_directory(tmp_path, capsys):
    for i in range(2):
        write_trajectory(tmp_path / f"clean_{i}.json", CLEAN_STEPS)
    profile_path = tmp_path / "profile.json"
    code = main(
        ["calibrate", str(tmp_path), "--name", "general", "--save", str(profile_path)]
    )
    assert code == 0
    assert "recommended drift threshold" in capsys.readouterr().out
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile["name"] == "general"
    assert 0 < profile["drift_threshold"] < 1


def test_calibrate_empty_directory(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["calibrate", str(empty)]) == 2
