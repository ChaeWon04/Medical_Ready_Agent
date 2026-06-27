"""
사용법:
  python main.py --source synthea --data_dir data/raw/synthea
  python main.py --source mimic_iv --data_dir data/raw/mimic4 --mode structured
  python main.py --source mimic_iv --data_dir data/raw/mimic4 --mode note
  python main.py --source eicu --data_dir data/raw/eicu
"""
import argparse
import pandas as pd
from pathlib import Path
from graph.pipeline import pipeline


def run_synthea(data_dir: Path):
    patients    = pd.read_csv(data_dir / "patients.csv")
    conditions  = pd.read_csv(data_dir / "conditions.csv")
    medications = pd.read_csv(data_dir / "medications.csv")
    encounters  = pd.read_csv(data_dir / "encounters.csv")
    observations = pd.read_csv(data_dir / "observations.csv")

    pids = patients["Id"].tolist()
    print(f"[Synthea] 환자 {len(pids)}명 처리 시작")
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
        _log(state)


def run_mimic(data_dir: Path, mode: str):
    hosp_dir = data_dir / "demo" / "hosp"

    diagnoses_df = pd.read_csv(hosp_dir / "diagnoses_icd.csv.gz", compression="gzip")
    prescriptions_df = pd.read_csv(hosp_dir / "prescriptions.csv.gz", compression="gzip")
    admissions_df = pd.read_csv(hosp_dir / "admissions.csv.gz", compression="gzip")

    print(f"[MIMIC-IV] 입원 {len(admissions_df)}건 처리 시작")
    for _, row in admissions_df.iterrows():
        state = pipeline.invoke({
            "source": "mimic_iv",
            "raw_input": {
                "subject_id": str(row["subject_id"]),
                "hadm_id": str(row["hadm_id"]),
                "diagnoses_df": diagnoses_df,
                "prescriptions_df": prescriptions_df,
            },
            "record": None,
            "error": None,
        })
        _log(state)


def run_eicu(data_dir: Path):
    patient_df = pd.read_csv(data_dir / "patient.csv")
    diagnosis_df = pd.read_csv(data_dir / "diagnosis.csv")
    medication_df = pd.read_csv(data_dir / "medication.csv")
    lab_df = pd.read_csv(data_dir / "lab.csv")

    # 노트 파일 있으면 로드
    note_path = data_dir / "note.csv"
    note_df = pd.read_csv(note_path) if note_path.exists() else None

    print(f"[eICU] 환자 {len(patient_df)}건 처리 시작")
    for _, row in patient_df.iterrows():
        stay_id = str(row["patientunitstayid"])

        # 노트가 있으면 노트 우선
        if note_df is not None:
            notes = note_df[note_df["patientunitstayid"].astype(str) == stay_id]
            if not notes.empty:
                note_text = " ".join(notes["notetext"].dropna().tolist())
                state = pipeline.invoke({
                    "source": "eicu",
                    "raw_input": {"note_text": note_text, "patient_stay_id": stay_id},
                    "record": None,
                    "error": None,
                })
                _log(state)
                continue

        state = pipeline.invoke({
            "source": "eicu",
            "raw_input": {
                "patient_stay_id": stay_id,
                "diagnosis_df": diagnosis_df,
                "medication_df": medication_df,
                "lab_df": lab_df,
            },
            "record": None,
            "error": None,
        })
        _log(state)


def _log(state: dict):
    if state.get("error"):
        print(f"  [ERROR] {state['error']}")
    elif state.get("record"):
        r = state["record"]
        status = r.get("quality", {}).get("status", "?")
        q = r.get("quality", {}).get("q_index", 0)
        print(f"  [OK] {r.get('record_id', '')[:8]}... | {status} | Q={q:.2f}")

        import json
        from config import OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_DIR / "ai_ready.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["synthea", "mimic_iv", "eicu"], required=True)
    parser.add_argument("--data_dir", type=Path, required=True)
    parser.add_argument("--mode", choices=["structured", "note"], default="structured",
                        help="MIMIC-IV 전용: structured(테이블) or note(임상노트)")
    args = parser.parse_args()

    if args.source == "synthea":
        run_synthea(args.data_dir)
    elif args.source == "mimic_iv":
        run_mimic(args.data_dir, args.mode)
    elif args.source == "eicu":
        run_eicu(args.data_dir)
