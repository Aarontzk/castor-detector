"""Delegation pattern: a strong orchestrator (Claude) hands subtasks to cheap
local qwen workers via Ollama's Anthropic-compatible /v1/messages endpoint,
while CastorObserver watches every handoff LIVE (UC-2).

This is the heterogeneous-chain pattern Castor is built for: the orchestrator
designs the roles and prompts; the small local model does the per-step work;
Castor flags the step where the worker chain starts drifting — in real time,
without blocking the pipeline.

Run:  .venv/Scripts/python examples/delegate_to_ollama.py
Needs: ollama serve + qwen2.5:3b pulled.
"""
from __future__ import annotations

import json
import urllib.request

from castor import CastorObserver, ThresholdProfile

OLLAMA = "http://localhost:11434/v1/messages"  # Anthropic-compatible endpoint
MODEL = "qwen2.5:3b"

SOURCE = (
    "Nimbus Ltd reported Q1 revenue of 840,000 dollars with costs of 610,000 "
    "dollars. In Q2, revenue rose to 910,000 dollars while costs increased to "
    "700,000 dollars. A one-time grant of 15,000 dollars in Q2 is excluded "
    "from operating profit."
)
QUESTION = "How did Q2 operating profit compare to Q1?"

# The orchestrator (Claude) designs the chain; qwen only executes one role at a time.
ROLES = [
    ("extractor", "Extract the facts relevant to the question from this document. "
                  "Max 3 sentences, no answer yet.\n\nDocument: {source}\n\nQuestion: {question}"),
    ("analyst",   "Using ONLY these extracted facts, compute what they imply. "
                  "Max 4 sentences.\n\nQuestion: {question}\n\nFacts: {previous}"),
    ("writer",    "Turn this analysis into a 2-sentence final answer.\n\n"
                  "Question: {question}\n\nAnalysis: {previous}"),
]


def qwen(prompt: str) -> str:
    """One delegated worker call (Claude -> qwen via Anthropic-compatible API)."""
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


def main() -> None:
    # Live observer: anchor = source doc, flags fire the moment a handoff drifts.
    observer = CastorObserver(
        profile=ThresholdProfile.load("validation/calibrated-general.json"),
        anchor=SOURCE,
        on_flag=lambda d: print(f"  !! CASTOR FLAG step {d.step_id}: {'; '.join(d.flag_reasons)}"),
    )

    previous = ""
    for step_id, (role, template) in enumerate(ROLES, 1):
        output = qwen(template.format(source=SOURCE, question=QUESTION, previous=previous))
        print(f"[{role}] {output[:120]}...")
        observer.observe({"step_id": step_id, "agent_name": role, "role": "llm", "text": output})
        previous = output

    print("\n" + observer.report().to_text())


if __name__ == "__main__":
    main()
