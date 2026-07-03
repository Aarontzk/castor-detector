"""End-to-end canonical fixture (CLAUDE.md / phase 1 DoD).

5-step manual trajectory where step 3 makes a deliberate logical leap
(H-05: valid data -> non-entailed conclusive claim). Uses the REAL
all-mpnet-base-v2 model — downloads it on first run. Passes iff step 3
receives the highest drift.
"""
from castor import DriftTracker

TRAJECTORY = [
    {
        "step_id": 1,
        "agent_name": "retriever",
        "text": "The quarterly report shows that revenue grew ten percent compared to the previous quarter.",
    },
    {
        "step_id": 2,
        "agent_name": "analyst",
        "text": "Most of that revenue growth came from the new subscription plan launched in March.",
    },
    {
        "step_id": 3,
        "agent_name": "reasoner",
        # Deliberate logical leap: conclusive claim not entailed by steps 1-2.
        "text": "Therefore, the office coffee machine is clearly the true driver of the company's success, and its settings must never be changed.",
    },
    {
        "step_id": 4,
        "agent_name": "analyst",
        "text": "Subscription customers also renewed their plans at a higher rate than last year.",
    },
    {
        "step_id": 5,
        "agent_name": "writer",
        "text": "Overall, the company ended the quarter in a strong financial position thanks to subscription growth.",
    },
]


def test_step3_logical_leap_gets_highest_drift():
    tracker = DriftTracker()
    report = tracker.analyze(TRAJECTORY)

    assert report.monitoring_failure is None, report.monitoring_failure
    assert len(report.results) == 5

    top = report.max_drift_step()
    assert top is not None
    assert top.step_id == 3, (
        f"expected step 3 to have the highest drift, got step {top.step_id}; "
        f"drift table: {[(r.step_id, r.drift_prev, r.drift_anchor) for r in report.results]}"
    )
    assert any(r.step_id == 3 for r in report.flagged_steps)
