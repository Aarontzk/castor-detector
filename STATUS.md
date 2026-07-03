# STATUS

**All phases 1–5 implemented (2026-07-03). Awaiting owner review before publish.**

## Phase Map

| Phase | Scope | Status |
|---|---|---|
| 0 | Env setup, test trajectories | done |
| 1 | Drift core: FR-1, FR-2, FR-3, FR-5 subset, FR-12 | done — DoD met (canonical fixture: step 3 highest drift) |
| 2 | Taxonomy: FR-4, FR-6 | done — DoD met: 69% classification accuracy on injected set (target 60–70%) |
| 3 | Attribution + reporting: FR-7, FR-8 | done — DoD met: structured output with `method` + `confidence` fields |
| 4 | Validation + injection: FR-10, PRD S12 | done at PRD-minimum scale — see docs/VALIDATION.md; semi-natural (Ollama) set NOT run (Ollama absent) |
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
- v1 candidates from validation: p99 calibration or 2-consecutive-flags verdict (FPR); aggregate-vs-max (context_swap dilution); claim-level decomposition (numeric/entity); semi-natural Ollama dataset
