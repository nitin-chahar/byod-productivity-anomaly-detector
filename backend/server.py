"""
Flask REST API Server for BYOD Productivity Logger.
Provides endpoints for client applications, browser dashboards, and extensions to:
- Log student browsing activity and trigger real-time ML classification
- Query live metrics and activity logs
- Inspect real-time anomaly detection outputs
- Test SMTP email alerting connectivity
- Trigger automated simulation batches
"""

import csv
import logging
import os
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    from backend.config import (
        API_DEBUG,
        API_HOST,
        API_PORT,
        ALERT_THRESHOLD,
        FRONTEND_DIR,
        STUDENT_ACTIVITY_LOG,
        REAL_TIME_ANOMALIES_LOG,
        SENDER_EMAIL,
        SENDER_PASSWORD,
    )
    from backend.logging_handler import log_visit
    from backend.send_alert import test_smtp_connection
except ImportError:
    from config import (
        API_DEBUG,
        API_HOST,
        API_PORT,
        ALERT_THRESHOLD,
        FRONTEND_DIR,
        STUDENT_ACTIVITY_LOG,
        REAL_TIME_ANOMALIES_LOG,
        SENDER_EMAIL,
        SENDER_PASSWORD,
    )
    from logging_handler import log_visit
    from send_alert import test_smtp_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"
)
logger = logging.getLogger("BYOD.Server")

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})


