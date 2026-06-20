from pydantic import BaseModel, Field
from typing import Optional


class Medication(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None


class AIReadyRecord(BaseModel):
    patient_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    chief_complaint: Optional[str] = None
    diagnoses: list[str] = Field(default_factory=list)
    icd10_codes: list[str] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    encounter_type: Optional[str] = None  # "outpatient" | "emergency" | "inpatient"
    quality_score: Optional[float] = None
    readability_score: Optional[float] = None
    source: str = "synthea"  # "synthea" | "mimic" | "eicu"
    flagged: bool = False
