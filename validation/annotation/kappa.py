"""Inter-annotator agreement for the organic origin labels.

Primary number for the paper: human-versus-human Cohen's kappa on the 10
overlap chains. LLM-versus-human agreement on the same 10 is reported next to
it, so the machine-assisted labels on the single-annotated chains carry a
measured reliability figure rather than an assumption.

Reports, per annotator pair:
  - origin_step: exact agreement, within-1 agreement, Cohen's kappa
  - error_type: agreement and kappa
  - cascade_occurred: agreement

Run:  python validation/annotation/kappa.py
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORMS_DIR = ROOT / "forms"
ASSIGNMENTS = ROOT / "assignments.json"


def overlap_chains() -> set[str]:
    """The 10 double-annotated chains — the only valid basis for agreement.

    Every pair is scored on these and nothing else. Intersecting whatever both
    files happen to have filled would silently include the single-annotated
    chains, where one side may be a machine draft: an LLM-vs-LLM comparison
    would then be reported as an LLM-vs-human cross-check.
    """
    return set(json.loads(ASSIGNMENTS.read_text(encoding="utf-8"))["overlap"])


def load_annotations() -> dict[str, dict[str, dict]]:
    """Load every annotator file into {annotator: {chain_id: record}}, keeping
    only records that were actually filled in."""
    out: dict[str, dict[str, dict]] = {}
    for path in sorted(FORMS_DIR.glob("annotations-*.json")):
        name = path.stem.replace("annotations-", "")
        records = json.loads(path.read_text(encoding="utf-8"))
        filled = {
            r["chain_id"]: r for r in records if r.get("cascade_occurred") is not None
        }
        if filled:
            out[name] = filled
    return out


def cohens_kappa(labels_a: list, labels_b: list) -> float | None:
    """Cohen's kappa for two aligned label sequences.

    Returns None when kappa is undefined: fewer than two items, or both
    annotators used a single identical category so chance agreement is 1.
    """
    if len(labels_a) < 2:
        return None
    n = len(labels_a)
    categories = sorted({str(x) for x in labels_a + labels_b})
    observed = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    expected = 0.0
    for category in categories:
        p_a = sum(1 for x in labels_a if str(x) == category) / n
        p_b = sum(1 for x in labels_b if str(x) == category) / n
        expected += p_a * p_b
    if abs(1.0 - expected) < 1e-12:
        return None
    return (observed - expected) / (1.0 - expected)


def within_one(labels_a: list, labels_b: list) -> float:
    """Fraction of items where the two origin steps differ by at most one step.

    Reported because Castor's own attribution target is +/-1: a labelling
    disagreement of one step is a different kind of problem from a wholesale
    disagreement about where the chain broke.
    """
    hits = 0
    for a, b in zip(labels_a, labels_b):
        if a is None or b is None:
            hits += int(a == b)
        elif abs(int(a) - int(b)) <= 1:
            hits += 1
    return hits / len(labels_a) if labels_a else 0.0


def compare(
    name_a: str, name_b: str, a: dict[str, dict], b: dict[str, dict], basis: set[str]
) -> None:
    """Print the full agreement block for one annotator pair, over `basis` only."""
    shared = sorted(set(a) & set(b) & basis)
    if len(shared) < 2:
        print(f"\n{name_a} vs {name_b}: only {len(shared)} shared overlap chain(s), skipped")
        return

    origin_a = [a[c]["origin_step"] for c in shared]
    origin_b = [b[c]["origin_step"] for c in shared]
    type_a = [a[c]["error_type"] for c in shared]
    type_b = [b[c]["error_type"] for c in shared]
    casc_a = [a[c]["cascade_occurred"] for c in shared]
    casc_b = [b[c]["cascade_occurred"] for c in shared]

    exact = sum(1 for x, y in zip(origin_a, origin_b) if x == y) / len(shared)
    k_origin = cohens_kappa(origin_a, origin_b)
    k_type = cohens_kappa(type_a, type_b)
    agree_type = sum(1 for x, y in zip(type_a, type_b) if x == y) / len(shared)
    agree_casc = sum(1 for x, y in zip(casc_a, casc_b) if x == y) / len(shared)
    fmt = lambda v: "undefined" if v is None else f"{v:.3f}"

    print(f"\n{name_a} vs {name_b} (n={len(shared)})")
    print(f"  origin_step      exact {exact:.0%}   within-1 {within_one(origin_a, origin_b):.0%}"
          f"   kappa {fmt(k_origin)}")
    print(f"  error_type       agree {agree_type:.0%}   kappa {fmt(k_type)}")
    print(f"  cascade_occurred agree {agree_casc:.0%}")

    disagreements = [
        (c, a[c]["origin_step"], b[c]["origin_step"], a[c]["error_type"], b[c]["error_type"])
        for c in shared
        if a[c]["origin_step"] != b[c]["origin_step"] or a[c]["error_type"] != b[c]["error_type"]
    ]
    if disagreements:
        print("  disagreements (chain: origin a/b, type a/b):")
        for chain, oa, ob, ta, tb in disagreements:
            print(f"    {chain}: step {oa}/{ob}, {ta}/{tb}")


def main() -> None:
    annotations = load_annotations()
    if not annotations:
        print("no filled annotations found in", FORMS_DIR)
        return

    basis = overlap_chains()
    print("filled annotations per annotator:")
    for name, records in sorted(annotations.items()):
        drafted = sum(1 for r in records.values() if r.get("verified_by_human") is False)
        suffix = f" ({drafted} machine-drafted, unverified)" if drafted else ""
        print(f"  {name}: {len(records)} chains, {len(set(records) & basis)}/10 overlap{suffix}")

    for name_a, name_b in combinations(sorted(annotations), 2):
        compare(name_a, name_b, annotations[name_a], annotations[name_b], basis)

    print("\nNote: the paper reports human-vs-human kappa as the reliability")
    print("figure. LLM-vs-human pairs are a cross-check on the machine-assisted")
    print("labels used for the single-annotated chains.")


if __name__ == "__main__":
    main()
