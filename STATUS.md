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

- Detection 55% (target 70% — semantic-shift kinds hit 73%; token-level fabrication ~29% is an architectural boundary, claim-level verification is v1 per PRD H-06)
- FPR 27% calibrated (target 20%); **default CHARM thresholds: 93% FPR — calibration is mandatory**, README warns
- Attribution ±1: 84% (target 50% ✓) · Classification: 69% ✓ · Latency 316ms/step CPU ✓ · Naive baseline 10% — beaten 5× ✓

## Open items (owner decisions)

- ~~PyPI name~~ — resolved: `castor-detector` (owner, 2026-07-03); import name stays `castor`
- ~~Publish to GitHub~~ — done 2026-07-03: https://github.com/Aarontzk/castor-detector (public, CI + release workflows active)
- PyPI publish — ONE owner step left: add trusted publisher on pypi.org (project `castor-detector`, owner `Aarontzk`, repo `castor-detector`, workflow `release.yml`, environment `pypi`), then `git tag v0.1.0 && git push --tags`
- v1 candidates from validation (priority order, evidence in docs/VALIDATION.md):
  1. Omission/completeness signal — dominant organic failure mode (5/8 origins), invisible to drift+NLI; add reverse-entailment coverage check + `omission` injection kind in FR-10
  2. Claim-level numeric verification — NLI blind to arithmetic (entail 0.83–0.99 on wrong/fabricated numbers)
  3. Verdict rule rework — per-signal triggers (entailment collapse), not aggregate-only; synthetic-calibrated θ missed 8/8 organic cascades that per-step flags caught
  4. p99 calibration or 2-consecutive-flags (synthetic FPR 27%)
  5. Multilingual embedder preset for ID pipelines (ID→EN code-switch read as 0.73 drift)
  6. Role-aware entailment thresholds — summarization/condensing steps trip the same threshold as reasoning steps (found while building examples/self_healing_chain.py)

## Examples added (owner requests, not core Castor features)

- `examples/delegate_to_ollama.py` — Claude-as-orchestrator delegates to local qwen via Ollama's Anthropic-compatible endpoint; CastorObserver watches live
- `examples/self_healing_chain.py` — orchestrator-side retry loop using Castor's flags (re-grounds worker in clean facts, max 1 retry, reports "unresolved" honestly if still flagged). Castor itself stays passive per CLAUDE.md hard rule; this loop lives entirely outside it
