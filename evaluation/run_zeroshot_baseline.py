"""
Type3(Hallucination 감소율) 비교용 "단일 LLM Zero-shot" 베이스라인 생성기.

에이전트 구조(Parser 규칙기반 처리 -> Critic/Refine 반복검증 -> Annotator) 없이,
같은 원본 데이터를 Qwen3-4B에 그대로 넣고 딱 한 번만 호출해서 구조화한다.
data/test/ai_ready_*.jsonl에 이미 있는 것과 동일한 50명(MIMIC)/50명(eICU) 환자에 대해서만 생성.

사전 준비물 (main.py 돌릴 때와 동일):
  vllm serve Qwen/Qwen3-4B --port 8000 --dtype auto
  export VLLM_BASE_URL=http://localhost:8000/v1

실행:
  python evaluation/run_zeroshot_baseline.py --source mimic
  python evaluation/run_zeroshot_baseline.py --source eicu
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

from models.model_loader import llm

ROOT = Path(__file__).parent.parent
TEST_DIR = ROOT / "data" / "test"

SYSTEM_PROMPT = """You are a medical data extraction assistant.
Extract structured information from the raw clinical records below and return ONLY valid JSON. No explanation, no markdown."""

ZEROSHOT_PROMPT = """Below is raw clinical data for one patient. Extract diagnoses and medications
and return them in the exact JSON format shown. Do not invent any value that is not present or
directly implied by the data below.

Raw data:
{raw_data}

Return JSON in this exact format:
{{
  "diagnoses": [
    {{"icd10_code": "...", "description": "...", "confidence": "confirmed|suspected|ruled_out"}}
  ],
  "medications": [
    {{"name": "...", "dose": null, "unit": null}}
  ]
}}"""

ZEROSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "diagnoses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "icd10_code": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["confirmed", "suspected", "ruled_out"]},
                },
                "required": ["icd10_code", "description", "confidence"],
            },
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dose": {"type": ["number", "null"]},
                    "unit": {"type": ["string", "null"]},
                },
                "required": ["name"],
            },
        },
    },
    "required": ["diagnoses", "medications"],
}


def _parse_json(response: str) -> dict:
    response = re.sub(r"```(?:json)?\s*|\s*```", "", response)
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        return {"diagnoses": [], "medications": []}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"diagnoses": [], "medications": []}


def _load_test_patient_ids(source: str) -> list[str]:
    """이미 만들어둔 ai_ready 결과에서 patient_id만 재사용 (같은 50명 대상으로 비교해야 하므로)."""
    pattern = "ai_ready_mimic_*.jsonl" if source == "mimic" else "ai_ready_eicu_*.jsonl"
    matches = sorted(TEST_DIR.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"{pattern} 파일을 data/test/에서 못 찾음")
    ids = []
    with open(matches[-1], encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ids.append(json.loads(line)["patient_id"])
    return ids


def _mimic_raw_text(subject_id: str, admissions, diagnoses_icd, prescriptions) -> str:
    lines = []
    adm = admissions[admissions["subject_id"].astype(str) == subject_id]
    if not adm.empty:
        lines.append(f"Admission type: {adm.iloc[0].get('admission_type', '')}")
    dx = diagnoses_icd[diagnoses_icd["subject_id"].astype(str) == subject_id]
    for _, row in dx.iterrows():
        lines.append(f"Diagnosis code (ICD-{row['icd_version']}): {row['icd_code']}")
    rx = prescriptions[prescriptions["subject_id"].astype(str) == subject_id]
    for _, row in rx.iterrows():
        lines.append(f"Prescription: {row['drug']} {row.get('dose_val_rx', '')}{row.get('dose_unit_rx', '')} via {row.get('route', '')}")
    return "\n".join(lines)


def _eicu_raw_text(stay_id: str, diagnosis, medication) -> str:
    lines = []
    dx = diagnosis[diagnosis["patientunitstayid"].astype(str) == stay_id]
    for _, row in dx.iterrows():
        lines.append(f"Diagnosis: {row['diagnosisstring']} (code candidates: {row.get('icd9code', '')})")
    rx = medication[medication["patientunitstayid"].astype(str) == stay_id]
    for _, row in rx.iterrows():
        lines.append(f"Medication: {row['drugname']} {row.get('dosage', '')} via {row.get('routeadmin', '')}")
    return "\n".join(lines)


def run(source: str):
    ids = _load_test_patient_ids(source)
    print(f"[{source}] 대상 환자 {len(ids)}명")

    if source == "mimic":
        admissions = pd.read_csv(ROOT / "data/raw/mimic4/admissions.csv", dtype=str)
        diagnoses_icd = pd.read_csv(ROOT / "data/raw/mimic4/diagnoses_icd.csv", dtype=str)
        prescriptions = pd.read_csv(ROOT / "data/raw/mimic4/prescriptions.csv", dtype=str)
        out_path = TEST_DIR / "zeroshot_mimic.jsonl"
        raw_fn = lambda pid: _mimic_raw_text(pid, admissions, diagnoses_icd, prescriptions)
    else:
        diagnosis = pd.read_csv(ROOT / "data/raw/eICU/diagnosis.csv", dtype=str)
        medication = pd.read_csv(ROOT / "data/raw/eICU/medication.csv", dtype=str)
        out_path = TEST_DIR / "zeroshot_eicu.jsonl"
        raw_fn = lambda pid: _eicu_raw_text(pid, diagnosis, medication)

    with open(out_path, "w", encoding="utf-8") as out:
        for i, pid in enumerate(ids, 1):
            raw_text = raw_fn(pid)
            prompt = ZEROSHOT_PROMPT.format(raw_data=raw_text[:4000])
            response = llm.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                json_schema=ZEROSHOT_SCHEMA,
            )
            parsed = _parse_json(response)
            record = {
                "patient_id": pid,
                "diagnoses": parsed.get("diagnoses", []),
                "medications": parsed.get("medications", []),
                "raw_input": raw_text,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"  [{i}/{len(ids)}] {pid} 완료 (dx={len(record['diagnoses'])}, med={len(record['medications'])})")

    print(f"저장 완료: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["mimic", "eicu"], required=True)
    args = parser.parse_args()
    run(args.source)
