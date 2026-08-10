# Results and Discussion (draft)

Draft for the semifinal paper. Every number here is reproducible from the repo;
the command that produces it is named next to it. Two sections are stubs waiting
on work owned by others and are marked as such rather than written around.

Status of inputs:

| Input | Owner | State |
|---|---|---|
| Organic set N=28, annotated | Fabio | done |
| Completeness (omission) signal | Fabio | done, measured |
| Cohen's kappa, machine vs human | Farel | done — origin kappa 1.000, type 0.859 (n=10) |
| Cohen's kappa, human vs human | Fabio | **pending** — second annotator outstanding |
| Verdict rule rework | Farel | implemented + omission trigger measured; two trigger levels **unmeasured** (see 2.5) |

---

## 1. Experimental setup

### 1.1 Two evaluation sets

**Synthetic (N=180).** 30 clean trajectories plus 150 with a single injected
error of known kind and position (`validation/run_validation.py`). Injection
never targets step 0, so the anchor stays clean and the injected error remains
measurable. This set gives controlled ground truth and is the basis for the
detection, classification and latency figures reported in Section 2 of the
paper.

**Organic (N=28).** Real agent chains produced by a local `qwen2.5:3b` under an
information bottleneck: four agents (extractor, analyst, reasoner, writer) in a
line, each seeing only its predecessor's output and never the source document
(`validation/agent_chain.py`, `validation/agent_chain_batch2.py`). No errors are
injected. The anchor is overridden to the source document, so drift is measured
against the ground truth the chain was supposed to preserve. Tasks are 28
fact-grounded questions in English and Indonesian, each source containing one
clause that changes the correct answer.

The organic set is what this section is about. Injected errors test whether a
detector finds errors we planted; organic chains test whether it finds the ones
a model actually makes.

### 1.2 Annotation protocol

Each chain was annotated for the **first step whose output deviates from the
source**, plus one error type from `{omission, arithmetic, misread,
fabrication}` (`validation/annotation/GUIDE.md`). A step that faithfully carries
an upstream error forward is not itself an origin. Legitimate compression is not
an omission: a writer step is expected to shed supporting detail.

Reliability is measured on a 10-chain overlap annotated independently by two
annotators, stratified across both collection batches and both question
languages; the remaining 18 are split 9/9
(`validation/annotation/prepare.py`, seed 42).

**Machine-versus-human agreement (measured).** One human annotator completed all
ten overlap chains by hand, without reading the machine pass or any other
annotator's labels. Against the machine pass on the same ten:

| Field | Agreement | Cohen's kappa |
|---|---|---|
| `origin_step` | 10/10 exact (100%) | **1.000** |
| `error_type` | 9/10 (90%) | **0.859** |
| `cascade_occurred` | 10/10 (100%) | — |

Perfect agreement on *where* the chain broke, across ten chains spanning both
batches and both languages, is the figure that matters here: origin step is what
Castor is scored against, and it is the label a reader has most reason to
suspect. The single error-type disagreement (`organic-04`) is not a disagreement
about the origin — both passes place it at step 2 — but about how to name an
error that is simultaneously an invented quantity and a miscalculation built on
it. The human annotator recorded the reasoning at labelling time: step 2 invents
both "30 regular seats per wheelchair space" and a 57-seat bus capacity, neither
present in the source, and the arithmetic slip that follows (186/57 = 3.26
rounded to 3) is downstream of the invention. We report the human label
(`fabrication`) and note the alternative.

Two caveats. Ten items is a small basis, and kappa on a near-degenerate label
distribution is unstable — the origin figure should be read as "no disagreement
was found in ten chains", not as a precise 1.000. And the human annotator had
previously reviewed machine-drafted labels for nine *different* (non-overlap)
chains, which cannot leak an overlap label but does expose the machine pass's
reasoning style.

> **PENDING (second annotator).** Human-versus-human kappa on the same ten
> chains is the figure the protocol was designed around and it is not yet
> available: the second annotator's pass is outstanding. Until it lands, label
> reliability rests on the machine-versus-human comparison above, which is
> weaker evidence — a single human confirming a machine pass is not two
> independent humans agreeing. If that kappa falls below 0.6 it is reported as
> measured, because a low kappa is itself a finding about how hard origin
> attribution is to label.

---

## 2. Results

### 2.1 Organic chains cascade, and the failure mode is not what N=8 suggested

24 of 28 chains (86%) deviated from their source without any injection. The
origin sits at step 1 in 16 of 24 cases (67%) and step 2 in the remaining 8: the
extractor, the only agent that ever sees the source, is where most cascades
begin.

