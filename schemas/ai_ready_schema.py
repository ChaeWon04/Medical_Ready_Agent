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
    is_active: bool = True    # STOP 컬럼 기반: 현재 활성 질환 여부
    onset_date: Optional[str] = None  # 진단 시작일 (START 컬럼)

    @field_validator("icd10_code")
    @classmethod
    def validate_icd10(cls, v: str) -> str:
        # ICD10CM은 3번째 자리가 문자인 최신 코드(I1A, I5A 등)도 유효
        if not re.match(r"^[A-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$", v):
            raise ValueError(f"유효하지 않은 ICD-10 코드: {v}")
        return v


class Medication(BaseModel):
    name: str
    dose: Optional[float] = None
    # 단위 화이트리스트는 agents/agent1_parser.py의 UNIT_CANONICAL/normalize_unit()에서 강제됨
    # (계량 단위는 UCUM, 제형은 RxNorm Dose Form 기준으로 검증된 값만 통과, 그 외는 파싱 단계에서 None)
    unit: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    is_active: bool = True  # STOP 컬럼 기반: 현재 복용 중 여부


class Observation(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    is_abnormal: Optional[bool] = None
    observed_date: Optional[str] = None  # 측정일 (DATE 컬럼)


class ClinicalContext(BaseModel):
    """Agent 3가 생성하는 임상 컨텍스트 주석"""
    situation: ClinicalSituation
    roles: List[RelationshipRole]
    accessibility_score: float = Field(ge=0.0, le=1.0)  # 가독성·지역격차 반영


class QualityMetadata(BaseModel):
    """Agent 2 Reflexion 루프 결과"""
    reflexion_loops: int = Field(ge=0, le=3)
    hallucination_flags: List[str] = []  # 감지된 오류 목록
    reason_codes: List[str] = []  # golden standard 사유 코드 (NR1, NR8 등) - agents/criteria.py 참고
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

    encounter_date: Optional[str] = None  # 기준 방문일 (가장 최근 encounter START)

    # 사람 검토 필요 플래그 (juyoung 브랜치)
    flagged: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)

    def is_valid(self) -> bool:
        return self.quality.status == DataStatus.AI_READY and not self.flagged
