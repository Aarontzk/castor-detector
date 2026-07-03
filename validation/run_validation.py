"""Validation run (PRD Section 12): detection rate, FPR, attribution accuracy,
classification accuracy, ablation, baseline, latency.

Methodology:
- 30 clean trajectories, split 15 calibration / 15 held-out.
- Thresholds calibrated on the calibration split only (p95 of each signal).
- Errors injected (FR-10) into ALL 30 clean trajectories x 5 kinds = 150
  corrupted trajectories with known origin step and kind.
- FPR measured on the 15 HELD-OUT clean trajectories only.
- Ablation: prev-only vs anchor-only vs dual vs dual+NLI vs naive baseline.

Run:  .venv/Scripts/python validation/run_validation.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import (
    CascadeAnalyzer,
    CrossEncoderEntailment,
    INJECTION_KINDS,
    SentenceTransformerEmbedder,
    ThresholdProfile,
    Trajectory,
    inject,
)
from castor.taxonomy import (
    CONFIDENCE_INFLATION,
    CONTEXT_POISONING,
    INFERENCE,
)

EXPECTED_TYPE = {
    "numeric_fabrication": INFERENCE,
    "entity_distortion": INFERENCE,
    "causal_leap": INFERENCE,
    "certainty_inflation": CONFIDENCE_INFLATION,
    "context_swap": CONTEXT_POISONING,
}

ROOT = Path(__file__).resolve().parent


def load_clean() -> list[tuple[str, Trajectory]]:
    data = json.loads((ROOT / "clean_trajectories.json").read_text(encoding="utf-8"))
    return [(item["id"], Trajectory.from_steps(item["steps"])) for item in data]


def analyze_all(items, embedder, nli, profile):
    """One CascadeReport per trajectory; shared models, fresh analyzer each."""
    reports = []
    for name, trajectory in items:
        analyzer = CascadeAnalyzer(embedder=embedder, entailment=nli, profile=profile)
        reports.append((name, analyzer.analyze(trajectory)))
    return reports


def signal_values(reports):
    """Collect per-signal step values across reports for calibration."""
    prev, anchor, aggregate = [], [], []
    for _, report in reports:
        for step in report.steps:
            if step.drift_prev is not None:
                prev.append(step.drift_prev)
            if step.drift_anchor is not None:
                anchor.append(step.drift_anchor)
            if step.aggregate is not None:
                aggregate.append(step.aggregate)
    return np.array(prev), np.array(anchor), np.array(aggregate)


def variant_verdicts(report, thresholds):
    """Ablation verdicts recomputed from one report's signals."""
    prev = [s.drift_prev for s in report.steps if s.drift_prev is not None]
    anchor = [s.drift_anchor for s in report.steps if s.drift_anchor is not None]
    aggregate = [s.aggregate for s in report.steps if s.aggregate is not None]
    return {
        "prev_only": any(v > thresholds["prev"] for v in prev),
        "anchor_only": any(v > thresholds["anchor"] for v in anchor),
        "dual": any(v > thresholds["prev"] for v in prev)
        or any(v > thresholds["anchor"] for v in anchor),
        "dual_nli": any(v > thresholds["aggregate"] for v in aggregate),
    }


def naive_baseline_verdict(trajectory, embedder, threshold):
    """Baseline: single similarity check, final output vs first step."""
    texts = [s.text for s in trajectory.steps if s.has_measurable_text]
    if len(texts) < 2:
        return False
    from castor import cosine_similarity

    vectors = embedder.embed([texts[0], texts[-1]])
    return (1.0 - cosine_similarity(vectors[0], vectors[1])) > threshold


