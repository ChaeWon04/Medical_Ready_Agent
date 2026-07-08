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

# 약물 dose 단위 정규화 표. key는 전부 소문자로 비교(대소문자 무시), value가 최종 저장되는 정규 표기.
# 1) 계량 단위 - UCUM(data/vocab/Athena.zip) 기준으로 확인된 것들
# 2) 제형 단위 - RxNorm Dose Form(TTY=DF, rxnav.nlm.nih.gov) 기준으로 확인된 것들
# 3) 포장/개수 단위 - 표준 어휘엔 없지만 흔한 영어 단어라 mg/mcg류와 헷갈릴 위험이 없어 그대로 인정
UNIT_CANONICAL = {
    # 1) 계량 단위 (UCUM)
    "g": "g", "gm": "g",
    "mg": "mg",
    "mcg": "mcg",
    "ml": "mL",
    "unit": "unit", "units": "unit",
    "meq": "mEq",
    "mmol": "mmol",
    "l": "L",
    "%": "%",
    "iu": "IU",
    "mu": "MU", "million units": "MU",
    # 2) 제형 단위 (RxNorm Dose Form)
    "tab": "TAB", "cap": "CAP", "puff": "PUFF", "spry": "SPRY", "ptch": "PTCH",
    "inh": "INH", "supp": "SUPP", "syr": "SYR", "loz": "LOZ", "waf": "WAF",
    # 3) 포장/개수 단위 (오인식 위험 없어 표준 어휘 없이 그대로 인정)
    "vial": "VIAL", "drop": "DROP", "gtt": "gtt", "amp": "AMP", "pkt": "PKT",
    "tube": "TUBE", "stck": "STCK", "neb": "NEB", "bag": "BAG", "cadd": "CADD",
    "dose": "dose", "enema": "Enema", "film": "FILM", "troc": "TROC",
    "crea": "CREA", "appl": "Appl",
    # 속도/복합 표기 (드묾, 원본 그대로 인정)
    "mcg/hr": "mcg/hr", "mcg/h": "mcg/hr", "mg/hr": "mg/hr", "mg/day": "mg/day",
    "ml/hr": "mL/hr", "mcg/kg/min": "mcg/kg/min", "mg pe": "mg PE",
}


def normalize_unit(raw) -> Optional[str]:
    if not raw:
        return None
    return UNIT_CANONICAL.get(str(raw).strip().lower())


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
    csv_path = Path(__file__).parent.parent / "data" / "vocab" / "icd9to10.csv"
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

def _load_snomed_mapping() -> tuple[dict, dict]:
    csv_path = Path(__file__).parent.parent / "data" / "vocab" / "snomed_to_icd10.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype=str)
        code_map = dict(zip(df["snomed_code"].str.strip(), df["icd10_code"].str.strip()))
        desc_map = dict(zip(df["icd10_code"].str.strip(), df["icd10_description"].str.strip()))
        return code_map, desc_map
    return {
        "44054006": "E11.9", "73211009": "E11.9", "38341003": "I10",
        "22298006": "I21.9", "13645005": "J44.1", "195967001": "J45.909",
        "49436004": "I48.91", "66383009": "K05.10", "65363002": "H66.9",
    }, {}

