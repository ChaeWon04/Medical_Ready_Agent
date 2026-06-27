import json
import re
import uuid
import pandas as pd
from pathlib import Path
from typing import Optional
from models.model_loader import llm
from schemas.ai_ready_schema import (
    AIReadyRecord, Diagnosis, Medication, Observation,
    QualityMetadata, DataStatus
)

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

def _load_icd9_mapping() -> dict:
    csv_path = Path(__file__).parent.parent / "data" / "icd9to10.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype=str, header=0)
        return dict(zip(df.iloc[:, 0].str.strip(), df.iloc[:, 1].str.strip()))
    # CSV 없을 때 fallback
    return {
        "250.00": "E11.9", "250.02": "E11.9", "401.9": "I10",
        "428.0": "I50.9", "410.90": "I21.9", "490": "J44.1",
        "493.90": "J45.909", "585.9": "N18.9", "276.1": "E87.1",
        "486": "J18.9", "414.01": "I25.10", "427.31": "I48.91",
    }

ICD9_TO_ICD10 = _load_icd9_mapping()

EXTRACT_SCHEMA = {
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
                    "is_negated": {"type": "boolean"},
                },
                "required": ["icd10_code", "description", "confidence", "is_negated"],
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
                    "route": {"type": ["string", "null"]},
                    "frequency": {"type": ["string", "null"]},
                },
                "required": ["name"],
            },
        },
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "unit": {"type": ["string", "null"]},
                    "reference_range": {"type": ["string", "null"]},
                    "is_abnormal": {"type": ["boolean", "null"]},
                },
                "required": ["name", "value"],
            },
        },
    },
    "required": ["diagnoses", "medications", "observations"],
}

SNOMED_TO_ICD10 = {
    "44054006": "E11.9", "73211009": "E11.9", "38341003": "I10",
    "22298006": "I21.9", "13645005": "J44.1", "195967001": "J45.909",
    "40055000": "N18.9", "49436004": "I48.91",
}


