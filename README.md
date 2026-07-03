# Castor

**Castor tells you WHERE your agent chain started hallucinating — not just that it did.**

Open-source observability & attribution layer for multi-agent LLM systems. Detects **hallucination cascades** — small errors in one step that propagate and amplify through subsequent steps while passing every per-step check.

- **Detect** — dual-reference semantic drift (previous step + anchor) and NLI transition validity
- **Classify** — 4 cascade types (Retrieval, Inference, Context Poisoning, Confidence Inflation)
- **Attribute** — candidate origin step, threshold-based, with honest confidence (never causal proof)

100% local and free: sentence-transformers + a local NLI cross-encoder. No paid APIs. Passive observer — never modifies, blocks, or crashes your pipeline.

## Quick start

```python
from castor import CascadeAnalyzer

steps = [
    {"step_id": 1, "agent_name": "retriever", "text": "Revenue grew ten percent last quarter."},
    {"step_id": 2, "agent_name": "analyst",   "text": "Growth came mostly from the new subscription plan."},
    {"step_id": 3, "agent_name": "reasoner",  "text": "Therefore the office coffee machine drives our success."},
    {"step_id": 4, "agent_name": "writer",    "text": "The company ended the quarter in a strong position."},
]

report = CascadeAnalyzer().analyze(steps)
print(report.to_text())          # human-readable
report.to_json()                 # machine-readable, for CI
```

Models (~1.2 GB total) download automatically on first use. Drift-only mode (no NLI, faster): `CascadeAnalyzer(entailment=False)`.

## Live observation (passive, non-blocking)

```python
from castor import CastorObserver

observer = CastorObserver(on_flag=lambda d: print(f"drift at step {d.step_id}"))
observer.observe({"step_id": 1, "text": "..."})   # call after each pipeline step
report = observer.report()
```

## LangChain

```python
from castor.integrations.langchain import CastorCallbackHandler

handler = CastorCallbackHandler()
chain.invoke(inputs, config={"callbacks": [handler]})
print(handler.observer.report().to_text())
```

## CLI

```
castor analyze trajectory.json            # exit 1 if cascade detected (CI-friendly)
castor analyze trajectory.json --no-nli --json-out report.json
castor calibrate ./clean_runs --save profile.json   # per-domain thresholds (recommended!)
castor analyze trajectory.json --profile profile.json
```

## Build regression suites with error injection

```python
from castor import inject, Trajectory

corrupted, record = inject(clean_trajectory, "causal_leap", seed=42)
# record.step_index is your ground-truth origin — assert Castor finds it
```

Kinds: `numeric_fabrication`, `entity_distortion`, `causal_leap`, `certainty_inflation`, `context_swap`.

## Honest limitations (read before trusting the output)

- **Attribution is threshold-based candidate identification, not causal inference.** Every attribution carries `method: "threshold-based"` and a confidence score.
- **Default thresholds are starting points** (inherited from CHARM research). Raw cosine distances vary a lot by domain — run `castor calibrate` on your own clean trajectories before relying on flags. See `docs/VALIDATION.md`.
- **Aggregator weights (0.4/0.4/0.2) are manual defaults**, not learned values.
- **Confidence-language tracking is lexicon-based (EN+ID)** and brittle across writing styles — it is a secondary signal only.
- Adversarial/prompt-injection defense is permanently out of scope (see CASPIAN / LLM Guard for that).

## Development

```
pip install -e ".[dev]"
pytest                                   # full suite (downloads models on first run)
python validation/run_validation.py      # metrics + ablation (PRD Section 12)
```

Spec: `castor-prd.md`. Status: `STATUS.md`. License: MIT.
