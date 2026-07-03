# Benchmark — Castor v0.1 (FR-11)

**Date:** 2026-07-03 · **Hardware:** consumer laptop CPU (no GPU), Windows
**Method:** 20-step trajectory from the validation clean set, median of 3 runs
**Reproduce:** `python validation/benchmark.py` (numbers are hardware-dependent)

## Per-step latency

| Configuration | ms/step | Reduction |
|---|---:|---:|
| Full pipeline (drift + NLI + classify + attribute) | 68.7 | baseline |
| Drift-only (`entailment=False`) | 18.4 | **−73%** |
| Drift-only + MiniLM embedder | 4.3 | **−94%** |

All well under the FR-11 target of <500 ms/step. (The validation run reported 316 ms/step on 5-step trajectories — shorter chains amortize per-trajectory overhead worse; both numbers are honest for their shapes.)

## What you can reduce, and by how much

| Knob | What drops | How much | Trade-off |
|---|---|---:|---|
| `CascadeAnalyzer(entailment=False)` | per-step latency | **−73%** | loses NLI signal: detection fell 55%→44% total in validation, certainty-inflation 83%→33%. Don't use for accuracy-critical runs |
| `CastorObserver(async_mode=True)` | blocking time in the HOST pipeline thread | **−99.9%** (67.6 → 0.08 ms/step) | drift work moves to a background thread; flags arrive slightly later; `report()` waits for drain (~0.5s here) |
| Embedding cache (automatic, FR-1) | re-analysis of an already-seen trajectory | **−100%** (20.7 → <0.1 ms/step) | none — correctness identical; this is why live observation stays cheap as the trajectory grows |
| Swap embedder to `all-MiniLM-L6-v2` | embedding latency | **−77%** vs mpnet; cache memory **−50%** (3.0 → 1.5 KB/step) | UNVALIDATED for accuracy — all validation metrics were measured on mpnet. Re-run `validation/run_validation.py` and recalibrate thresholds before trusting MiniLM |
| Sliding window `cache_window=128` (automatic) | embedding-cache memory on long trajectories | **−87%** on a 1000-step run (3.1 → 0.4 MB) | evicted steps re-embed if re-analyzed from scratch |

## Cold start (once per process)

| Model | First-call latency |
|---|---:|
| all-mpnet-base-v2 (embedding) | ~103 s* |
| nli-deberta-v3-base (NLI) | ~8 s |
| all-MiniLM-L6-v2 (alt embedding) | ~19 s (incl. 90 MB download) |

*Anomalously slow on this Windows machine (cold disk read of a 420 MB model + antivirus scan, likely). Subsequent loads are seconds. Cold start does not affect per-step overhead — models load once.

## Practical recipes

- **Live production observation, minimal intrusion:** `CastorObserver(async_mode=True)` → 0.08 ms blocking per step, full analysis only at `report()`.
- **CI regression gate, fastest:** `castor analyze --no-nli` → 73% faster, accept the detection loss on NLI-dependent cascade types.
- **Post-mortem debugging (UC-1):** full pipeline. 68.7 ms/step means a 100-step trajectory analyzes in ~7 s — latency is irrelevant here, keep maximum signal.