@app.route("/", methods=["GET"])
def index():
    """Serves the web dashboard user interface."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return send_from_directory(str(FRONTEND_DIR), "index.html")
    return jsonify({
        "status": "online",
        "service": "BYOD Productivity Logger API",
        "version": "1.0.0"
    }), 200


@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check route returning system status."""
    active_sender = os.environ.get("SMTP_SENDER_EMAIL", SENDER_EMAIL or "")
    active_pwd = os.environ.get("SMTP_APP_PASSWORD", SENDER_PASSWORD or "")
    smtp_ready = bool(active_sender and active_pwd)

    return jsonify({
        "status": "online",
        "service": "BYOD Sentinel Productivity API",
        "version": "1.0.0",
        "smtp_configured": smtp_ready,
        "sender_email": active_sender if smtp_ready else None,
        "alert_threshold_seconds": ALERT_THRESHOLD
    }), 200


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Calculates summary statistics from activity logs."""
    total = 0
    productive = 0
    non_productive = 0
    alerts = 0

    if os.path.exists(STUDENT_ACTIVITY_LOG):
        try:
            with open(STUDENT_ACTIVITY_LOG, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total += 1
                    cat = row.get("Category", "").strip()
                    alt = row.get("Alert", "").strip().upper()
                    if cat == "Productive":
                        productive += 1
                    elif cat == "Non-Productive":
                        non_productive += 1
                    if alt == "YES":
                        alerts += 1
        except Exception as e:
            logger.error(f"Error reading activity log: {e}")

    active_sender = os.environ.get("SMTP_SENDER_EMAIL", SENDER_EMAIL or "")
    active_pwd = os.environ.get("SMTP_APP_PASSWORD", SENDER_PASSWORD or "")

    return jsonify({
        "total_visits": total,
        "productive_count": productive,
        "non_productive_count": non_productive,
        "alerts_triggered": alerts,
        "alert_threshold": ALERT_THRESHOLD,
        "smtp_configured": bool(active_sender and active_pwd),
        "sender_email": active_sender or "Not configured"
    }), 200


@app.route("/api/logs", methods=["GET"])
def get_recent_logs():
    """Returns the most recent activity logs."""
    limit = int(request.args.get("limit", 25))
    logs = []

    if os.path.exists(STUDENT_ACTIVITY_LOG):
        try:
            with open(STUDENT_ACTIVITY_LOG, mode="r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                # Return most recent rows first
                for row in reversed(reader[-limit:]):
                    logs.append({
                        "user_id": row.get("User_Id"),
                        "timestamp": row.get("Timestamp(Start)"),
                        "url": row.get("URL"),
                        "category": row.get("Category"),
                        "time_spent": row.get("TimeSpent(s)"),
                        "alert": row.get("Alert"),
                        "excess_time": row.get("ExcessTime(s)"),
                        "email": row.get("E-mail")
                    })
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")

    return jsonify({"count": len(logs), "logs": logs}), 200


@app.route("/api/anomalies", methods=["GET"])
def get_anomalies():
    """Returns the latest anomaly detection calculations."""
    anomalies = []
    if os.path.exists(REAL_TIME_ANOMALIES_LOG):
        try:
            with open(REAL_TIME_ANOMALIES_LOG, mode="r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                anomalies = reader[-20:]
        except Exception as e:
            logger.error(f"Error reading anomalies: {e}")

    return jsonify({"count": len(anomalies), "anomalies": anomalies}), 200


@app.route("/api/clear-logs", methods=["POST"])
def clear_activity_logs():
    """Resets activity logs and anomalies to empty state."""
    try:
        from backend.logging_handler import log_lock
    except ImportError:
        from logging_handler import log_lock

    with log_lock:
        try:
            with open(STUDENT_ACTIVITY_LOG, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "User_Id", "Timestamp(Start)", "URL", "Category",
                    "TimeSpent(s)", "Alert", "TimeStamp(End)", "ExcessTime(s)", "E-mail"
                ])

            if os.path.exists(REAL_TIME_ANOMALIES_LOG):
                with open(REAL_TIME_ANOMALIES_LOG, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "User_Id", "Total_Websites", "Productive_Count", "Non_Productive_Count",
                        "Session_Duration", "E_mail", "Switches", "Anomaly_Score",
                        "Anomaly", "Z_Score", "Z_Anomaly", "Total_Alerts"
                    ])

            return jsonify({"message": "All activity logs cleared successfully"}), 200
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            return jsonify({"error": f"Failed to clear logs: {e}"}), 500


@app.route("/api/test-email", methods=["POST"])
def trigger_test_email():
    """Sends a test email via SMTP to verify credentials and delivery."""
    data = request.get_json(silent=True) or {}
    recipient = data.get("email")

    success, message = test_smtp_connection(test_recipient=recipient)
    return jsonify({
        "success": success,
        "message": message
    }), 200 if success else 400


@app.route("/api/simulate", methods=["POST"])
def trigger_simulation():
    """Executes a quick batch simulation of sample student activity."""
    try:
        from data.sample.sample_urls import SAMPLE_BROWSING_ACTIVITY
    except ImportError:
        SAMPLE_BROWSING_ACTIVITY = [
            (101, "https://www.github.com", 400, "dev@school.edu"),
            (102, "https://www.instagram.com", 600, "student@school.edu"),
            (103, "https://www.youtube.com/wwe", 450, "student@school.edu")
        ]

    batch = SAMPLE_BROWSING_ACTIVITY[:3]
    results = []
    for uid, url, time_s, em in batch:
        res = log_visit(uid, url, time_s, em)
        results.append(res)

    return jsonify({
        "message": f"Successfully simulated {len(results)} browsing visits!",
        "records": results
    }), 200


@app.route("/log-visit", methods=["POST"])
def log_user_visit():
    """
    Receives browsing session payload from frontend/client, classifies the URL,
    and logs the activity to CSV with alert thresholds.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    data = request.get_json()

    user_id = data.get("user_id")
    url = data.get("url")
    time_spent = data.get("time_spent")
    email = data.get("email")

    # Validate required parameters
    missing_fields = []
    for field_name, val in [("user_id", user_id), ("url", url), ("time_spent", time_spent), ("email", email)]:
        if val is None or str(val).strip() == "":
            missing_fields.append(field_name)

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing_fields
        }), 400

    try:
        user_id_int = int(user_id)
        time_spent_int = int(time_spent)
    except (ValueError, TypeError):
        return jsonify({"error": "user_id and time_spent must be valid integers"}), 400

    try:
        record = log_visit(
            user_id=user_id_int,
            url=str(url).strip(),
            time_spent=time_spent_int,
            email=str(email).strip()
        )

        return jsonify({
            "message": "Visit logged successfully!",
            "data": {
                "user_id": record["user_id"],
                "url": record["url"],
                "category": record["category"],
                "time_spent": record["time_spent"],
                "alert": record["alert_status"],
                "excess_time": record["excess_time"],
                "email": record["email"]
            }
        }), 200

    except Exception as e:
        logger.exception("Error processing visit log request:")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(f" 🚀 BYOD Sentinel Server starting at http://{API_HOST}:{API_PORT}")
    print("=" * 60 + "\n")
    app.run(host=API_HOST, port=API_PORT, debug=API_DEBUG)
