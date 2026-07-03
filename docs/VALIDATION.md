# Validation Report — Castor v0.1 (Phase 4)

**Date:** 2026-07-03 · **Method:** PRD Section 12 · **Hardware:** consumer CPU (no GPU)
**Reproduce:** `python validation/run_validation.py`

## Setup

- **Dataset:** 30 manually written clean trajectories (5 steps each; domains: numeric/finance, science, procedural, geography, narrative, multi-turn support; English + Indonesian).
- **Split:** 15 calibration / 15 held-out. Thresholds calibrated as p95 of each signal on the calibration split only; FPR measured on held-out only.
- **Injected set:** all 30 clean × 5 injection kinds (FR-10) = 150 corrupted trajectories with known origin step and kind.
- **Models:** all-mpnet-base-v2 (embeddings) + cross-encoder/nli-deberta-v3-base (NLI), both local.

## Headline results

| Metric | Target (PRD S13) | Result | Verdict |
|---|---|---|---|
| Detection rate (dual+NLI, calibrated) | ≥70% | **55%** | ❌ miss — see analysis |
| False positive rate | ≤20% | **27%** | ❌ miss (close) |
| Attribution accuracy ±1 step | ≥50% | **84%** | ✅ |
| Attribution accuracy exact step | (no target) | 47% | — |
| Classification accuracy (phase 2 DoD ≥60–70%) | ≥60% | **69%** | ✅ |
| Overhead per step (CPU) | <500 ms | **316 ms** | ✅ |
| Beat naive baseline clearly | required | 55% vs **10%** | ✅ |

## CHARM default thresholds do NOT transfer (confirmed)

With the out-of-the-box defaults (δ=0.18, θ=0.55), FPR on clean trajectories is **93%**.
Raw cosine distances between coherent adjacent steps on all-mpnet-base-v2 run ~0.4–0.8 — far above CHARM's reported scale. **`castor calibrate` on your own clean runs is not optional; it is required.** The README says so.

Calibrated thresholds from this dataset (shipped as `validation/calibrated-general.json`, but calibrate your own):
drift ≈ 0.815 (p95 anchor), aggregate ≈ 0.712.

## Per-kind detection (calibrated)

| Injection kind | dual+NLI | dual | prev-only | anchor-only | naive | attr ±1 | class |
|---|---|---|---|---|---|---|---|
| numeric_fabrication | 30% | 30% | 23% | 23% | 10% | 89% | 33% |
| entity_distortion | 27% | 30% | 27% | 23% | 10% | 88% | 25% |
| causal_leap | 53% | 30% | 23% | 20% | 10% | 88% | 100% |
| certainty_inflation | 83% | 33% | 27% | 23% | 10% | 84% | 96% |
| context_swap | 83% | 97% | 93% | 97% | 10% | 80% | 48% |
| **TOTAL** | **55%** | 44% | 39% | 37% | 10% | **84%** | **69%** |

(attribution/classification rates conditional on dual+NLI detection)

## Analysis (honest)

1. **The 55% headline hides a split.** Semantic-shift cascades (causal_leap, certainty_inflation, context_swap) average **73%** detection. Token-level fabrications (numeric_fabrication, entity_distortion) average **~29%** — changing "340 units" to "1,097 units" barely moves a sentence embedding. This is a *known architectural boundary*, not a tuning problem: PRD H-06 already schedules claim-level decomposition for v1. Embedding drift cannot and will not catch small token edits.
2. **NLI earns its cost** (ablation): dual+NLI 55% vs dual 44% vs prev-only 39% vs anchor-only 37%. Biggest gains exactly where drift is blind: certainty_inflation 33%→83%, causal_leap 30%→53%. Keep all components.
3. **Exception:** for context_swap, pure dual drift (97%) beats dual+NLI aggregate (83%) — weighted aggregation dilutes a huge drift spike when the swapped text happens to be internally coherent. Aggregate-vs-max is a v1 recalibration question.
4. **FPR 27% vs target 20%:** p95 calibration mathematically yields ~1 flagged step per ~20 clean steps; a 5-step trajectory has 4+ measurements, so per-trajectory FPR compounds. Options for v1: calibrate at p99, or require 2 consecutive flagged steps for a verdict. Not tuned here to avoid overfitting the same small dataset twice.
5. **Attribution is the strong suit:** 84% within ±1 step of the true origin (target 50%). Exact-step 47%, mostly off-by-one downstream — the corrupted step's *successor* often drifts hardest (dual-reference ranking mitigates but doesn't eliminate this).
6. **Naive baseline (final-vs-input similarity): 10%.** Castor's reason to exist is confirmed — trajectory-level tracking beats terminal checks by 5×.

## Component keep/drop decisions (PRD S12.4)

| Component | Verdict | Evidence |
|---|---|---|
| drift_prev | keep | 39% standalone; part of best combo |
| drift_anchor | keep | 37% standalone; context_swap 97% |
| NLI entailment | keep | +11pp total, +50pp on certainty_inflation |
| Confidence-language tracker | keep (secondary) | certainty_inflation 83% needs it; weight stays 0.2 |
| Weighted aggregator | keep, recalibrate in v1 | dilutes drift spikes (context_swap); weights are manual defaults |

## Known limitations of this validation

- Synthetic-only errors (FR-10). Semi-natural Ollama-generated trajectories (PRD S12.2) not run — Ollama not installed on this machine; queued as an open task.
- 30 clean trajectories is the PRD minimum; distributions are noisy (±1 trajectory ≈ 7pp FPR).
- Calibration and injection share the same 30 clean sources (held-out split only isolates FPR). A fully disjoint test set is a v1 task.
