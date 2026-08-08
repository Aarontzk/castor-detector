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

## Organic validation (semi-natural, PRD S12.2) — added 2026-07-03

**Setup:** 8 real agent chains run via Ollama `qwen2.5:3b` (deviation from PRD's
qwen2.5-coder/phi4-mini — it's what was installed; a small general model is
*more* hallucination-prone, which suits this test). Linear 4-agent chain
(extractor → analyst → reasoner → writer) with an information bottleneck: each
agent sees only the previous agent's output, never the source document. Anchor
override = source document. Tasks: 8 fact-grounded questions (EN+ID), manually
annotated against the sources. Reproduce: `validation/agent_chain.py` +
`validation/analyze_organic.py`.

**Every single chain (8/8) cascaded organically.** No injection needed —
qwen2.5:3b at temperature 0.8 produced real errors in all runs.

| Chain | Annotated origin (manual) | Castor first flag | Hit |
|---|---|---|---|
| 01 profit | step 2 (subtracts excluded grant) | step 3 (entail 0.001) | ±1 |
| 02 warehouse | step 2 (claims 380 ≥ 450) | step 2 (entail 0.060) | **exact** |
| 03 reactor | step 1 (omits recalibration + 74° rule); step 4 fabricates "74°" | step 2 | ±1; step-4 fabrication MISSED (entail 0.990) |
| 04 buses | step 2 (nonsense math, wrong ceiling) | step 2 (entail 0.003) | **exact** |
| 05 campaign | step 1 (drops the excluded-400 figure) | step 2 | ±1 |
| 06 panen (ID) | step 1 (drops planting date) | step 2 (drift 0.732 — ID→EN language switch) | ±1 |
| 07 flight | step 1 (drops walk time, merges policies) → step 2 fabricates rules | step 2 | ±1 |
| 08 anggaran (ID) | step 1 (omits phase-1/2 spend) → step 2 wrong remainder | step 2 | ±1 |

**Results:** step-level flags fired in 8/8 cascades; first flag within ±1 of
the annotated origin in **8/8**, exact in 2/8. Trajectory-level verdict
(aggregate > calibrated θ) fired in **0/8** — the θ calibrated on the synthetic
clean set does not transfer to organic chains; the per-signal flags (mostly
entailment collapse, 0.001–0.06) did all the real work. No organic FPR is
reported: the model produced zero clean runs to measure it on.

**Findings that matter for v1:**

