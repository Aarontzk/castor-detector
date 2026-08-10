"""Verdict-rule sweep for the organic set (v1 item 3), cached so it sweeps free.

The trajectory-level verdict is the product's headline output: it is what the
CLI exits non-zero on, and it gates classification and attribution in
`CascadeAnalyzer._analyze`. On the organic set the shipped aggregate-only rule
fires on 0 of 24 annotated cascades while per-step flags catch all 24, so the
headline contradicts the evidence underneath it.

Aggregation is the reason. The aggregate is a weighted MEAN of three signals, so
one collapsed signal is diluted by two calm ones: an entailment of 0.003 is
strong evidence on its own, but averaged at weight 0.4 against a low drift and a
flat certainty delta it lands under theta.

This script measures the alternative: a DISJUNCTION over per-signal triggers,
where each trigger is set at collapse grade rather than at the per-step flag
grade. Recall is measured on the annotated cascades, chain-level false positives
on the annotated clean chains.

Pass 1 scores every chain once with shared model instances and caches the raw
per-step signals. Pass 2 sweeps rules over the cache at no cost.

Run:  python validation/sweep_verdict.py            # uses cache when present
      python validation/sweep_verdict.py --refresh  # rebuild the cache
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import CascadeAnalyzer, ThresholdProfile  # noqa: E402
from castor.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_NLI_MODEL  # noqa: E402
from castor.embedding import SentenceTransformerEmbedder  # noqa: E402
from castor.entailment import CrossEncoderEntailment  # noqa: E402

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "verdict-cache.json"
ANNOTATIONS = ROOT / "annotation" / "forms" / "annotations-claude.json"
BASE_PROFILE = ThresholdProfile.load(ROOT / "calibrated-general.json")

# Offline/air-gapped escape hatch: point these at local model directories when
# the Hub is unreachable. Defaults keep the published model ids.
EMBED_MODEL = os.environ.get("CASTOR_EMBED_MODEL", DEFAULT_EMBEDDING_MODEL)
NLI_MODEL = os.environ.get("CASTOR_NLI_MODEL", DEFAULT_NLI_MODEL)


def build_cache() -> list[dict]:
    """Score every annotated chain once and cache raw per-step signal values.

    Raw values are threshold-independent, so one pass supports any rule the
    sweep wants to try. Coverage is the exception: it is computed against
    `coverage_threshold`, so it is cached at the shipped 0.5 (the sweep in
    `sweep_omission.py` established that this knob barely moves the partition).
    """
    annotations = {
        r["chain_id"]: r
        for r in json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
        if r.get("cascade_occurred") is not None
    }
    # Shared model instances for the whole run instead of one pair per chain.
    embedder = SentenceTransformerEmbedder(model_name=EMBED_MODEL)
    checker = CrossEncoderEntailment(model_name=NLI_MODEL)

    rows = []
    for path in sorted((ROOT / "organic").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        truth = annotations.get(data["id"])
        if truth is None:
            continue
        analyzer = CascadeAnalyzer(
            embedder=embedder,
            entailment=checker,
            profile=BASE_PROFILE,
            anchor=data["source"],
        )
        report = analyzer.analyze(data["steps"])
        rows.append({
            "id": data["id"],
            "cascade": bool(truth["cascade_occurred"]),
            "origin_step": truth["origin_step"],
            "error_type": truth["error_type"],
            "shipped_verdict": bool(report.verdict),
            "steps": [
                {
                    "step_id": s.step_id,
                    "agent": s.agent_name,
                    "drift_prev": s.drift_prev,
                    "drift_anchor": s.drift_anchor,
                    "entailment": s.entailment,
                    "contradiction": s.contradiction,
                    "certainty_delta": s.certainty_delta,
                    "conclusive": s.conclusive,
                    "aggregate": s.aggregate,
                    "coverage": s.coverage,
                    "omission": s.omission,
                    "flag_reasons": list(s.flag_reasons),
                }
                for s in report.steps
            ],
        })
        print(f"  scored {data['id']} ({len(report.steps)} steps)", flush=True)
    return rows


def load_cache(refresh: bool) -> list[dict]:
    if not refresh and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    print("building verdict cache (loads mpnet + NLI, one pass over 28 chains)...")
    rows = build_cache()
    CACHE.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"cached -> {CACHE}")
    return rows


@dataclass(frozen=True)
class Rule:
    """One candidate verdict rule. None disables that trigger."""

    name: str
    aggregate: float | None = None       # any step aggregate > x
    entail_collapse: float | None = None  # any step entailment < x
    drift_anchor: float | None = None     # any step drift_anchor > x
    omission: float | None = None         # any step omission > x
    consecutive_flags: bool = False       # two adjacent steps both flagged

    def fires(self, row: dict) -> bool:
        steps = row["steps"]
        get = lambda key: [s[key] for s in steps if s[key] is not None]
        if self.aggregate is not None and any(v > self.aggregate for v in get("aggregate")):
            return True
        if self.entail_collapse is not None and any(
            v < self.entail_collapse for v in get("entailment")
        ):
            return True
        if self.drift_anchor is not None and any(
            v > self.drift_anchor for v in get("drift_anchor")
        ):
            return True
        if self.omission is not None and any(v > self.omission for v in get("omission")):
            return True
        if self.consecutive_flags:
            flags = [bool(s["flag_reasons"]) for s in steps]
            if any(a and b for a, b in zip(flags, flags[1:])):
                return True
        return False


def evaluate(rule: Rule, rows: list[dict]) -> dict:
    cascaded = [r for r in rows if r["cascade"]]
    clean = [r for r in rows if not r["cascade"]]
    hits = sum(1 for r in cascaded if rule.fires(r))
    false = sum(1 for r in clean if rule.fires(r))
    return {
        "name": rule.name,
        "recall": hits,
        "n_cascade": len(cascaded),
        "fp": false,
        "n_clean": len(clean),
    }


def report(results: list[dict]) -> None:
    print(f"\n{'rule':<44} {'recall':>14} {'chain FPR':>14}")
    print("-" * 74)
    for r in results:
        rec = f"{r['recall']}/{r['n_cascade']} ({100 * r['recall'] / r['n_cascade']:.0f}%)"
        fpr = (
            f"{r['fp']}/{r['n_clean']} ({100 * r['fp'] / r['n_clean']:.0f}%)"
            if r["n_clean"] else "-"
        )
        print(f"{r['name']:<44} {rec:>14} {fpr:>14}")


def main() -> None:
    rows = load_cache("--refresh" in sys.argv)
    cascaded = [r for r in rows if r["cascade"]]
    clean = [r for r in rows if not r["cascade"]]
    print(f"\nchains: {len(rows)} total | {len(cascaded)} cascaded | {len(clean)} clean")
    print(f"profile: {BASE_PROFILE.name} | aggregate_threshold {BASE_PROFILE.aggregate_threshold}"
          f" | entail_threshold {BASE_PROFILE.entail_threshold}")

    shipped = sum(1 for r in cascaded if r["shipped_verdict"])
    shipped_fp = sum(1 for r in clean if r["shipped_verdict"])
    print(f"shipped verdict as analysed: {shipped}/{len(cascaded)} recall, "
          f"{shipped_fp}/{len(clean)} chain FPR")

    # Signal distributions: what separates cascaded from clean at all?
    print("\nper-signal minima/maxima by class (what a trigger has to separate)")
    for key, agg in (("entailment", min), ("drift_anchor", max),
                     ("omission", max), ("aggregate", max)):
        def summarise(subset):
            vals = []
            for r in subset:
                v = [s[key] for s in r["steps"] if s[key] is not None]
                if v:
                    vals.append(agg(v))
            if not vals:
                return "-"
            vals.sort()
            return (f"min {vals[0]:.3f} p25 {vals[len(vals) // 4]:.3f} "
                    f"med {vals[len(vals) // 2]:.3f} max {vals[-1]:.3f}")
        print(f"  {agg.__name__}({key}):")
        print(f"    cascaded  {summarise(cascaded)}")
        print(f"    clean     {summarise(clean)}")

    baselines = [
        Rule("shipped: aggregate-only", aggregate=BASE_PROFILE.aggregate_threshold),
        Rule("any per-step flag", aggregate=BASE_PROFILE.aggregate_threshold,
             entail_collapse=BASE_PROFILE.entail_threshold,
             drift_anchor=BASE_PROFILE.drift_threshold,
             omission=BASE_PROFILE.omission_threshold),
        Rule("two consecutive flagged steps", consecutive_flags=True),
    ]
    report([evaluate(r, rows) for r in baselines])

    print("\nsingle-trigger sweeps (isolating each signal)")
    singles: list[Rule] = []
    for x in (0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.4, 0.72):
        singles.append(Rule(f"entailment collapse < {x}", entail_collapse=x))
    for x in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95):
        singles.append(Rule(f"drift_anchor > {x}", drift_anchor=x))
    for x in (0.2, 0.25, 0.34, 0.5, 0.67):
        singles.append(Rule(f"omission > {x}", omission=x))
    for x in (0.4, 0.5, 0.55, 0.6, 0.65, 0.7123):
        singles.append(Rule(f"aggregate > {x}", aggregate=x))
    report([evaluate(r, rows) for r in singles])

    print("\ndisjunction candidates")
    combos = [
        Rule("entail<0.01 OR aggr>0.7123",
             entail_collapse=0.01, aggregate=BASE_PROFILE.aggregate_threshold),
        Rule("entail<0.05 OR aggr>0.7123",
             entail_collapse=0.05, aggregate=BASE_PROFILE.aggregate_threshold),
        Rule("entail<0.01 OR drift>0.85 OR aggr>0.7123",
             entail_collapse=0.01, drift_anchor=0.85,
             aggregate=BASE_PROFILE.aggregate_threshold),
        Rule("entail<0.01 OR omit>0.34 OR aggr>0.7123",
             entail_collapse=0.01, omission=0.34,
             aggregate=BASE_PROFILE.aggregate_threshold),
        Rule("entail<0.005 OR drift>0.9 OR omit>0.5 OR aggr>0.7123",
             entail_collapse=0.005, drift_anchor=0.9, omission=0.5,
             aggregate=BASE_PROFILE.aggregate_threshold),
    ]
    report([evaluate(r, rows) for r in combos])

    print("\nNOTE: only 4 clean organic chains exist, so chain-level FPR has 25pp")
    print("resolution. Any rule chosen here must be re-checked on the 15 held-out")
    print("clean synthetic trajectories (validation/run_validation.py).")


if __name__ == "__main__":
    main()
