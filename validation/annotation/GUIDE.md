# Annotation guide: organic chain origin labelling

Ground truth for the organic validation set (N=28). Every chain is a 4-step
linear pipeline (extractor, analyst, reasoner, writer) run under an information
bottleneck: each agent sees only the previous agent's output, never the source
document. The source document is the ground truth the chain was supposed to
stay faithful to.

Your job: read the source, then read the steps in order, and mark **the first
step whose output deviates from the source**.

## Fields

| Field | Values | Meaning |
|---|---|---|
| `cascade_occurred` | true / false | Did any step deviate from the source at all? |
| `origin_step` | 1..4, or null | First step that introduced a deviation. null only when `cascade_occurred` is false. |
| `error_type` | see below | Nature of the deviation at the origin step. |
| `evidence` | short string | Quote or paraphrase of the specific deviation. Required when a cascade occurred. |
| `notes` | string | Anything unclear, borderline, or worth flagging. Optional. |

## Error types

Pick the type that best describes what went wrong **at the origin step**. If two
apply, pick the one that caused the wrong final answer.

- **`omission`** — the step silently drops a fact from the source that the
  question needs. The text stays true, but incomplete. Typical case: a summary
  that leaves out the exclusion clause, the deadline, or the reserved amount.
  This is the mode drift and forward entailment cannot see, because a faithful
  subset entails perfectly.
- **`arithmetic`** — the numbers present are right but the calculation is wrong
  (wrong operator, wrong ceiling, sign error).
- **`misread`** — a fact from the source is present but its meaning is inverted
  or misapplied. Typical case: an amount marked "excluded" is included anyway,
  or a conditional rule is applied unconditionally.
- **`fabrication`** — a fact, number, or rule appears that is not in the source
  and cannot be derived from it.
- **`none`** — only valid when `cascade_occurred` is false.

## Rules for deciding the origin step

1. **First deviation wins.** If step 1 omits the exclusion clause and step 3
   then computes a wrong total because of it, the origin is step 1, not step 3.
   The later step is the cascade, not the origin.
2. **Judge each step against the source, not against the previous step.** A step
   that faithfully carries forward an earlier error is not itself an origin.
3. **Incompleteness counts as deviation** when the dropped fact is needed to
   answer the question. If the dropped fact is irrelevant to the question, it is
   not an error.
4. **Legitimate compression is not omission.** The writer step is supposed to be
   short. Dropping supporting detail while keeping the answer correct is fine.
5. **A truncated step is not automatically an error.** Some steps stop
   mid-sentence because of the generation token limit. Judge only the content
   that is present. Note the truncation in `notes`.
6. **When genuinely torn, pick the earlier step** and say why in `notes`. The
   `notes` field is what adjudication uses later.

## Independence rule (overlap set)

Ten chains are annotated by both annotators. Cohen's kappa is computed from
those ten only, and kappa is only meaningful if the two passes are independent.

**Do not read the other annotator's file, and do not read
`annotations-claude.json`, before finishing your own overlap set.** Reading any
other labels first turns the agreement number into an artefact.

If kappa lands below 0.6, that gets written into the paper as measured. It is a
finding about how hard origin attribution is to label, not something to hide.

## Machine-assisted labels

`annotations-claude.json` holds a full pass over all 28 chains produced by an
LLM assistant. It exists for two reasons:

1. As a draft for the 18 single-annotated chains, so a human verifies rather
   than labels from scratch.
2. As a cross-check: the same file also covers the 10 overlap chains, so
   LLM-versus-human agreement can be reported next to human-versus-human
   agreement on the same items.

Any label that reaches the paper must have been read by a human. The paper must
state that the single-annotated chains were LLM-drafted and human-verified.

## Running

```
python validation/annotation/prepare.py   # split + blank forms + review sheet
python validation/annotation/kappa.py     # agreement report once forms are filled
```
