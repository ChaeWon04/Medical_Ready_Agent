from pathlib import Path
import os

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PMC_DIR = DATA_DIR / "pmc"
OUTPUT_DIR = DATA_DIR / "output"
CHROMA_DIR = BASE_DIR / "rag" / "chroma_db"

# Synthea CSV 경로 (juyoung 브랜치 호환)
SYNTHEA_CSV_DIR = DATA_DIR / "synthea" / "synthea_sample_data_csv_latest"

for d in [RAW_DIR, PMC_DIR, OUTPUT_DIR, CHROMA_DIR, SYNTHEA_CSV_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Data source: "synthea" | "mimic_iv" | "eicu"
DATA_SOURCE = "synthea"

USE_CLAUDE_API = False
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# vLLM 서버 주소 (A팀 설정 후 채워넣기)
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")

# Local Model
MODEL_ID = "Qwen/Qwen3-4B"
LOAD_IN_4BIT = True
DEVICE_MAP = "auto"

# Generation
MAX_NEW_TOKENS = 2048
TEMPERATURE = 0.1
ENABLE_THINKING = False  # non-thinking 모드 고정

# RAG
EMBED_MODEL_ID = "NeuML/pubmedbert-base-embeddings"
RAG_TOP_K = 5
CHROMA_COLLECTION = "pmc_medical"

# Reflexion
MAX_REFLEXION_LOOPS = 3
QUALITY_THRESHOLD = 0.8
