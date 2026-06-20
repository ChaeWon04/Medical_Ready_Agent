import pandas as pd
from datetime import date
from config import SYNTHEA_CSV_DIR, DATA_SOURCE
from schemas.ai_ready_schema import AIReadyRecord, Medication
from models.model_loader import generate


def _load_synthea():
    patients = pd.read_csv(SYNTHEA_CSV_DIR / "patients.csv")
    conditions = pd.read_csv(SYNTHEA_CSV_DIR / "conditions.csv")
    medications = pd.read_csv(SYNTHEA_CSV_DIR / "medications.csv")
    encounters = pd.read_csv(SYNTHEA_CSV_DIR / "encounters.csv")
    observations = pd.read_csv(SYNTHEA_CSV_DIR / "observations.csv")
    return patients, conditions, medications, encounters, observations


def _calc_age(birthdate_str: str) -> int:
    birth = date.fromisoformat(str(birthdate_str)[:10])
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _parse_record(pid, patients, conditions, medications, encounters, observations) -> AIReadyRecord:
    p = patients[patients["Id"] == pid].iloc[0]
    conds = conditions[conditions["PATIENT"] == pid]["DESCRIPTION"].tolist()
    meds = medications[medications["PATIENT"] == pid]["DESCRIPTION"].tolist()
    enc = encounters[encounters["PATIENT"] == pid]

    enc_type = "inpatient" if "inpatient" in enc["ENCOUNTERCLASS"].values else "outpatient"

    reason = enc.sort_values("START", ascending=False)["REASONDESCRIPTION"].dropna()
    chief_complaint = str(reason.iloc[0]) if not reason.empty else None

    obs = observations[observations["PATIENT"] == pid]
    symptoms = obs[obs["TYPE"] == "text"]["DESCRIPTION"].dropna().unique().tolist()

    if not symptoms and conds:
        raw = generate(
            f"Given these diagnoses: {conds}\n"
            "List 3-5 main symptoms (comma-separated, no explanations)."
        )
        symptoms = [s.strip() for s in raw.split(",") if s.strip()]

    icd_raw = generate(
        f"Extract ICD-10 codes for these diagnoses: {conds}\n"
        "Return comma-separated ICD-10 codes only."
    )
    icd_codes = [c.strip() for c in icd_raw.split(",") if c.strip()]

    age = _calc_age(p["BIRTHDATE"]) if pd.notna(p.get("BIRTHDATE")) else None

    return AIReadyRecord(
        patient_id=pid,
        age=age,
        gender=p.get("GENDER"),
        chief_complaint=chief_complaint,
        diagnoses=conds,
        icd10_codes=icd_codes,
        medications=[Medication(name=m) for m in meds],
        symptoms=symptoms,
        encounter_type=enc_type,
        source=DATA_SOURCE,
    )


def run(limit: int = 10) -> list[AIReadyRecord]:
    patients, conditions, medications, encounters, observations = _load_synthea()
    pids = patients["Id"].tolist()[:limit]
    return [_parse_record(pid, patients, conditions, medications, encounters, observations) for pid in pids]