An earlier report on the first 8 chains identified omission as the dominant
failure mode. At N=28 that does not hold (`validation/annotation/summarize.py`):

| Error type at origin | N=8 | N=28 |
|---|---|---|
| misread (fact retained, meaning inverted or misapplied) | 2/8 (25%) | **12/24 (50%)** |
| omission (fact silently dropped) | **5/8 (62%)** | 9/24 (38%) |
| fabrication | 0/8 (0%) | 2/24 (8%) |
| arithmetic | 1/8 (12%) | 1/24 (4%) |

The N=28 column reflects the human-verified labels. The machine-only pass read
`organic-04` as arithmetic and `organic-18` as fabrication; the human pass
reversed both. Notably, **no origin step differed between the two passes**, so
every attribution result below is unchanged by the correction — the labelling
disagreement is entirely about naming the error, not locating it.

The larger mode is *misread*. The model keeps the critical fact and inverts what
it means: a gauge with a "+6 psi calibration drift" is corrected upward instead
of downward; a store rule stating that percentage discounts and coupons cannot
be combined is quoted correctly and then violated in the next clause; a trainee
who "counts as half a staff unit" among five rostered nurses is added on top of
the five. These are not retrieval failures. The fact is present, in the step's
own text, and used backwards.

This matters for the paper's original framing. Omission and misread call for
different instrumentation: omission is a coverage question, misread is a
consistency question between a stated rule and its application. Only the first
is addressed by the signal reported below.

### 2.2 A completeness signal doubles origin attribution

Drift and forward entailment share a structural blind spot. A step that drops a
source fact is a faithful *subset* of its predecessor: it contradicts nothing,
so entailment scores high, and it stays close in embedding space, so drift stays
low. The failure is invisible by construction.

We invert the entailment direction (`src/castor/omission.py`). Forward
entailment asks whether a step is supported by its predecessor. **Coverage** asks
whether a step still entails each fact of the source, scoring
`(premise = step text, hypothesis = source fact)` for every anchor fact.
**Omission** is the coverage a step lost relative to the step before it, so the
loss is charged to the step that caused it rather than to every step downstream.
The same NLI cross-encoder is reused with reversed inputs: no training, no
additional model.

Measured over the 28 annotated chains at shipped defaults
(`validation/measure_omission.py`):

| Origin attribution | drift + entailment | + completeness |
|---|---|---|
| all cascaded, exact | 6/24 (25%) | **12/24 (50%)** |
| all cascaded, within-1 | 18/24 (75%) | **23/24 (96%)** |
| omission-labelled chains, exact | 0/9 (0%) | **5/9 (56%)** |
| omission-labelled chains, within-1 | 7/9 (78%) | **9/9 (100%)** |

Two things are worth separating. The signal adds **no detection**: both
configurations flag 24/24 cascades, and there is no chain where the completeness
check produces the only flag. What it adds is **attribution** — it moved the
first flag closer to the annotated origin on 10 chains and doubled exact-origin
accuracy. On the chains it was designed for, exact attribution went from zero to
56%, because those cascades previously surfaced only one step late, when the
consequence of the dropped fact finally contradicted something.

For a tool whose claim is *where* a chain broke rather than *that* it broke, this
is the axis that matters.

### 2.3 The precision cost, and the first organic false-positive measurement

The first eight organic chains all cascaded, so no organic false-positive rate
could be measured. Batch 2 produced four clean chains, making it measurable
(`validation/measure_fpr.py`):

| | drift + entailment | + completeness |
|---|---|---|
| clean chains with at least one flagged step | 4/4 | 4/4 |
| clean steps flagged | 5/16 (31%) | 7/16 (44%) |

Chain-level false positives do not change, because the legacy signals already
flag every clean chain. The completeness signal adds step-level noise on top of
a baseline that was already saturated.

This is the honest counterweight to Section 2.2. The synthetic-calibrated
profile fails in both directions on organic data: its trajectory-level verdict
fires on 0/28 real cascades, while its per-step flags fire on every clean run.
Calibration is a precondition for this tool, not a refinement.

### 2.4 Threshold sensitivity

`validation/sweep_omission.py` caches the raw (step x fact) entailment matrix
once and sweeps thresholds over the cache.

**The coverage threshold is nearly irrelevant.** Fact-level entailment scores are
strongly bimodal: 68% of the 400 scored pairs fall below 0.05 and 26% above 0.8,
leaving 7% in the ambiguous middle. Any cut between 0.05 and 0.9 produces almost
the same partition. This is a useful robustness property: the parameter that
looks most arbitrary turns out not to be a tuning surface at all.

