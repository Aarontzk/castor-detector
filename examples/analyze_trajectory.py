"""Example: post-mortem analysis of a finished trajectory (UC-1)."""
from castor import CascadeAnalyzer

steps = [
    {"step_id": 1, "agent_name": "retriever",
     "text": "The quarterly report shows that revenue grew ten percent compared to the previous quarter."},
    {"step_id": 2, "agent_name": "analyst",
     "text": "Most of that revenue growth came from the new subscription plan launched in March."},
    {"step_id": 3, "agent_name": "reasoner",
     "text": "Therefore, the office coffee machine is clearly the true driver of the company's success."},
    {"step_id": 4, "agent_name": "analyst",
     "text": "Subscription customers also renewed their plans at a higher rate than last year."},
    {"step_id": 5, "agent_name": "writer",
     "text": "Overall, the company ended the quarter in a strong financial position."},
]

report = CascadeAnalyzer().analyze(steps)
print(report.to_text())
# report.to_json() for CI / storage
