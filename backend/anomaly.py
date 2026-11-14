"""
Real-time Anomaly Detection Service for BYOD Productivity Monitoring.
Uses Watchdog to observe student activity logs reactively, aggregates browsing
metrics, and executes dual-engine anomaly detection:
1. Multi-variable Unsupervised Anomaly Detection (Isolation Forest)
2. Task-switching Frequency Outlier Detection (Statistical Z-Score)
"""

import logging
import os
import time
from typing import Optional
import numpy as np
import pandas as pd
from scipy.stats import zscore
from sklearn.ensemble import IsolationForest
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

try:
    from backend.config import (
        STUDENT_ACTIVITY_LOG,
        REAL_TIME_ANOMALIES_LOG,
        ANOMALY_AUDIT_LOG,
        ISOLATION_FOREST_CONTAMINATION,
        Z_SCORE_THRESHOLD,
    )
    from backend.send_alert import send_anomaly_alerts
except ImportError:
    from config import (
        STUDENT_ACTIVITY_LOG,
        REAL_TIME_ANOMALIES_LOG,
        ANOMALY_AUDIT_LOG,
        ISOLATION_FOREST_CONTAMINATION,
        Z_SCORE_THRESHOLD,
    )
    from send_alert import send_anomaly_alerts

logger = logging.getLogger("BYOD.AnomalyDetection")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Global tracker for detecting newly emerging anomalies
prev_data: Optional[pd.DataFrame] = None


def aggregate_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates student browsing logs per User_Id to extract behavioral features:
    total websites visited, productive count, non-productive count,
    total session duration, and frequency of category switches.
    """
    if df.empty or "User_Id" not in df.columns:
        return pd.DataFrame()

    aggregated = df.groupby("User_Id").agg(
        Total_Websites=("URL", "count"),
        Productive_Count=("Category", lambda x: (x == "Productive").sum()),
        Non_Productive_Count=("Category", lambda x: (x == "Non-Productive").sum()),
        Session_Duration=("TimeSpent(s)", "sum"),
        E_mail=("E-mail", "first")
    ).reset_index()

    # Calculate category switches (consecutive shifts in browsing category per user)
    df_sorted = df.copy()
    df_sorted["Prev_Category"] = df_sorted.groupby("User_Id")["Category"].shift(1)
    df_sorted["Switches"] = (
        (df_sorted["Category"] != df_sorted["Prev_Category"]) &
        (df_sorted["Prev_Category"].notna())
    ).astype(int)

    switch_counts = df_sorted.groupby("User_Id")["Switches"].sum().reset_index()
    aggregated = aggregated.merge(switch_counts, on="User_Id", how="left")
    aggregated["Switches"] = aggregated["Switches"].fillna(0).astype(int)

    return aggregated


def detect_anomalies(aggregated_data: pd.DataFrame) -> pd.DataFrame:
    """
    Applies Isolation Forest to detect multi-variable session anomalies
    based on Total_Websites, Session_Duration, and Switches.
    """
    if aggregated_data.empty:
        return aggregated_data

    features = aggregated_data[["Total_Websites", "Session_Duration", "Switches"]]

    # Isolation Forest requires at least 1 sample, but works best with multiple samples
    try:
        model = IsolationForest(
            contamination=ISOLATION_FOREST_CONTAMINATION,
            random_state=42
        )
        scores = model.fit_predict(features)
        aggregated_data["Anomaly_Score"] = scores
        # Scikit-learn Isolation Forest returns -1 for anomalies, 1 for normal
        aggregated_data["Anomaly"] = [1 if s == -1 else 0 for s in scores]
    except Exception as e:
        logger.error(f"Error fitting Isolation Forest: {e}")
        aggregated_data["Anomaly_Score"] = 1
        aggregated_data["Anomaly"] = 0

    return aggregated_data


def calculate_z_scores(aggregated_data: pd.DataFrame, raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes statistical Z-scores on rapid category switching and computes
    total non-productive visits per user.
    """
    if aggregated_data.empty:
        return aggregated_data

    # Compute Z-score on task switches (fallback to 0 if standard deviation is 0)
    switches = aggregated_data["Switches"]
    if len(switches) > 1 and switches.std() > 0:
        aggregated_data["Z_Score"] = zscore(switches)
        # Handle possible NaN from zero variance
        aggregated_data["Z_Score"] = aggregated_data["Z_Score"].fillna(0.0)
    else:
        aggregated_data["Z_Score"] = 0.0

    aggregated_data["Z_Anomaly"] = (
        aggregated_data["Z_Score"] > Z_SCORE_THRESHOLD
    ).astype(int)

    # Total non-productive visits per user
    if "Category" in raw_df.columns:
        alerts = (
            raw_df[raw_df["Category"] == "Non-Productive"]
            .groupby("User_Id")
            .size()
            .reset_index(name="Total_Alerts")
        )
        aggregated_data = aggregated_data.merge(alerts, on="User_Id", how="left")
        aggregated_data["Total_Alerts"] = aggregated_data["Total_Alerts"].fillna(0).astype(int)
    else:
        aggregated_data["Total_Alerts"] = 0

    return aggregated_data


