"""Origin-attribution accuracy against the resolved HUMAN ground truth.

Runs offline. `measure_omission.py` needs mpnet + the NLI cross-encoder and
~1.2 GB of downloads; this script replays `omission-cache.json`, which already
holds the per-step legacy flags and the (step x anchor-fact) entailment matrix
from that scoring pass. Reproducing the headline attribution numbers therefore
costs no models and a second of CPU.

It is self-checking: scored against the machine labels it reproduces the figures
`measure_omission.py` published (25%/75% and 50%/96%), which is what licenses
using it for the human-labelled basis.

Ground truth is the resolved human labelling (see `export_hf_dataset.py`):
single-annotated chains take their annotator, double-annotated chains take the
agreed label, and the three disputed chains are broken by majority across both
humans plus the independent machine pass.

Run:  python validation/measure_attribution.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))

from castor.omission import omission_series  # noqa: E402

sys.path.insert(0, str(ROOT))
from export_hf_dataset import load_best_labels  # noqa: E402

CACHE = {e["id"]: e for e in json.loads(
    (ROOT / "omission-cache.json").read_text(encoding="utf-8"))}
MACHINE = {r["chain_id"]: r for r in json.loads(
    (ROOT / "annotation" / "forms" / "annotations-claude.json").read_text(encoding="utf-8"))}

# The shipped defaults the cached pass was scored under.
COVERAGE_THRESHOLD = 0.5
OMISSION_THRESHOLD = 0.25


def first_flag(entry: dict, use_omission: bool) -> int | None:
    """Earliest flagged step, optionally counting omission-only flags."""
    matrix = entry["entail_matrix"]
    coverage = [
        sum(1 for p in row if p >= COVERAGE_THRESHOLD) / len(row) if row else 0.0
        for row in matrix
    ]
    omissions = omission_series(coverage)
    for index, step_id in enumerate(entry["step_ids"]):
        if entry["legacy_flagged"][index] or (
            use_omission and omissions[index] > OMISSION_THRESHOLD
        ):
            return int(step_id)
    return None


def block(title: str, truth: dict[str, dict], subset: list[str] | None = None) -> None:
    chains = [c for c in truth if truth[c]["cascade_occurred"]]
    if subset is not None:
        chains = [c for c in chains if c in subset]
    if not chains:
        return
    print(f"\n{title} (n={len(chains)})")
    for label, use_omission in (("drift + entailment", False), ("+ omission signal", True)):
        exact = near = 0
        for chain in chains:
            predicted = first_flag(CACHE[chain], use_omission)
            actual = truth[chain]["origin_step"]
            if predicted is not None:
                exact += predicted == actual
                near += abs(predicted - actual) <= 1
        total = len(chains)
        print(f"  {label:<20} exact {exact}/{total} ({100 * exact / total:>3.0f}%)"
              f"   within-1 {near}/{total} ({100 * near / total:>3.0f}%)")


def main() -> None:
    human = load_best_labels()
    machine = {c: {"cascade_occurred": r["cascade_occurred"],
                   "origin_step": r["origin_step"]} for c, r in MACHINE.items()}

    print("SELF-CHECK — scored against the machine labels")
    print("(must reproduce measure_omission.py: 25%/75% then 50%/96%)")
    block("all cascaded chains", machine)

    print("\n" + "=" * 62)
    print("RESULTS — scored against the resolved human ground truth")
    block("all cascaded chains", human)

    omission_chains = [c for c, r in human.items() if r["error_type"] == "omission"]
    block("chains annotated `omission`", human, omission_chains)

    agreement: dict[str, int] = {}
    for record in human.values():
        kind = record.get("label_agreement", "unknown").split(":")[0]
        agreement[kind] = agreement.get(kind, 0) + 1
    print("\nlabel basis: " + ", ".join(f"{n} {k}" for k, n in sorted(agreement.items())))

    types: dict[str, int] = {}
    for record in human.values():
        if record["cascade_occurred"]:
            types[record["error_type"]] = types.get(record["error_type"], 0) + 1
    total = sum(types.values())
    print(f"\nerror types over {total} cascaded chains:")
    for name, count in sorted(types.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<12} {count}/{total} ({100 * count / total:.0f}%)")


if __name__ == "__main__":
    main()
