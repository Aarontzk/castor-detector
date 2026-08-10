"""Prompt-driven entry for the 10 overlap labels. Writes valid JSON.

Hand-editing the form is the main way a labelling session gets lost: one
missing comma and the file will not parse. This walks the overlap chains one at
a time, validates each field against GUIDE.md, and saves after every chain so
an interrupted session keeps its work.

It never displays another annotator's labels, and it never displays the machine
draft. Agreement on the overlap set is only meaningful if the two passes are
independent.

Run:  python validation/annotation/enter_labels.py farel     # or: fabio
      python validation/annotation/enter_labels.py farel --redo organic-04
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORMS = ROOT / "forms"
ERROR_TYPES = ("omission", "arithmetic", "misread", "fabrication", "none")


def ask(prompt: str, valid=None, allow_blank: bool = False) -> str:
    """Re-prompt until the answer is one of `valid`."""
    while True:
        try:
            answer = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nstopped — everything entered so far is saved.")
            raise SystemExit(0)
        if allow_blank and not answer:
            return ""
        if valid is None and answer:
            return answer
        if valid is not None and answer.lower() in valid:
            return answer.lower()
        expected = "/".join(valid) if valid else "a non-empty value"
        print(f"  -> expected {expected}")


def label_one(chain_id: str, position: str) -> dict:
    print(f"\n=== {chain_id}  ({position})")
    cascade = ask("  cascade occurred? [y/n]: ", ("y", "n")) == "y"

    if not cascade:
        notes = ask("  notes (optional): ", allow_blank=True)
        return {
            "chain_id": chain_id,
            "cascade_occurred": False,
            "origin_step": None,
            "error_type": "none",
            "evidence": "",
            "notes": notes,
        }

    origin = int(ask("  first deviating step? [1-4]: ", ("1", "2", "3", "4")))
    print(f"  error type: {', '.join(ERROR_TYPES[:4])}")
    error_type = ask("  type: ", ERROR_TYPES[:4])
    evidence = ask("  evidence (quote or paraphrase the deviation): ")
    notes = ask("  notes (optional): ", allow_blank=True)
    return {
        "chain_id": chain_id,
        "cascade_occurred": True,
        "origin_step": origin,
        "error_type": error_type,
        "evidence": evidence,
        "notes": notes,
    }


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python enter_labels.py <annotator> [--redo <chain_id>]")
    annotator = args[0].lower()

    form_path = FORMS / f"annotations-{annotator}.json"
    if not form_path.exists():
        raise SystemExit(f"no form at {form_path} — run prepare.py first")

    redo = None
    if "--redo" in sys.argv:
        redo = sys.argv[sys.argv.index("--redo") + 1]

    overlap = json.loads((ROOT / "assignments.json").read_text(encoding="utf-8"))["overlap"]
    records = json.loads(form_path.read_text(encoding="utf-8"))
    by_id = {r["chain_id"]: r for r in records}

    if redo:
        todo = [redo]
    else:
        todo = [c for c in overlap
                if c in by_id and by_id[c].get("cascade_occurred") is None]

    if not todo:
        done = sum(1 for c in overlap if by_id.get(c, {}).get("cascade_occurred") is not None)
        print(f"all {done}/{len(overlap)} overlap chains already labelled for {annotator}.")
        print("re-do one with:  --redo <chain_id>")
        return

    print(f"annotator: {annotator} | {len(todo)} overlap chain(s) to label")
    print("read each chain in overlap-worksheet.md first. Ctrl+C saves and exits.\n")

    for index, chain_id in enumerate(todo, start=1):
        record = label_one(chain_id, f"{index} of {len(todo)}")
        # A human typed it, so it is verified by definition.
        record["verified_by_human"] = True
        by_id[chain_id].update(record)
        form_path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"  saved ({index}/{len(todo)})")

    remaining = [c for c in overlap if by_id[c].get("cascade_occurred") is None]
    print(f"\ndone. overlap complete: {len(overlap) - len(remaining)}/{len(overlap)}")
    if remaining:
        print(f"still blank: {', '.join(remaining)}")
    else:
        print("both annotators finished? run:  python validation/annotation/kappa.py")


if __name__ == "__main__":
    main()
