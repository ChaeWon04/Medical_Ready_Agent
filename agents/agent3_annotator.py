import re
import json
from models.model_loader import llm
from schemas.ai_ready_schema import (
    AIReadyRecord, ClinicalContext, ClinicalSituation, RelationshipRole
)

SYSTEM_PROMPT = """You are a clinical context classifier.
Analyze the medical record and return ONLY valid JSON. No explanation."""

SITUATION_PROMPT = """Classify the clinical situation for this medical record.

Source: {source}
Chief complaint: {chief_complaint}
Symptoms: {symptoms}

Return JSON:
{{
  "situation": "outpatient|emergency|inpatient"
}}

Rules:
- inpatient: ICU, admission, ward, hospitalized
- emergency: ED, ER, urgent, acute
- outpatient: clinic, office, follow-up, ambulatory"""

SITUATION_SCHEMA = {
    "type": "object",
    "required": ["situation"],
    "properties": {
        "situation": {
            "type": "string",
            "enum": ["outpatient", "emergency", "inpatient"],
        }
    },
}

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

        for situation, keywords in SITUATION_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return situation

        if record.source == "mimic_iv":
            return ClinicalSituation.INPATIENT
        if record.source == "synthea":
            return ClinicalSituation.OUTPATIENT
        if record.source == "eicu":
            return ClinicalSituation.INPATIENT

        return self._llm_situation(record)

    def _llm_situation(self, record: AIReadyRecord) -> ClinicalSituation:
        prompt = SITUATION_PROMPT.format(
            source=record.source,
            chief_complaint=record.chief_complaint or "unknown",
            symptoms=", ".join(record.symptoms[:5]) or "none",
        )
        response = llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            json_schema=SITUATION_SCHEMA,
        )
        parsed = self._parse_json(response)

        mapping = {
            "outpatient": ClinicalSituation.OUTPATIENT,
            "emergency": ClinicalSituation.EMERGENCY,
            "inpatient": ClinicalSituation.INPATIENT,
        }
        return mapping.get(parsed.get("situation", ""), ClinicalSituation.OUTPATIENT)

    def _label_roles(self, record: AIReadyRecord) -> list[RelationshipRole]:
        roles = [RelationshipRole.PHYSICIAN, RelationshipRole.PATIENT]

        text = (record.clinical_text or "").lower()
        if any(kw in text for kw in ["family", "guardian", "parent", "caregiver", "보호자"]):
            roles.append(RelationshipRole.GUARDIAN)

        if (
            record.age is not None
            and record.age < 18
            and RelationshipRole.GUARDIAN not in roles
        ):
            roles.append(RelationshipRole.GUARDIAN)

        return roles

    def _calc_accessibility(self, record: AIReadyRecord) -> float:
        score = 0.0

        active_dx = [d for d in record.diagnoses if d.is_active]
        active_meds = [m for m in record.medications if m.is_active]

        if active_dx:
            score += 0.3
        if active_meds:
            score += 0.2
        if record.observations:
            score += 0.2

        valid_dx = [d for d in active_dx if d.icd10_code and not d.icd10_code.startswith("R99")]
        if valid_dx:
            score += 0.15

        if record.quality.q_index >= 0.8:
            score += 0.15
        elif record.quality.q_index >= 0.5:
            score += 0.07

        return round(min(1.0, score), 2)

    def _parse_json(self, response: str) -> dict:
        response = re.sub(r"```(?:json)?\s*|\s*```", "", response)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
