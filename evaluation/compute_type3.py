"""
Type3: Hallucination 감소율 계산.

"Hallucination" 정의: 원본 소스 테이블(진단/투약)에 없는 값을 만들어낸 것.
golden standard가 아니라 원본 원시 테이블과 대조한다 (golden standard는 일부만
라벨링된 표본이라 "gold에 없다"가 "원본에 없다"를 의미하지 않기 때문).

- 단일 LLM Zero-shot: evaluation/run_zeroshot_baseline.py 산출물
- 파이프라인: data/output/test/ai_ready_*.jsonl

실행: python evaluation/compute_type3.py
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
TEST_DIR = ROOT / "data" / "output" / "test"
VOCAB_CSV = ROOT / "data" / "vocab" / "icd9to10.csv"


def _normalize_code(code) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(code).upper())


def _normalize_name(name) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _load_crosswalk_icd9_to_icd10() -> dict[str, set[str]]:
    df = pd.read_csv(VOCAB_CSV, dtype=str, header=0)
    df.columns = ["icd9", "icd10"]
    mapping: dict[str, set[str]] = {}
    for icd9, icd10 in zip(df["icd9"], df["icd10"]):
        key_dot = _normalize_code(icd9)
        mapping.setdefault(key_dot, set()).add(_normalize_code(icd10))
    return mapping


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


# ── MIMIC 원본 기준 진단/투약 코드 집합 구축 ──────────────────────────

def build_mimic_ground_truth() -> dict[str, dict]:
    diagnoses_icd = pd.read_csv(ROOT / "data/raw/mimic4/diagnoses_icd.csv", dtype=str)
    prescriptions = pd.read_csv(ROOT / "data/raw/mimic4/prescriptions.csv", dtype=str)
    crosswalk = _load_crosswalk_icd9_to_icd10()

    gt: dict[str, dict] = {}
    for subject_id, group in diagnoses_icd.groupby("subject_id"):
        codes = set()
        for _, row in group.iterrows():
            raw = _normalize_code(row["icd_code"])
            if row["icd_version"] == "9":
                codes |= crosswalk.get(raw, set())
                codes.add(raw)  # 변환 전 원본도 혹시 몰라 같이 허용
            else:
                codes.add(raw)
        gt.setdefault(subject_id, {"dx_codes": set(), "med_names": set()})
        gt[subject_id]["dx_codes"] = codes

    for subject_id, group in prescriptions.groupby("subject_id"):
        names = set(_normalize_name(d) for d in group["drug"].dropna())
        gt.setdefault(subject_id, {"dx_codes": set(), "med_names": set()})
        gt[subject_id]["med_names"] = names

    return gt


# ── eICU 원본 기준 진단/투약 코드 집합 구축 ──────────────────────────

def build_eicu_ground_truth() -> dict[str, dict]:
    diagnosis = pd.read_csv(ROOT / "data/raw/eICU/diagnosis.csv", dtype=str)
    medication = pd.read_csv(ROOT / "data/raw/eICU/medication.csv", dtype=str)

    crosswalk = _load_crosswalk_icd9_to_icd10()

    gt: dict[str, dict] = {}
    for stay_id, group in diagnosis.groupby("patientunitstayid"):
        codes = set()
        for _, row in group.iterrows():
            raw = str(row.get("icd9code", ""))
            for c in raw.split(","):
                c = c.strip()
                if c and c.lower() != "nan":
                    norm_c = _normalize_code(c)
                    codes.add(norm_c)
                    # MIMIC 쪽과 동일하게, ICD-9로 보이는 후보는 크로스워크로 변환한 ICD-10도
                    # 정답 집합에 같이 넣는다 (원본에 ICD-10 후보가 같이 없는 경우 대비)
                    codes |= crosswalk.get(norm_c, set())
        gt.setdefault(stay_id, {"dx_codes": set(), "med_names": set()})
        gt[stay_id]["dx_codes"] = codes

    for stay_id, group in medication.groupby("patientunitstayid"):
        names = set(_normalize_name(d) for d in group["drugname"].dropna())
        gt.setdefault(stay_id, {"dx_codes": set(), "med_names": set()})
        gt[stay_id]["med_names"] = names

    return gt


# ── hallucination 판정 ────────────────────────────────────────────────

def _med_name_grounded(pred_name: str, gt_names: set[str]) -> bool:
    p = _normalize_name(pred_name)
    if not p:
        return False
    return any(p == g or (len(p) > 4 and len(g) > 4 and (p in g or g in p)) for g in gt_names)


def hallucination_stats(records: list[dict], gt: dict[str, dict], id_key: str = "patient_id") -> dict:
    dx_total = dx_halluc = 0
    med_total = med_halluc = 0

    for r in records:
        pid = r.get(id_key)
        patient_gt = gt.get(pid, {"dx_codes": set(), "med_names": set()})

        for d in r.get("diagnoses", []):
            code = _normalize_code(d.get("icd10_code", ""))
            if not code:
                continue
            dx_total += 1
            if code not in patient_gt["dx_codes"]:
                dx_halluc += 1

        for m in r.get("medications", []):
            med_total += 1
            if not _med_name_grounded(m.get("name", ""), patient_gt["med_names"]):
                med_halluc += 1

    return {
        "diagnoses_total": dx_total,
        "diagnoses_hallucinated": dx_halluc,
        "diagnoses_hallucination_rate": round(dx_halluc / dx_total * 100, 1) if dx_total else None,
        "medications_total": med_total,
        "medications_hallucinated": med_halluc,
        "medications_hallucination_rate": round(med_halluc / med_total * 100, 1) if med_total else None,
    }


def reduction_rate(zeroshot_rate, pipeline_rate):
    if zeroshot_rate is None or pipeline_rate is None or zeroshot_rate == 0:
        return None
    return round((zeroshot_rate - pipeline_rate) / zeroshot_rate * 100, 1)


def main():
    results = {}

    for source, gt_builder, ai_file, zs_file in [
        ("MIMIC", build_mimic_ground_truth, sorted(TEST_DIR.glob("ai_ready_mimic_*.jsonl"))[-1], TEST_DIR / "zeroshot_mimic.jsonl"),
        ("eICU", build_eicu_ground_truth, sorted(TEST_DIR.glob("ai_ready_eicu_*.jsonl"))[-1], TEST_DIR / "zeroshot_eicu.jsonl"),
    ]:
        print(f"\n=== {source} ===")
        gt = gt_builder()

        ai_records = load_jsonl(ai_file)
        zs_records = load_jsonl(zs_file)

        ai_stats = hallucination_stats(ai_records, gt)
        zs_stats = hallucination_stats(zs_records, gt)

        print(f"[파이프라인 ({ai_file.name})]  {ai_stats}")
        print(f"[Zero-shot ({zs_file.name})]  {zs_stats}")

        dx_reduction = reduction_rate(zs_stats["diagnoses_hallucination_rate"], ai_stats["diagnoses_hallucination_rate"])
        med_reduction = reduction_rate(zs_stats["medications_hallucination_rate"], ai_stats["medications_hallucination_rate"])

        print(f"  diagnoses Hallucination 감소율:   {dx_reduction}%")
        print(f"  medications Hallucination 감소율: {med_reduction}%")

        results[source] = {
            "pipeline": ai_stats,
            "zeroshot": zs_stats,
            "diagnoses_hallucination_reduction_pct": dx_reduction,
            "medications_hallucination_reduction_pct": med_reduction,
        }

    out = Path(__file__).parent / "results_type3.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료: {out}")


if __name__ == "__main__":
    main()
