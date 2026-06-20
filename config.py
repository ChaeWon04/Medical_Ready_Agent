from pathlib import Path

BASE_DIR = Path(__file__).parent

# "synthea" | "mimic" | "eicu"
DATA_SOURCE = "synthea"
USE_CLAUDE_API = DATA_SOURCE == "synthea"

# Paths
DATA_DIR = BASE_DIR / "data"
SYNTHEA_CSV_DIR = DATA_DIR / "synthea" / "synthea_sample_data_csv_latest"
RAW_DIR = DATA_DIR / "raw"
PMC_DIR = DATA_DIR / "pmc"
OUTPUT_DIR = DATA_DIR / "output"
CHROMA_DIR = BASE_DIR / "chroma_db"

# Models
LOCAL_MODEL_NAME = "OpenMeditron/Meditron3-Qwen2.5-7B"
CLAUDE_MODEL = "claude-sonnet-4-6"

# RAG
EMBEDDING_MODEL = "pritamdeka/S-PubMedBert-MS-MARCO"
TOP_K = 3

# Reflexion
MAX_REFINE_ITERATIONS = 3
QUALITY_THRESHOLD = 0.8
