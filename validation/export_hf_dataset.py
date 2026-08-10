"""Export the Castor benchmark as a Hugging Face dataset (three JSONL splits).

Produces the artefact behind every number in `docs/VALIDATION.md`, so a reader
can reproduce the evaluation without running the generators:

  clean.jsonl     30 hand-written clean trajectories (the injection base)
  injected.jsonl  150 = 30 clean x 5 error kinds, each with a ground-truth
                  origin step and kind (FR-10, deterministic under seed)
  organic.jsonl   28 real qwen2.5:3b agent chains under an information
                  bottleneck, with human-verified origin annotations

The injected split is regenerated here with exactly the seed schedule
`run_validation.py` uses (`seed=index * 7 + 1`), so the exported file and the
reported metrics come from identical inputs.

Run:  python validation/export_hf_dataset.py [--out hf-dataset]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from castor import INJECTION_KINDS, Trajectory, inject  # noqa: E402

ROOT = Path(__file__).resolve().parent
ANNOTATIONS = ROOT / "annotation" / "forms" / "annotations-claude.json"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"  {path.name:<16} {len(rows):>4} rows")


def export_clean(out: Path) -> list[dict]:
    data = json.loads((ROOT / "clean_trajectories.json").read_text(encoding="utf-8"))
    rows = [
        {
            "id": item["id"],
            "domain": item["domain"],
            "steps": item["steps"],
            "n_steps": len(item["steps"]),
        }
        for item in data
    ]
    write_jsonl(out / "clean.jsonl", rows)
    return data


def export_injected(out: Path, clean: list[dict]) -> None:
    """30 clean x 5 kinds, labelled with the injected origin step and kind."""
    rows = []
    for index, item in enumerate(clean):
        trajectory = Trajectory.from_steps(item["steps"])
        for kind in INJECTION_KINDS:
            corrupted, record = inject(trajectory, kind, seed=index * 7 + 1)
            rows.append({
                "id": f"{item['id']}--{kind}",
                "source_id": item["id"],
                "domain": item["domain"],
                "injection_kind": kind,
                "origin_step_id": record.step_id,
                "origin_step_index": record.step_index,
                "original_text": record.original_text,
                "injected_text": record.injected_text,
                "steps": [
                    {"step_id": s.step_id, "text": s.text} for s in corrupted.steps
                ],
                "seed": index * 7 + 1,
            })
    write_jsonl(out / "injected.jsonl", rows)


def load_best_labels() -> dict[str, dict]:
    """Best available label per chain, preferring human-verified over machine.

    A human-verified record wins over the machine pass for the same chain, and
    the row records which it was: a published dataset that hides whether a label
    was written by a person or a model is not reusable as ground truth.
    """
    best: dict[str, dict] = {}
    for record in json.loads(ANNOTATIONS.read_text(encoding="utf-8")):
        best[record["chain_id"]] = {**record, "label_source": "machine"}

    for path in sorted((ROOT / "annotation" / "forms").glob("annotations-*.json")):
        who = path.stem.replace("annotations-", "")
        if who == "claude":
            continue
        for record in json.loads(path.read_text(encoding="utf-8")):
            if record.get("cascade_occurred") is None:
                continue
            if not record.get("verified_by_human"):
                continue
            best[record["chain_id"]] = {**record, "label_source": f"human:{who}"}
    return best


def export_organic(out: Path) -> None:
    """Real agent chains plus their origin annotations, joined on chain id."""
    annotations = load_best_labels()
    rows = []
    for path in sorted((ROOT / "organic").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        truth = annotations.get(data["id"], {})
        rows.append({
            "id": data["id"],
            "question": data["question"],
            "source": data["source"],
            "model": data.get("model"),
            "temperature": data.get("temperature"),
            "steps": [
                {
                    "step_id": s["step_id"],
                    "agent_name": s.get("agent_name"),
                    "role": s.get("role"),
                    "text": s["text"],
                }
                for s in data["steps"]
            ],
            "cascade_occurred": truth.get("cascade_occurred"),
            "origin_step": truth.get("origin_step"),
            "error_type": truth.get("error_type"),
            "evidence": truth.get("evidence", ""),
            "annotation_notes": truth.get("notes", ""),
            "label_source": truth.get("label_source", "machine"),
        })
    write_jsonl(out / "organic.jsonl", rows)
    human = sum(1 for r in rows if r["label_source"].startswith("human"))
    print(f"    -> {human}/{len(rows)} labels human-verified, "
          f"{len(rows) - human} machine")


CARD = """---
license: mit
task_categories:
  - text-classification
language:
  - en
  - id
tags:
  - hallucination-detection
  - multi-agent
  - llm-evaluation
  - agent-trajectories
  - observability
pretty_name: Castor Cascade Benchmark
size_categories:
  - n<1K
configs:
  - config_name: clean
    data_files: clean.jsonl
  - config_name: injected
    data_files: injected.jsonl
  - config_name: organic
    data_files: organic.jsonl
---

# Castor Cascade Benchmark

Trajectories for evaluating **hallucination cascade** detection in multi-agent
LLM pipelines: a small error at one step propagates through later steps while
every per-step check keeps passing, because each step is locally coherent with
a poisoned premise.