def process_anomalies(file_path: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Reads the updated activity log, aggregates session behavior, detects anomalies,
    saves the output to CSV, and triggers email notifications.
    """
    global prev_data

    target_file = str(file_path or STUDENT_ACTIVITY_LOG)
    if not os.path.exists(target_file):
        logger.warning(f"Activity log not found at {target_file}")
        return None

    try:
        df = pd.read_csv(target_file)
    except Exception as e:
        logger.error(f"Failed to read activity log from {target_file}: {e}")
        return None

    if df.empty:
        logger.info("Activity log is empty. No anomalies to calculate.")
        return None

    aggregated = aggregate_data(df)
    if aggregated.empty:
        return None

    aggregated = detect_anomalies(aggregated)
    aggregated = calculate_z_scores(aggregated, df)
    aggregated = aggregated.fillna(0)

    # Save to anomalies CSV
    os.makedirs(os.path.dirname(os.path.abspath(REAL_TIME_ANOMALIES_LOG)), exist_ok=True)
    aggregated.to_csv(REAL_TIME_ANOMALIES_LOG, index=False)
    logger.info(f"Anomaly detection output saved to {REAL_TIME_ANOMALIES_LOG}")

    # Dispatch alerts
    try:
        send_anomaly_alerts(str(REAL_TIME_ANOMALIES_LOG))
    except Exception as e:
        logger.error(f"Error dispatching anomaly alerts: {e}")

    # Audit newly emerging anomalies
    if prev_data is not None and not prev_data.empty:
        new_anomalies = aggregated[aggregated["Anomaly"] == 1]
        if not new_anomalies.empty and "User_Id" in prev_data.columns:
            merged = new_anomalies.merge(
                prev_data[["User_Id", "Anomaly"]],
                on="User_Id",
                suffixes=("_new", "_old"),
                how="left"
            )
            emerging = merged[merged["Anomaly_old"] != 1]
            if not emerging.empty:
                os.makedirs(os.path.dirname(os.path.abspath(ANOMALY_AUDIT_LOG)), exist_ok=True)
                with open(ANOMALY_AUDIT_LOG, "a", encoding="utf-8") as log_file:
                    emerging.to_csv(log_file, index=False, header=False)
                logger.info(f"Logged {len(emerging)} new emerging anomalies to {ANOMALY_AUDIT_LOG}")

    prev_data = aggregated.copy()
    return aggregated


class ActivityFileWatcher(FileSystemEventHandler):
    """Watches student_activity.csv for modifications and runs real-time processing."""

    def __init__(self, target_filename: str = "student_activity.csv"):
        super().__init__()
        self.target_filename = target_filename

    def on_modified(self, event):
        if event.src_path.endswith(self.target_filename):
            logger.info(f"Detected modification in {self.target_filename}. Re-evaluating anomalies...")
            process_anomalies(event.src_path)


def start_watcher():
    """Starts the real-time watchdog observer loop."""
    activity_file = str(STUDENT_ACTIVITY_LOG)
    watch_dir = os.path.dirname(os.path.abspath(activity_file))

    logger.info(f"Initializing baseline anomaly check on {activity_file}...")
    process_anomalies(activity_file)

    logger.info(f"Starting real-time file observer on directory: {watch_dir}")
    event_handler = ActivityFileWatcher()
    observer = Observer()
    observer.schedule(event_handler, path=watch_dir, recursive=False)
    observer.start()

    print("\n" + "=" * 60)
    print(" 🛡️  BYOD Anomaly Watcher Running (Ctrl+C to stop)")
    print(f" Watching: {activity_file}")
    print("=" * 60 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping anomaly watcher...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    start_watcher()
