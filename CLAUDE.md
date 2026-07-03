# CLAUDE.md — Castor

This file is read by Claude Code at the start of every session. It is the operational guide for working on this repository. The full specification lives in `castor-prd.md` (single source of truth). When this file and the PRD conflict, the PRD wins. When anything is ambiguous, ask the owner — do not assume.

## Project Overview

Castor is an open-source **observability & attribution layer** for multi-agent LLM systems. It detects **hallucination cascades** — small errors in one step that propagate and amplify through subsequent steps while passing every per-step check.

Castor does three things: **detect** (semantic drift, dual-reference), **classify** (4 cascade types from CHARM taxonomy), **attribute** (candidate origin step, threshold-based, with honest confidence).

Castor is NOT: a hallucination preventer, a security/adversarial tool, a guardrail that blocks output, or a causal-proof engine.

Tagline: *"Castor tells you WHERE your agent chain started hallucinating — not just that it did."*

## Hard Rules (never violate)

1. **Passive observer.** Castor never modifies, blocks, or delays the user's pipeline in v0.x. Detection reports only.
2. **Never crash the host pipeline.** All internal exceptions must be caught and reported as monitoring failures (PRD FR-12). A bug in Castor must never take down the user's system.
3. **Zero paid API dependencies.** All models run locally (sentence-transformers, cross-encoder NLI). If a feature seems to need a paid API, stop and ask.
4. **Honest attribution.** Attribution output must always include `method: "threshold-based"` and a confidence score. Never present attribution as causal proof.
5. **Stay in phase.** Only implement the phase the owner has explicitly approved. Do not implement future-phase features "while you're at it." Current phase is tracked in `STATUS.md` (create it if missing).
6. **Multimodal-ready data model, text-only measurement.** Trajectory steps carry `modality` and `raw_ref` fields from day one (PRD FR-1), but drift measurement in v0.x is text-only. Do not add multimodal embedding logic in v0.x.
7. **Configurable thresholds.** Never hardcode thresholds inline. Defaults live in one config location: `δ_drift = 0.18`, `τ_entail = 0.72` (starting points from CHARM, expected to be recalibrated).

## Architecture (module boundaries)

```
Ingestion (Python API / callback / CLI)
  → Trajectory Store (all steps + cached embeddings)
    → Drift Tracker (dual-reference: prev + anchor)
    → Entailment Checker (NLI, phase 2+)
    → Confidence-Language Tracker (hedging words, phase 2+)
  → Aggregator (configurable weights, defaults from CHARM)
    → Taxonomy Classifier (phase 2+)
    → Origin Attribution (phase 3+)
  → Report (JSON + human-readable)
```

Every box is a module behind an interface. Modules must be replaceable without touching others (research foundations are new and may be revised). The `Embedder` interface must stay pluggable — users may swap in multilingual models.

## Phase Map (see PRD Section 15 for full definitions of done)

| Phase | Scope | FRs |
|---|---|---|
| 0 | Env setup, test trajectories | — |
| 1 | Drift core (CURRENT unless STATUS.md says otherwise) | FR-1, FR-2, FR-3, FR-5 subset, FR-12 |
| 2 | Taxonomy classification | FR-4, FR-6 |
| 3 | Attribution + reporting | FR-7, FR-8 |
| 4 | Validation + error injection toolkit | FR-10, PRD Section 12 |
| 5 | Packaging, LangChain adapter, CLI, publish | FR-9, FR-11 |

## Tech Stack (fixed unless owner approves change)

- Python 3.10+, src layout, `pyproject.toml`, pytest
- Embeddings: `sentence-transformers` / `all-mpnet-base-v2` (behind `Embedder` interface)
- NLI (phase 2+): `cross-encoder/nli-deberta-v3-base`
- Numerics: numpy only — avoid heavy dependencies
- Local LLM for test simulation only: Ollama (qwen2.5-coder / phi4-mini)
- License: MIT

## Coding Conventions

- Type hints everywhere; dataclasses (or pydantic if justified — ask first) for data models
- Every public function gets a docstring stating what it does and which FR it implements (e.g., `# FR-3`)
- Embeddings are computed once per step and cached — never recompute inside loops
- No global state; a `CastorObserver` instance owns its trajectory
- Keep functions small; prefer composition over inheritance
- English for code/comments/docs; test fixture texts may be Indonesian or English (drift logic must work for both — do not bake English-only assumptions into logic; the hedging-word lexicon in phase 2 is explicitly bilingual EN+ID)

## Testing Requirements

- Every FR implemented gets unit tests + at least one integration test
- Canonical end-to-end fixture: a 5-step trajectory where step 3 makes a deliberate logical leap; the test passes iff step 3 receives the highest drift flag
- Error-handling tests are mandatory: empty step, non-text step, model load failure (must degrade with explicit warning, not crash — FR-12)
- Run `pytest` before declaring any task complete; report results honestly, including failures

## Workflow Protocol

1. At session start: read `STATUS.md` for current phase and open tasks. If it doesn't exist, create it from the Phase Map above with phase 1 active.
2. Before writing code for any task: state briefly which FR(s) it implements. If the task maps to no FR, stop and ask.
3. After completing a task: run tests, update `STATUS.md`, then **stop and wait for confirmation**. Do not chain into the next phase autonomously.
4. When a design decision isn't covered by the PRD: list the options with trade-offs and ask. Log resolved decisions in `DECISIONS.md` (one line each: date, decision, reason).
5. Never mark a phase done unless its Definition of Done (PRD Section 15) is demonstrably met.

## Known Limitations to Preserve in Docs (do not paper over)

- Aggregator weights (0.4/0.4/0.2) are inherited from CHARM as reasonable manual defaults, not learned values — documented as a known limitation
- Default thresholds are starting points; real domains require `castor calibrate` (single global thresholds are unfair across task types)
- LLM self-reported confidence is unreliable (CPM standalone ≈38% detection in CHARM) — confidence signals are secondary only, never a primary gate
- Attribution is threshold-based candidate identification, not causal inference

## Out of Scope — Reject and Flag if Requested Casually

Adversarial/prompt-injection defense (H-20, permanently out), active blocking (v1 opt-in at earliest), transfer entropy (v2), cross-modal drift measurement (v2), dashboards (v1/v2), non-linear agent topologies (v2). If the owner asks for these, point to PRD Section 8 non-goals and confirm they want to change scope before proceeding.
