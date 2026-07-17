import json
import re
import config
from models.model_loader import llm
from rag.retriever import retriever
from schemas.ai_ready_schema import AIReadyRecord, QualityMetadata, DataStatus
from agents.criteria import run_rule_checks
from config import MAX_REFLEXION_LOOPS, QUALITY_THRESHOLD


def _log(msg: str):
    # config.RUN_LOG를 (이름이 아니라) 모듈 속성으로 매번 읽어야, main.py가 실행 중에
    # split(train/test)별 경로로 바꿔치기한 값을 그대로 따라간다 - "from config import RUN_LOG"로
    # 받으면 import 시점 값에 고정돼서 main.py가 나중에 바꿔도 반영이 안 됨
    print(msg)
    with open(config.RUN_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

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
    {{"field": "...", "issue": "...", "suggested_fix": "...", "code": "NR5"}}
  ],
  "passed": true
}}

Each issue's "code" must be exactly one of:
- "NR11" — medication dose/unit errors (check 1 below)
- "NR5"  — everything else (negation failures, reference-context contradictions, copy-forward
  duplicates, no active diagnoses — checks 2-5 below)

The reference context only covers a few of this patient's conditions — it is background reading, not a checklist.
A diagnosis/medication/observation that is simply not mentioned in the context is NOT an error by itself.

This record comes from MIMIC-IV prescription order data, which is an administration log, not a curated
medication list. The SAME drug name legitimately appears multiple times with different doses/times/routes
(e.g. dose titration, scheduled redosing, PRN doses). Do NOT flag repeated medication names as duplicates
or errors — only flag a medication entry if its OWN dose/unit is individually implausible or malformed.

Check for:
1. Medication dose errors (unit mismatch: g vs mg vs mcg, or implausible dose value) — evaluate each entry independently
2. Negation failures (ruled_out diagnosis marked as confirmed)
3. Values that directly CONTRADICT the reference context (e.g. context states a fact and the record states the opposite) — do NOT flag something merely because the context is silent about it
4. Copy-forward errors: same ICD-10 code AND same onset_date (different dates = separate encounters, NOT duplicates)
5. No active clinical diagnoses (zero is_active=true items)

Do NOT check ICD-10 code-vs-description matching — that is already validated deterministically upstream against the official ICD-10 crosswalk and is out of scope here.

Do NOT flag any of the following — they are valid:
- SNOMED description suffixes: "(finding)", "(disorder)", "(situation)", "(morphologic abnormality)" are standard terminology
- Standard UCUM units: "Cel", "mm[Hg]", "10*3/uL", "10*6/uL", "g/dL", "kg/m2", "/min", "%", "fL", "pg" are all correct
- Z-codes (Z00-Z99) that reflect real documented patient conditions
- Same ICD-10 code appearing with different onset_dates (separate clinical encounters)
- Any diagnosis, medication, or observation that the reference context simply doesn't mention
- The same medication name appearing multiple times (this is expected administration-log behavior, not a duplicate)

