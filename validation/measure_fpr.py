"""Step-level false-positive breakdown on the chains annotated clean.

Organic FPR has never been measurable before: batch 1 produced no clean runs
(docs/VALIDATION.md says so explicitly). Batch 2 produced four, so this is the
first organic false-positive figure this project can report, and it needs to be
attributed per signal rather than left as a single chain-level number.

Run:  python validation/measure_fpr.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import CascadeAnalyzer, ThresholdProfile  # noqa: E402

ROOT = Path(__file__).resolve().parent
PROFILE = ThresholdProfile.load(ROOT / "calibrated-general.json")
ANNOTATIONS = ROOT / "annotation" / "forms" / "annotations-claude.json"


def signal_of(reason: str) -> str:
    """Bucket a flag reason string by which signal raised it."""
    if reason.startswith("omission"):
        return "omission"
    if reason.startswith("entailment"):
        return "entailment"
    if reason.startswith("aggregate"):
        return "aggregate"
    return "drift"


def main() -> None:
    annotations = {
        r["chain_id"]: r
        for r in json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    }
    clean_ids = [
        cid for cid, r in annotations.items() if r.get("cascade_occurred") is False
    ]
    print(f"chains annotated clean: {len(clean_ids)} ({', '.join(sorted(clean_ids))})")
    print(f"profile: {PROFILE.name} | drift {PROFILE.drift_threshold} "
          f"| entail {PROFILE.entail_threshold} | aggregate {PROFILE.aggregate_threshold} "
          f"| omission {PROFILE.omission_threshold}")

    total_steps = 0
    flagged_steps = 0
    by_signal: Counter[str] = Counter()
    steps_by_signal: dict[str, int] = Counter()

    for chain_id in sorted(clean_ids):
        data = json.loads((ROOT / "organic" / f"{chain_id}.json").read_text(encoding="utf-8"))
        analyzer = CascadeAnalyzer(profile=PROFILE, anchor=data["source"])
        report = analyzer.analyze(data["steps"])
        print(f"\n=== {chain_id} — {data['question'][:60]}")
        for s in report.steps:
            total_steps += 1
            fmt = lambda v: f"{v:.3f}" if v is not None else "  -  "
            signals = {signal_of(r) for r in s.flag_reasons}
            if s.flagged:
                flagged_steps += 1
                for name in signals:
                    steps_by_signal[name] += 1
                for reason in s.flag_reasons:
                    by_signal[signal_of(reason)] += 1
            print(f"  step {s.step_id} {str(s.agent_name):<10} "
                  f"d_prev={fmt(s.drift_prev)} d_anchor={fmt(s.drift_anchor)} "
                  f"entail={fmt(s.entailment)} cover={fmt(s.coverage)} "
                  f"omit={fmt(s.omission)} {'FLAG: ' + ', '.join(sorted(signals)) if s.flagged else ''}")

    print(f"\nstep-level false positives: {flagged_steps}/{total_steps} "
          f"({100 * flagged_steps / max(total_steps, 1):.0f}%)")
    print("steps flagged, by signal (a step can trip more than one):")
    for name, count in steps_by_signal.most_common():
        print(f"  {name:<12} {count}/{total_steps} ({100 * count / max(total_steps, 1):.0f}%)")
    print("\nomission-only false positives (steps where omission is the sole reason): "
          + str(sum(1 for name, c in steps_by_signal.items() if name == "omission" and c)
                and "see per-step table above"))


if __name__ == "__main__":
    main()
