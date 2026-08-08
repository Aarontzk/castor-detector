"""Aggregate the organic annotations into the numbers the paper reports.

Reads one annotator file (default: the machine-assisted pass) and prints the
label distribution over the full set, split by collection batch and by question
language, so the batch-1-only claims in docs/VALIDATION.md can be restated at
N=28 instead of N=8.

Run:  python validation/annotation/summarize.py [annotator]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAINS_DIR = ROOT.parent / "organic"
_ID_MARKERS = ("apakah", "berapa", "kapan", "perlu", "cukup", "bagaimana", "sebaiknya")


def chain_meta() -> dict[str, dict]:
    """Map each chain id to its batch and question language."""
    meta = {}
    for path in sorted(CHAINS_DIR.glob("organic-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        index = int(data["id"].split("-")[1])
        question = data["question"].lower()
        meta[data["id"]] = {
            "batch": "batch1" if index <= 8 else "batch2",
            "lang": "ID" if any(m in question for m in _ID_MARKERS) else "EN",
        }
    return meta


def share(count: int, total: int) -> str:
    """Format a count as 'n/total (pp%)' with a guard against division by zero."""
    return f"{count}/{total}" + (f" ({100 * count / total:.0f}%)" if total else "")


def block(title: str, records: list[dict]) -> None:
    """Print one distribution block for a subset of the annotations."""
    total = len(records)
    cascaded = [r for r in records if r["cascade_occurred"]]
    clean = total - len(cascaded)
    print(f"\n{title} (n={total})")
    print(f"  cascaded          {share(len(cascaded), total)}")
    print(f"  clean             {share(clean, total)}")
    if not cascaded:
        return
    origins = Counter(r["origin_step"] for r in cascaded)
    types = Counter(r["error_type"] for r in cascaded)
    print("  origin step:      " + ", ".join(
        f"step {step} {share(n, len(cascaded))}" for step, n in sorted(origins.items())))
    print("  error type:       " + ", ".join(
        f"{name} {share(n, len(cascaded))}" for name, n in types.most_common()))


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "claude"
    path = ROOT / "forms" / f"annotations-{name}.json"
    records = [
        r for r in json.loads(path.read_text(encoding="utf-8"))
        if r.get("cascade_occurred") is not None
    ]
    if not records:
        print(f"{path.name}: no filled annotations")
        return

    meta = chain_meta()
    print(f"source: {path.name}")
    block("FULL SET", records)
    for key in ("batch1", "batch2"):
        subset = [r for r in records if meta[r["chain_id"]]["batch"] == key]
        if subset:
            block(f"by batch: {key}", subset)
    for key in ("EN", "ID"):
        subset = [r for r in records if meta[r["chain_id"]]["lang"] == key]
        if subset:
            block(f"by language: {key}", subset)

    contested = [r for r in records if "ontested" in (r.get("notes") or "")]
    if contested:
        print(f"\ncontested labels flagged for adjudication ({len(contested)}):")
        for r in contested:
            print(f"  {r['chain_id']}: step {r['origin_step']}, {r['error_type']}")


if __name__ == "__main__":
    main()
