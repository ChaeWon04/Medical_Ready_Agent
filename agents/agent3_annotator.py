import re
import json
from models.model_loader import llm
from schemas.ai_ready_schema import (
    AIReadyRecord, ClinicalContext, ClinicalSituation, RelationshipRole
)

SYSTEM_PROMPT = """You are a clinical context classifier.
Analyze the medical record and return ONLY valid JSON. No explanation."""

ANNOTATE_PROMPT = """Analyze this medical record and classify its clinical context.

Medical record:
{record}

Return JSON:
{{
  "situation": "outpatient|emergency|inpatient",
  "roles": ["physician", "patient", "guardian"],
  "accessibility_score": 0.0
}}

Rules:
- situation: outpatient(외래/진료), emergency(응급실), inpatient(입원)
  - Clues: ICU/admission → inpatient, ED/ER → emergency, clinic/office → outpatient
- roles: list of roles present in the record
- accessibility_score: 0.0~1.0
  - 1.0 = complete, structured, no jargon
  - 0.5 = partial data or heavy abbreviations
  - 0.0 = missing critical fields or unreadable"""

SITUATION_KEYWORDS = {
    ClinicalSituation.INPATIENT: ["icu", "inpatient", "admission", "admitted", "ward", "hospitalized"],
    ClinicalSituation.EMERGENCY: ["emergency", "ed", "er", "urgent", "acute"],
    ClinicalSituation.OUTPATIENT: ["outpatient", "clinic", "office", "follow-up", "ambulatory"],
}


class Agent3Annotator:

    def annotate(self, record: AIReadyRecord) -> AIReadyRecord:
        situation = self._tag_situation(record)
        roles = self._label_roles(record)
        score = self._calc_accessibility(record)

        record.context = ClinicalContext(
            situation=situation,
            roles=roles,
            accessibility_score=score,
        )
        return record

    def _tag_situation(self, record: AIReadyRecord) -> ClinicalSituation:
        text = (record.clinical_text or "").lower()

        # 룰 기반 먼저
        for situation, keywords in SITUATION_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return situation

        # 데이터 소스 기반 fallback
        if record.source == "mimic_iv":
            return ClinicalSituation.INPATIENT  # MIMIC-IV는 ICU 데이터

        # LLM fallback
        return self._llm_situation(record)

    def _llm_situation(self, record: AIReadyRecord) -> ClinicalSituation:
        prompt = ANNOTATE_PROMPT.format(record=record.model_dump_json(indent=2))
        response = llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
        parsed = self._parse_json(response)

        raw = parsed.get("situation", "")
        mapping = {
            "outpatient": ClinicalSituation.OUTPATIENT,
            "emergency": ClinicalSituation.EMERGENCY,
            "inpatient": ClinicalSituation.INPATIENT,
        }
        return mapping.get(raw, ClinicalSituation.OUTPATIENT)

    def _label_roles(self, record: AIReadyRecord) -> list[RelationshipRole]:
        # 임상 기록에는 항상 의사와 환자가 존재
        roles = [RelationshipRole.PHYSICIAN, RelationshipRole.PATIENT]

        text = (record.clinical_text or "").lower()
        if any(kw in text for kw in ["family", "guardian", "parent", "caregiver", "보호자"]):
            roles.append(RelationshipRole.GUARDIAN)

        return roles

    def _calc_accessibility(self, record: AIReadyRecord) -> float:
        score = 0.0

        # 필드 존재 여부
        if record.diagnoses:
            score += 0.3
        if record.medications:
            score += 0.2
        if record.observations:
            score += 0.2

        # ICD-10 코드 정규화 여부
        if record.diagnoses and all(dx.icd10_code for dx in record.diagnoses):
            score += 0.15

        # 품질 지수 반영
        if record.quality.q_index >= 0.8:
            score += 0.15
        elif record.quality.q_index >= 0.5:
            score += 0.07

        return round(min(1.0, score), 2)

    def _parse_json(self, response: str) -> dict:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
