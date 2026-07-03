# DECISIONS

- 2026-07-02 — "Highest drift" ranking uses mean(drift_prev, drift_anchor). Reason: dual reference separates the leap step (high on both) from the step after it that returns to course (high prev, low anchor). This is a ranking convenience only, NOT the CHARM weighted aggregator (that arrives with phase 2 signals).
- 2026-07-02 — Anchor override accepts a text or a list of texts (consensus = mean embedding, per FR-3). Index-based override skipped: the PRD's use case (anchor = source document, H-02) is text.
- 2026-07-02 — Malformed steps at ingestion (missing text, non-string text, garbage payloads) are recorded as notes and skipped in measurement, never raised (FR-12). `Trajectory.from_json` on an explicitly bad file DOES raise ValueError — it is a direct user call, not the observation hot path.
- 2026-07-02 — stdlib dataclasses (frozen) for data models, not pydantic (CLAUDE.md default; pydantic needs owner approval).
- 2026-07-02 — Local package/dist name stays `castor`; PyPI availability check deferred to phase 5 (PRD open question 3).
- 2026-07-03 — Owner approved finishing all remaining phases in one pass ("sekalian semua selesaiin").
- 2026-07-03 — Verdict rule = any step's aggregate > θ. Aggregate renormalises weights when a signal is missing (NLI degraded), keeping the [0,1] scale.
- 2026-07-03 — Observer hot path runs drift-only flagging; NLI runs once in report() (215ms+/transition too heavy per-step on CPU; FR-11 <500ms/step kept: 316ms measured including NLI at report time).
- 2026-07-03 — Classifier returns best single type when verdict=true but no type clears the multi-label cutoff — report never silently empty on a flagged run.
- 2026-07-03 — Injection never targets step index 0: anchor must stay clean or the injected error is unmeasurable by definition.
- 2026-07-03 — Validation calibration = p95 per signal on a 15-trajectory calibration split; FPR on 15 held-out. p99/2-consecutive-flags deferred to v1 to avoid double-fitting the same small dataset.
- 2026-07-03 — CLI exit codes: 0 clean, 1 cascade, 2 monitoring failure (CI-friendly, UC-3/V5).
- 2026-07-03 — Semi-natural Ollama dataset (PRD S12.2) skipped: Ollama not installed on dev machine. Logged in STATUS as open item, not silently dropped.
- 2026-07-03 — PyPI distribution name = `castor-detector` (owner decision, PRD S16.3 resolved). Import name stays `castor`; CLI stays `castor`.
- 2026-07-03 — Organic validation model = qwen2.5:3b (installed on owner machine), not PRD's qwen2.5-coder/phi4-mini. Deviation accepted: small general model is more hallucination-prone, better for capturing organic cascades.
- 2026-07-03 — Organic chain design: 4 agents with information bottleneck (each sees only previous output, source doc withheld downstream); anchor override = source doc. Reproduces H-05/H-10 organically — 8/8 runs cascaded without injection.
- 2026-07-04 — Self-healing stays an EXAMPLE in v0.x, not an API (owner + Claude aligned on option A). Reasons: FPR 27% means auto-retry would fire on 1-in-4 healthy runs; writer-role false flags observed in the demo itself; "passive = zero-risk install" is the v0.1 adoption argument. Healing API ships in v1 once FPR is down (p99/2-flag verdict, role-aware entailment thresholds). README now sells the 4-rung value ladder with the healing pattern as copyable example.
- 2026-07-03 — `castor-prd.md` untracked from the public GitHub repo (owner call: internal spec docs don't belong in a public repo). File stays on disk and `.gitignore`d going forward; still the single source of truth locally per CLAUDE.md, just no longer pushed. Not scrubbed from prior git history — only removed going forward.