Reminder before you answer: "not mentioned in context" and "repeated medication name" are NEVER by themselves
reasons to add an entry to "issues". Only include an issue if you can point to a concrete, self-contained
error in the record.

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

        passages = self._retrieve_context(record)
        context = self._format_context(passages)
        _log(f"\n[Agent2] record_id={record.record_id[:8]} - [RAG] 검색 실행 ({len(passages)}건 근거 조회)")
        if passages:
            for i, (text, score) in enumerate(passages, 1):
                snippet = text[:100].replace("\n", " ")
                _log(f"  [RAG] 근거 {i} (유사도 {score}): {snippet}...")
        else:
            _log("  [RAG] 검색된 근거 없음")

        for loop in range(MAX_REFLEXION_LOOPS):
            _log(f"[Agent2] Loop {loop + 1}/{MAX_REFLEXION_LOOPS} 시작 (record_id={record.record_id[:8]})")
            issues = self._critic(record, context)
            history.append((record, issues, loop + 1))

            if not issues:
                _log(f"[Agent2] Loop {loop + 1}: 문제 없음 -> 종료")
                break

            q_index = self._calc_q_index(record, issues, loop + 1)
            if q_index >= QUALITY_THRESHOLD:
                _log(f"[Agent2] Loop {loop + 1}: Q-index {q_index} >= 임계값 {QUALITY_THRESHOLD} -> 종료")
                break

            _log(f"[Agent2] Loop {loop + 1}: {len(issues)}건 문제 발견 -> Refine 실행")
            record = self._refine(record, issues)

        best_record, best_issues, best_loops = min(history, key=lambda x: len(x[1]))

        # 최종 규칙 기반 감사 (NR1/NR2/NR4/NR7) - refine 루프엔 안 넣음.
        # 이유: 정말 데이터가 비어있는 걸 LLM이 "고치려고" 하면 값을 지어내서 hallucination만 늘어남.
        # 그래서 loop 다 끝난 best_record에 대해서만 감사하고, 결과는 issue 카운트/사유 코드에만 반영.
        rule_issues = run_rule_checks(best_record)
        all_issues = best_issues + rule_issues

        active_dx = [d for d in best_record.diagnoses if d.is_active]
        has_context = bool(best_record.chief_complaint or best_record.symptoms)

        reason_codes = {i.get("code", "") for i in rule_issues if i.get("code")}
        # Critic이 각 issue에 매긴 code(NR5/NR11)를 그대로 씀. LLM이 code를 빼먹거나
        # 잘못된 값을 주면(스키마 enum이 있어도 완전히 강제는 안 되므로) NR8(catch-all)로 대체.
        reason_codes |= {
            i["code"] if i.get("code") in ("NR5", "NR11") else "NR8"
            for i in best_issues
        }
        if not active_dx:
            reason_codes.add("NR9")
        if not has_context:
            reason_codes.add("NR3")
        reason_codes = sorted(reason_codes)

        best_record.quality = QualityMetadata(
            reflexion_loops=best_loops,
            hallucination_flags=[
                f"[{i.get('code') or 'NR8'}] {i.get('issue', '')}" for i in all_issues
            ],
            reason_codes=reason_codes,
            q_index=self._calc_q_index(best_record, all_issues, best_loops),
            status=(
                DataStatus.AI_READY
                if (not all_issues and active_dx and has_context)
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

    def _critic(self, record: AIReadyRecord, context: str) -> list[dict]:
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
                            "code": {"type": "string", "enum": ["NR5", "NR11"]},
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
        filtered = self._filter_false_positives(parsed.get("issues", []))

        if filtered:
            _log(f"  [Critic] 판정: {len(filtered)}건 문제 발견")
        else:
            _log("  [Critic] 판정: 문제 없음")

        return filtered

    def _format_context(self, passages: list[tuple[str, float]]) -> str:
        if not passages:
            return "No reference context available."
        return "\n\n".join(
            f"[Reference {i+1}]\n{text}" for i, (text, _) in enumerate(passages)
        )

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
            corrected_record.diagnoses = self._lock_diagnosis_codes(record.diagnoses, corrected_record.diagnoses)
            return corrected_record
        except Exception:
            return record

    def _lock_diagnosis_codes(self, original: list, corrected: list) -> list:
        """icd10_code/description은 파싱 단계에서 공식 크로스워크로 이미 검증된 값이라
        refine이 절대 못 건드리게 원본으로 되돌림. is_active/is_negated/confidence 같은
        판단이 필요한 필드만 refine 결과를 그대로 씀 (negation failures 등은 정상적으로 고쳐짐).
        refine이 리스트 개수/순서를 바꿔버리면(코드/설명을 index로 매칭할 수 없는 상태) 안전하게
        원본 diagnoses 전체를 그대로 반환."""
        if len(original) != len(corrected):
            return original
        locked = []
        for orig_dx, new_dx in zip(original, corrected):
            new_dx.icd10_code = orig_dx.icd10_code
            new_dx.description = orig_dx.description
            locked.append(new_dx)
        return locked

    _SNOMED_FP = (
        "has a description 'finding'",
        "has a description 'disorder'",
        "has a description 'situation'",
        "has a description 'morphologic",
        "is not a standard chief complaint",
        "not a clinical diagnosis",
        "is redundant",
    )
    _UCUM_FP = (
        "'Cel'", "should be 'Celsius'", "should be '°C'",
        "'mm[Hg]'", "should be 'mmHg'",
        "'10*3/uL'", "'10*6/uL'",
        "should be '10^3", "should be '10^6",
    )
    _CORRECT_FP = (" is correct ", " is valid", "but the chief complaint is")
    _DUPE_FP = ("same onset_date",)
    # 모델이 스스로 "문제 아님"이라고 결론 내려놓고도 issues 리스트엔 넣는 자기모순 패턴
    # (소문자로 비교해서 대소문자 표기 흔들림 방지)
    _SELF_CONTRADICT_FP = (
        "not an error", "not an issue", "no mismatch found", "no error found",
        "which is plausible", "which matches the description", "which is valid",
        "which is correct", "which is expected", "this is not incorrect",
    )

    def _filter_false_positives(self, issues: list[dict]) -> list[dict]:
        filtered = []
        for issue in issues:
            text = issue.get("issue", "")
            text_lower = text.lower()
            if any(p in text for p in self._SNOMED_FP):
                continue
            if any(p in text for p in self._UCUM_FP):
                continue
            if any(p in text for p in self._CORRECT_FP):
                continue
            if any(p in text for p in self._DUPE_FP):
                continue
            if any(p in text_lower for p in self._SELF_CONTRADICT_FP):
                continue
            filtered.append(issue)
        return filtered

    def _build_query(self, record: AIReadyRecord) -> str:
        parts = []
        for dx in record.diagnoses[:3]:
            parts.append(dx.description)
        for med in record.medications[:3]:
            parts.append(med.name)
        return " ".join(parts) if parts else "medical record validation"

    def _retrieve_context(self, record: AIReadyRecord, per_query_k: int = 2,
                           max_passages: int = 10) -> list[tuple[str, float]]:
        """진단마다 개별 검색해서 근거 커버리지를 넓힘 (상위 3개짜리 통합 쿼리 하나로는
        진단이 많은 레코드의 나머지 진단들이 근거 없이 critic한테 넘어가는 문제가 있었음)"""
        dx_descriptions = [dx.description for dx in record.diagnoses if dx.description][:10]
        queries = dx_descriptions if dx_descriptions else [self._build_query(record)]

        best_by_text: dict[str, float] = {}
        for q in queries:
            for text, score in retriever.retrieve_with_scores(q, top_k=per_query_k):
                if text not in best_by_text or score > best_by_text[text]:
                    best_by_text[text] = score

        ranked = sorted(best_by_text.items(), key=lambda x: x[1], reverse=True)
        return ranked[:max_passages]

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
