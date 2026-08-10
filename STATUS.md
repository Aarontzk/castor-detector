# STATUS

**All phases 1–5 implemented (2026-07-03). Awaiting owner review before publish.**

## Phase Map

| Phase | Scope | Status |
|---|---|---|
| 0 | Env setup, test trajectories | done |
| 1 | Drift core: FR-1, FR-2, FR-3, FR-5 subset, FR-12 | done — DoD met (canonical fixture: step 3 highest drift) |
| 2 | Taxonomy: FR-4, FR-6 | done — DoD met: 69% classification accuracy on injected set (target 60–70%) |
| 3 | Attribution + reporting: FR-7, FR-8 | done — DoD met: structured output with `method` + `confidence` fields |
| 4 | Validation + injection: FR-10, PRD S12 | done — synthetic (30 clean + 150 injected) AND semi-natural organic (8 Ollama qwen2.5:3b chains, 8/8 cascaded, first flag ±1 of origin in 8/8). See docs/VALIDATION.md |
| 5 | Packaging, adapters, CLI: FR-9, FR-11 | code done (observer API, LangChain callback, CLI, entry point). NOT done: GitHub/PyPI publish, external-tester <15min check — needs owner |

## Test suite

103 passed / 1 skipped on the fake-model suite (includes `tests/test_verdict.py`,
12 tests pinning the reworked verdict rule). The 4 model-backed files
(`test_e2e`, `test_e2e_full`, `test_embedding`, `test_entailment`) and 3 tests in
`test_cli` need the real mpnet + NLI models and were **not run** in the last
session — the environment could not download them. They failed identically on
unmodified code under `HF_HUB_OFFLINE=1`, so they are environment-blocked, not
regressions. Re-run the full suite on a machine with model access before release:

```
pytest                                   # expect the model-backed tests to pass
python validation/sweep_verdict.py --refresh   # fills in the unmeasured verdict levels
```

## Validation headlines (docs/VALIDATION.md)

Synthetic set (30 clean + 150 injected):

- Detection 55% (target 70% — semantic-shift kinds hit 73%; token-level fabrication ~29% is an architectural boundary, claim-level verification is v1 per PRD H-06)
- FPR 27% calibrated (target 20%); **default CHARM thresholds: 93% FPR — calibration is mandatory**, README warns
- Attribution ±1: 84% (target 50% ✓) · Classification: 69% ✓ · Latency 316ms/step CPU ✓ · Naive baseline 10% — beaten 5× ✓

Organic set, extended to N=28 on 2026-08-07 (all labels annotated, `validation/annotation/`):

- 24/28 chains cascaded, 4 clean. Origin attribution with the omission signal, scored against the resolved human labels: **54% exact, 96% within-1** (29%/75% without it)
- Dominant failure mode is **misread** (11/24), not omission (8/24) — the N=8 "omission dominates" claim did not survive the larger sample
- First organic FPR measurable: **4/4 clean chains flagged**, 31% of clean steps before the omission signal and 44% after
- Trajectory-level verdict fired on 0/28 under the old aggregate-only rule. The rule was reworked 2026-08-08 (item 3 below); the replacement's recall is **not yet measured** — run `validation/sweep_verdict.py --refresh` before quoting a number anywhere

Annotation COMPLETE (2026-08-10): both annotators finished 19/19. All 28 organic chains now carry a human label. **Human-vs-human Cohen's kappa on the 10 overlap chains: `origin_step` 0.844 (9/10 exact), `error_type` 0.589 (7/10), `cascade_occurred` 9/10.** Error-type kappa is below the 0.6 threshold set in advance and is reported as measured — annotators agree on *where* a chain broke far more than on *what to call* the error, which puts a noise ceiling on classification accuracy. Three disagreements, all substantive: `organic-04` and `organic-12` (error type only, same origin step) and `organic-26`, which exposed a real gap in the scheme — it defines cascade as deviation from the source, but that chain deviates without changing the final answer.

## Open items (owner decisions)

- ~~PyPI name~~ — resolved: `castor-detector` (owner, 2026-07-03); import name stays `castor`
- ~~Publish to GitHub~~ — done 2026-07-03: https://github.com/Aarontzk/castor-detector (public, CI + release workflows active)
- PyPI publish — ONE owner step left: add trusted publisher on pypi.org (project `castor-detector`, owner `Aarontzk`, repo `castor-detector`, workflow `release.yml`, environment `pypi`), then `git tag v0.1.0 && git push --tags`
- Hugging Face dataset — **built and ready to upload**, needs owner account. `python validation/export_hf_dataset.py` writes `hf-dataset/` (clean 30 / injected 150 / organic 28 JSONL + dataset card). Upload: `huggingface-cli upload <user>/castor-cascade-benchmark hf-dataset . --repo-type=dataset`
- Video demo — script written (`docs/DEMO_SCRIPT.md`, shot-by-shot with commands, timings and fallbacks). Recording is an owner step
- v1 candidates from validation (priority order, evidence in docs/VALIDATION.md):
  1. ~~Omission/completeness signal~~ — SHIPPED 2026-08-07 (`src/castor/omission.py`, reverse-entailment coverage, no training). Origin attribution on the organic set: exact 25%→50%, within-1 75%→96%; on omission-labelled chains 0%→56% exact. Cost: step-level FPR on clean chains 31%→44%. Still open from this item: the `omission` injection kind in FR-10 (synthetic toolkit still has no omission generator)
  2. Claim-level numeric verification — NLI blind to arithmetic (entail 0.83–0.99 on wrong/fabricated numbers)
  3. ~~Verdict rule rework~~ — SHIPPED 2026-08-08 (structure), partially measured. Aggregate-only → disjunction: aggregate OR entailment collapse OR anchor-drift collapse, each individually disableable, plus `CascadeReport.verdict_reasons` naming the trigger and step. Strict superset of the old rule, so recall cannot fall. **Measured:** omission is *not* a usable verdict trigger — the 4 clean chains' max omission (0.67/0.67/0.75/1.00) sits at the top of the cascaded range, so it ships disabled (`omission_collapse=None`). Also measured: "any per-step flag" = 24/24 recall but 4/4 chain FPR, which bounds what any threshold rule can do on this set. **NOT measured:** the `entail_collapse` (0.01) and `drift_collapse` (0.9) levels are reasoned starting points — `validation/sweep_verdict.py --refresh` is written and ready but has not been run (model download failed in the authoring environment). Run it before quoting any verdict recall number
  4. p99 calibration or 2-consecutive-flags — now the top-value item: organic step-level FPR is 31% before the omission signal and 44% after, and 4/4 clean organic chains trip a flag
  5. Multilingual embedder preset for ID pipelines (ID→EN code-switch read as 0.73 drift)
  6. Role-aware thresholds — must cover entailment AND omission together. Measured: suppressing omission alone on writer/reasoner changed false positives by 0pp, because forward entailment already flags those steps. Coverage by role: extractor 0.54, analyst 0.45, reasoner 0.06, writer 0.04
  7. Fact-level coverage measures paraphrase distance as much as completeness — a faithful extractor scores only 0.54 mean coverage, which is what drives the omission false positives on clean chains

## Examples added (owner requests, not core Castor features)

- `examples/delegate_to_ollama.py` — Claude-as-orchestrator delegates to local qwen via Ollama's Anthropic-compatible endpoint; CastorObserver watches live
- `examples/self_healing_chain.py` — orchestrator-side retry loop using Castor's flags (re-grounds worker in clean facts, max 1 retry, reports "unresolved" honestly if still flagged). Castor itself stays passive per CLAUDE.md hard rule; this loop lives entirely outside it
