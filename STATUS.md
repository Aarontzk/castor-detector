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

89/89 green (80 unit with fake models, 9 integration/e2e with real mpnet + NLI).

## Validation headlines (docs/VALIDATION.md)

Synthetic set (30 clean + 150 injected):

- Detection 55% (target 70% — semantic-shift kinds hit 73%; token-level fabrication ~29% is an architectural boundary, claim-level verification is v1 per PRD H-06)
- FPR 27% calibrated (target 20%); **default CHARM thresholds: 93% FPR — calibration is mandatory**, README warns
- Attribution ±1: 84% (target 50% ✓) · Classification: 69% ✓ · Latency 316ms/step CPU ✓ · Naive baseline 10% — beaten 5× ✓

Organic set, extended to N=28 on 2026-08-07 (all labels annotated, `validation/annotation/`):

- 24/28 chains cascaded, 4 clean. Origin attribution with the omission signal: **50% exact, 96% within-1** (25%/75% without it)
- Dominant failure mode is **misread** (11/24), not omission (9/24) — the N=8 "omission dominates" claim did not survive the larger sample
- First organic FPR measurable: **4/4 clean chains flagged**, 31% of clean steps before the omission signal and 44% after
- Trajectory-level verdict still fires on 0/28 — item 3 below

Caveat: organic labels are currently a single machine-assisted pass. The two-annotator round (10 overlap for Cohen's kappa, 18 split) is prepared but not yet run.

## Open items (owner decisions)

- ~~PyPI name~~ — resolved: `castor-detector` (owner, 2026-07-03); import name stays `castor`
- ~~Publish to GitHub~~ — done 2026-07-03: https://github.com/Aarontzk/castor-detector (public, CI + release workflows active)
- PyPI publish — ONE owner step left: add trusted publisher on pypi.org (project `castor-detector`, owner `Aarontzk`, repo `castor-detector`, workflow `release.yml`, environment `pypi`), then `git tag v0.1.0 && git push --tags`
- v1 candidates from validation (priority order, evidence in docs/VALIDATION.md):
  1. ~~Omission/completeness signal~~ — SHIPPED 2026-08-07 (`src/castor/omission.py`, reverse-entailment coverage, no training). Origin attribution on the organic set: exact 25%→50%, within-1 75%→96%; on omission-labelled chains 0%→56% exact. Cost: step-level FPR on clean chains 31%→44%. Still open from this item: the `omission` injection kind in FR-10 (synthetic toolkit still has no omission generator)
  2. Claim-level numeric verification — NLI blind to arithmetic (entail 0.83–0.99 on wrong/fabricated numbers)
  3. Verdict rule rework — per-signal triggers (entailment collapse), not aggregate-only; synthetic-calibrated θ fired on 0/28 organic cascades that per-step flags caught
  4. p99 calibration or 2-consecutive-flags — now the top-value item: organic step-level FPR is 31% before the omission signal and 44% after, and 4/4 clean organic chains trip a flag
  5. Multilingual embedder preset for ID pipelines (ID→EN code-switch read as 0.73 drift)
  6. Role-aware thresholds — must cover entailment AND omission together. Measured: suppressing omission alone on writer/reasoner changed false positives by 0pp, because forward entailment already flags those steps. Coverage by role: extractor 0.54, analyst 0.45, reasoner 0.06, writer 0.04
  7. Fact-level coverage measures paraphrase distance as much as completeness — a faithful extractor scores only 0.54 mean coverage, which is what drives the omission false positives on clean chains

## Examples added (owner requests, not core Castor features)

- `examples/delegate_to_ollama.py` — Claude-as-orchestrator delegates to local qwen via Ollama's Anthropic-compatible endpoint; CastorObserver watches live
- `examples/self_healing_chain.py` — orchestrator-side retry loop using Castor's flags (re-grounds worker in clean facts, max 1 retry, reports "unresolved" honestly if still flagged). Castor itself stays passive per CLAUDE.md hard rule; this loop lives entirely outside it
