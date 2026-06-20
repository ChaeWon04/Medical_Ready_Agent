from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PMC_DIR = DATA_DIR / "pmc"
OUTPUT_DIR = DATA_DIR / "output"
CHROMA_DIR = BASE_DIR / "rag" / "chroma_db"

for d in [RAW_DIR, PMC_DIR, OUTPUT_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Model
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
