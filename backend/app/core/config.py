"""Project configuration and environment-driven settings."""

from pathlib import Path
import os
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(PROJECT_ROOT / "data" / "raw")))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", str(PROJECT_ROOT / "data" / "processed")))
APP_DATA_DIR = Path(os.getenv("APP_DATA_DIR", str(PROJECT_ROOT / "data" / "app")))
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(PROJECT_ROOT / "models")))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", str(PROJECT_ROOT / "reports")))
FIGURES_DIR = REPORTS_DIR / "figures"
METRICS_DIR = REPORTS_DIR / "metrics"

MASTER_BEHAVIORAL_PATH = RAW_DATA_DIR / "master_behavioral_matrix.parquet"
FEATURE_MATRIX_V1_PATH = RAW_DATA_DIR / "feature_matrix_v1.parquet"

MODEL_BUNDLE_PATH = Path(
    os.getenv("MODEL_BUNDLE_PATH", str(MODELS_DIR / "isolation_forest_v1.joblib"))
)
VALIDATION_SCORE_REF_PATH = Path(
    os.getenv("VALIDATION_SCORE_REF_PATH", str(MODELS_DIR / "validation_score_reference.npy"))
)
DATABASE_PATH = Path(
    os.getenv("INSIDER_THREAT_DB_PATH", str(APP_DATA_DIR / "insider_threat.db"))
)

DEFAULT_CORS_ORIGINS = "http://localhost:5173"
CORS_ORIGINS: List[str] = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

# Phase 6 Session & Security Configuration
SESSION_COOKIE_NAME = "isd_session"
CSRF_COOKIE_NAME = "isd_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "12"))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() == "true"
SESSION_COOKIE_SAMESITE = "lax"
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_SEC = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SEC", "60"))

RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
MODEL_VERSION = "isolation_forest_v1"
