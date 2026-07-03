"""Semi-natural dataset generator (PRD S12.2): real local LLM agent chain via Ollama.

Linear 4-agent chain with information bottleneck — each agent sees ONLY the
previous agent's output, never the source document. This reproduces the
cascade mechanism organically (H-05, H-10): extraction slips propagate as
authoritative context.

Run:  .venv/Scripts/python validation/agent_chain.py
Writes one trajectory JSON per task to validation/organic/.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://localhost:11434/api/generate"
OUT_DIR = Path(__file__).resolve().parent / "organic"

AGENTS = [
    (
        "extractor",
        "You are a fact extraction agent. Extract the facts from the document "
        "that are relevant to the question. Be concise (max 4 sentences). "
        "Do not answer the question yet.\n\nDocument:\n{source}\n\nQuestion: {question}",
    ),
    (
        "analyst",
        "You are an analyst agent. Using ONLY the extracted facts below, work out "
        "what they mean for the question. Show any calculation briefly (max 4 "
        "sentences).\n\nQuestion: {question}\n\nExtracted facts:\n{previous}",
    ),
    (
        "reasoner",
        "You are a reasoning agent. Based ONLY on the analysis below, draw a "
        "conclusion and one recommendation (max 3 sentences).\n\nQuestion: "
        "{question}\n\nAnalysis:\n{previous}",
    ),
    (
        "writer",
        "You are a writing agent. Turn the conclusion below into a short final "
        "answer for the user (max 3 sentences).\n\nQuestion: {question}\n\n"
        "Conclusion:\n{previous}",
    ),
]

TASKS = [
    {
        "id": "organic-01",
        "question": "How did Q2 profit compare to Q1?",
        "source": "Nimbus Ltd reported Q1 revenue of 840,000 dollars with costs of 610,000 dollars. In Q2, revenue rose to 910,000 dollars while costs increased to 700,000 dollars. The company also received a one-time grant of 15,000 dollars in Q2, which is excluded from operating profit.",
    },
    {
        "id": "organic-02",
        "question": "Which warehouse should handle the new order of 450 units?",
        "source": "The Bekasi warehouse has 380 units in stock and can ship within 2 days. The Semarang warehouse has 520 units but needs 5 days to ship. Orders above 400 units may be split between warehouses if needed. The customer requested delivery within 4 days.",
    },
    {
        "id": "organic-03",
        "question": "Is the reactor within safe operating limits?",
        "source": "The cooling system operates safely between 40 and 75 degrees Celsius. Sensor A reads 71 degrees, sensor B reads 68 degrees. Sensor A was flagged last month for reading 3 degrees too high and is scheduled for recalibration. Readings above 74 degrees require immediate shutdown.",
    },
    {
        "id": "organic-04",
        "question": "How many buses are needed for the school trip?",
        "source": "The school trip includes 174 students and 12 teachers. Each bus seats 45 passengers. Two students use wheelchairs, and each wheelchair space replaces 3 regular seats. School policy requires at least one teacher per bus.",
    },
    {
        "id": "organic-05",
        "question": "Did the marketing campaign meet its target?",
        "source": "The campaign targeted 3,000 new sign-ups with a budget of 20,000 dollars. It achieved 3,420 sign-ups but spent 24,500 dollars. The cost-per-signup target was 7 dollars. Sign-ups from the partner channel, 400 of the total, are excluded from the campaign's own performance count.",
    },
    {
        "id": "organic-06",
        "question": "Kapan sebaiknya panen dilakukan?",
        "source": "Padi varietas Ciherang biasanya dipanen 115 sampai 125 hari setelah tanam. Sawah ini ditanami tanggal 10 Maret. Curah hujan tinggi diperkirakan mulai minggu kedua Juli. Panen saat hujan menurunkan kualitas gabah dan menaikkan biaya pengeringan sekitar 20 persen.",
    },
    {
        "id": "organic-07",
        "question": "Should the flight be delayed for the connecting passengers?",
        "source": "Flight GA-204 departs at 14:30 with 143 passengers booked. Twelve passengers connect from flight GA-118, which lands at 13:50, a 25-minute walk from the departure gate. Policy allows delays up to 20 minutes if more than 10 connecting passengers are affected. A delay beyond 15 minutes forfeits the departure slot, adding a further 40-minute wait.",
    },
    {
        "id": "organic-08",
        "question": "Berapa sisa anggaran proyek dan cukupkah untuk fase akhir?",
        "source": "Anggaran proyek total 500 juta rupiah. Fase satu menghabiskan 180 juta, fase dua 210 juta. Fase akhir diperkirakan butuh 95 juta rupiah. Ada dana kontingensi terpisah 50 juta yang hanya boleh dipakai dengan persetujuan direksi.",
    },
]


def ask(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.8, "num_predict": 220},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read())["response"].strip()


def run_chain(task: dict) -> dict:
    steps = []
    previous = ""
    for index, (agent, template) in enumerate(AGENTS, 1):
        prompt = template.format(
            source=task["source"], question=task["question"], previous=previous
        )
        t0 = time.perf_counter()
        output = ask(prompt)
        seconds = time.perf_counter() - t0
        print(f"  {agent}: {seconds:.1f}s, {len(output)} chars")
        steps.append(
            {
                "step_id": index,
                "agent_name": agent,
                "role": "llm",
                "text": output,
                "metadata": {"latency_s": round(seconds, 2)},
            }
        )
        previous = output
    return {
        "id": task["id"],
        "question": task["question"],
        "source": task["source"],
        "model": MODEL,
        "temperature": 0.8,
        "steps": steps,
    }


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for task in TASKS:
        print(f"{task['id']}: {task['question']}")
        result = run_chain(task)
        out = OUT_DIR / f"{task['id']}.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {out.name}")


if __name__ == "__main__":
    main()
