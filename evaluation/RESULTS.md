# 평가 결과 (최신)

`python evaluation/compute_metrics.py` 실행 결과. 숫자 바뀌면 이 파일도 다시 생성해서 갱신할 것.

## Type1 — 추출 성능

| 소스 | 항목 | Precision | Recall | F1 | 비고 |
|---|---|---|---|---|---|
| MIMIC | diagnoses | 0.909 | 1.0 | 0.952 | |
| MIMIC | medications | 0.999 | 0.987 | 0.993 | |
| MIMIC | observations | - | - | - | 원본에 lab 데이터 없어 평가 제외 |
| eICU | diagnoses | 0.183 | 0.443 | 0.259 | golden standard 보완 대기중 (49건 검토 요청함) |
| eICU | medications | 1.0 | 0.965 | 0.982 | golden standard 보완 완료 |
| eICU | observations | 1.0 | 1.0 | 1.0 | 결정론적 테이블 복사라 참고용 (AI 품질 지표 아님) |

## Type2 — 오분류율

| 소스 | 항목 | 오분류율 | 비고 |
|---|---|---|---|
| MIMIC | situation | 0.0% | |
| MIMIC | roles | 0.0% | |
| eICU | situation | 평가 제외 | 원본에 입원경로 정보 없음, 파이프라인이 무조건 inpatient로 고정 출력하는 구조적 한계 |
| eICU | roles | 24.0% | golden standard가 성인 환자에게도 임상적 판단으로 보호자 role을 부여한 케이스를 규칙 기반 로직(나이<18·키워드)이 못 잡음. 파이프라인 한계로 보고서에 서술 |

## Type3 — Hallucination 감소율

미계산. zero-shot 베이스라인(`evaluation/run_zeroshot_baseline.py`)을 GPU에서 실행해야 함.

## 남은 작업

- [ ] eICU diagnoses golden standard 보완 (`evaluation/eicu_diagnosis_review_needed.csv` 49건 검토 + 원본 전체 반영)
- [ ] Type3용 zero-shot 베이스라인 생성 (MIMIC/eICU 둘 다, GPU 필요)
- [ ] Type3 계산 스크립트 작성 (베이스라인 나온 뒤)