def main() -> None:
    embedder = SentenceTransformerEmbedder()
    nli = CrossEncoderEntailment()
    clean = load_clean()
    cal_split, holdout_split = clean[:15], clean[15:]
    default_profile = ThresholdProfile()

    print("=== calibration (15 clean trajectories, defaults profile) ===")
    t0 = time.perf_counter()
    cal_reports = analyze_all(cal_split, embedder, nli, default_profile)
    cal_seconds = time.perf_counter() - t0
    n_cal_steps = sum(len(r.steps) for _, r in cal_reports)
    prev, anchor, aggregate = signal_values(cal_reports)
    thresholds = {
        "prev": float(np.percentile(prev, 95)),
        "anchor": float(np.percentile(anchor, 95)),
        "aggregate": float(np.percentile(aggregate, 95)),
    }
    naive_values = []
    for _, trajectory in cal_split:
        texts = [s.text for s in trajectory.steps if s.has_measurable_text]
        vectors = embedder.embed([texts[0], texts[-1]])
        from castor import cosine_similarity

        naive_values.append(1.0 - cosine_similarity(vectors[0], vectors[1]))
    thresholds["naive"] = float(np.percentile(naive_values, 95))
    calibrated_profile = ThresholdProfile(
        name="calibrated-general",
        drift_threshold=round(max(thresholds["prev"], thresholds["anchor"]), 4),
        aggregate_threshold=round(thresholds["aggregate"], 4),
    )
    print(f"calibrated thresholds: {thresholds}")
    print(f"latency: {cal_seconds / max(n_cal_steps, 1) * 1000:.0f} ms/step (embed+NLI, CPU)")

    print("\n=== FPR on 15 held-out clean trajectories ===")
    holdout_reports = analyze_all(holdout_split, embedder, nli, calibrated_profile)
    fp = {"prev_only": 0, "anchor_only": 0, "dual": 0, "dual_nli": 0, "naive": 0,
          "default_verdict": 0}
    for (name, trajectory), (_, report) in zip(holdout_split, holdout_reports):
        for variant, verdict in variant_verdicts(report, thresholds).items():
            fp[variant] += verdict
        fp["naive"] += naive_baseline_verdict(trajectory, embedder, thresholds["naive"])
    default_holdout = analyze_all(holdout_split, embedder, nli, default_profile)
    fp["default_verdict"] = sum(r.verdict for _, r in default_holdout)
    n_holdout = len(holdout_split)
    for variant, count in fp.items():
        print(f"  {variant:<16} FPR = {count}/{n_holdout} = {count / n_holdout:.0%}")

    print("\n=== detection + attribution on 150 injected trajectories ===")
    detected = {k: {"prev_only": 0, "anchor_only": 0, "dual": 0, "dual_nli": 0, "naive": 0}
                for k in INJECTION_KINDS}
    attribution_exact = {k: 0 for k in INJECTION_KINDS}
    attribution_pm1 = {k: 0 for k in INJECTION_KINDS}
    classified = {k: 0 for k in INJECTION_KINDS}
    detected_dualnli_total = {k: 0 for k in INJECTION_KINDS}
    per_kind_n = {k: 0 for k in INJECTION_KINDS}

    for index, (name, trajectory) in enumerate(clean):
        for kind in INJECTION_KINDS:
            corrupted, record = inject(trajectory, kind, seed=index * 7 + 1)
            per_kind_n[kind] += 1
            analyzer = CascadeAnalyzer(embedder=embedder, entailment=nli,
                                       profile=calibrated_profile)
            report = analyzer.analyze(corrupted)
            verdicts = variant_verdicts(report, thresholds)
            for variant, verdict in verdicts.items():
                detected[kind][variant] += verdict
            detected[kind]["naive"] += naive_baseline_verdict(
                corrupted, embedder, thresholds["naive"]
            )
            if verdicts["dual_nli"]:
                detected_dualnli_total[kind] += 1
                # Attribution accuracy measured only when detected.
                if report.attribution:
                    positions = {s.step_id: i for i, s in enumerate(report.steps)}
                    top = report.attribution[0].origin_step
                    top_pos = positions.get(top)
                    if top_pos == record.step_index:
                        attribution_exact[kind] += 1
                    if top_pos is not None and abs(top_pos - record.step_index) <= 1:
                        attribution_pm1[kind] += 1
                predicted_types = {t.cascade_type for t in report.classification}
                if EXPECTED_TYPE[kind] in predicted_types:
                    classified[kind] += 1

    print(f"{'kind':<22} {'dual+NLI':>9} {'dual':>6} {'prev':>6} {'anchor':>7} {'naive':>6}"
          f" {'attr=':>6} {'attr±1':>7} {'class':>6}")
    totals = {"dual_nli": 0, "dual": 0, "prev_only": 0, "anchor_only": 0, "naive": 0,
              "exact": 0, "pm1": 0, "cls": 0, "det": 0, "n": 0}
    for kind in INJECTION_KINDS:
        n = per_kind_n[kind]
        det = detected_dualnli_total[kind]
        totals["n"] += n
        totals["det"] += det
        for key_from, key_to in [("dual_nli", "dual_nli"), ("dual", "dual"),
                                 ("prev_only", "prev_only"),
                                 ("anchor_only", "anchor_only"), ("naive", "naive")]:
            totals[key_to] += detected[kind][key_from]
        totals["exact"] += attribution_exact[kind]
        totals["pm1"] += attribution_pm1[kind]
        totals["cls"] += classified[kind]
        print(
            f"{kind:<22} {detected[kind]['dual_nli'] / n:>8.0%} {detected[kind]['dual'] / n:>6.0%}"
            f" {detected[kind]['prev_only'] / n:>6.0%} {detected[kind]['anchor_only'] / n:>7.0%}"
            f" {detected[kind]['naive'] / n:>6.0%}"
            f" {attribution_exact[kind] / max(det, 1):>6.0%}"
            f" {attribution_pm1[kind] / max(det, 1):>7.0%}"
            f" {classified[kind] / max(det, 1):>6.0%}"
        )
    n_total = totals["n"]
    det_total = max(totals["det"], 1)
    print(
        f"{'TOTAL':<22} {totals['dual_nli'] / n_total:>8.0%} {totals['dual'] / n_total:>6.0%}"
        f" {totals['prev_only'] / n_total:>6.0%} {totals['anchor_only'] / n_total:>7.0%}"
        f" {totals['naive'] / n_total:>6.0%}"
        f" {totals['exact'] / det_total:>6.0%} {totals['pm1'] / det_total:>7.0%}"
        f" {totals['cls'] / det_total:>6.0%}"
    )
    print("\n(attr/class rates conditional on dual+NLI detection)")
    print(f"recommended profile: {calibrated_profile}")


if __name__ == "__main__":
    main()
