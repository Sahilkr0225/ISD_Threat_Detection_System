"""Project configuration and path settings."""

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(PROJECT_ROOT / "data" / "raw")))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", str(PROJECT_ROOT / "data" / "processed")))
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(PROJECT_ROOT / "models")))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", str(PROJECT_ROOT / "reports")))
FIGURES_DIR = REPORTS_DIR / "figures"
METRICS_DIR = REPORTS_DIR / "metrics"

MASTER_BEHAVIORAL_PATH = RAW_DATA_DIR / "master_behavioral_matrix.parquet"
FEATURE_MATRIX_V1_PATH = RAW_DATA_DIR / "feature_matrix_v1.parquet"

RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

