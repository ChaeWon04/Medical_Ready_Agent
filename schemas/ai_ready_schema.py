from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
import re


class ClinicalSituation(str, Enum):
    OUTPATIENT = "outpatient"   # 진료
    EMERGENCY = "emergency"     # 응급
    INPATIENT = "inpatient"     # 입원


class RelationshipRole(str, Enum):
    PHYSICIAN = "physician"
    PATIENT = "patient"
    GUARDIAN = "guardian"


class DataStatus(str, Enum):
    AI_READY = "AI_READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


class Diagnosis(BaseModel):
    icd10_code: str
    description: str
    confidence: Literal["confirmed", "suspected", "ruled_out"]
    is_negated: bool = False  # "r/o DM" 같은 부정 표현 처리

    @field_validator("icd10_code")
    @classmethod
    def validate_icd10(cls, v: str) -> str:
        if not re.match(r"^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$", v):
            raise ValueError(f"유효하지 않은 ICD-10 코드: {v}")
        return v


class Medication(BaseModel):
    name: str
    dose: Optional[float] = None
    unit: Optional[Literal["g", "mg", "mcg", "mL", "unit"]] = None  # 단위 오인식 방지
    route: Optional[str] = None
    frequency: Optional[str] = None


class Observation(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: Optional[bool] = None


class ClinicalContext(BaseModel):
    """Agent 3가 생성하는 임상 컨텍스트 주석"""
    situation: ClinicalSituation
    roles: List[RelationshipRole]
    accessibility_score: float = Field(ge=0.0, le=1.0)  # 가독성·지역격차 반영


class QualityMetadata(BaseModel):
    """Agent 2 Reflexion 루프 결과"""
    reflexion_loops: int = Field(ge=0, le=3)
    hallucination_flags: List[str] = []  # 감지된 오류 목록
    q_index: float = Field(ge=0.0, le=1.0)  # 품질 지수
    status: DataStatus


class AIReadyRecord(BaseModel):
    """최종 AI-Ready 출력 스키마"""
    record_id: str
    source: Literal["synthea", "mimic_iv", "eicu"]
    patient_id: str

    # 환자 기본 정보 (juyoung 브랜치)
    age: Optional[int] = None
    gender: Optional[str] = None
    chief_complaint: Optional[str] = None
    symptoms: List[str] = []

    # Agent 1 출력
    diagnoses: List[Diagnosis] = []
    medications: List[Medication] = []
    observations: List[Observation] = []
    clinical_text: Optional[str] = None  # 원본 임상 노트 (MIMIC-IV)

    # Agent 3 출력
    context: Optional[ClinicalContext] = None

    # Agent 2 출력
    quality: QualityMetadata

    # 사람 검토 필요 플래그 (juyoung 브랜치)
    flagged: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def is_valid(self) -> bool:
        return self.quality.status == DataStatus.AI_READY and not self.flagged
