"""
data/test/ 의 ai_ready_*.jsonl vs *_golden_standard*.json(l) 비교해서
Type1(Precision/Recall/F1), Type2(오분류율) 계산.

Type3(Hallucination 감소율)은 zero-shot 베이스라인 산출물이 따로 필요해서
이 스크립트에는 아직 안 들어있음 (베이스라인 파일 생기면 추가 예정).

실행: python eval/compute_metrics.py
"""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
TEST_DIR = ROOT / "data" / "test"
VOCAB_CSV = ROOT / "data" / "vocab" / "icd9to10.csv"

# eICU는 원본부터 ICD-10이라 정규화 불필요. MIMIC만 아래 크로스워크 필요.
_crosswalk_df = None


def _normalize_code(code: str) -> str:
    """MIMIC 원본/golden standard는 점(.) 없는 표기(Z45018)를 쓰고, 파이프라인은
    점 포함 표기(Z45.018)를 쓴다. 같은 코드인데 표기만 다른 걸 다른 코드로
    오채점하지 않도록 비교 전에 항상 이 함수로 정규화한다."""
    return re.sub(r"[^A-Z0-9]", "", str(code).upper())


def _load_crosswalk():
    """icd9_code -> {가능한 icd10_code 후보 집합} 의 '역방향' 인덱스도 같이 만든다.
    (icd10_code -> 그 코드를 만들어낼 수 있는 icd9 원본 집합)
    이걸로 '두 ICD-10 코드가 같은 ICD-9 모호성에서 나온 서로 다른 후보인지'를 판별한다.
    키는 전부 _normalize_code()로 정규화해서 저장 (점 유무 차이로 못 찾는 일 방지)."""
    global _crosswalk_df
    if _crosswalk_df is not None:
        return _crosswalk_df
    df = json_free_read_csv(VOCAB_CSV)
    icd9_to_icd10 = {}
    for icd9, icd10 in df:
        icd9_to_icd10.setdefault(_normalize_code(icd9), set()).add(_normalize_code(icd10))
    icd10_to_icd9_sources = {}
    for icd9, icd10s in icd9_to_icd10.items():
        for icd10 in icd10s:
            icd10_to_icd9_sources.setdefault(icd10, set()).add(icd9)
    _crosswalk_df = icd10_to_icd9_sources
    return _crosswalk_df


def json_free_read_csv(path: Path) -> list[tuple[str, str]]:
    """pandas 없이 가볍게 csv 두 컬럼만 읽기 (icd9, icd10)."""
    rows = []
    with open(path, encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            parts = line.rstrip("\n").split(",")
            if len(parts) >= 2:
                rows.append((parts[0].strip(), parts[1].strip()))
    return rows


def icd_codes_crosswalk_equivalent(code_a: str, code_b: str) -> bool:
    """code_a, code_b가 같은 ICD-9 코드에서 갈라져 나온 서로 다른 유효 후보인지 확인.
    (icd9to10.csv에서 두 ICD-10 코드의 '원본 ICD-9 집합'이 하나라도 겹치면 True)"""
    idx = _load_crosswalk()
    sources_a = idx.get(_normalize_code(code_a), set())
    sources_b = idx.get(_normalize_code(code_b), set())
    return bool(sources_a & sources_b)


def load_jsonl(path: Path) -> list[dict]:
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def index_by_patient(records: list[dict]) -> dict[str, dict]:
    return {r["patient_id"]: r for r in records}


# ── Type1: Precision / Recall / F1 ──────────────────────────────────

_UNRESOLVED = ("MANUAL_REVIEW", None, "")


def match_diagnoses(gold_dx: list[dict], ai_dx: list[dict], use_crosswalk: bool) -> tuple[int, int, int, int]:
    """반환: (TP, FP, FN, 제외건수)
    제외 대상: MIMIC은 "MANUAL_REVIEW" 문자열, eICU는 icd10_code가 null인 경우
    (라벨링 팀이 코드를 못 찾아서 정답 없이 비워둔 항목들 - 둘 다 같은 의미)."""
    excluded = sum(1 for d in gold_dx if d.get("icd10_code") in _UNRESOLVED)
    gold_codes = [_normalize_code(d["icd10_code"]) for d in gold_dx if d.get("icd10_code") not in _UNRESOLVED]
    ai_codes = [_normalize_code(d["icd10_code"]) for d in ai_dx if d.get("icd10_code") not in _UNRESOLVED]

    gold_remaining = gold_codes.copy()
    tp = 0
    fp = 0
    for code in ai_codes:
        matched_idx = None
        for i, g in enumerate(gold_remaining):
            if g == code or (use_crosswalk and icd_codes_crosswalk_equivalent(g, code)):
                matched_idx = i
                break
        if matched_idx is not None:
            tp += 1
            gold_remaining.pop(matched_idx)
        else:
            fp += 1
    fn = len(gold_remaining)
    return tp, fp, fn, excluded


def _norm_med_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_medications(gold_meds: list[dict], ai_meds: list[dict]) -> tuple[int, int, int]:
    """이름 정규화 후 포함관계로 매칭 (완전 동일 표기를 기대하기 어려워서 느슨하게 비교)."""
    gold_names = [_norm_med_name(m["name"]) for m in gold_meds]
    ai_names = [_norm_med_name(m["name"]) for m in ai_meds]

    gold_remaining = gold_names.copy()
    tp = 0
    fp = 0
    for name in ai_names:
        matched_idx = None
        for i, g in enumerate(gold_remaining):
            if g == name or (len(g) > 4 and len(name) > 4 and (g in name or name in g)):
                matched_idx = i
                break
        if matched_idx is not None:
            tp += 1
            gold_remaining.pop(matched_idx)
        else:
            fp += 1
    fn = len(gold_remaining)
    return tp, fp, fn


def match_observations(gold_obs: list[dict], ai_obs: list[dict]) -> tuple[int, int, int]:
    """검사명(name) 기준 매칭. eICU만 해당 (MIMIC은 원본에 lab 데이터 없어서 호출 안 함)."""
    def norm(o):
        return re.sub(r"[^a-z0-9]", "", str(o.get("name", "")).lower())

    gold_names = [norm(o) for o in gold_obs]
    ai_names = [norm(o) for o in ai_obs]

    gold_remaining = gold_names.copy()
    tp = 0
    fp = 0
    for name in ai_names:
        if name in gold_remaining:
            gold_remaining.remove(name)
            tp += 1
        else:
            fp += 1
    fn = len(gold_remaining)
    return tp, fp, fn


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)


