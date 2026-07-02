import json
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
1. ICD-10 code clearly mismatched with description (e.g. cardiac code paired with respiratory description)
2. Medication dose errors (unit mismatch: g vs mg vs mcg, or implausible dose value)
3. Negation failures (ruled_out diagnosis marked as confirmed)
4. Hallucinated values not supported by context
5. Copy-forward errors: same ICD-10 code AND same onset_date (different dates = separate encounters, NOT duplicates)
6. No active clinical diagnoses (zero is_active=true items)

Do NOT flag any of the following — they are valid:
- SNOMED description suffixes: "(finding)", "(disorder)", "(situation)", "(morphologic abnormality)" are standard terminology
- Standard UCUM units: "Cel", "mm[Hg]", "10*3/uL", "10*6/uL", "g/dL", "kg/m2", "/min", "%", "fL", "pg" are all correct
- Z-codes (Z00-Z99) that reflect real documented patient conditions
- Same ICD-10 code appearing with different onset_dates (separate clinical encounters)

If no issues found, return {{"issues": [], "passed": true}}"""

REFINE_SYSTEM = """You are a medical data correction assistant.
Fix the medical record based on the issues list and return ONLY the corrected record as valid JSON."""

REFINE_PROMPT = """Fix the medical record below based on the issues list.

Issues to fix:
{issues}

Original record:
{record}

Return the corrected record in the same JSON structure. No explanation."""

REFINE_SCHEMA = {
    "type": "object",
    "required": ["record_id", "source", "patient_id", "diagnoses",
                 "medications", "observations", "quality"],
    "properties": {
        "record_id": {"type": "string"},
        "source": {"type": "string"},
        "patient_id": {"type": "string"},
        "age": {"type": ["integer", "null"]},
        "gender": {"type": ["string", "null"]},
        "chief_complaint": {"type": ["string", "null"]},
        "symptoms": {"type": "array", "items": {"type": "string"}},
        "diagnoses": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["icd10_code", "description", "confidence"],
                "properties": {
                    "icd10_code": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "string",
                                   "enum": ["confirmed", "suspected", "ruled_out"]},
                    "is_negated": {"type": "boolean"},
                    "is_active": {"type": "boolean"},
                    "onset_date": {"type": ["string", "null"]},
                },
            },
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "dose": {"type": ["number", "null"]},
                    "unit": {"type": ["string", "null"]},
                    "route": {"type": ["string", "null"]},
                    "frequency": {"type": ["string", "null"]},
                    "is_active": {"type": "boolean"},
                },
            },
        },
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "value"],
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "unit": {"type": ["string", "null"]},
                    "is_abnormal": {"type": ["boolean", "null"]},
                    "observed_date": {"type": ["string", "null"]},
                },
            },
        },
        "quality": {"type": "object"},
    },
}


class Agent2Reflexion:

    _OBS_WHITELIST = frozenset({
        "Systolic Blood Pressure", "Diastolic Blood Pressure",
        "Heart rate", "Respiratory rate", "Body temperature",
        "Body Height", "Body Weight", "Body mass index (BMI) [Ratio]",
        "Hemoglobin [Mass/volume] in Blood",
        "Leukocytes [#/volume] in Blood by Automated count",
        "Glucose [Mass/volume] in Blood",
        "Creatinine [Mass/volume] in Blood",
        "Platelets [#/volume] in Blood by Automated count",
        "Sodium [Moles/volume] in Serum or Plasma",
        "Potassium [Moles/volume] in Serum or Plasma",
        "Oxygen saturation in Arterial blood",
    })

    def run(self, record: AIReadyRecord) -> AIReadyRecord:
        history = []  # (record, issues, loop_num)

        for loop in range(MAX_REFLEXION_LOOPS):
            issues = self._critic(record)
            history.append((record, issues, loop + 1))

            if not issues:
                break

            if self._calc_q_index(record, issues, loop + 1) >= QUALITY_THRESHOLD:
                break

            record = self._refine(record, issues)

        best_record, best_issues, best_loops = min(history, key=lambda x: len(x[1]))

        active_dx = [d for d in best_record.diagnoses if d.is_active]
        has_context = bool(best_record.chief_complaint or best_record.symptoms)

        best_record.quality = QualityMetadata(
            reflexion_loops=best_loops,
            hallucination_flags=[i.get("issue", "") for i in best_issues],
            q_index=self._calc_q_index(best_record, best_issues, best_loops),
            status=(
                DataStatus.AI_READY
                if (not best_issues and active_dx and has_context)
                else DataStatus.NEEDS_REVIEW
            ),
        )
        return best_record

    def _slim_record(self, record: AIReadyRecord) -> dict:
        return {
            "age": record.age,
            "gender": record.gender,
            "chief_complaint": record.chief_complaint,
            "symptoms": record.symptoms[:5],
            "diagnoses": [
                {
                    "icd10_code": d.icd10_code,
                    "description": d.description,
                    "confidence": d.confidence,
                    "is_active": d.is_active,
                }
                for d in record.diagnoses
            ],
            "medications": [
                {"name": m.name, "dose": m.dose, "unit": m.unit}
                for m in record.medications if m.is_active
            ],
            "observations": [
                {"name": o.name, "value": o.value, "unit": o.unit}
                for o in record.observations
                if o.name in self._OBS_WHITELIST
            ],
        }

    def _critic(self, record: AIReadyRecord) -> list[dict]:
        query = self._build_query(record)
        context = retriever.format_context(query)
        slim = json.dumps(self._slim_record(record), indent=2)
        prompt = CRITIC_PROMPT.format(context=context, record=slim)

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
                            "suggested_fix": {"type": "string"},
                        },
                    },
                },
                "passed": {"type": "boolean"},
            },
        }

        response = llm.generate(
            system_prompt=CRITIC_SYSTEM,
            user_prompt=prompt,
            json_schema=critic_schema,
        )

        parsed = self._parse_json(response)
        return parsed.get("issues", [])

    def _refine(self, record: AIReadyRecord, issues: list[dict]) -> AIReadyRecord:
        issues_str = json.dumps(issues)
        refine_input = json.loads(record.model_dump_json())
        refine_input["observations"] = [
            o for o in refine_input["observations"]
            if o["name"] in self._OBS_WHITELIST
        ]
        record_json = json.dumps(refine_input)

        prompt = REFINE_PROMPT.format(issues=issues_str, record=record_json)
        response = llm.generate(
            system_prompt=REFINE_SYSTEM,
            user_prompt=prompt,
            json_schema=REFINE_SCHEMA,
        )

        corrected = self._parse_json(response)
        if not corrected:
            return record

        try:
            corrected_record = AIReadyRecord(**corrected)
            corrected_record.observations = record.observations
            return corrected_record
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
        score -= len(issues) * 0.1
        score -= (loops - 1) * 0.05
        active_dx = [d for d in record.diagnoses if d.is_active]
        if not active_dx:
            score -= 0.2
        if not record.medications and not record.observations:
            score -= 0.1
        if not record.chief_complaint and not record.symptoms:
            score -= 0.1
        return round(max(0.0, min(1.0, score)), 2)

    def _parse_json(self, response: str) -> dict:
        response = re.sub(r"```(?:json)?\s*|\s*```", "", response)
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
