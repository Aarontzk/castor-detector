"""Performance benchmark (FR-11): per-step overhead by component, and how much
each optional knob reduces it.

Run:  .venv/Scripts/python validation/benchmark.py
Results are hardware-dependent (this run: consumer CPU, no GPU).
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import (
    CascadeAnalyzer,
    CastorObserver,
    CrossEncoderEntailment,
    DriftTracker,
    SentenceTransformerEmbedder,
    ThresholdProfile,
)

ROOT = Path(__file__).resolve().parent
N_RUNS = 3
PROFILE = ThresholdProfile(name="bench", drift_threshold=0.815, aggregate_threshold=0.7123)


def load_texts(n: int = 20) -> list[dict]:
    data = json.loads((ROOT / "clean_trajectories.json").read_text(encoding="utf-8"))
    steps = [step for item in data for step in item["steps"]][:n]
    return [{"step_id": i, "text": s["text"]} for i, s in enumerate(steps, 1)]


def median_time(fn, runs: int = N_RUNS) -> float:
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples)


def main() -> None:
    steps = load_texts(20)
    n = len(steps)
    print(f"benchmark: {n}-step trajectory, median of {N_RUNS} runs, CPU\n")

    # --- cold start (model loads, first call) ---
    t0 = time.perf_counter()
    embedder = SentenceTransformerEmbedder()
    embedder.embed(["warmup sentence for the embedding model"])
    embed_load = time.perf_counter() - t0
    t0 = time.perf_counter()
    nli = CrossEncoderEntailment()
    nli.check("warmup premise", "warmup hypothesis")
    nli_load = time.perf_counter() - t0
    print(f"cold start: embedding model {embed_load:.1f}s, NLI model {nli_load:.1f}s (once per process)")

    # --- MiniLM alternative embedder (pluggable, FR-2) ---
    t0 = time.perf_counter()
    minilm = SentenceTransformerEmbedder("sentence-transformers/all-MiniLM-L6-v2")
    minilm.embed(["warmup"])
    minilm_load = time.perf_counter() - t0
    print(f"cold start: MiniLM alternative {minilm_load:.1f}s\n")

    # --- batch analyze: full vs drift-only vs MiniLM ---
    full = median_time(
        lambda: CascadeAnalyzer(embedder=embedder, entailment=nli, profile=PROFILE).analyze(steps)
    )
    drift_only = median_time(
        lambda: CascadeAnalyzer(embedder=embedder, entailment=False, profile=PROFILE).analyze(steps)
    )
    drift_minilm = median_time(
        lambda: CascadeAnalyzer(embedder=minilm, entailment=False, profile=PROFILE).analyze(steps)
    )
    print(f"full pipeline (drift+NLI+classify+attrib): {full / n * 1000:7.1f} ms/step")
    print(f"drift-only (entailment=False):             {drift_only / n * 1000:7.1f} ms/step"
          f"  (-{(1 - drift_only / full) * 100:.0f}%)")
    print(f"drift-only + MiniLM embedder:              {drift_minilm / n * 1000:7.1f} ms/step"
          f"  (-{(1 - drift_minilm / full) * 100:.0f}% vs full, -{(1 - drift_minilm / drift_only) * 100:.0f}% vs mpnet drift-only)")

    # --- embedding cache: repeat analyze on same tracker ---
    tracker = DriftTracker(embedder=embedder, drift_threshold=PROFILE.drift_threshold)
    tracker.analyze(steps)  # fill cache
    first = median_time(lambda: DriftTracker(
        embedder=embedder, drift_threshold=PROFILE.drift_threshold).analyze(steps), runs=1)
    cached = median_time(lambda: tracker.analyze(steps))
    print(f"\ndrift analyze, cold cache:                 {first / n * 1000:7.1f} ms/step")
    print(f"drift analyze, warm cache (FR-1):          {cached / n * 1000:7.1f} ms/step"
          f"  (-{(1 - cached / first) * 100:.0f}%)")

    # --- stream observe: sync vs async blocking time in host thread ---
    sync_observer = CastorObserver(embedder=embedder, entailment=False, profile=PROFILE)
    sync_samples = []
    for step in steps:
        t0 = time.perf_counter()
        sync_observer.observe(step)
        sync_samples.append(time.perf_counter() - t0)
    async_observer = CastorObserver(embedder=embedder, entailment=False, profile=PROFILE,
                                    async_mode=True)
    async_samples = []
    for step in steps:
        t0 = time.perf_counter()
        async_observer.observe(step)
        async_samples.append(time.perf_counter() - t0)
    t0 = time.perf_counter()
    async_observer.close()
    drain = time.perf_counter() - t0
    sync_mean = statistics.mean(sync_samples) * 1000
    async_mean = statistics.mean(async_samples) * 1000
    print(f"\nobserve() blocking, sync:                  {sync_mean:7.1f} ms/step")
    print(f"observe() blocking, async_mode=True:       {async_mean:7.2f} ms/step"
          f"  (-{(1 - async_mean / sync_mean) * 100:.1f}%)  [drain at close: {drain:.2f}s]")

    # --- memory: embedding cache, sliding window (FR-11) ---
    dim_mpnet, dim_minilm = 768, 384
    per_step = dim_mpnet * 4
    long_run = 1000
    uncapped = long_run * per_step / 1e6
    capped = (128 + 1) * per_step / 1e6
    print(f"\nembedding cache: {per_step / 1024:.1f} KB/step (mpnet, float32)")
    print(f"1000-step trajectory: {uncapped:.1f} MB uncapped -> {capped:.2f} MB with window=128"
          f"  (-{(1 - capped / uncapped) * 100:.0f}%)")
    print(f"MiniLM cache would be {dim_minilm * 4 / 1024:.1f} KB/step (-50%)")


if __name__ == "__main__":
    main()
