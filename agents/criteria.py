"""
Golden standard 검수 기준(NR 코드) 정의 + 규칙 기반(rule) 체크 함수.

check_type:
  "rule" - 파이썬 코드로 결정론적으로 판정 (LLM 호출 없음, 크레딧 소모 없음)
  "llm"  - CRITIC_PROMPT를 통해 critic LLM이 의미적으로 판단 (agent2_reflexion.py)
  "gate" - 별도 status 게이트로 이미 처리됨 (reason_codes에 라벨만 붙음, issues/refine 대상 아님)
  "upstream" - 더 앞 단계(파싱, JSON 검증)에서 이미 차단되어 critic까지 도달하지 않음
"""
import re
from schemas.ai_ready_schema import AIReadyRecord

CRITERIA = [
    {"code": "NR1", "category": "데이터 공백", "check_type": "rule",
     "description": "JSON 주요 필수 Key의 Value가 빈 문자열, 빈 배열이거나 필드 자체가 누락된 경우"},
    {"code": "NR2", "category": "의료 정보 누락", "check_type": "rule",
     "description": "필드는 채워져 있으나 임상 도메인 정보가 없는 플레이스홀더 값(Unknown, None 등)인 경우"},
    {"code": "NR3", "category": "임상 데이터 부재", "check_type": "gate",
     "description": "필수 임상 정보(CC, Symptoms)가 파이프라인 최소 추출 규격 미달로 비어있는 상태 "
                     "(NR1의 CC/Symptoms 전용 사례 - 새 로직 아님, has_context 게이트에 라벨만 부여)"},
    {"code": "NR4", "category": "인코딩/텍스트 깨짐", "check_type": "rule",
     "description": "String 데이터에 인코딩 깨짐(mojibake) 또는 이상 특수문자가 삽입된 경우"},
    {"code": "NR5", "category": "문맥/논리 해석 불가", "check_type": "llm",
     "description": "임상적 선후관계가 무너졌거나 필드 간 구조적 불일치로 해석 불가한 경우 (negation 포함)"},
    {"code": "NR6", "category": "시스템/파싱 오류", "check_type": "upstream",
     "description": "JSON Syntax 에러, Truncated 등 - parse_node에서 실패하면 error 상태로 빠져 critic까지 안 옴"},
    {"code": "NR7", "category": "개인정보 노출", "check_type": "rule",
     "description": "연구원 실명, 병원 코드, 로컬 경로 등 파이프라인이 새로 흘린 민감정보. "
                     "MIMIC/eICU는 이미 비식별화되어 있어 현재 데이터엔 거의 안 걸림 - "
                     "현장 데이터 적용 대비용 안전망으로 미리 추가"},
    {"code": "NR8", "category": "Reflexion Critic 검출", "check_type": "gate",
     "description": "critic LLM이 찾아낸 모든 임상/구조적 모순 (NR5, NR11 등 llm 판정의 catch-all 라벨)"},
    {"code": "NR9", "category": "활성 진단 없음", "check_type": "gate",
     "description": "diagnoses 배열 내 is_active=true인 진단이 0개인 상태 (파이프라인 에러) - "
                     "새 로직 아님, active_dx 게이트에 라벨만 부여"},
    {"code": "NR10", "category": "코드-설명 불일치", "check_type": "upstream",
     "description": "ICD 코드와 description이 다른 질병을 가리키는 경우. "
                     "agent1_parser._mimic_diagnoses에서 공식 크로스워크 대조로 파싱 단계에서 원천 차단됨"},
    {"code": "NR11", "category": "약물 단위 오류", "check_type": "llm",
     "description": "medications 용량 단위가 g/mg/mcg 간 혼용되거나 비정상 수치인 경우"},
]

_PLACEHOLDER_VALUES = {"unknown", "none", "n/a", "na", "null", "undefined", "-", "nan"}

_MOJIBAKE_PATTERN = re.compile(r"�|â€|Ã[\x80-\xbf]")

# NR7: 현재 데이터엔 해당 없음(MIMIC/eICU가 이미 비식별화), 현장 적용 대비용
_LOCAL_PATH_PATTERN = re.compile(r"(/home/[\w./-]+|/Users/[\w./-]+|[A-Za-z]:\\\\Users\\\\[\w.\\\\-]+)")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def _is_placeholder(text) -> bool:
    return isinstance(text, str) and text.strip().lower() in _PLACEHOLDER_VALUES


