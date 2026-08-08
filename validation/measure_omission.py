"""Measure the omission signal against the annotated organic set (v1 item 1).

The question this answers: does reverse-entailment coverage catch cascade
origins that drift and forward entailment miss, and what does it cost in false
positives on the chains annotated as clean?

Reports, over all 28 annotated chains:
  - attribution accuracy (exact and within-1) using the legacy signals only
    (drift, forward entailment, aggregate), then with omission flags added
  - the same split for chains whose annotated error type is `omission`, which
    is the mode the signal was built for
  - flag rate on chains annotated clean, the first organic false-positive
    figure this project has been able to measure

Run:  python validation/measure_omission.py [--detail]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import CascadeAnalyzer, ThresholdProfile  # noqa: E402

ROOT = Path(__file__).resolve().parent
PROFILE = ThresholdProfile.load(ROOT / "calibrated-general.json")
ANNOTATIONS = ROOT / "annotation" / "forms" / "annotations-claude.json"


def load_annotations() -> dict[str, dict]:
    """Annotated ground truth keyed by chain id."""
    return {
        r["chain_id"]: r
        for r in json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
        if r.get("cascade_occurred") is not None
    }


def first_flag(steps, include_omission: bool) -> int | None:
    """Earliest flagged step id, optionally ignoring omission-only flags.

    A step counts as flagged by the legacy signals when at least one of its
    reasons is not the omission reason, which is how the before/after
    comparison is kept honest on a single analysis pass.
    """
    for step in steps:
        reasons = [r for r in step.flag_reasons if include_omission or not r.startswith("omission")]
        if reasons:
            return int(step.step_id)
    return None


def score(hits: list[tuple[int | None, int]]) -> tuple[str, str, str]:
    """Turn (predicted, annotated) pairs into found / exact / within-1 shares."""
    total = len(hits)
    if not total:
        return "-", "-", "-"
    found = sum(1 for p, _ in hits if p is not None)
    exact = sum(1 for p, a in hits if p is not None and p == a)
    near = sum(1 for p, a in hits if p is not None and abs(p - a) <= 1)
    pct = lambda n: f"{n}/{total} ({100 * n / total:.0f}%)"
    return pct(found), pct(exact), pct(near)


def main() -> None:
    detail = "--detail" in sys.argv
    annotations = load_annotations()
    rows = []

    for path in sorted((ROOT / "organic").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        truth = annotations.get(data["id"])
        if truth is None:
            continue
        analyzer = CascadeAnalyzer(profile=PROFILE, anchor=data["source"])
        report = analyzer.analyze(data["steps"])
        rows.append({
            "id": data["id"],
            "truth": truth,
            "report": report,
            "legacy": first_flag(report.steps, include_omission=False),
            "with_omission": first_flag(report.steps, include_omission=True),
        })
        if detail:
            print(f"\n=== {data['id']} (annotated origin "
                  f"{truth['origin_step']}, {truth['error_type']})")
            for s in report.steps:
                fmt = lambda v: f"{v:.3f}" if v is not None else "  -  "
                print(f"  step {s.step_id} {str(s.agent_name):<10} "
                      f"d_anchor={fmt(s.drift_anchor)} entail={fmt(s.entailment)} "
                      f"cover={fmt(s.coverage)} omit={fmt(s.omission)} "
                      f"{'FLAG' if s.flagged else ''}")

    cascaded = [r for r in rows if r["truth"]["cascade_occurred"]]
    clean = [r for r in rows if not r["truth"]["cascade_occurred"]]
    omission_cases = [r for r in cascaded if r["truth"]["error_type"] == "omission"]

    def block(title: str, subset: list[dict]) -> None:
        if not subset:
            return
        print(f"\n{title} (n={len(subset)})")
        for label, key in (("drift + entailment", "legacy"), ("+ omission signal", "with_omission")):
            found, exact, near = score(
                [(r[key], r["truth"]["origin_step"]) for r in subset]
            )
            print(f"  {label:<20} flagged {found:<14} exact {exact:<14} within-1 {near}")

    print(f"profile: {PROFILE.name} | coverage_threshold {PROFILE.coverage_threshold} "
          f"| omission_threshold {PROFILE.omission_threshold}")
    block("ALL CASCADED CHAINS", cascaded)
    block("CHAINS ANNOTATED AS OMISSION", omission_cases)

    if clean:
        print(f"\nCHAINS ANNOTATED CLEAN (n={len(clean)})")
        for label, key in (("drift + entailment", "legacy"), ("+ omission signal", "with_omission")):
            fired = sum(1 for r in clean if r[key] is not None)
            print(f"  {label:<20} any step flagged: {fired}/{len(clean)} "
                  f"({100 * fired / len(clean):.0f}% chain-level false positives)")

    gained = [r for r in cascaded if r["legacy"] is None and r["with_omission"] is not None]
    improved = [
        r for r in cascaded
        if r["legacy"] is not None and r["with_omission"] is not None
        and abs(r["with_omission"] - r["truth"]["origin_step"])
        < abs(r["legacy"] - r["truth"]["origin_step"])
    ]
    print(f"\nchains where omission provided the only flag: {len(gained)}"
          + (f" ({', '.join(r['id'] for r in gained)})" if gained else ""))
    print(f"chains where omission moved the first flag closer to the origin: {len(improved)}"
          + (f" ({', '.join(r['id'] for r in improved)})" if improved else ""))


if __name__ == "__main__":
    main()