This is the evaluation data behind [Castor](https://github.com/Aarontzk/castor-detector).
Every number in the project's `docs/VALIDATION.md` is reproducible from it.

**No model weights are published here.** Castor trains nothing — it composes two
off-the-shelf local models (`all-mpnet-base-v2`, `cross-encoder/nli-deberta-v3-base`).
The dataset is the asset.

## Splits

| Split | Rows | What it is |
|---|---|---|
| `clean` | 30 | Hand-written correct trajectories, 5 steps each, EN + ID, spanning numeric / narrative / analytic domains. The base for injection and the source of calibration thresholds. |
| `injected` | 150 | `clean` x 5 error kinds, one controlled error per trajectory with a known origin step. Deterministic. |
| `organic` | 28 | Real 4-agent chains generated by a local `qwen2.5:3b`, no injected errors, with human-verified origin annotations. |

### `injected` — five error kinds

Generated by `castor.inject` (seeded, reproducible). Injection never targets
step 0, so the anchor stays clean and the error remains measurable downstream.

| Kind | What it does |
|---|---|
| `numeric_fabrication` | Perturbs a figure into a wrong one |
| `entity_distortion` | Swaps a proper noun for a wrong one |
| `causal_leap` | Appends a conclusive non-sequitur |
| `certainty_inflation` | Rewrites hedges as absolutes |
| `context_swap` | Replaces step content with off-domain material |

### `organic` — the harder split

Four agents (extractor, analyst, reasoner, writer) in a line under an
**information bottleneck**: each agent sees only its predecessor's output and
never the source document. Each source contains one clause that changes the
correct answer. Nothing is injected — these are the mistakes the model actually
made.

24 of 28 chains cascaded. Annotated origin error types:

| Error type | Count |
|---|---|
| `misread` (fact present, meaning inverted) | 12/24 (50%) |
| `omission` (fact silently dropped) | 9/24 (38%) |
| `fabrication` | 2/24 (8%) |
| `arithmetic` | 1/24 (4%) |

`misread` dominating is a correction to an earlier N=8 reading of this data,
where `omission` appeared dominant. That was a small-sample artefact.

## Fields

**`clean`** — `id`, `domain`, `steps[{step_id, text}]`, `n_steps`

**`injected`** — `id`, `source_id`, `domain`, `injection_kind`,
`origin_step_id`, `origin_step_index`, `original_text`, `injected_text`,
`steps[{step_id, text}]`, `seed`

**`organic`** — `id`, `question`, `source`, `model`, `temperature`,
`steps[{step_id, agent_name, role, text}]`, `cascade_occurred`, `origin_step`,
`error_type`, `evidence`, `annotation_notes`, `label_source`

`label_source` is `human:<name>` for a human-written or human-verified label and
`machine` otherwise. Filter on it if you only want human ground truth.

## Usage

```python
from datasets import load_dataset

organic = load_dataset("<your-username>/castor-cascade-benchmark", "organic")["train"]
row = organic[0]
print(row["source"])         # ground truth the chain should have preserved
print(row["origin_step"])    # annotated first deviating step
```

Scoring a detector: predict the origin step per trajectory, compare against
`origin_step` (organic) or `origin_step_id` (injected). Report exact-match and
within-1 accuracy separately — within-1 is the honest headline for a
threshold-based method, since a cascade's first *visible* symptom often lands
one step after its cause.

## Honest limitations

- **The `organic` split is small (28 chains, 4 of them clean).** Chain-level
  false-positive rates measured on it have 25pp resolution. Treat it as
  directional evidence, not a precision benchmark.
- **Annotation provenance is mixed and the rows say which.** 19 of 28 organic
  labels are human-written or human-verified (`label_source` starts with
  `human:`); the remaining 9 are a machine pass. Measured agreement between the
  machine pass and an independent human on the 10-chain overlap: `origin_step`
  10/10 exact (kappa 1.000), `error_type` 9/10 (kappa 0.859). Ten items is a
  small basis and kappa on a near-degenerate label distribution is unstable —
  read the origin figure as "no disagreement found in ten chains", not as a
  precise 1.000. Human-versus-human agreement is not yet available.
- **`injected` errors are synthetic.** Rule-based injection produces cleaner,
  more separable errors than a real model does. Detection rates on `injected`
  run higher than on `organic` for that reason; do not quote them as real-world
  performance.
- **One generator model.** All organic chains come from `qwen2.5:3b` at
  temperature 0.8. Failure-mode distribution is a property of that model at that
  size, not of LLM agents in general.
- **Single topology.** Linear 4-step chains only. Branching and cyclic agent
  graphs are not represented.

## Citation

```bibtex
@software{castor2026,
  title  = {Castor: Hallucination Cascade Detection for Multi-Agent LLM Pipelines},
  author = {Tim Fable},
  year   = {2026},
  url    = {https://github.com/Aarontzk/castor-detector},
  license = {MIT}
}
```

License: MIT, matching the Castor repository.
"""


def main() -> None:
    out_name = "hf-dataset"
    if "--out" in sys.argv:
        out_name = sys.argv[sys.argv.index("--out") + 1]
    out = Path(__file__).resolve().parents[1] / out_name
    out.mkdir(parents=True, exist_ok=True)

    print(f"exporting to {out}/")
    clean = export_clean(out)
    export_injected(out, clean)
    export_organic(out)
    (out / "README.md").write_text(CARD, encoding="utf-8")
    print(f"  {'README.md':<16} dataset card")
    print("\nnext (owner step — needs your HF account):")
    print("  pip install huggingface_hub")
    print("  huggingface-cli login")
    print(f"  huggingface-cli upload <user>/castor-cascade-benchmark {out} . --repo-type=dataset")


if __name__ == "__main__":
    main()