class Agent1Parser:

    # ── Synthea CSV (룰 기반, juyoung 브랜치) ────────────────────

    def parse_synthea(
        self,
        pid: str,
        patients: pd.DataFrame,
        conditions: pd.DataFrame,
        medications: pd.DataFrame,
        encounters: pd.DataFrame,
        observations: pd.DataFrame,
    ) -> AIReadyRecord:
        p = patients[patients["Id"] == pid].iloc[0]
        age = self._calc_age(str(p.get("BIRTHDATE", "")))
        gender = str(p.get("GENDER", ""))

        diagnoses = self._synthea_diagnoses(conditions, pid)
        meds = self._synthea_medications(medications, pid)
        obs = self._synthea_observations(observations, pid)
        chief_complaint = self._synthea_chief_complaint(encounters, pid)
        symptoms = self._synthea_symptoms(observations, pid, [d.description for d in diagnoses])
        encounter_type = self._synthea_encounter_type(encounters, pid)

        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="synthea",
            patient_id=pid,
            age=age,
            gender=gender,
            chief_complaint=chief_complaint,
            symptoms=symptoms,
            diagnoses=diagnoses,
            medications=meds,
            observations=obs,
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def _calc_age(self, birthdate_str: str) -> Optional[int]:
        from datetime import date
        try:
            birth = date.fromisoformat(birthdate_str[:10])
            today = date.today()
            return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except Exception:
            return None

    def _synthea_diagnoses(self, df: pd.DataFrame, pid: str) -> list[Diagnosis]:
        results = []
        for _, row in df[df["PATIENT"] == pid].iterrows():
            desc = str(row.get("DESCRIPTION", ""))
            code = self._llm_to_icd10(desc)
            if code:
                results.append(Diagnosis(icd10_code=code, description=desc, confidence="confirmed"))
        return results

    def _synthea_medications(self, df: pd.DataFrame, pid: str) -> list[Medication]:
        return [
            Medication(name=str(row.get("DESCRIPTION", "")))
            for _, row in df[df["PATIENT"] == pid].iterrows()
        ]

    def _synthea_observations(self, df: pd.DataFrame, pid: str) -> list[Observation]:
        return [
            Observation(
                name=str(row.get("DESCRIPTION", "")),
                value=str(row.get("VALUE", "")),
                unit=str(row.get("UNITS", "")) or None,
            )
            for _, row in df[df["PATIENT"] == pid].iterrows()
            if row.get("TYPE") != "text"
        ]

    def _synthea_chief_complaint(self, encounters: pd.DataFrame, pid: str) -> Optional[str]:
        enc = encounters[encounters["PATIENT"] == pid]
        reason = enc.sort_values("START", ascending=False)["REASONDESCRIPTION"].dropna()
        return str(reason.iloc[0]) if not reason.empty else None

    _SDOH_KEYWORDS = (
        "[PRAPARE]", "[PhenX]", "status", "insurance", "education",
        "income", "language", "housing", "refugee", "farm work",
        "Armed Forces", "Race", "Hispanic", "Address", "employment",
    )

    def _synthea_symptoms(self, observations: pd.DataFrame, pid: str, diagnoses: list[str]) -> list[str]:
        obs = observations[observations["PATIENT"] == pid]
        text_obs = obs[obs["TYPE"] == "text"]["DESCRIPTION"].dropna().unique()
        symptoms = [
            d for d in text_obs
            if not any(k.lower() in d.lower() for k in self._SDOH_KEYWORDS)
        ]
        if not symptoms and diagnoses:
            raw = llm.generate(
                system_prompt="Return symptoms as comma-separated list only. No explanation.",
                user_prompt=f"List 3-5 main symptoms for these diagnoses: {diagnoses}",
            )
            symptoms = [s.strip() for s in raw.split(",") if s.strip()]
        return symptoms

    def _synthea_encounter_type(self, encounters: pd.DataFrame, pid: str) -> Optional[str]:
        enc = encounters[encounters["PATIENT"] == pid]
        if enc.empty:
            return None
        classes = enc["ENCOUNTERCLASS"].str.lower().values
        if any("inpatient" in c for c in classes):
            return "inpatient"
        if any("emergency" in c for c in classes):
            return "emergency"
        return "outpatient"

    # ── MIMIC-IV ──────────────────────────────────────────────────

    def parse_mimic_structured(
        self,
        subject_id: str,
        hadm_id: str,
        diagnoses_df: pd.DataFrame,
        prescriptions_df: pd.DataFrame,
    ) -> AIReadyRecord:
        diagnoses = self._mimic_diagnoses(diagnoses_df, subject_id, hadm_id)
        medications = self._mimic_medications(prescriptions_df, subject_id, hadm_id)
        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="mimic_iv",
            patient_id=subject_id,
            diagnoses=diagnoses,
            medications=medications,
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def parse_mimic_note(self, note_text: str, subject_id: str, hadm_id: str = "") -> AIReadyRecord:
        extracted = self._extract_with_llm(note_text)
        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="mimic_iv",
            patient_id=subject_id,
            diagnoses=[Diagnosis(**d) for d in extracted.get("diagnoses", [])],
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
            if version == "9":
                code = ICD9_TO_ICD10.get(raw_code, self._llm_to_icd10(raw_code))
            else:
                code = self._format_icd10(raw_code)
            if code:
                results.append(Diagnosis(icd10_code=code, description=raw_code, confidence="confirmed"))
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

    # ── eICU ──────────────────────────────────────────────────────

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
            diagnoses=[Diagnosis(**d) for d in extracted.get("diagnoses", [])],
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
                results.append(Diagnosis(icd10_code=code, description=desc, confidence="confirmed"))
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
            Observation(
                name=str(row.get("labname", "")),
                value=str(row.get("labresult", "")),
            )
            for _, row in df[df["patientunitstayid"].astype(str) == stay_id].iterrows()
        ]

    # ── 공통 유틸 ─────────────────────────────────────────────────

    def _extract_with_llm(self, note_text: str) -> dict:
        prompt = EXTRACT_PROMPT.format(note=note_text[:3000])
        # json_schema: A팀이 model_loader.py에 파라미터 추가 후 활성화
        response = llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt, json_schema=EXTRACT_SCHEMA)
        return self._parse_json(response)

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