**The omission threshold is the real knob.** At 0.20, attribution reaches 71%
exact and 100% within-1. We nonetheless ship 0.25 (50% / 96%). The sweep was
scored on the same 28 chains it was tuned on, and the false-positive side rests
on four clean chains. 0.20 is a tuned number, not a validated one, and a disjoint
organic set is the precondition for moving the default.

### 2.5 Verdict rule

The trajectory-level verdict fired on **0 of 24** organic cascades, while the
per-step flags it ignores caught all 24. The gap matters more than a wrong
boolean suggests: in our implementation the verdict *gates* classification and
attribution, so a false verdict returned an empty origin for every organic
cascade the system had already detected internally.

The cause is the aggregation operator. The rule was `any(step.aggregate > θ)`,
and the aggregate is a weighted mean of drift, entailment violation and
certainty inflation. A mean dilutes decisive evidence: an entailment of 0.003
enters at weight 0.4 alongside a low drift and a flat certainty delta, and the
result falls below θ. Averaging is the wrong operator for a signal that is
conclusive on its own.

We replace it with a disjunction. The aggregate rule survives as one disjunct,
joined by per-signal triggers set at *collapse grade* — deliberately stricter
than the per-step flag thresholds, on the principle that a step is worth showing
the user at flag grade but a trajectory should be declared broken only on
collapse-grade evidence. The new rule is a strict superset of the old, so recall
cannot decrease and false positives cannot improve; the entire question is what
the trade buys. The report additionally carries `verdict_reasons`, naming the
trigger and the step, since a disjunction that returns only a boolean cannot be
debugged.

**Omission fails as a verdict trigger, and the failure is informative.**
Recomputing per-chain maxima over all 28 chains:

| Max per-chain omission | Values |
|---|---|
| 4 chains annotated clean | 0.67, 0.67, 0.75, 1.00 |
| 24 chains annotated cascaded | 0.33 – 1.00 |

The clean chains occupy the top of the range. Any threshold below 0.67 flags
4/4 clean chains; at 0.75 recall falls to 17%. The cause is the paraphrase
effect of Section 2.4: condensing steps shed coverage legitimately, and a
correct chain sheds it as fast as a broken one — `organic-27` runs
1.00 → 1.00 → 0.00 → 0.00 while remaining correct throughout. We therefore ship
the omission trigger disabled. The signal that doubled *attribution* accuracy is
useless for *detection*, which is a concrete instance of a general point: the
two tasks reward different properties, and a signal validated on one should not
be assumed to transfer to the other.

**A bound on the whole approach.** Taking "any per-step flag" as the most
permissive rule available gives 24/24 recall and 4/4 chain-level false
positives. On this set no threshold over Castor's current signals separates
broken trajectories from healthy ones. The limitation is not the decision rule
but the signals: four clean chains look exactly like cascades to every one of
them.

> **Not yet measured.** The `entail_collapse` (0.01) and `drift_collapse` (0.9)
> levels are reasoned starting points, not calibrated values. The sweep that
> would fix them (`validation/sweep_verdict.py --refresh`) is implemented but
> was not run: the authoring environment could not download the two models. Any
> recall figure for the new rule must come from that run. Two caveats will bind
> it regardless — four clean organic chains give chain-level FPR a 25pp
> resolution, and the sweep tunes on the same 28 chains it scores, the
> double-fitting objection already recorded for the omission thresholds.

---

## 3. Discussion

### 3.1 A corrected claim is worth more than a confirmed one

The N=8 finding that omission dominates organic cascades was reported honestly
and turned out to be a small-sample artefact. We report the correction rather
than quietly restating the headline, for two reasons. First, the paper's numbers
function as a contract: a reader who clones the repository runs the same scripts
and must see the same figures. Second, the direction of the error is instructive.
Eight chains produced a 62% estimate for a quantity whose value at 28 chains is
38%. Any claim in this literature resting on single-digit sample counts, ours
included, should be read with that spread in mind.

### 3.2 Why detection did not move and attribution did

The completeness signal flagged no cascade that the existing signals missed. That
looks like a null result until the flags are examined per step. The dropped-fact
cascades were already being caught — one step late, at the point where the
missing fact produced a visible contradiction. The signal did not find new
cascades; it found the *beginning* of cascades that were previously only visible
by their consequences.