1. **Dominant organic failure mode = extraction OMISSION (5/8 origins).**
   A summary that silently drops the planting date or the phase-1/2 spend is
   drift-invisible and entailment-valid *by construction* — a faithful subset
   looks perfect to both signals. The synthetic toolkit (FR-10) doesn't even
   have an omission kind. v1 needs a completeness signal (reverse entailment:
   do the source's key facts entail into the extraction?).
2. **NLI is blind to arithmetic.** Wrong math stated fluently scores as
   entailed (01 step 2: 0.834 despite subtracting the excluded grant; 03
   step 4: 0.990 on a fabricated "74 degrees"). Matches the synthetic finding
   (numeric fabrication 30% detection). Claim-level numeric checks stay the
   #1 v1 priority.
3. **Verdict rule is the weak link, not the signals.** v1: verdict should
   trigger on per-signal evidence (e.g. entailment collapse below τ on a
   conclusive step), not only on the weighted aggregate.
4. **Language-switch artifact:** the chain answering an Indonesian question in
   English produced the run's largest drift (0.732) — mpnet is EN-centric, so
   code-switching reads as huge semantic drift. For ID pipelines, swap in a
   multilingual embedder (the `Embedder` interface exists for exactly this).

## Organic validation extended to N=28 — added 2026-08-07

Batch 2 added 20 chains (`validation/agent_chain_batch2.py`, same qwen2.5:3b
information-bottleneck setup), taking the organic set to 28. All 28 were
annotated under one written scheme (`validation/annotation/GUIDE.md`): first
step that deviates from the source, plus an error type. Two findings from the
N=8 write-up above do not survive the larger sample.

**Correction 1: omission is not the dominant failure mode.**

| Error type at the origin | N=8 (batch 1) | N=28 (full set) |
|---|---|---|
| misread (fact present, meaning inverted or misapplied) | 2/8 (25%) | **11/24 (46%)** |
| omission (fact silently dropped) | **5/8 (62%)** | 9/24 (38%) |
| arithmetic | 1/8 (12%) | 2/24 (8%) |
| fabrication | 0/8 | 2/24 (8%) |

The batch-1 claim that omission dominates was an artefact of eight samples. The
larger mode is *misread*: the step keeps the fact and inverts what it means. A
gauge drifting "+6 psi" gets added instead of subtracted; a clearance rule is
stated correctly and violated in the same sentence; a trainee counted as half a
unit is added on top of the five nurses who already include them. Omission
remains the second mode and remains the one drift and forward entailment cannot
see, which is why the signal below was still worth building.

**Correction 2: organic FPR is measurable now, and it is bad.**

Batch 1 produced no clean runs, so no organic FPR was reported. Batch 2 produced
four (`organic-13`, `-15`, `-20`, `-27`), and on those:

- chain-level false positives: **4/4** — every clean chain trips at least one flag
- step-level false positives: **31%** with drift + entailment, rising to 44-62%
  once the omission signal is on

The synthetic-calibrated profile does not transfer, in both directions: it
missed every organic cascade at the trajectory level (0/28 verdicts) and it
flags every organic clean run at the step level. Calibration is not a footnote
for this tool, it is a precondition.

### Omission signal (v1 item 1) — reverse-entailment coverage

`src/castor/omission.py`. Same NLI cross-encoder, inputs reversed: instead of
"is this step supported by its predecessor?", ask "does this step still entail
each fact of the source?". Coverage is the fraction of anchor facts a step
entails; omission is the coverage a step lost relative to the step before it,
so the drop is charged to the step that caused it. No training, no new model.

Measured over the 28 annotated chains (`validation/measure_omission.py`, shipped
defaults: coverage 0.5, omission 0.25):

| Origin attribution | drift + entailment | + omission signal |
|---|---|---|
| all cascaded chains, exact | 6/24 (25%) | **12/24 (50%)** |
| all cascaded chains, within-1 | 18/24 (75%) | **23/24 (96%)** |
| chains annotated `omission`, exact | 0/9 (0%) | **5/9 (56%)** |
| chains annotated `omission`, within-1 | 7/9 (78%) | **9/9 (100%)** |

The signal adds no detection: both configurations flag 24/24 cascades, and there
is no chain where omission is the only flag. What it buys is *attribution*, which
is the product's actual claim. It moved the first flag closer to the annotated
origin on 10 chains and doubled exact-origin accuracy.

The cost is precision on clean runs: step-level false positives rise from 31% to
44%. Chain-level false positives do not change (4/4 either way) because the
legacy signals already flag every clean chain.

**Threshold sweep** (`validation/sweep_omission.py`, cached NLI matrix so the
sweep is free after one pass):

- The **coverage threshold barely matters**. Fact-level entailment scores are
  strongly bimodal: 68% land below 0.05 and 26% above 0.8, with only 7% in the
  ambiguous middle. Any cut between 0.05 and 0.9 partitions almost identically.
- The **omission threshold is the real knob**. At 0.20 attribution reaches 71%
  exact and 100% within-1, against 50%/96% at the shipped 0.25 and 25%/75% with
  the signal off.
- Defaults are deliberately left at 0.5/0.25. The sweep was run on the same 28
  chains it is scored on, with only 4 clean chains behind the false-positive
  figure, so 0.20 is a tuned number rather than a validated one. A disjoint
  organic set is the prerequisite for moving the default.

**Negative result worth recording:** suppressing the omission flag on condensing
roles (writer, then writer + reasoner) did not reduce false positives at all.
Coverage does collapse by role exactly as predicted (mean anchor-fact coverage:
extractor 0.54, analyst 0.45, reasoner 0.06, writer 0.04), but those steps are
*already* flagged by forward entailment, so suppressing the omission flag alone
changes nothing. Role-aware thresholds (v1 item 6) have to apply to entailment
and omission together, or they buy nothing.

**Second-order finding:** a faithful extractor scores only 0.54 mean coverage.
The NLI model under-scores entailment when a step paraphrases the source instead
of quoting it, which is the direct cause of the omission flags on `organic-13`
and `organic-20`, both annotated clean. Fact-level coverage is measuring
paraphrase distance as much as it is measuring completeness. That is a real
limitation of this implementation, not a property of the chains.

### Annotation provenance and reliability

Ground truth for all 28 chains lives in `validation/annotation/`. The labels
used above are a single machine-assisted pass (`annotations-claude.json`) whose
origin steps match the earlier human annotations on all 8 batch-1 chains. That
agreement is not independent evidence: the same pass had already read the
batch-1 table in this document.

The human round is set up but not yet run: 10 chains are assigned to both
annotators for a Cohen's kappa, the remaining 18 are split 9/9. Until that lands,
**every number in this section rests on unverified single-pass labels** and
should be read as provisional.

## Self-healing loop demo (owner request, not a Castor feature)

`examples/self_healing_chain.py`: an ORCHESTRATOR-side pattern (Castor stays
passive) — re-ground the worker with clean facts + Castor's flag reason,
retry once, keep the original and report "unresolved" if still flagged. Two
runs on the same 3-step chain:

- Run A: analyst step healed on retry (entailment 0.010 → resolved); writer
  step unresolved after 2 attempts (entailment stuck at 0.056–0.075).
- Run B: analyst unresolved after 2 attempts (entailment 0.005–0.006); writer
  healed on retry (0.384 → resolved).

**Honest caveat found while building this:** the writer role (a condensing
summary step) trips the entailment threshold more easily than reasoning
steps, because summarization legitimately drops detail that full entailment
scoring penalizes — the same threshold (0.72) is applied to a "reason forward"
transition and a "compress down" transition, which are different tasks. This
is the heteroskedastic-signal problem the PRD already flags (Section 3.3) for
threshold profiles — role-aware entailment thresholds are a concrete v1
candidate this demo surfaces.

## Known limitations of this validation

- Synthetic-only errors (FR-10). Semi-natural Ollama-generated trajectories (PRD S12.2) not run — Ollama not installed on this machine; queued as an open task.
- 30 clean trajectories is the PRD minimum; distributions are noisy (±1 trajectory ≈ 7pp FPR).
- Calibration and injection share the same 30 clean sources (held-out split only isolates FPR). A fully disjoint test set is a v1 task.