SNOMED_TO_ICD10, ICD10_DESCRIPTIONS = _load_snomed_mapping()


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
        encounter_date = self._synthea_encounter_date(encounters, pid)

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
            encounter_date=encounter_date,
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
            snomed_desc = str(row.get("DESCRIPTION", ""))
            snomed = str(row.get("CODE", "")).strip()
            code = SNOMED_TO_ICD10.get(snomed) or self._llm_to_icd10(snomed_desc)
            # ICD10 표준 명칭이 있으면 사용, 없으면 Synthea SNOMED 설명 유지 (항목 7)
            desc = ICD10_DESCRIPTIONS.get(code, snomed_desc) if code else snomed_desc
            stop_val = row.get("STOP")
            is_active = pd.isna(stop_val) or str(stop_val).strip() in ("", "nan")
            onset = str(row.get("START", "")).strip() or None
            if code:
                results.append(Diagnosis(
                    icd10_code=code,
                    description=desc,
                    confidence="confirmed",
                    is_active=is_active,
                    onset_date=onset,
                ))
        return results

    def _synthea_medications(self, df: pd.DataFrame, pid: str) -> list[Medication]:
        sub = df[df["PATIENT"] == pid].copy()
        if sub.empty:
            return []
        sub["_is_active"] = sub["STOP"].isna() | (sub["STOP"].astype(str).str.strip().isin(["", "nan"]))
        sub = sub.sort_values(["_is_active", "START"], ascending=[False, False])
        sub = sub.drop_duplicates(subset=["DESCRIPTION"], keep="first")
        results = []
        for _, row in sub.iterrows():
            name = str(row.get("DESCRIPTION", ""))
            dose, unit = self._parse_dose(name)
            results.append(Medication(
                name=name,
                dose=dose,
                unit=unit,
                is_active=bool(row["_is_active"]),
            ))
        return results

    def _synthea_observations(self, df: pd.DataFrame, pid: str) -> list[Observation]:
        _EXCLUDE_OBS = {"QALY", "DALY", "QOLS"}
        sub = df[(df["PATIENT"] == pid) & (df["TYPE"] != "text")]
        sub = sub[~sub["DESCRIPTION"].isin(_EXCLUDE_OBS)]
        sub = sub.sort_values("DATE")
        sub = sub.drop_duplicates(subset=["DESCRIPTION"], keep="last")
        return [
            Observation(
                name=str(row.get("DESCRIPTION", "")),
                value=str(row.get("VALUE", "")),
                unit=str(row.get("UNITS", "")) or None,
                observed_date=str(row.get("DATE", "")) or None,
            )
            for _, row in sub.iterrows()
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
        _EXCLUDE_PREFIX = (
            "are you", "have you", "do you", "what", "how", "which", "when",
            "primary insurance", "employment", "education", "housing", "address",
            "race", "hispanic", "language", "discharged", "farm work", "refugee",
            "stress level", "tobacco", "pregnancy",
        )
        obs = observations[observations["PATIENT"] == pid]
        raw = obs[obs["TYPE"] == "text"]["DESCRIPTION"].dropna().unique()
        symptoms = [
            d for d in raw
            if not any(d.lower().startswith(e) for e in _EXCLUDE_PREFIX)
            and not any(k.lower() in d.lower() for k in self._SDOH_KEYWORDS)
        ]
        if not symptoms and diagnoses:
            raw = llm.generate(
                system_prompt="Return symptoms as comma-separated list only. No explanation.",
                user_prompt=f"List 3-5 main symptoms for these diagnoses: {diagnoses}",
            )
            symptoms = [s.strip() for s in raw.split(",") if s.strip()]
        return symptoms

    def _synthea_encounter_date(self, encounters: pd.DataFrame, pid: str) -> Optional[str]:
        enc = encounters[encounters["PATIENT"] == pid]
        if enc.empty:
            return None
        return str(enc.sort_values("START", ascending=False)["START"].iloc[0])

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
        admissions_df: pd.DataFrame = None,
        patients_df: pd.DataFrame = None,
        icd_desc_df: pd.DataFrame = None,
        labevents_df: pd.DataFrame = None,
    ) -> AIReadyRecord:
        if admissions_df is None: admissions_df = pd.DataFrame()
        if patients_df is None: patients_df = pd.DataFrame()
        if icd_desc_df is None: icd_desc_df = pd.DataFrame()
        if labevents_df is None: labevents_df = pd.DataFrame()

        age, gender = None, None
        if not patients_df.empty:
            p_rows = patients_df[patients_df["subject_id"].astype(str) == subject_id]
            if not p_rows.empty:
                p = p_rows.iloc[0]
                age = self._safe_int(p.get("anchor_age"))
                gender = str(p.get("gender", "")).strip() or None

        encounter_date, chief_complaint = None, None
        if not admissions_df.empty:
            a_rows = admissions_df[admissions_df["hadm_id"].astype(str) == hadm_id]
            if not a_rows.empty:
                a = a_rows.iloc[0]
                admittime = str(a.get("admittime", "")).strip()
                encounter_date = admittime[:10] if admittime and admittime.lower() not in ("", "nan") else None
                cc = str(a.get("diagnosis", "")).strip()
                chief_complaint = cc if cc and cc.lower() not in ("", "nan", "none") else None

        diagnoses = self._mimic_diagnoses(diagnoses_df, subject_id, hadm_id, icd_desc_df)
        medications = self._mimic_medications(prescriptions_df, subject_id, hadm_id)
        observations = self._mimic_labevents(labevents_df, hadm_id) if not labevents_df.empty else []

        # MIMIC-IV admissions엔 자유텍스트 diagnosis 컬럼이 없음(MIMIC-III에만 있던 필드).
        # 없으면 주진단(seq_num=1, diagnoses[0])을 chief_complaint 대리값으로 사용.
        if not chief_complaint and diagnoses:
            chief_complaint = diagnoses[0].description

        # ICD-10 R00-R99는 "증상, 징후 및 이상 임상/검사 소견" 챕터 - 공식적으로 증상 코드임
        symptoms = [d.description for d in diagnoses if d.icd10_code and d.icd10_code[0] == "R"]

        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="mimic_iv",
            patient_id=subject_id,
            age=age,
            gender=gender,
            chief_complaint=chief_complaint,
            symptoms=symptoms,
            diagnoses=diagnoses,
            medications=medications,
            observations=observations,
            encounter_date=encounter_date,
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

    def _mimic_diagnoses(self, df: pd.DataFrame, subject_id: str, hadm_id: str,
                         icd_desc_df: pd.DataFrame = None) -> list[Diagnosis]:
        if icd_desc_df is None: icd_desc_df = pd.DataFrame()
        desc_lookup = {}
        if not icd_desc_df.empty:
            for _, r in icd_desc_df.iterrows():
                k = (str(r.get("icd_code", "")).strip(), str(r.get("icd_version", "")).strip())
                desc_lookup[k] = str(r.get("long_title", "")).strip()

        mask = (df["subject_id"].astype(str) == subject_id) & (df["hadm_id"].astype(str) == hadm_id)
        sub = df[mask]
        if "seq_num" in sub.columns:
            sub = sub.sort_values("seq_num")  # seq_num=1(주진단)이 항상 첫 항목이 되도록
        results = []
        for _, row in sub.iterrows():
            raw_code = str(row.get("icd_code", "")).strip()
            version = str(row.get("icd_version", "10")).strip()
            desc = desc_lookup.get((raw_code, version), raw_code)
            if version == "9":
                code = ICD9_TO_ICD10.get(raw_code, self._llm_to_icd10(desc))
                # ICD-9 -> ICD-10 변환 시 desc는 원래 ICD-9 설명 그대로라 코드-설명이 안 맞을 수 있음.
                # 바뀐 ICD-10 코드 기준으로 공식 설명을 다시 찾아서 맞춰줌.
                # desc_lookup의 키는 dot 없는 raw 포맷(d_icd_diagnoses_ICD10.csv)이라 맞춰서 비교
                desc = desc_lookup.get((code.replace(".", ""), "10"), desc) if code else desc
            else:
                code = self._format_icd10(raw_code)
            if code:
                results.append(Diagnosis(icd10_code=code, description=desc, confidence="confirmed"))
        return results

    def _mimic_labevents(self, df: pd.DataFrame, hadm_id: str) -> list[Observation]:
        results = []
        for _, row in df[df["hadm_id"].astype(str) == hadm_id].iterrows():
            val = str(row.get("value", "")).strip()
            if not val or val.lower() in ("nan", "none", ""):
                continue
            results.append(Observation(
                name=str(row.get("label", row.get("itemid", ""))).strip(),
                value=val,
                unit=str(row.get("valueuom", "")).strip() or None,
                is_abnormal=str(row.get("flag", "")).lower() == "abnormal" or None,
            ))
        return results

    def _mimic_medications(self, df: pd.DataFrame, subject_id: str, hadm_id: str) -> list[Medication]:
        mask = (df["subject_id"].astype(str) == subject_id) & (df["hadm_id"].astype(str) == hadm_id)
        results = []
        for _, row in df[mask].iterrows():
            results.append(Medication(
                name=str(row.get("drug", "")),
                dose=self._safe_float(row.get("dose_val_rx")),
                unit=normalize_unit(row.get("dose_unit_rx")),
                route=str(row.get("route", "")) or None,
            ))
        return results

    # ── eICU ──────────────────────────────────────────────────────

    def parse_eicu_structured(
        self,
        patient_stay_id: str,
        patient_row: dict = None,
        diagnosis_df: pd.DataFrame = None,
        medication_df: pd.DataFrame = None,
        lab_df: pd.DataFrame = None,
    ) -> AIReadyRecord:
        if patient_row is None: patient_row = {}
        if diagnosis_df is None: diagnosis_df = pd.DataFrame()
        if medication_df is None: medication_df = pd.DataFrame()
        if lab_df is None: lab_df = pd.DataFrame()

        age_raw = str(patient_row.get("age", "")).strip()
        age = 90 if age_raw.startswith(">") else self._safe_int(age_raw)

        gender_raw = str(patient_row.get("gender", "")).strip().lower()
        gender = "M" if gender_raw == "male" else ("F" if gender_raw == "female" else None)

        cc = str(patient_row.get("apacheadmissiondx", "")).strip()
        chief_complaint = cc if cc and cc.lower() not in ("", "nan", "none") else None

        return AIReadyRecord(
            record_id=str(uuid.uuid4()),
            source="eicu",
            patient_id=patient_stay_id,
            age=age,
            gender=gender,
            chief_complaint=chief_complaint,
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
            # diagnosisstring은 eICU 자체 분류체계라 "system|category|specific" 형태의
            # 파이프 구분 문자열임. 최상위 신체계통 분류(첫 조각)만 빼고 나머지를 이어붙여서
            # 사람이 읽을 수 있는 설명으로 만듦.
            raw_desc = str(row.get("diagnosisstring", "")).strip()
            parts = [p.strip() for p in raw_desc.split("|") if p.strip()]
            desc = ", ".join(parts[1:]) if len(parts) > 1 else raw_desc
            icd9_raw = str(row.get("icd9code", "")).strip()
            codes = [c.strip() for c in icd9_raw.split(",") if c.strip() and c.strip().lower() != "nan"]
            code = None
            for c in codes:
                code = ICD9_TO_ICD10.get(c)
                if code:
                    break
            if not code:
                code = self._llm_to_icd10(desc) if desc else None
            if code:
                results.append(Diagnosis(icd10_code=code, description=desc, confidence="confirmed"))
        return results

    # eICU dosage가 가끔 "20 7"처럼 "용량 단위코드" 숫자쌍으로만 들어있음(단위가 텍스트로 안 남고
    # 내부 코드로 export된 것으로 보임). drugname에 스스로 용량이 적힌 행들로 역추적해서 확인한
    # 코드만 매핑 - 확신 없는 코드(8, 10021 등)는 억지로 추측하지 않고 그대로 null 둠.
    _EICU_DOSAGE_CODE_UNIT = {"1": "mL", "3": "mg", "4": "g", "7": "mEq"}

    def _parse_eicu_dosage(self, dosage_str: str) -> tuple[Optional[float], Optional[str]]:
        m = re.match(r"^([\d.]+)\s+(\d+)$", dosage_str.strip())
        if m:
            amount, code = m.group(1), m.group(2)
            unit = self._EICU_DOSAGE_CODE_UNIT.get(code)
            if unit:
                return self._safe_float(amount), normalize_unit(unit)
        return self._parse_dose(dosage_str)

    def _eicu_medications(self, df: pd.DataFrame, stay_id: str) -> list[Medication]:
        results = []
        for _, row in df[df["patientunitstayid"].astype(str) == stay_id].iterrows():
            drugname = row.get("drugname")
            if pd.isna(drugname) or not str(drugname).strip():
                continue  # drugname 결측치를 "nan" 문자열로 저장하지 않고 그냥 건너뜀
            dose_str = str(row.get("dosage", ""))
            dose, unit = self._parse_eicu_dosage(dose_str)
            results.append(Medication(
                name=str(drugname).strip(),
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

    # 긴 토큰(mcg/hr 등)이 짧은 토큰(mcg)보다 먼저 매칭되도록 길이 내림차순 정렬
    _UNIT_TOKEN_PATTERN = "|".join(
        re.escape(k) for k in sorted(UNIT_CANONICAL.keys(), key=len, reverse=True)
    )

    def _parse_dose(self, dose_str: str) -> tuple[Optional[float], Optional[str]]:
        match = re.search(rf"([\d.]+)\s*({self._UNIT_TOKEN_PATTERN})", dose_str, re.IGNORECASE)
        if match:
            return self._safe_float(match.group(1)), normalize_unit(match.group(2))
        return None, None

    def _safe_float(self, val) -> Optional[float]:
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, val) -> Optional[int]:
        try:
            return int(float(str(val)))
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
