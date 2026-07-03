"""Example: live passive observation with flag callback (UC-2)."""
from castor import CastorObserver

def on_flag(step_drift):
    print(f"[castor] step {step_drift.step_id} drifted: {'; '.join(step_drift.flag_reasons)}")

observer = CastorObserver(on_flag=on_flag)

# Your pipeline, unchanged — just call observe() after each step completes.
for step in [
    {"step_id": 1, "text": "User asked for a summary of the Q1 report."},
    {"step_id": 2, "text": "The Q1 report shows revenue grew eight percent."},
    {"step_id": 3, "text": "This proves our competitors are all going bankrupt."},
]:
    observer.observe(step)

print(observer.report().to_text())
