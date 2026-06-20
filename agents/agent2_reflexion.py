import json
import os
from config import USE_CLAUDE_API, MAX_REFINE_ITERATIONS, QUALITY_THRESHOLD, CLAUDE_MODEL
from schemas.ai_ready_schema import AIReadyRecord
from rag.retriever import retrieve
from models.model_loader import generate


def _critic_local(record: AIReadyRecord, context: list[str]) -> tuple[float, str]:
    prompt = (
        f"You are a medical QA critic. Evaluate this clinical record:\n"
        f"{record.model_dump_json(indent=2)}\n\n"
        f"Reference context:\n{chr(10).join(context)}\n\n"
        'Check: ICD-10 validity, negation errors, clinical consistency.\n'
        'Return JSON: {"score": 0.0-1.0, "feedback": "..."}'
    )
    raw = generate(prompt)
    try:
        result = json.loads(raw)
        return float(result["score"]), result["feedback"]
    except Exception:
        return 0.5, raw


def _critic_claude(record: AIReadyRecord, context: list[str]) -> tuple[float, str]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = (
        f"You are a medical QA critic. Evaluate this clinical record:\n"
        f"{record.model_dump_json(indent=2)}\n\n"
        f"Reference context:\n{chr(10).join(context)}\n\n"
        'Check: ICD-10 validity, negation errors, clinical consistency.\n'
        'Return JSON: {"score": 0.0-1.0, "feedback": "..."}'
    )
    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    try:
        result = json.loads(raw)
        return float(result["score"]), result["feedback"]
    except Exception:
        return 0.5, raw


def _refine(record: AIReadyRecord, feedback: str) -> AIReadyRecord:
    prompt = (
        f"Fix this clinical record based on feedback.\n"
        f"Record: {record.model_dump_json()}\n"
        f"Feedback: {feedback}\n"
        "Return corrected JSON only."
    )
    raw = generate(prompt)
    try:
        return AIReadyRecord(**json.loads(raw))
    except Exception:
        return record


def run(record: AIReadyRecord) -> AIReadyRecord:
    critic_fn = _critic_claude if USE_CLAUDE_API else _critic_local
    score, feedback = 0.0, ""

    for _ in range(MAX_REFINE_ITERATIONS):
        context = retrieve(" ".join(record.diagnoses + record.symptoms))
        score, feedback = critic_fn(record, context)

        if score >= QUALITY_THRESHOLD:
            record.quality_score = score
            return record

        record = _refine(record, feedback)

    # 최대 반복 초과 → 사람 검토 플래그
    record.quality_score = score
    record.flagged = True
    return record
