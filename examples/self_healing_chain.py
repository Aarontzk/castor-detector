"""Self-healing pattern: orchestrator (Claude, played here by this script)
uses Castor's per-step verdict to decide when to make the worker (qwen) redo
a step, then re-validates before continuing the chain.

Castor itself NEVER does this — it stays a passive observer (CLAUDE.md hard
rule: never modifies, blocks, or delays the pipeline). This loop lives
entirely OUTSIDE Castor: Castor only supplies the flag + reason; the
orchestrator decides what to do about it.

Why this avoids the "chain disloyalty" failure mode (PRD 2.2): a model asked
to review its OWN reasoning tends to rationalize and re-confirm it, not
correct it, because its own drifted output is already in its context. So the
retry prompt here does NOT say "check your answer" — it re-grounds the worker
in the ORIGINAL clean upstream facts and states the specific problem Castor
found, as if from a supervisor, not a self-critique.

Guardrails (so this can't loop or crash):
- max 1 retry per step (no infinite correction loops)
- correction is re-grounding with clean facts, never "please reconsider"
- if the retry is still flagged, the ORIGINAL output is kept and the step is
  reported as unresolved — Castor never silently swaps content the caller
  didn't ask for

Run:  .venv/Scripts/python examples/self_healing_chain.py
Needs: ollama serve + qwen2.5:3b pulled.
"""
from __future__ import annotations

import json
import urllib.request

from castor import CascadeAnalyzer, ThresholdProfile

OLLAMA = "http://localhost:11434/v1/messages"
MODEL = "qwen2.5:3b"

SOURCE = (
    "Nimbus Ltd reported Q1 revenue of 840,000 dollars with costs of 610,000 "
    "dollars. In Q2, revenue rose to 910,000 dollars while costs increased to "
    "700,000 dollars. A one-time grant of 15,000 dollars in Q2 is excluded "
    "from operating profit."
)
QUESTION = "How did Q2 operating profit compare to Q1?"

ROLES = [
    ("extractor", "Extract the facts relevant to the question from this document. "
                  "Max 3 sentences, no answer yet.\n\nDocument: {source}\n\nQuestion: {question}"),
    ("analyst",   "Using ONLY these extracted facts, compute what they imply. Show "
                  "any arithmetic explicitly. Max 4 sentences.\n\nQuestion: {question}"
                  "\n\nFacts: {previous}"),
    ("writer",    "Turn this analysis into a 2-sentence final answer.\n\n"
                  "Question: {question}\n\nAnalysis: {previous}"),
]

MAX_RETRIES = 1


def qwen(prompt: str) -> str:
    body = json.dumps(
        {"model": MODEL, "max_tokens": 250,
         "messages": [{"role": "user", "content": prompt}]}
    ).encode()
    req = urllib.request.Request(
        OLLAMA, data=body,
        headers={"Content-Type": "application/json", "x-api-key": "ollama"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    return "".join(block["text"] for block in data["content"] if block["type"] == "text").strip()


def correction_prompt(role: str, template: str, previous: str, reasons: tuple[str, ...]) -> str:
    """Re-ground the worker in clean upstream facts; state the problem as a
    supervisor finding, not a self-critique request (avoids chain disloyalty)."""
    original = template.format(source=SOURCE, question=QUESTION, previous=previous)
    return (
        f"{original}\n\n---\n"
        f"A supervisor checked your previous attempt at this exact task and found "
        f"a problem: {'; '.join(reasons)}. Redo the task above from scratch using "
        f"ONLY the facts given. Do not reference your previous attempt."
    )


def run_step(step_id: int, role: str, template: str, previous: str, analyzer: CascadeAnalyzer,
             trajectory: list[dict]) -> dict:
    """One chain step with up to MAX_RETRIES self-healing attempts."""
    prompt = template.format(source=SOURCE, question=QUESTION, previous=previous)
    for attempt in range(MAX_RETRIES + 1):
        output = qwen(prompt)
        candidate_trajectory = trajectory + [
            {"step_id": step_id, "agent_name": role, "role": "llm", "text": output}
        ]
        report = analyzer.analyze(candidate_trajectory)
        this_step = next(s for s in report.steps if s.step_id == step_id)

        if not this_step.flagged:
            status = "ok" if attempt == 0 else f"healed (attempt {attempt + 1})"
            print(f"[{role}] {status}: {output[:100]}...")
            return {"step_id": step_id, "agent_name": role, "role": "llm", "text": output}

        print(f"[{role}] attempt {attempt + 1} FLAGGED: {'; '.join(this_step.flag_reasons)}")
        if attempt < MAX_RETRIES:
            prompt = correction_prompt(role, template, previous, this_step.flag_reasons)

    print(f"[{role}] unresolved after {MAX_RETRIES + 1} attempts — keeping original output, "
          f"human review recommended")
    return {"step_id": step_id, "agent_name": role, "role": "llm", "text": output,
            "metadata": {"unresolved_flag": True}}


def main() -> None:
    analyzer = CascadeAnalyzer(
        profile=ThresholdProfile.load("validation/calibrated-general.json"),
        anchor=SOURCE,
    )
    trajectory: list[dict] = []
    previous = ""
    for step_id, (role, template) in enumerate(ROLES, 1):
        step = run_step(step_id, role, template, previous, analyzer, trajectory)
        trajectory.append(step)
        previous = step["text"]

    print("\n" + analyzer.analyze(trajectory).to_text())


if __name__ == "__main__":
    main()
