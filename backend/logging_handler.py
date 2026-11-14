"""
Thread-safe student activity logging and web content classification module.
Classifies browsing visits using pre-trained LinearSVC NLP pipeline and logs
activity records with alert evaluation to CSV.
"""

import csv
import logging
import os
import pickle
import threading
from datetime import datetime, timedelta
from typing import Optional

try:
    from backend.config import (
        MODEL_PATH,
        STUDENT_ACTIVITY_LOG,
        ALERT_THRESHOLD,
        PRODUCTIVE_CATEGORIES,
    )
    from backend.utils import extract_meta_data, extract_text_from_url
except ImportError:
    from config import (
        MODEL_PATH,
        STUDENT_ACTIVITY_LOG,
        ALERT_THRESHOLD,
        PRODUCTIVE_CATEGORIES,
    )
    from utils import extract_meta_data, extract_text_from_url

# Configure logger
logger = logging.getLogger("BYOD.LoggingHandler")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Global thread lock for synchronized file writes
log_lock = threading.Lock()

# Load Serialized Model
loaded_model = None
try:
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as model_file:
            loaded_model = pickle.load(model_file)
        logger.info(f"Loaded classification model from {MODEL_PATH}")
    else:
        logger.warning(f"Model file not found at {MODEL_PATH}. Fallback heuristic will be used.")
except Exception as e:
    logger.warning(f"Could not load ML model from {MODEL_PATH}: {e}. Fallback heuristic will be used.")


# Fallback keyword lists for resilient classification if model is unavailable
PRODUCTIVE_KEYWORDS = {
    "edu", "github", "stackoverflow", "geeksforgeeks", "leetcode", "coursera",
    "wikipedia", "docs", "learn", "study", "research", "portal", "lpu", "ums",
    "kaggle", "arxiv", "medium", "sciencedirect", "nih", "ieee"
}


def heuristic_classify(url: str, text: str) -> str:
    """Heuristic rule-based fallback classification if model is unavailable."""
    combined = (url + " " + text).lower()
    for kw in PRODUCTIVE_KEYWORDS:
        if kw in combined:
            return "Productive"
    return "Non-Productive"


def classify_url(url: str) -> str:
    """
    Classifies a website URL as 'Productive' or 'Non-Productive'.
    Scrapes live meta content, with fallback to URL lexical tokens.
    Uses LinearSVC model if loaded, else applies heuristic classification.
    """
    meta_data = extract_meta_data(url)
    text_for_classification = meta_data if meta_data else extract_text_from_url(url)

    if not text_for_classification.strip():
        text_for_classification = extract_text_from_url(url)

    if loaded_model is not None:
        try:
            prediction = loaded_model.predict([text_for_classification])[0]
            return "Productive" if prediction in PRODUCTIVE_CATEGORIES else "Non-Productive"
        except Exception as e:
            logger.debug(f"Model prediction failed for '{url}': {e}. Using heuristic.")

    return heuristic_classify(url, text_for_classification)


def initialize_log_file() -> None:
    """Ensures the activity log directory and CSV file with headers exist."""
    log_dir = os.path.dirname(os.path.abspath(STUDENT_ACTIVITY_LOG))
    os.makedirs(log_dir, exist_ok=True)

    if not os.path.exists(STUDENT_ACTIVITY_LOG):
        with open(STUDENT_ACTIVITY_LOG, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "User_Id",
                "Timestamp(Start)",
                "URL",
                "Category",
                "TimeSpent(s)",
                "Alert",
                "TimeStamp(End)",
                "ExcessTime(s)",
                "E-mail"
            ])
        logger.info(f"Initialized activity log file at {STUDENT_ACTIVITY_LOG}")


def log_visit(user_id: int, url: str, time_spent: int, email: str) -> dict:
    """
    Logs a single URL visit with productivity category, alert calculation,
    and thread-safe writing to the CSV activity log.
    """
    initialize_log_file()

    category = classify_url(url)
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=time_spent)

    is_alert = (category == "Non-Productive" and time_spent > ALERT_THRESHOLD)
    alert_status = "YES" if is_alert else "NO"
    excess_time = (time_spent - ALERT_THRESHOLD) if is_alert else "N/A"

    record = {
        "user_id": user_id,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "url": url,
        "category": category,
        "time_spent": time_spent,
        "alert_status": alert_status,
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "excess_time": excess_time,
        "email": email
    }

    with log_lock:
        with open(STUDENT_ACTIVITY_LOG, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                record["user_id"],
                record["start_time"],
                record["url"],
                record["category"],
                record["time_spent"],
                record["alert_status"],
                record["end_time"],
                record["excess_time"],
                record["email"]
            ])

    if is_alert:
        logger.warning(
            f"ALERT TRIGGERED: User {user_id} spent {time_spent}s on {url} "
            f"({category}), exceeding limit by {excess_time}s!"
        )
    else:
        logger.info(f"Visit logged: User {user_id} -> {url} [{category}, {time_spent}s]")

    return record


# Initialize on import
initialize_log_file()

if __name__ == "__main__":
    print("Testing logging_handler...")
    test_record = log_visit(101, "https://www.youtube.com/wwe", 450, "test@example.com")
    print("Logged record:", test_record)
