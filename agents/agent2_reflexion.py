import json
import os
import re
from models.model_loader import llm
from rag.retriever import retriever
from schemas.ai_ready_schema import AIReadyRecord, QualityMetadata, DataStatus
from config import MAX_REFLEXION_LOOPS, QUALITY_THRESHOLD

CRITIC_SYSTEM = """You are a medical data quality auditor.
Check the given medical record for errors and return ONLY valid JSON. No explanation."""

CRITIC_PROMPT = """Check this medical record for errors using the reference context below.

Reference context from medical literature:
{context}

Medical record:
{record}

Return JSON with this format:
{{
  "issues": [
    {{"field": "...", "issue": "...", "suggested_fix": "..."}}
  ],
  "passed": true
}}

Check for:
1. ICD-10 code mismatch with description
2. Medication dose errors (unit mismatch: g vs mg vs mcg)
3. Negation failures (ruled_out diagnosis marked as confirmed)
4. Hallucinated values not supported by context
5. Copy-forward errors (duplicate identical entries)
6. Empty diagnoses list (flag if diagnoses array is empty)

If no issues found, return {{"issues": [], "passed": true}}"""

REFINE_SYSTEM = """You are a medical data correction assistant.
Fix the medical record based on the issues list and return ONLY the corrected record as valid JSON."""

REFINE_PROMPT = """Fix the medical record below based on the issues list.

Issues to fix:
{issues}

Original record:
{record}

Return the corrected record in the same JSON structure. No explanation."""


class Agent2Reflexion:

    def run(self, record: AIReadyRecord) -> AIReadyRecord:
        issues = []
        loops = 0

        for loop in range(MAX_REFLEXION_LOOPS):
            loops = loop + 1
            issues = self._critic(record)

            if not issues:
                break

            record = self._refine(record, issues)

        record.quality = QualityMetadata(
            reflexion_loops=loops,
            hallucination_flags=[i.get("issue", "") for i in issues],
            q_index=self._calc_q_index(record, issues, loops),
            status=DataStatus.AI_READY if (not issues and record.diagnoses) else DataStatus.NEEDS_REVIEW,
        )
        return record

    def _critic(self, record: AIReadyRecord) -> list[dict]:
        query = self._build_query(record)
        context = retriever.format_context(query)
        record_json = record.model_dump_json(indent=2)
        prompt = CRITIC_PROMPT.format(context=context, record=record_json)

        critic_schema = {
            "type": "object",
            "required": ["issues", "passed"],
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string"},
                            "issue": {"type": "string"},
                            "suggested_fix": {"type": "string"}
                        }
                    }
                },
                "passed": {"type": "boolean"}
            }
        }

        response = llm.generate(
            system_prompt=CRITIC_SYSTEM,
            user_prompt=prompt,
            json_schema=critic_schema   # A파트 완료 후 실제 동작
        )

        parsed = self._parse_json(response)
        return parsed.get("issues", [])

    def _refine(self, record: AIReadyRecord, issues: list[dict]) -> AIReadyRecord:
        issues_str = json.dumps(issues, indent=2)
        record_json = record.model_dump_json(indent=2)

        prompt = REFINE_PROMPT.format(issues=issues_str, record=record_json)
        response = llm.generate(system_prompt=REFINE_SYSTEM, user_prompt=prompt)

        corrected = self._parse_json(response)
        if not corrected:
            return record

        try:
            return AIReadyRecord(**corrected)
        except Exception:
            return record

    def _build_query(self, record: AIReadyRecord) -> str:
        parts = []
        for dx in record.diagnoses[:3]:
            parts.append(dx.description)
        for med in record.medications[:3]:
            parts.append(med.name)
        return " ".join(parts) if parts else "medical record validation"

    def _calc_q_index(self, record: AIReadyRecord, issues: list[dict], loops: int) -> float:
        score = 1.0
        score -= len(issues) * 0.1          # 오류 하나당 -0.1
        score -= (loops - 1) * 0.05         # 루프 추가 시마다 -0.05
        if not record.diagnoses:
            score -= 0.2
        if not record.medications and not record.observations:
            score -= 0.1
        return round(max(0.0, min(1.0, score)), 2)

    def _parse_json(self, response: str) -> dict:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
