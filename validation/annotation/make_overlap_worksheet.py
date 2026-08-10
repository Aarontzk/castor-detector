"""Build a single-page worksheet for the 10 double-annotated (kappa) chains.

Deliberately contains NO analysis, no candidate origin, no correct answer, and
no other annotator's labels. Both annotators read the same page, so anything
interpretive printed here would anchor them identically and inflate the very
agreement figure the overlap set exists to measure.

What it does add is mechanical: source sentences are numbered so "which fact
went missing" is checkable at a glance, and steps that stop mid-sentence are
marked, since a token-limit truncation is not an error (GUIDE rule 5).

Run:  python validation/annotation/make_overlap_worksheet.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORGANIC = ROOT.parent / "organic"
OUT = ROOT / "overlap-worksheet.md"

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

HEADER = """# Overlap worksheet — the 10 kappa chains

**For: Farel and Fabio, separately.** These are the only chains that produce
Cohen's kappa, so they must be annotated by hand and independently.

> **Do not open** `annotations-claude.json`, `annotations-farel.json`, or
> `annotations-fabio.json` until you have finished all ten. Agreement is only
> meaningful if neither of you saw anything else first.

This page contains no analysis and no suggested answers, by design.

## For each chain

1. Read the numbered source facts.
2. **Work out the correct answer yourself before reading the steps.**
3. Read steps 1 to 4 in order. Mark the **first** step that deviates from the
   source.
4. Write the label on the answer line, then enter all ten at the end.

## Rules that decide the close calls

- **First deviation wins.** A later step faithfully carrying an earlier error is
  not the origin — it is the cascade.
- **Judge each step against the SOURCE**, not against the step before it.
- **A dropped fact counts** only if the question needs it.
- **Compression is not omission.** The writer step is supposed to be short.
- **`[TRUNCATED]` is not an error.** Judge only the content present.
- **Torn between two steps? Pick the earlier one and say why in notes.**

## Error types

| Type | Test |
|---|---|
| `omission` | A needed fact is **missing**. What is written stays true. |
| `misread` | The fact is **present but its meaning is inverted** or misapplied. |
| `arithmetic` | Right numbers, **wrong calculation**. |
| `fabrication` | A fact, number or rule appears that is **not in the source**. |
| `none` | Only when `cascade_occurred` is false. |

## Entering your answers

```
python validation/annotation/enter_labels.py farel     # or: fabio
```

It prompts chain by chain and writes valid JSON, so no hand-editing.

---
"""


def looks_truncated(text: str) -> bool:
    """A step that stops mid-sentence hit the generation token limit."""
    return not text.rstrip().endswith((".", "!", "?", '"', ")", "%"))


def main() -> None:
    assignments = json.loads((ROOT / "assignments.json").read_text(encoding="utf-8"))
    overlap = assignments["overlap"]

    parts = [HEADER]
    for position, chain_id in enumerate(overlap, start=1):
        data = json.loads((ORGANIC / f"{chain_id}.json").read_text(encoding="utf-8"))
        parts.append(f"\n## {position}/10 · {chain_id}\n")
        parts.append(f"**Question:** {data['question']}\n")

        facts = [s.strip() for s in SENTENCE_SPLIT.split(data["source"].strip()) if s.strip()]
        parts.append("**Source facts:**\n")
        parts.extend(f"{index}. {fact}\n" for index, fact in enumerate(facts, start=1))
        parts.append("")

        for step in data["steps"]:
            text = " ".join(step["text"].split())
            mark = " `[TRUNCATED]`" if looks_truncated(step["text"]) else ""
            role = step.get("role") or step.get("agent_name") or "step"
            parts.append(f"**Step {step['step_id']} — {role}**{mark}\n")
            parts.append(f"> {text}\n")

        parts.append(
            "**Answer:** cascade `____`  ·  origin_step `____`  ·  "
            "type `____`\n\n**Evidence:**\n\n**Notes:**\n\n---\n"
        )

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUT} ({len(overlap)} chains)")


if __name__ == "__main__":
    main()
