"""
Centralized Configuration Module for BYOD Productivity Logger & Anomaly Detection.
Manages file paths, detection thresholds, server settings, and email configurations.
"""

import os
from pathlib import Path

# Try to import dotenv for loading .env file, fall back gracefully if not installed
try:
    from dotenv import load_dotenv
    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

# Base directory definitions
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

# Load .env file from root directory if dotenv is available
if _HAS_DOTENV:
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
else:
    # Minimal fallback parser if dotenv is not yet installed
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val

# Directory layout
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
RAW_DATA_DIR = DATA_DIR / "raw"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
MODELS_DIR = ROOT_DIR / "models"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Ensure essential runtime directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Helper for backward-compatible path resolution
def _resolve_file(primary_path: Path, fallback_path: Path) -> Path:
    if primary_path.exists():
        return primary_path
    if fallback_path.exists():
        return fallback_path
    return primary_path

# Model and Data Paths
PRIMARY_MODEL_PATH = MODELS_DIR / "svm_stem(3,3).sav"
FALLBACK_MODEL_PATH = BACKEND_DIR / "svm_stem(3,3).sav"
MODEL_PATH = _resolve_file(PRIMARY_MODEL_PATH, FALLBACK_MODEL_PATH)

PRIMARY_ACTIVITY_LOG = LOGS_DIR / "student_activity.csv"
FALLBACK_ACTIVITY_LOG = BACKEND_DIR / "student_activity.csv"
STUDENT_ACTIVITY_LOG = _resolve_file(PRIMARY_ACTIVITY_LOG, FALLBACK_ACTIVITY_LOG)

REAL_TIME_ANOMALIES_LOG = LOGS_DIR / "real_time_anomalies.csv"
ANOMALY_AUDIT_LOG = LOGS_DIR / "anomaly_log.csv"
DATASET_PATH = RAW_DATA_DIR / "website_classification.csv"

# Monitoring & Classification Rules
ALERT_THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", 300))       # Exceeding 5 mins on non-productive
SWITCH_THRESHOLD = int(os.environ.get("SWITCH_THRESHOLD", 120))     # 2 mins threshold for category switch
PRODUCTIVE_CATEGORIES = {1, 2, 4, 9, 10}                            # Ed, Tech, Business, Reference, News

# Anomaly Detection Parameters
ISOLATION_FOREST_CONTAMINATION = float(os.environ.get("IF_CONTAMINATION", 0.05))
Z_SCORE_THRESHOLD = float(os.environ.get("Z_SCORE_THRESHOLD", 3.0))

# Flask API Configuration
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", 5000))
API_DEBUG = os.environ.get("API_DEBUG", "True").lower() in ("true", "1", "yes")

# SMTP Alert Configuration (Read securely from environment)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SENDER_EMAIL = os.environ.get("SMTP_SENDER_EMAIL", "")
SENDER_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "")