This is the distinction between a detector and an attributor, and it is the
distinction the product is built on. A tool that says "this chain is unreliable"
sends an engineer to read four steps. A tool that says "step 1 dropped the
exclusion clause" sends them to one.

### 3.3 The precision problem is now the binding constraint

With attribution at 96% within-1, the limiting factor is no longer finding the
origin but the rate of flags on healthy runs: 44% of clean steps, 4/4 clean
chains. At that rate a team stops reading the flags, and the attribution accuracy
becomes irrelevant.

Two measured causes, each with a concrete fix:

**Paraphrase is scored as incompleteness.** A faithful extractor scores only 0.54
mean coverage. The NLI model under-scores entailment when a step restates a fact
in different words rather than quoting it, which directly produces the omission
flags on `organic-13` and `organic-20`, both annotated clean. Fact-level coverage
is measuring paraphrase distance as much as completeness. Claim-level extraction
before entailment scoring, rather than sentence-level hypotheses, is the
principled fix.

**Condensing roles legitimately shed coverage.** Mean anchor-fact coverage by
role: extractor 0.54, analyst 0.45, reasoner 0.06, writer 0.04. A writer that
compresses four sentences into one has not omitted anything; it has done its job.

The second cause produced our clearest negative result. Suppressing the
completeness flag on writer and reasoner steps changed the false-positive rate by
zero percentage points, because forward entailment already flags those steps for
the same underlying reason. Role-aware thresholds, which we had proposed as a
fix for entailment alone, only pay off if applied across both signals at once.
Testing the fix on one signal in isolation would have shown a benefit that does
not exist.

### 3.4 Limitations

1. **Provisional labels.** The organic figures rest on one machine-assisted
   annotation pass. The two-annotator round is prepared but unfinished; until
   kappa exists, label reliability is asserted rather than measured.
2. **Small clean set.** Four clean chains stand behind every false-positive
   figure. One chain is 25 percentage points.
3. **Tuning and evaluation share a set.** The threshold sweep and the reported
   accuracies come from the same 28 chains. Defaults were deliberately not moved
   to the sweep optimum for this reason, but the reported accuracies are still
   optimistic.
4. **One generator model.** All 28 chains come from `qwen2.5:3b` at temperature
   0.8, in one four-agent topology. The failure-mode distribution in Section 2.1
   describes that configuration, not agent pipelines in general.
5. **Anchor required.** The completeness signal needs a ground-truth document.
   Pipelines with no retrievable source get no coverage signal at all.
6. **Cost not re-measured.** Coverage scores `steps x facts` NLI pairs against
   `steps - 1` for the forward check, so NLI work grows with source length. The
   FR-11 latency budget has not been re-measured with the signal enabled.
7. **Misread is unaddressed.** The dominant failure mode at N=28 has no dedicated
   signal. Coverage cannot see it: a step that inverts a rule still entails it.

### 3.5 What we would do next

Ranked by measured value rather than novelty:

1. **Precision before capability.** 44% step-level false positives is the number
   that decides whether anyone keeps the tool installed. Two-consecutive-flag
   verdicts and p99 calibration are the cheapest levers.
2. **Claim-level hypotheses.** Replacing sentence-level anchor facts with
   extracted claims addresses both the paraphrase problem and the arithmetic
   blindness documented for the forward check.
3. **A consistency signal for misread.** The largest failure mode is currently
   detected only by accident, when the misapplied rule happens to produce a
   contradiction downstream.
4. **A disjoint organic set.** Every remaining threshold question is blocked on
   having chains that were not used for tuning.

---

## Reproducing every number in this section

```
python validation/annotation/prepare.py       # split, forms, review sheet
python validation/annotation/summarize.py     # Section 2.1 distributions
python validation/annotation/kappa.py         # Section 1.2 (pending human round)
python validation/measure_omission.py         # Section 2.2 attribution table
python validation/measure_fpr.py              # Section 2.3 false positives
python validation/sweep_omission.py           # Section 2.4 sweep
python validation/sweep_verdict.py --refresh  # Section 2.5 verdict triggers
python validation/export_hf_dataset.py        # rebuild the published dataset
python -m pytest tests/                       # full suite; needs the two models
```

The fake-model subset runs without any download and covers the verdict rule:

```
python -m pytest tests/ --ignore=tests/test_e2e.py --ignore=tests/test_e2e_full.py \
                        --ignore=tests/test_embedding.py --ignore=tests/test_entailment.py
# 103 passed, 1 skipped (12 of those pin the reworked verdict rule)
```
