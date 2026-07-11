# 평가 결과

## Type1 — 추출 성능

| 소스 | 항목 | Precision | Recall | F1 |
|---|---|---|---|---|
| MIMIC | diagnoses | 0.909 | 1.0 | **0.952** |
| MIMIC | medications | 0.999 | 0.987 | **0.993** |
| MIMIC | observations | - | - | - |
| eICU | diagnoses | 0.768 | 0.982 | **0.862** |
| eICU | medications | 1.0 | 0.988 | **0.994** |
| eICU | observations | 1.0 | 1.0 | **1.0** |

## Type2 — 오분류율

| 소스 | 항목 | 오분류율 |
|---|---|---|
| MIMIC | situation | 0.0% |
| MIMIC | roles | 0.0% |
| eICU | situation | 평가 제외 |
| eICU | roles | 4.0% |

## Type3 — Hallucination 감소율 (단일 LLM Zero-shot 대비)

| 소스 | 항목 | 파이프라인 환각률 | Zero-shot 환각률 | 감소율 |
|---|---|---|---|---|
| MIMIC | diagnoses | 8.9% | 86.2% | **89.7%** |
| MIMIC | medications | 0.1% | 2.3% | **95.7%** |
| eICU | diagnoses | 19.9% | 92.6% | **78.5%** |
| eICU | medications | 0.0% | 31.1% | **100.0%** |
