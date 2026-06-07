from pathlib import Path

RAW_DATA_PATH = Path("data/raw/criteo-uplift.csv")

INTERIM_DIR = Path("data/interim")
PROCESSED_DIR = Path("data/processed")
REFERENCE_DIR = Path("data/reference")

FEATURE_COLS = [f"f{i}" for i in range(11)]
TREATMENT_COL = "treatment"

PRIMARY_TARGET_COL = "conversion"
FALLBACK_TARGET_COL = "visit"

RANDOM_STATE = 42