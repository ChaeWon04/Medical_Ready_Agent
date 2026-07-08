"""
사용법:
  python main.py --source mimic_iv --data_dir data/raw/mimic4 --split train --max_records 200
  python main.py --source mimic_iv --data_dir data/raw/mimic4 --split test
  python main.py --source eicu --data_dir data/raw/eicu --split train
  python main.py --source eicu --data_dir data/raw/eicu --split test
  python main.py --source synthea --data_dir data/raw/synthea
"""
import argparse
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from graph.pipeline import pipeline
from config import OUTPUT_DIR, RUN_LOG

_SOURCE_SHORT = {"synthea": "synthea", "mimic_iv": "mimic", "eicu": "eicu"}
_KST = ZoneInfo("Asia/Seoul")


def _run_ts() -> str:
    return datetime.now(_KST).strftime("%m%d_%H%M%S")


def _load_split_ids(split_csv: Path, id_col: str, split: str) -> set:
    if not split_csv.exists() or split == "all":
        return None  # None = 필터 없음
    df = pd.read_csv(split_csv)
    return set(df[df["split"] == split][id_col].astype(str).tolist())


def run_synthea(data_dir: Path, split: str, max_records: int):
    patients    = pd.read_csv(data_dir / "patients.csv")
    conditions  = pd.read_csv(data_dir / "conditions.csv")
    medications = pd.read_csv(data_dir / "medications.csv")
    encounters  = pd.read_csv(data_dir / "encounters.csv")
    observations = pd.read_csv(data_dir / "observations.csv")

    pids = patients["Id"].tolist()
    if max_records:
        pids = pids[:max_records]
    print(f"[Synthea] 환자 {len(pids)}명 처리 시작")
    run_ts = _run_ts()
    for pid in pids:
        state = pipeline.invoke({
            "source": "synthea",
            "raw_input": {
                "pid": pid,
                "patients": patients,
                "conditions": conditions,
                "medications": medications,
                "encounters": encounters,
                "observations": observations,
            },
            "record": None,
            "error": None,
        })
        _log(state, "synthea", run_ts)


def run_mimic(data_dir: Path, mode: str, split: str, max_records: int):
    diagnoses_df = pd.read_csv(data_dir / "diagnoses_icd.csv")
    prescriptions_df = pd.read_csv(data_dir / "prescriptions.csv")
    admissions_df = pd.read_csv(data_dir / "admissions.csv")
    patients_df = pd.read_csv(data_dir / "patients.csv")

    icd_parts = []
    for fname in ("d_icd_diagnoses.csv",
                  "d_icd_diagnoses_icd9.csv", "d_icd_diagnoses_ICD9.csv",
                  "d_icd_diagnoses_icd10.csv", "d_icd_diagnoses_ICD10.csv"):
        p = data_dir / fname
        if p.exists():
            icd_parts.append(pd.read_csv(p))
    icd_desc_df = pd.concat(icd_parts, ignore_index=True) if icd_parts else pd.DataFrame()

    lab_path = data_dir / "labevents.csv"
    labevents_df = pd.read_csv(lab_path) if lab_path.exists() else pd.DataFrame()

    allowed_ids = _load_split_ids(data_dir / "mimic_split.csv", "hadm_id", split)

    hadm_ids = admissions_df["hadm_id"].dropna().unique().tolist()
    if allowed_ids is not None:
        hadm_ids = [h for h in hadm_ids if str(h) in allowed_ids]
    if split == "train":
        hadm_ids = hadm_ids[:200]
    elif max_records:
        hadm_ids = hadm_ids[:max_records]

    print(f"[MIMIC-IV] 입원 {len(hadm_ids)}건 처리 시작 (split={split})")
    run_ts = _run_ts()
    for hadm_id in hadm_ids:
        a_row = admissions_df[admissions_df["hadm_id"].astype(str) == str(hadm_id)].iloc[0]
        state = pipeline.invoke({
            "source": "mimic_iv",
            "raw_input": {
                "subject_id": str(a_row["subject_id"]),
                "hadm_id": str(hadm_id),
                "diagnoses_df": diagnoses_df,
                "prescriptions_df": prescriptions_df,
                "admissions_df": admissions_df,
                "patients_df": patients_df,
                "icd_desc_df": icd_desc_df,
                "labevents_df": labevents_df,
            },
            "record": None,
            "error": None,
        })
        _log(state, "mimic_iv", run_ts)


def run_eicu(data_dir: Path, split: str, max_records: int):
    patient_df = pd.read_csv(data_dir / "patient.csv")
    diagnosis_df = pd.read_csv(data_dir / "diagnosis.csv")
    medication_df = pd.read_csv(data_dir / "medication.csv")
    lab_df = pd.read_csv(data_dir / "lab.csv")

    note_path = data_dir / "note.csv"
    note_df = pd.read_csv(note_path) if note_path.exists() else None

    allowed_ids = _load_split_ids(data_dir / "eicu_split.csv", "patientunitstayid", split)

    rows = list(patient_df.iterrows())
    if allowed_ids is not None:
        rows = [(i, r) for i, r in rows if str(r["patientunitstayid"]) in allowed_ids]
    if max_records:
        rows = rows[:max_records]

    print(f"[eICU] 환자 {len(rows)}건 처리 시작 (split={split})")
    run_ts = _run_ts()
    for _, row in rows:
        stay_id = str(row["patientunitstayid"])

        if note_df is not None:
            notes = note_df[note_df["patientunitstayid"].astype(str) == stay_id]
            if not notes.empty:
                note_text = " ".join(notes["notetext"].dropna().tolist())
                state = pipeline.invoke({
                    "source": "eicu",
                    "raw_input": {"note_text": note_text, "patient_stay_id": stay_id,
                                  "patient_row": row.to_dict()},
                    "record": None,
                    "error": None,
                })
                _log(state, "eicu", run_ts)
                continue

        state = pipeline.invoke({
            "source": "eicu",
            "raw_input": {
                "patient_stay_id": stay_id,
                "patient_row": row.to_dict(),
                "diagnosis_df": diagnosis_df,
                "medication_df": medication_df,
                "lab_df": lab_df,
            },
            "record": None,
            "error": None,
        })
        _log(state, "eicu", run_ts)



def _log(state: dict, source: str, run_ts: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"ai_ready_{_SOURCE_SHORT.get(source, source)}_{run_ts}.jsonl"

    def _write_log(msg):
        print(msg)
        with open(RUN_LOG, "a", encoding="utf-8") as lf:
            lf.write(msg + "\n")

    if state.get("error"):
        _write_log(f"  [ERROR] {state['error']}")
    elif state.get("record"):
        r = state["record"]
        status = r.get("quality", {}).get("status", "?")
        q = r.get("quality", {}).get("q_index", 0)
        _write_log(f"  [OK] {r.get('record_id', '')[:8]}... | {status} | Q={q:.2f}")
        with open(OUTPUT_DIR / fname, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["synthea", "mimic_iv", "eicu"], required=True)
    parser.add_argument("--data_dir", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "test", "all"], default="all")
    parser.add_argument("--max_records", type=int, default=None,
                        help="최대 처리 레코드 수 (예: MIMIC train 400 중 200만 쓸 때 --max_records 200)")
    parser.add_argument("--mode", choices=["structured", "note"], default="structured")
    args = parser.parse_args()

    if args.source == "synthea":
        run_synthea(args.data_dir, args.split, args.max_records)
    elif args.source == "mimic_iv":
        run_mimic(args.data_dir, args.mode, args.split, args.max_records)
    elif args.source == "eicu":
        run_eicu(args.data_dir, args.split, args.max_records)