def check_nr1_empty_fields(record: AIReadyRecord) -> list[dict]:
    issues = []
    for i, dx in enumerate(record.diagnoses):
        if not dx.icd10_code or not dx.icd10_code.strip():
            issues.append({"code": "NR1", "field": f"diagnoses[{i}].icd10_code",
                            "issue": "필수 필드 icd10_code가 비어있음", "suggested_fix": "값 채우거나 항목 제거"})
        if not dx.description or not dx.description.strip():
            issues.append({"code": "NR1", "field": f"diagnoses[{i}].description",
                            "issue": "필수 필드 description이 비어있음", "suggested_fix": "값 채우거나 항목 제거"})
    for i, med in enumerate(record.medications):
        if not med.name or not med.name.strip():
            issues.append({"code": "NR1", "field": f"medications[{i}].name",
                            "issue": "필수 필드 name이 비어있음", "suggested_fix": "값 채우거나 항목 제거"})
    return issues


def check_nr2_placeholder_values(record: AIReadyRecord) -> list[dict]:
    issues = []
    if _is_placeholder(record.chief_complaint):
        issues.append({"code": "NR2", "field": "chief_complaint",
                        "issue": f"플레이스홀더 값 '{record.chief_complaint}'", "suggested_fix": "null로 대체"})
    for i, s in enumerate(record.symptoms):
        if _is_placeholder(s):
            issues.append({"code": "NR2", "field": f"symptoms[{i}]",
                            "issue": f"플레이스홀더 값 '{s}'", "suggested_fix": "항목 제거"})
    for i, dx in enumerate(record.diagnoses):
        if _is_placeholder(dx.description):
            issues.append({"code": "NR2", "field": f"diagnoses[{i}].description",
                            "issue": f"플레이스홀더 값 '{dx.description}'", "suggested_fix": "항목 제거 또는 재파싱"})
    return issues


def check_nr4_encoding_artifacts(record: AIReadyRecord) -> list[dict]:
    issues = []
    texts = [("chief_complaint", record.chief_complaint)]
    texts += [(f"symptoms[{i}]", s) for i, s in enumerate(record.symptoms)]
    texts += [(f"diagnoses[{i}].description", d.description) for i, d in enumerate(record.diagnoses)]
    for field, text in texts:
        if text and _MOJIBAKE_PATTERN.search(text):
            issues.append({"code": "NR4", "field": field,
                            "issue": f"인코딩 깨짐 의심: {text[:50]}", "suggested_fix": "원본 인코딩 재확인 후 재파싱"})
    return issues


def check_nr7_pii_leakage(record: AIReadyRecord) -> list[dict]:
    """MIMIC/eICU는 이미 비식별화된 데이터라 현재는 거의 안 걸림.
    파이프라인이 처리 중 새로 흘린 노이즈(로컬 경로/이메일/IP)만 대상 - 현장 데이터 적용 대비용."""
    issues = []
    texts = [("chief_complaint", record.chief_complaint), ("clinical_text", record.clinical_text)]
    texts += [(f"symptoms[{i}]", s) for i, s in enumerate(record.symptoms)]
    for field, text in texts:
        if not text:
            continue
        if _LOCAL_PATH_PATTERN.search(text):
            issues.append({"code": "NR7", "field": field, "issue": "로컬 파일 경로 노출 의심", "suggested_fix": "제거"})
        if _EMAIL_PATTERN.search(text):
            issues.append({"code": "NR7", "field": field, "issue": "이메일 주소 노출 의심", "suggested_fix": "마스킹"})
        if _IP_PATTERN.search(text):
            issues.append({"code": "NR7", "field": field, "issue": "IP 주소 노출 의심", "suggested_fix": "마스킹"})
    return issues


# check_type="rule"인 것들만 순서대로. NR3/NR9는 별도 status 게이트라 여기 안 들어감(agent2_reflexion.run 참고).
RULE_CHECKS = [
    check_nr1_empty_fields,
    check_nr2_placeholder_values,
    check_nr4_encoding_artifacts,
    check_nr7_pii_leakage,
]


def run_rule_checks(record: AIReadyRecord) -> list[dict]:
    issues = []
    for check in RULE_CHECKS:
        issues.extend(check(record))
    return issues
