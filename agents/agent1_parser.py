import json
import re
import uuid
import pandas as pd
from datetime import date
from typing import Optional
from models.model_loader import llm
from schemas.ai_ready_schema import (
    AIReadyRecord, Diagnosis, Medication, Observation,
    QualityMetadata, DataStatus
)
from config import SYNTHEA_CSV_DIR

SYSTEM_PROMPT = """You are a medical data extraction assistant.
Extract structured information from clinical text and return ONLY valid JSON. No explanation, no markdown."""

EXTRACT_PROMPT = """Extract from the clinical note below and return as JSON:

{{
  "diagnoses": [
    {{"icd10_code": "...", "description": "...", "confidence": "confirmed|suspected|ruled_out", "is_negated": false}}
  ],
  "medications": [
    {{"name": "...", "dose": null, "unit": null, "route": null, "frequency": null}}
  ],
  "observations": [
    {{"name": "...", "value": "...", "unit": null, "reference_range": null, "is_abnormal": null}}
  ]
}}

Rules:
- confidence = "ruled_out" if negated (r/o, no history of, denied, negative for)
- is_negated = true for negated diagnoses
- dose must be a float, unit must be one of: g, mg, mcg, mL, unit
- Use ICD-10 codes (e.g. E11.9, I10, J44.1)

Clinical note:
{note}"""

ICD9_TO_ICD10 = {
    "250.00": "E11.9", "250.02": "E11.9", "401.9": "I10",
    "428.0": "I50.9", "410.90": "I21.9", "490": "J44.1",
    "493.90": "J45.909", "585.9": "N18.9", "276.1": "E87.1",
    "486": "J18.9", "414.01": "I25.10", "427.31": "I48.91",
}