def type1_report(source: str, gold: list[dict], ai: list[dict], use_crosswalk: bool, include_observations: bool):
    gold_idx = index_by_patient(gold)
    ai_idx = index_by_patient(ai)
    common = sorted(set(gold_idx) & set(ai_idx))

    dx_tp = dx_fp = dx_fn = dx_excl = 0
    med_tp = med_fp = med_fn = 0
    obs_tp = obs_fp = obs_fn = 0

    for pid in common:
        g, a = gold_idx[pid], ai_idx[pid]
        tp, fp, fn, excl = match_diagnoses(g.get("diagnoses", []), a.get("diagnoses", []), use_crosswalk)
        dx_tp += tp; dx_fp += fp; dx_fn += fn; dx_excl += excl

        tp, fp, fn = match_medications(g.get("medications", []), a.get("medications", []))
        med_tp += tp; med_fp += fp; med_fn += fn

        if include_observations:
            tp, fp, fn = match_observations(g.get("observations", []), a.get("observations", []))
            obs_tp += tp; obs_fp += fp; obs_fn += fn

    print(f"\n[{source}] Type1 추출 성능 (환자 {len(common)}명 대조)")
    p, r, f1 = prf(dx_tp, dx_fp, dx_fn)
    print(f"  diagnoses   P={p} R={r} F1={f1}  (TP={dx_tp} FP={dx_fp} FN={dx_fn}, MANUAL_REVIEW 제외={dx_excl})")
    p, r, f1 = prf(med_tp, med_fp, med_fn)
    print(f"  medications P={p} R={r} F1={f1}  (TP={med_tp} FP={med_fp} FN={med_fn})")
    if include_observations:
        p, r, f1 = prf(obs_tp, obs_fp, obs_fn)
        print(f"  observations P={p} R={r} F1={f1}  (TP={obs_tp} FP={obs_fp} FN={obs_fn})")
    else:
        print("  observations - 평가 제외 (원본에 lab 데이터 없음)")


# ── Type2: 오분류율 ──────────────────────────────────────────────────

# MIMIC golden standard가 "icu"로 표기한 걸 파이프라인 스키마(outpatient/emergency/inpatient)에 맞게 정규화
_SITUATION_ALIAS = {"icu": "inpatient"}


def type2_report(source: str, gold: list[dict], ai: list[dict]):
    gold_idx = index_by_patient(gold)
    ai_idx = index_by_patient(ai)
    common = sorted(set(gold_idx) & set(ai_idx))

    sit_mismatch = 0
    roles_mismatch = 0
    n = 0
    for pid in common:
        g_ctx = gold_idx[pid].get("context")
        a_ctx = ai_idx[pid].get("context")
        if not g_ctx or not a_ctx:
            continue
        n += 1
        g_sit = _SITUATION_ALIAS.get(g_ctx["situation"], g_ctx["situation"])
        a_sit = _SITUATION_ALIAS.get(a_ctx["situation"], a_ctx["situation"])
        if g_sit != a_sit:
            sit_mismatch += 1
        if set(g_ctx.get("roles", [])) != set(a_ctx.get("roles", [])):
            roles_mismatch += 1

    print(f"\n[{source}] Type2 오분류율 (context 라벨 있는 {n}명 대조)")
    print(f"  situation 오분류율: {round(sit_mismatch / n * 100, 1) if n else 'N/A'}%  ({sit_mismatch}/{n})")
    print(f"  roles 오분류율:     {round(roles_mismatch / n * 100, 1) if n else 'N/A'}%  ({roles_mismatch}/{n})")


# ── main ─────────────────────────────────────────────────────────────

def main():
    mimic_gold = load_jsonl(TEST_DIR / "mimic_golden_standard_50.json")
    mimic_ai = load_jsonl(TEST_DIR / "ai_ready_mimic_0711_152207.jsonl")
    eicu_gold = load_jsonl(TEST_DIR / "eicu_golden_standard.jsonl")
    eicu_ai = load_jsonl(TEST_DIR / "ai_ready_eicu_0710_193043.jsonl")

    type1_report("MIMIC", mimic_gold, mimic_ai, use_crosswalk=True, include_observations=False)
    type1_report("eICU", eicu_gold, eicu_ai, use_crosswalk=False, include_observations=True)

    type2_report("MIMIC", mimic_gold, mimic_ai)
    type2_report("eICU", eicu_gold, eicu_ai)

    print(
        "\nType3 (Hallucination 감소율)은 zero-shot 베이스라인 결과가 아직 없어서 생략."
        " 베이스라인 파일 생기면 이어서 추가."
    )


if __name__ == "__main__":
    main()
