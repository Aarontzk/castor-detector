# Castor

**Castor tells you WHERE your agent chain started hallucinating — not just that it did.**

Your multi-agent pipeline gave a confident wrong answer. Every per-step check passed. Somewhere in the middle, one agent made a small mistake — and every agent after it treated that mistake as trusted context. Standard detectors can't see this: cascade output is *locally coherent* at every step. Coherent with a poisoned premise.

Castor is a passive observability layer that tracks the whole trajectory and points at the step where it broke.

```
step 1  extractor  ✓
step 2  analyst    ✗ ← cascade origin: entailment 0.003, "3 buses" is not entailed by the facts
step 3  reasoner   ✗   (propagating step 2's fabrication)
step 4  writer     ✓-looking, confidently wrong
```

100% local and free (sentence-transformers + local NLI cross-encoder — no paid APIs). Passive by design: it never modifies, blocks, or crashes your pipeline. If Castor itself fails, your pipeline doesn't.

## What you do with the origin step

Knowing *where* and *what type* turns "my AI is flaky" into a one-line fix:

| Castor says | You fix | You don't touch |
|---|---|---|
| Origin = retrieval step, Retrieval Cascade | your retriever / data source | any reasoning prompt |
| Origin = analyst, entailment collapse | that one agent's prompt, or its model | everything else |
| Origin = extractor, facts dropped | the extraction prompt | the whole downstream |
| Certainty rising with no new evidence | the handoff format between agents | the models |

In our organic validation (28 real local-LLM chains, 24 of which cascaded), the dominant origin was a *misread* — a step that keeps the source fact and inverts what it means (12/24, 50%), ahead of silent omission (9/24, 38%). Castor puts the first flag within one step of the annotated origin on 23 of 24 chains, so the fix lands on one prompt instead of four.

## The ladder: from debugging to auto-healing

**1. Post-mortem debugging** — hours of log-reading becomes minutes:
```python
from castor import CascadeAnalyzer
report = CascadeAnalyzer().analyze(steps)   # list of {"step_id", "text", "agent_name", ...}
print(report.to_text())                     # verdict, per-step signals, origin candidates
```

**2. CI regression gate** — block merges that make reliability worse:
```
castor analyze trajectory.json    # exit 1 if cascade detected → fails the build
castor analyze run.json --json-out report.json   # machine-readable for dashboards
```
Build regression suites with the built-in error injector (`castor.inject`, 5 error kinds, seeded).

**3. Per-role cost optimization** — Castor's per-step data shows *which agent role* is the weak link. Upgrade that one role's model; keep the cheap model everywhere else.

**4. Self-healing (pattern, 30 lines)** — detection → automatic repair, *outside* Castor:
[`examples/self_healing_chain.py`](examples/self_healing_chain.py) — the orchestrator reads Castor's flag, re-runs **only the poisoned step** with clean grounding (one extra LLM call instead of a full re-run), keeps the original + reports honestly if the retry is still flagged. Live demo output:
```
[analyst] attempt 1 FLAGGED: entailment 0.010 < threshold 0.72
[analyst] healed (attempt 2): ... operating profit Q1 $230,000, Q2 $210,000 ...
```
Why isn't this a built-in API? Honesty: our measured false-positive rate (27%) is not yet low enough to auto-retry your pipeline's steps behind your back. The pattern is yours to copy today; the API ships in v1 once FPR is where it should be. Castor v0.x never touches your pipeline.

## Install

```
pip install castor-detector        # you still `import castor`
```
Models (~1.2 GB) download on first use. Drift-only mode (no NLI, 73% faster): `CascadeAnalyzer(entailment=False)`.

## Live observation (passive, non-blocking)

```python
from castor import CastorObserver

observer = CastorObserver(on_flag=lambda d: print(f"drift at step {d.step_id}"))
observer.observe({"step_id": 1, "text": "..."})   # after each pipeline step
report = observer.report()
```
`async_mode=True` cuts host-thread blocking to ~0.08 ms/step (see `docs/BENCHMARK.md`).

## LangChain

```python
from castor.integrations.langchain import CastorCallbackHandler

handler = CastorCallbackHandler()
chain.invoke(inputs, config={"callbacks": [handler]})
print(handler.observer.report().to_text())
```

## Local / heterogeneous chains (Ollama)

[`examples/delegate_to_ollama.py`](examples/delegate_to_ollama.py) — a strong orchestrator delegates to cheap local workers via Ollama's Anthropic-compatible endpoint while Castor watches every handoff. In our runs it caught a real numeric fabrication ($215k vs the correct $210k) at the exact step it entered.

## Calibrate before you trust it (required, 2 minutes)

```
castor calibrate ./clean_runs --save profile.json
castor analyze trajectory.json --profile profile.json
```
The research-inherited defaults flagged 93% of clean trajectories in our validation — raw drift scales vary hugely by domain. Calibration on ~15 of your own clean runs fixes this. Full numbers: [`docs/VALIDATION.md`](docs/VALIDATION.md).

## Honest limitations (read before trusting the output)

- **Attribution is threshold-based candidate identification, not causal proof.** Every attribution carries `method: "threshold-based"` + a confidence score.
- **Small token-level fabrications (a wrong number, a swapped name) mostly evade embedding drift** (~29% detection) — claim-level verification is the #1 v1 item. Semantic-shift cascades detect at ~73%.
- **Extraction omission** — an agent silently dropping a key fact — is invisible to drift and forward entailment by construction. The reverse-entailment completeness signal now ships (`src/castor/omission.py`): it doubles exact-origin accuracy on the organic set (25% → 50%, within-1 75% → 96%) and adds no detection, only attribution. It costs precision: step-level false positives on clean chains rise 31% → 44%.
- **Fact-level coverage measures paraphrase distance as much as completeness.** A faithful extractor that paraphrases instead of quoting scores only 0.54 mean coverage, which is what drives most omission false positives.
- Aggregator weights are manual defaults from the CHARM paper, not learned. Confidence-language tracking is lexicon-based (EN+ID), secondary only.
- **The trajectory-level verdict is the weakest part of the system.** It is a disjunction over per-signal triggers (`report.verdict_reasons` names which one fired), replacing an aggregate-only rule that returned "no cascade" on 24/24 real cascades. Two of its trigger levels are still uncalibrated starting points. And on our organic set *every* clean chain trips at least one per-step flag, so no threshold over the current signals cleanly separates broken trajectories from healthy ones. Trust the per-step output and the origin candidate before you trust the boolean.
- Adversarial/prompt-injection defense is permanently out of scope (see CASPIAN / LLM Guard).

## Development

```
pip install -e ".[dev]"
pytest                                   # model-based tests download ~1.2 GB on first run
python validation/run_validation.py      # synthetic metrics + ablation
python validation/agent_chain.py         # generate organic trajectories via Ollama
python validation/sweep_verdict.py       # verdict-trigger sweep (cached after one pass)
python validation/export_hf_dataset.py   # rebuild the published benchmark dataset
```

No network? The fake-model suite covers everything except the two model
integrations:

```
pytest --ignore=tests/test_e2e.py --ignore=tests/test_e2e_full.py \
       --ignore=tests/test_embedding.py --ignore=tests/test_entailment.py
```

Spec: `castor-prd.md` · Status: `STATUS.md` · Validation: `docs/VALIDATION.md` · Benchmark: `docs/BENCHMARK.md` · License: MIT