class Agent1Parser:

    def __init__(self):
        self._synthea_cache = None

    # ── Synthea CSV (juyoung) ─────────────────────────────────────

    def parse_synthea(self, patient_id: str) -> AIReadyRecord:
        patients, conditions, medications, encounters, observations = self._load_synthea()
        return self._parse_synthea_record(
            patient_id, patients, conditions, medications, encounters, observations
        )

    def _load_synthea(self):
        if self._synthea_cache is None:
            self._synthea_cache = (
                pd.read_csv(SYNTHEA_CSV_DIR / "patients.csv"),
                pd.read_csv(SYNTHEA_CSV_DIR / "conditions.csv"),
                pd.read_csv(SYNTHEA_CSV_DIR / "medications.csv"),
                pd.read_csv(SYNTHEA_CSV_DIR / "encounters.csv"),
                pd.read_csv(SYNTHEA_CSV_DIR / "observations.csv"),
            )
        return self._synthea_cache

    def _calc_age(self, birthdate_str: str) -> int:
        birth = date.fromisoformat(str(birthdate_str)[:10])
        today = date.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    def _parse_synthea_record(self, pid, patients, conditions, medications, encounters, observations) -> AIReadyRecord:
        p = patients[patients["Id"] == pid].iloc[0]
        cond_descs = conditions[conditions["PATIENT"] == pid]["DESCRIPTION"].tolist()
        med_descs = medications[medications["PATIENT"] == pid]["DESCRIPTION"].tolist()
        enc = encounters[encounters["PATIENT"] == pid]
        obs = observations[observations["PATIENT"] == pid]

        enc_type = "inpatient" if "inpatient" in enc["ENCOUNTERCLASS"].values else "outpatient"

        reason = enc.sort_values("START", ascending=False)["REASONDESCRIPTION"].dropna()
        chief_complaint = str(reason.iloc[0]) if not reason.empty else None

        symptoms = obs[obs["TYPE"] == "text"]["DESCRIPTION"].dropna().unique().tolist()
        if not symptoms and cond_descs:
            raw = llm.generate(
                system_prompt="You are a medical assistant. Be concise.",
                user_prompt=f"Given these diagnoses: {cond_descs}\nList 3-5 main symptoms (comma-separated, no explanations).",
            )
            symptoms = [s.strip() for s in raw.split(",") if s.strip()]

        age = self._calc_age(p["BIRTHDATE"]) if pd.notna(p.get("BIRTHDATE")) else None

        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="synthea",
            patient_id=pid,
            age=age,
            gender=p.get("GENDER"),
            chief_complaint=chief_complaint,
            symptoms=symptoms,
            diagnoses=self._synthea_diagnoses(cond_descs),
            medications=[Medication(name=m) for m in med_descs],
            clinical_text=enc_type,  # Agent3 situation 분류에 활용
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def _synthea_diagnoses(self, descriptions: list[str]) -> list[Diagnosis]:
        results = []
        for desc in descriptions:
            icd10 = self._llm_to_icd10(desc)
            if icd10:
                try:
                    results.append(Diagnosis(icd10_code=icd10, description=desc, confidence="confirmed"))
                except Exception:
                    pass
        return results

    # ── MIMIC-IV (feat/pipeline-scaffold) ────────────────────────

    def parse_mimic_structured(
        self,
        subject_id: str,
        hadm_id: str,
        diagnoses_df: pd.DataFrame,
        prescriptions_df: pd.DataFrame,
    ) -> AIReadyRecord:
        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="mimic_iv",
            patient_id=subject_id,
            diagnoses=self._mimic_diagnoses(diagnoses_df, subject_id, hadm_id),
            medications=self._mimic_medications(prescriptions_df, subject_id, hadm_id),
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def parse_mimic_note(self, note_text: str, subject_id: str, hadm_id: str = "") -> AIReadyRecord:
        extracted = self._extract_with_llm(note_text)
        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="mimic_iv",
            patient_id=subject_id,
            diagnoses=self._safe_diagnoses(extracted.get("diagnoses", [])),
            medications=[Medication(**m) for m in extracted.get("medications", [])],
            observations=[Observation(**o) for o in extracted.get("observations", [])],
            clinical_text=note_text,
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def _mimic_diagnoses(self, df: pd.DataFrame, subject_id: str, hadm_id: str) -> list[Diagnosis]:
        mask = (df["subject_id"].astype(str) == subject_id) & (df["hadm_id"].astype(str) == hadm_id)
        results = []
        for _, row in df[mask].iterrows():
            raw_code = str(row.get("icd_code", ""))
            version = str(row.get("icd_version", "10"))
            code = ICD9_TO_ICD10.get(raw_code, self._llm_to_icd10(raw_code)) if version == "9" else self._format_icd10(raw_code)
            if code:
                try:
                    results.append(Diagnosis(icd10_code=code, description=raw_code, confidence="confirmed"))
                except Exception:
                    pass
        return results

    def _mimic_medications(self, df: pd.DataFrame, subject_id: str, hadm_id: str) -> list[Medication]:
        mask = (df["subject_id"].astype(str) == subject_id) & (df["hadm_id"].astype(str) == hadm_id)
        results = []
        for _, row in df[mask].iterrows():
            unit = str(row.get("dose_unit_rx", ""))
            results.append(Medication(
                name=str(row.get("drug", "")),
                dose=self._safe_float(row.get("dose_val_rx")),
                unit=unit if unit in ("g", "mg", "mcg", "mL", "unit") else None,
                route=str(row.get("route", "")) or None,
            ))
        return results

    # ── eICU (feat/pipeline-scaffold) ────────────────────────────

    def parse_eicu_structured(
        self,
        patient_stay_id: str,
        diagnosis_df: pd.DataFrame,
        medication_df: pd.DataFrame,
        lab_df: pd.DataFrame,
    ) -> AIReadyRecord:
        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="eicu",
            patient_id=patient_stay_id,
            diagnoses=self._eicu_diagnoses(diagnosis_df, patient_stay_id),
            medications=self._eicu_medications(medication_df, patient_stay_id),
            observations=self._eicu_labs(lab_df, patient_stay_id),
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def parse_eicu_note(self, note_text: str, patient_stay_id: str) -> AIReadyRecord:
        extracted = self._extract_with_llm(note_text)
        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="eicu",
            patient_id=patient_stay_id,
            diagnoses=self._safe_diagnoses(extracted.get("diagnoses", [])),
            medications=[Medication(**m) for m in extracted.get("medications", [])],
            observations=[Observation(**o) for o in extracted.get("observations", [])],
            clinical_text=note_text,
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def _eicu_diagnoses(self, df: pd.DataFrame, stay_id: str) -> list[Diagnosis]:
        results = []
        for _, row in df[df["patientunitstayid"].astype(str) == stay_id].iterrows():
            icd9 = str(row.get("icd9code", ""))
            desc = str(row.get("diagnosisstring", ""))
            code = ICD9_TO_ICD10.get(icd9, self._llm_to_icd10(desc))
            if code:
                try:
                    results.append(Diagnosis(icd10_code=code, description=desc, confidence="confirmed"))
                except Exception:
                    pass
        return results

    def _eicu_medications(self, df: pd.DataFrame, stay_id: str) -> list[Medication]:
        results = []
        for _, row in df[df["patientunitstayid"].astype(str) == stay_id].iterrows():
            dose_str = str(row.get("dosage", ""))
            dose, unit = self._parse_dose(dose_str)
            results.append(Medication(
                name=str(row.get("drugname", "")),
                dose=dose,
                unit=unit,
                route=str(row.get("routeadmin", "")) or None,
                frequency=str(row.get("frequency", "")) or None,
            ))
        return results

    def _eicu_labs(self, df: pd.DataFrame, stay_id: str) -> list[Observation]:
        return [
            Observation(name=str(row.get("labname", "")), value=str(row.get("labresult", "")))
            for _, row in df[df["patientunitstayid"].astype(str) == stay_id].iterrows()
        ]

    # ── 공통 유틸 ─────────────────────────────────────────────────

    def _extract_with_llm(self, note_text: str) -> dict:
        prompt = EXTRACT_PROMPT.format(note=note_text[:3000])
        response = llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
        return self._parse_json(response)

    def _safe_diagnoses(self, raw_list: list[dict]) -> list[Diagnosis]:
        results = []
        for d in raw_list:
            try:
                results.append(Diagnosis(**d))
            except Exception:
                pass
        return results

    def _llm_to_icd10(self, description: str) -> Optional[str]:
        if not description.strip():
            return None
        response = llm.generate(
            system_prompt="Return only an ICD-10 code. No explanation.",
            user_prompt=f"ICD-10 code for: {description}",
        )
        match = re.search(r"[A-Z]\d{2}(\.[0-9A-Z]{1,4})?", response)
        return match.group(0) if match else None

    def _format_icd10(self, raw: str) -> Optional[str]:
        raw = raw.strip()
        if len(raw) >= 3:
            return f"{raw[:3]}.{raw[3:]}" if len(raw) > 3 and "." not in raw else raw
        return None

    def _parse_dose(self, dose_str: str) -> tuple[Optional[float], Optional[str]]:
        match = re.search(r"([\d.]+)\s*(g|mg|mcg|mL|unit)", dose_str, re.IGNORECASE)
        if match:
            return self._safe_float(match.group(1)), match.group(2).lower()
        return None, None

    def _safe_float(self, val) -> Optional[float]:
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    def _parse_json(self, response: str) -> dict:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            return {"diagnoses": [], "medications": [], "observations": []}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"diagnoses": [], "medications": [], "observations": []}
