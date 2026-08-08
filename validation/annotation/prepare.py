"""Prepare the organic annotation round: split, blank forms, review sheet.

Deterministic and re-runnable. Existing filled forms are never overwritten:
each annotator's file is only created when missing, and re-running merges in
chains that were added later without touching labels already entered.

Split policy (documented so the paper can state it):
  - 10 chains are annotated by BOTH annotators. Cohen's kappa comes from these.
  - The remaining 18 are split 9/9, single annotation each.
  - The overlap set is stratified across the two collection batches
    (organic-01..08, organic-09..28) and across question language (EN/ID), so
    agreement is not measured on an easy or homogeneous subset.

Run:  python validation/annotation/prepare.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAINS_DIR = ROOT.parent / "organic"
FORMS_DIR = ROOT / "forms"
SEED = 42
ANNOTATORS = ("farel", "fabio")
N_OVERLAP = 10

# Indonesian question markers, enough to separate EN from ID in this task set.
_ID_MARKERS = ("apakah", "berapa", "kapan", "perlu", "cukup", "bagaimana", "sebaiknya")


def load_chains() -> list[dict]:
    """Read every organic chain JSON, sorted by id for a stable split."""
    chains = []
    for path in sorted(CHAINS_DIR.glob("organic-*.json")):
        chains.append(json.loads(path.read_text(encoding="utf-8")))
    return chains


def language_of(chain: dict) -> str:
    """Classify a chain's question as ID or EN from lexical markers."""
    question = chain["question"].lower()
    return "ID" if any(marker in question for marker in _ID_MARKERS) else "EN"


def batch_of(chain: dict) -> str:
    """Which collection batch a chain belongs to (01-08 vs 09-28)."""
    index = int(chain["id"].split("-")[1])
    return "batch1" if index <= 8 else "batch2"


def stratified_overlap(chains: list[dict]) -> list[str]:
    """Pick the overlap set, proportional across batch and spanning both languages.

    Proportional allocation keeps the agreement estimate representative of the
    full set instead of concentrating it in one batch.
    """
    rng = random.Random(SEED)
    strata: dict[tuple[str, str], list[str]] = {}
    for chain in chains:
        strata.setdefault((batch_of(chain), language_of(chain)), []).append(chain["id"])

    total = len(chains)
    picked: list[str] = []
    # Largest-remainder allocation so the per-stratum counts sum to exactly N_OVERLAP.
    quotas = {key: len(ids) * N_OVERLAP / total for key, ids in strata.items()}
    base = {key: int(value) for key, value in quotas.items()}
    remainder = N_OVERLAP - sum(base.values())
    by_frac = sorted(strata, key=lambda key: (-(quotas[key] - base[key]), key))
    for key in by_frac[:remainder]:
        base[key] += 1

    for key in sorted(strata):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        picked.extend(ids[: base[key]])
    return sorted(picked)


def split_singles(chains: list[dict], overlap: set[str]) -> dict[str, list[str]]:
    """Split the non-overlap chains evenly, alternating so each annotator gets
    a comparable mix of batch and language."""
    rng = random.Random(SEED + 1)
    rest = [c for c in chains if c["id"] not in overlap]
    rest.sort(key=lambda c: (batch_of(c), language_of(c), c["id"]))
    buckets: dict[tuple[str, str], list[str]] = {}
    for chain in rest:
        buckets.setdefault((batch_of(chain), language_of(chain)), []).append(chain["id"])

    assigned: dict[str, list[str]] = {name: [] for name in ANNOTATORS}
    turn = 0
    for key in sorted(buckets):
        ids = sorted(buckets[key])
        rng.shuffle(ids)
        for chain_id in ids:
            assigned[ANNOTATORS[turn % len(ANNOTATORS)]].append(chain_id)
            turn += 1
    for name in assigned:
        assigned[name].sort()
    return assigned


def blank_entry(chain_id: str) -> dict:
    """One empty annotation record, fields spelled out so the form is self-documenting."""
    return {
        "chain_id": chain_id,
        "cascade_occurred": None,
        "origin_step": None,
        "error_type": None,
        "evidence": "",
        "notes": "",
    }


def write_form(name: str, chain_ids: list[str]) -> tuple[int, int]:
    """Create or extend one annotator's form. Never overwrites existing labels."""
    FORMS_DIR.mkdir(parents=True, exist_ok=True)
    path = FORMS_DIR / f"annotations-{name}.json"
    existing: dict[str, dict] = {}
    if path.exists():
        for entry in json.loads(path.read_text(encoding="utf-8")):
            existing[entry["chain_id"]] = entry
    merged = [existing.get(cid, blank_entry(cid)) for cid in chain_ids]
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    filled = sum(1 for e in merged if e["cascade_occurred"] is not None)
    return filled, len(merged)


def write_review_sheet(chains: list[dict], assignment: dict) -> None:
    """Render every chain as readable markdown so annotators do not read raw JSON."""
    lines = [
        "# Review sheet: organic chains (N=%d)" % len(chains),
        "",
        "Read the source, then the steps in order. Mark the FIRST step that",
        "deviates from the source. Labelling rules: see GUIDE.md.",
        "",
    ]
    for chain in chains:
        who = [name for name, ids in assignment["single"].items() if chain["id"] in ids]
        tag = "OVERLAP (both annotators)" if chain["id"] in assignment["overlap"] else f"single: {who[0]}"
        lines += [
            f"## {chain['id']} [{language_of(chain)}, {batch_of(chain)}] — {tag}",
            "",
            f"**Question:** {chain['question']}",
            "",
            "**Source:**",
            "",
            f"> {chain['source']}",
            "",
        ]
        for step in chain["steps"]:
            text = step["text"].strip().replace("\n", "\n> ")
            lines += [
                f"**Step {step['step_id']} — {step['agent_name']}**",
                "",
                f"> {text}",
                "",
            ]
        lines.append("---")
        lines.append("")
    (ROOT / "review-sheet.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    chains = load_chains()
    overlap = stratified_overlap(chains)
    singles = split_singles(chains, set(overlap))

    assignment = {
        "seed": SEED,
        "n_chains": len(chains),
        "overlap": overlap,
        "single": singles,
        "policy": (
            "10 overlap chains annotated independently by both annotators "
            "(Cohen's kappa source); remaining 18 split 9/9, single annotation. "
            "Overlap stratified by batch and question language."
        ),
    }
    (ROOT / "assignments.json").write_text(
        json.dumps(assignment, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"chains: {len(chains)}")
    print(f"overlap ({len(overlap)}): {', '.join(overlap)}")
    for name in ANNOTATORS:
        todo = sorted(set(overlap) | set(singles[name]))
        filled, total = write_form(name, todo)
        print(f"{name}: {total} chains to annotate ({len(overlap)} overlap + "
              f"{len(singles[name])} single), {filled} already filled")

    write_review_sheet(chains, assignment)
    print("wrote assignments.json, forms/, review-sheet.md")


if __name__ == "__main__":
    main()
