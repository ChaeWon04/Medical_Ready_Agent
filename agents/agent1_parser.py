import json
import re
import uuid
import pandas as pd
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

ICD9_TO_ICD10 = {
    "250.00": "E11.9", "250.02": "E11.9", "401.9": "I10",
    "428.0": "I50.9", "410.90": "I21.9", "490": "J44.1",
    "493.90": "J45.909", "585.9": "N18.9", "276.1": "E87.1",
    "486": "J18.9", "414.01": "I25.10", "427.31": "I48.91",
}

SNOMED_TO_ICD10 = {
    "44054006": "E11.9", "73211009": "E11.9", "38341003": "I10",
    "22298006": "I21.9", "13645005": "J44.1", "195967001": "J45.909",
    "40055000": "N18.9", "49436004": "I48.91",
}


class Agent1Parser:

    # ── Synthea FHIR JSON (룰 기반) ───────────────────────────────

    def parse_synthea(self, fhir_path: str) -> AIReadyRecord:
        """FHIR Bundle JSON 파일 1개(환자 1명) → AIReadyRecord"""
        import json as _json
        with open(fhir_path, encoding="utf-8") as f:
            bundle = _json.load(f)

        entries = bundle.get("entry", [])
        resources = [e["resource"] for e in entries if "resource" in e]

        patient_id = self._fhir_patient_id(resources)
        diagnoses = self._fhir_diagnoses(resources)
        medications = self._fhir_medications(resources)
        observations = self._fhir_observations(resources)

        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="synthea",
            patient_id=patient_id,
            diagnoses=diagnoses,
            medications=medications,
            observations=observations,
            quality=QualityMetadata(reflexion_loops=0, q_index=0.0, status=DataStatus.NEEDS_REVIEW),
        )

    def _fhir_patient_id(self, resources: list) -> str:
        for r in resources:
            if r.get("resourceType") == "Patient":
                return r.get("id", str(uuid.uuid4()))
        return str(uuid.uuid4())

    def _fhir_diagnoses(self, resources: list) -> list[Diagnosis]:
        results = []
        for r in resources:
            if r.get("resourceType") != "Condition":
                continue
            codings = r.get("code", {}).get("coding", [])
            if not codings:
                continue
            snomed_code = codings[0].get("code", "")
            description = codings[0].get("display", "")
            clinical_status = (
                r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active")
            )
            icd10 = SNOMED_TO_ICD10.get(snomed_code) or self._llm_to_icd10(description)
            if not icd10:
                continue
            results.append(Diagnosis(
                icd10_code=icd10,
                description=description,
                confidence="confirmed" if clinical_status == "active" else "ruled_out",
                is_negated=clinical_status == "resolved",
            ))
        return results

    def _fhir_medications(self, resources: list) -> list[Medication]:
        results = []
        for r in resources:
            if r.get("resourceType") != "MedicationRequest":
                continue
            if r.get("status") not in ("active", "completed"):
                continue
            display = (
                r.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "")
            )
            name, dose, unit = self._parse_med_display(display)
            results.append(Medication(name=name, dose=dose, unit=unit))
        return results

    def _parse_med_display(self, display: str):
        """'Clopidogrel 75 MG Oral Tablet' → (name, dose, unit)"""
        match = re.match(r"^(.*?)\s+([\d.]+)\s*(MG|G|MCG|ML)\b", display, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            dose = self._safe_float(match.group(2))
            unit = match.group(3).lower().replace("ml", "mL")
            return name, dose, unit
        return display, None, None

    def _fhir_observations(self, resources: list) -> list[Observation]:
        results = []
        for r in resources:
            if r.get("resourceType") != "Observation":
                continue
            name = r.get("code", {}).get("text") or (
                r.get("code", {}).get("coding", [{}])[0].get("display", "")
            )
            vq = r.get("valueQuantity", {})
            if not vq:
                continue
            results.append(Observation(
                name=name,
                value=str(vq.get("value", "")),
                unit=vq.get("unit") or None,
            ))
        return results

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
            source="mimic_iv",  # eICU도 ICU 데이터로 통일
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
            source="mimic_iv",
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
        response = llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
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
