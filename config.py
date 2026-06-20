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

# Synthea는 합성 데이터 → Claude API 사용 가능
# MIMIC-IV / eICU는 PhysioNet DUA → 로컬 모델만
USE_CLAUDE_API = os.getenv("ANTHROPIC_API_KEY") is not None and DATA_SOURCE == "synthea"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Local Model (MIMIC-IV / eICU용)
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
