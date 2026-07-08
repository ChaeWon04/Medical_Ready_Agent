# Medical_Ready_Agent

의료 원본 데이터(Synthea / MIMIC-IV / eICU)를 LLM 기반 3단계 에이전트 파이프라인에 통과시켜,
구조화·검수·주석까지 끝난 "AI-Ready" 레코드(JSONL)로 변환하는 프로젝트입니다.

## 아키텍처

`graph/pipeline.py`가 LangGraph로 아래 3개 노드를 순서대로 실행합니다.

1. **Agent1 Parser** (`agents/agent1_parser.py`) — 소스별 원본 테이블/노트를 파싱해 `AIReadyRecord`로 변환
2. **Agent2 Reflexion** (`agents/agent2_reflexion.py`) — RAG(PMC 논문) 근거를 참고해 Critic이 문제를 찾고, 필요하면 Refine으로 재작성. `config.MAX_REFLEXION_LOOPS`(기본 3회)까지 반복하며 `q_index`가 `config.QUALITY_THRESHOLD`(기본 0.8) 이상이면 즉시 종료
3. **Agent3 Annotator** (`agents/agent3_annotator.py`) — 임상 상황/역할/접근성 점수 등 컨텍스트 주석 부여

출력 스키마는 `schemas/ai_ready_schema.py`의 `AIReadyRecord`를 따르며, 판정 기준 코드(NR1~)는
`agents/criteria.py`에 정의되어 있습니다.

실제 LLM 추론은 `main.py` 프로세스 안에서 도는 게 아니라, 별도로 띄운 **vLLM 서버**에 OpenAI 호환
API로 요청을 보내는 구조입니다 (`models/model_loader.py`).

## 환경 설정

```bash
git clone https://github.com/ChaeWon04/Medical_Ready_Agent.git
cd Medical_Ready_Agent
pip install -r requirements.txt
pip install vllm
```

GPU 인스턴스를 새로 띄울 때 드라이버/CUDA 버전이 안 맞으면 아래 compat 패키지를 설치합니다
(인스턴스마다 매번 필요할 수 있음, 경로는 `dpkg -L cuda-compat-13-0`로 재확인):

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-compat-13-0

echo 'export LD_LIBRARY_PATH=/usr/local/cuda-13.0/compat:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### vLLM 서버 실행 (터미널 하나 계속 띄워둠)

```bash
vllm serve Qwen/Qwen3-4B --port 8000 --dtype auto
```

`config.py`의 `MODEL_ID`(`Qwen/Qwen3-4B`)와 반드시 같은 모델을 서빙해야 합니다.

### 정상 작동 확인 (새 터미널)

```bash
curl http://localhost:8000/v1/models
```

## 파이프라인 실행

```bash
export VLLM_BASE_URL=http://localhost:8000/v1   # config.py 기본값과 동일, 명시적으로 설정 권장

# Synthea (합성 데이터, git에 샘플 포함됨)
python main.py --source synthea --data_dir data/raw/synthea

# MIMIC-IV
python main.py --source mimic_iv --data_dir data/raw/mimic4 --split train --max_records 200
python main.py --source mimic_iv --data_dir data/raw/mimic4 --split test

# eICU
python main.py --source eicu --data_dir data/raw/eicu --split train
python main.py --source eicu --data_dir data/raw/eicu --split test
```

- `--source`는 `synthea` / `mimic_iv` / `eicu` 셋 중 하나만 허용됩니다 (`mimic`은 오류).
- Linux는 대소문자를 구분하므로 `--data_dir` 경로와 실제 폴더명의 대소문자가 정확히 일치해야 합니다.
- 결과는 `data/output/ai_ready_<split>.jsonl`과 `data/output/run.log`에 누적 기록됩니다.

### 소스별 필요 파일

| source | `--data_dir` | 필요 파일 |
|---|---|---|
| synthea | `data/raw/synthea` | `patients.csv`, `conditions.csv`, `medications.csv`, `encounters.csv`, `observations.csv` |
| mimic_iv | `data/raw/mimic4` | `admissions.csv`, `patients.csv`, `diagnoses_icd.csv`, `prescriptions.csv`, `d_icd_diagnoses_ICD9.csv`/`_ICD10.csv`, (선택) `labevents.csv`, (선택) `mimic_split.csv` |
| eicu | `data/raw/eicu` | `patient.csv`, `diagnosis.csv`, `medication.csv`, `lab.csv`, (선택) `note.csv`, (선택) `eicu_split.csv` |

## MIMIC-IV / eICU 데이터 취급 주의

`data/raw/mimic4/*`, `data/raw/eicu/*`는 `.gitignore`로 막혀 있어 **git에 올라가지 않습니다**.
PhysioNet 자격 인증(credentialed access)이 필요한 규제 데이터이므로:

- 팀원 각자 본인 명의로 credentialed access를 받아 개별적으로 원본을 내려받아야 합니다.
- 원본이든 이 파이프라인이 만든 파생 결과물(JSONL)이든, 일반 개인 클라우드 드라이브 등 비보안
  경로로 공유하지 않습니다. 소속 기관이 승인한 보안 스토리지 또는 통제된 서버 안에서만 공유합니다.

## RAG (PMC 논문 기반 팩트체크)

Agent2 Critic이 참고하는 PMC 벡터DB는 `rag/retriever.py`가 `config.CHROMA_DIR`
(`rag/chroma_db/`) + 컬렉션명 `pmc_medical`을 읽습니다. 이 DB가 비어 있어도 파이프라인은
에러 없이 "근거 없음"으로 처리하고 계속 진행합니다.

```bash
python data/collect_pmc.py      # NCBI PMC OA 벌크 데이터에서 논문 샘플링 → ./pmc_xml_selected/
python rag/build_vectordb.py    # XML 파싱·청킹·임베딩 → rag/pmc_vectordb/ (컬렉션명 pmc_corpus)
```

> ⚠️ **알려진 이슈**: 위 두 스크립트가 실제로 쓰는 경로/컬렉션명이 서로, 그리고
> `rag/retriever.py`가 읽는 경로(`rag/chroma_db/`, `pmc_medical`)와도 일치하지 않습니다.
> 즉 위 명령을 그대로 실행해도 Agent2가 실제로 참조하는 벡터DB에는 반영되지 않습니다.
> 지금은 `rag/pmc_vectordb.zip`(사전 빌드된 결과물)을 압축 해제해 `rag/chroma_db/`
> 위치·컬렉션명에 맞게 수동으로 옮기는 임시 방편이 필요하며, 근본적으로는 세 파일의
> 경로/컬렉션명을 통일하는 코드 수정이 필요합니다.

## 품질 지표 (Q-index)

`agents/agent2_reflexion.py`의 `_calc_q_index()`가 계산하는 규칙 기반 점수입니다.

- 1.0에서 시작
- Critic이 찾은 issue 1개당 -0.1
- 리플렉션 루프 1회 초과분마다 -0.05
- 활성 진단(active diagnosis)이 하나도 없으면 -0.2
- 투약·검사 관측치가 둘 다 없으면 -0.1
- 주호소·증상이 둘 다 없으면 -0.1
- 0~1 사이로 clamp

`config.QUALITY_THRESHOLD`(기본 0.8) 이상이면 해당 루프에서 통과 처리됩니다. 사람 라벨링
검증셋과의 상관관계가 아직 확인되지 않은 휴리스틱이므로, 절대적인 정확도 지표로 간주하지
않는 것을 권장합니다.
