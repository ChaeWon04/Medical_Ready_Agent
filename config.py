from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PMC_DIR = DATA_DIR / "pmc"
OUTPUT_DIR = DATA_DIR / "output"
CHROMA_DIR = BASE_DIR / "rag" / "chroma_db"

# Synthea CSV 경로 (juyoung)
SYNTHEA_CSV_DIR = DATA_DIR / "synthea" / "synthea_sample_data_csv_latest"

for d in [RAW_DIR, PMC_DIR, OUTPUT_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 데이터 소스 & API 라우팅
DATA_SOURCE = "synthea"  # "synthea" | "mimic_iv" | "eicu"
USE_CLAUDE_API = DATA_SOURCE == "synthea"  # Synthea → Claude Critic, 실데이터 → 로컬

# 로컬 모델 (Qwen3-4B, 4bit 양자화)
MODEL_ID = "Qwen/Qwen3-4B"
LOAD_IN_4BIT = True
DEVICE_MAP = "auto"

# 생성 파라미터
MAX_NEW_TOKENS = 2048
TEMPERATURE = 0.1
ENABLE_THINKING = False

# Claude API (Synthea Critic 전용)
CLAUDE_MODEL = "claude-sonnet-4-6"

# RAG
EMBED_MODEL_ID = "NeuML/pubmedbert-base-embeddings"
RAG_TOP_K = 5
CHROMA_COLLECTION = "pmc_medical"

# Reflexion
MAX_REFLEXION_LOOPS = 3
QUALITY_THRESHOLD = 0.8
