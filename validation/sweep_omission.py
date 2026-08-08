"""Threshold sweep for the omission signal, cached so it runs once and sweeps free.

The first FPR measurement showed the coverage check firing on clean steps for
two separate reasons: condensing roles legitimately shed coverage, and the
default coverage threshold assumes more entailment mass than this NLI model
gives a faithful paraphrase. Both are calibration questions, so they deserve a
measured answer rather than a hand-picked constant.

Pass 1 scores every (step, anchor-fact) pair once with a single shared model
instance and caches the raw entailment matrix. Pass 2 sweeps thresholds over the
cache, which costs nothing, and reports the attribution/false-positive trade-off
for each setting.

Run:  python validation/sweep_omission.py           # uses cache when present
      python validation/sweep_omission.py --refresh # rebuild the cache
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import CascadeAnalyzer, ThresholdProfile  # noqa: E402
from castor.entailment import CrossEncoderEntailment  # noqa: E402
from castor.omission import omission_series, split_facts  # noqa: E402

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "omission-cache.json"
ANNOTATIONS = ROOT / "annotation" / "forms" / "annotations-claude.json"
BASE_PROFILE = ThresholdProfile.load(ROOT / "calibrated-general.json")

COVERAGE_GRID = (0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
OMISSION_GRID = (0.2, 0.25, 0.34, 0.5, 0.67, 0.75, 1.01)


def build_cache() -> list[dict]:
    """Score every chain once: legacy flags plus the raw (step x fact) NLI matrix."""
    annotations = {
        r["chain_id"]: r
        for r in json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
        if r.get("cascade_occurred") is not None
    }
    # One model instance for the whole run instead of one per chain.
    checker = CrossEncoderEntailment()
    # omission_threshold above 1.0 can never fire, which isolates the legacy signals.
    legacy_profile = ThresholdProfile(
        name=BASE_PROFILE.name,
        drift_threshold=BASE_PROFILE.drift_threshold,
        entail_threshold=BASE_PROFILE.entail_threshold,
        aggregate_threshold=BASE_PROFILE.aggregate_threshold,
        coverage_threshold=BASE_PROFILE.coverage_threshold,
        omission_threshold=2.0,
    )

    rows = []
    for path in sorted((ROOT / "organic").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        truth = annotations.get(data["id"])
        if truth is None:
            continue
        analyzer = CascadeAnalyzer(
            profile=legacy_profile, entailment=checker, anchor=data["source"]
        )
        report = analyzer.analyze(data["steps"])
        facts = split_facts(data["source"])
        # Measure the same steps the analyzer measured, in the same order.
        measured_ids = {str(s.step_id) for s in report.steps}
        texts = [s["text"] for s in data["steps"] if str(s["step_id"]) in measured_ids]
        pairs = [(t, f) for t in texts for f in facts]
        scored = checker.check_batch(pairs) if pairs else []
        width = max(len(facts), 1)
        matrix = [
            [scored[i * width + j].entailment for j in range(len(facts))]
            for i in range(len(texts))
        ]
        rows.append({
            "id": data["id"],
            "origin_step": truth["origin_step"],
            "cascade": truth["cascade_occurred"],
            "error_type": truth["error_type"],
            "roles": [s.agent_name for s in report.steps],
            "step_ids": [int(s.step_id) for s in report.steps],
            "legacy_flagged": [bool(s.flag_reasons) for s in report.steps],
            "entail_matrix": matrix,
        })
        print(f"cached {data['id']} ({len(facts)} facts)", flush=True)

    CACHE.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return rows


def evaluate(rows: list[dict], cover_t: float, omit_t: float,
             skip_roles: frozenset[str] = frozenset()) -> dict:
    """Attribution and false-positive rates for one threshold setting.

    `skip_roles` suppresses the omission flag for named agent roles, which is
    how the role-aware variant is tested without changing the signal itself.
    """
    cascaded_hits, clean_fp_steps, clean_steps, clean_chains_fp = [], 0, 0, 0
    omission_hits = []

    for row in rows:
        matrix = row["entail_matrix"]
        if not matrix or not matrix[0]:
            continue
        coverages = [
            sum(1 for value in step_row if value >= cover_t) / len(step_row)
            for step_row in matrix
        ]
        omissions = omission_series(coverages)
        flags = []
        for index, flagged in enumerate(row["legacy_flagged"]):
            role = (row["roles"][index] or "").lower()
            omit_fires = omissions[index] > omit_t and role not in skip_roles
            flags.append(flagged or omit_fires)

        first = next(
            (row["step_ids"][i] for i, on in enumerate(flags) if on), None
        )
        if row["cascade"]:
            cascaded_hits.append((first, row["origin_step"]))
            if row["error_type"] == "omission":
                omission_hits.append((first, row["origin_step"]))
        else:
            clean_steps += len(flags)
            clean_fp_steps += sum(1 for on in flags if on)
            clean_chains_fp += 1 if any(flags) else 0

    def acc(hits):
        if not hits:
            return 0.0, 0.0
        exact = sum(1 for p, a in hits if p is not None and p == a) / len(hits)
        near = sum(1 for p, a in hits if p is not None and abs(p - a) <= 1) / len(hits)
        return exact, near

    exact, near = acc(cascaded_hits)
    o_exact, o_near = acc(omission_hits)
    return {
        "exact": exact,
        "within1": near,
        "omission_exact": o_exact,
        "omission_within1": o_near,
        "fp_steps": clean_fp_steps / max(clean_steps, 1),
        "fp_chains": clean_chains_fp,
    }


def main() -> None:
    if "--refresh" in sys.argv or not CACHE.exists():
        rows = build_cache()
    else:
        rows = json.loads(CACHE.read_text(encoding="utf-8"))
    print(f"\nchains in cache: {len(rows)}")

    baseline = evaluate(rows, cover_t=0.5, omit_t=2.0)
    print(f"\nlegacy signals only: exact {baseline['exact']:.0%}  "
          f"within-1 {baseline['within1']:.0%}  "
          f"step FP {baseline['fp_steps']:.0%}  chain FP {baseline['fp_chains']}/4")

    print("\ncover  omit   exact  within1  omitExact  omitWithin1  stepFP  chainFP")
    best = []
    for cover_t in COVERAGE_GRID:
        for omit_t in OMISSION_GRID:
            m = evaluate(rows, cover_t, omit_t)
            best.append((m["within1"], -m["fp_steps"], cover_t, omit_t, m))
            print(f"{cover_t:5.2f}  {omit_t:4.2f}   {m['exact']:5.0%}  {m['within1']:7.0%}"
                  f"  {m['omission_exact']:9.0%}  {m['omission_within1']:11.0%}"
                  f"  {m['fp_steps']:6.0%}  {m['fp_chains']:6d}/4")

    best.sort(reverse=True)
    top_w1, neg_fp, cover_t, omit_t, m = best[0]
    print(f"\nbest by within-1 then fewest step FPs: coverage {cover_t}, omission {omit_t}"
          f" -> within-1 {top_w1:.0%}, step FP {-neg_fp:.0%}")

    print("\nrole-aware variant (omission suppressed on condensing roles)")
    for roles in (frozenset({"writer"}), frozenset({"writer", "reasoner"})):
        m = evaluate(rows, cover_t, omit_t, skip_roles=roles)
        label = "+".join(sorted(roles))
        print(f"  skip {label:<16} exact {m['exact']:5.0%}  within-1 {m['within1']:5.0%}"
              f"  step FP {m['fp_steps']:5.0%}  chain FP {m['fp_chains']}/4")


if __name__ == "__main__":
    main()
