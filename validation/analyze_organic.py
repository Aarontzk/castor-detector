"""Analyze the organic (Ollama-generated) trajectories with Castor.

Anchor = the SOURCE DOCUMENT (H-02 override) — drift is measured against the
ground truth the chain was supposed to stay faithful to.

Run:  .venv/Scripts/python validation/analyze_organic.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import CascadeAnalyzer, ThresholdProfile

ROOT = Path(__file__).resolve().parent
PROFILE = ThresholdProfile.load(ROOT / "calibrated-general.json")


def main() -> None:
    for path in sorted((ROOT / "organic").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        analyzer = CascadeAnalyzer(profile=PROFILE, anchor=data["source"])
        report = analyzer.analyze(data["steps"])
        print(f"\n=== {data['id']} — {data['question']}")
        print(f"verdict: {'CASCADE' if report.verdict else 'clean'}"
              f"{' [degraded]' if report.degraded else ''}")
        for s in report.steps:
            fmt = lambda v: f"{v:.3f}" if v is not None else "  -  "
            print(f"  step {s.step_id} {s.agent_name:<10} d_prev={fmt(s.drift_prev)}"
                  f" d_anchor={fmt(s.drift_anchor)} entail={fmt(s.entailment)}"
                  f" aggr={fmt(s.aggregate)} {'FLAG' if s.flagged else ''}")
        if report.attribution:
            top = report.attribution[0]
            print(f"  origin candidate: step {top.origin_step} ({top.origin_agent}), "
                  f"confidence {top.confidence}")
        if report.classification:
            print("  types: " + ", ".join(
                f"{t.cascade_type}({t.confidence:.2f})" for t in report.classification))


if __name__ == "__main__":
    main()
