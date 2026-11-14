"""
Flask REST API Server for BYOD Productivity Logger.
Provides endpoints for client applications and browser extensions to log student
browsing activity and trigger real-time ML classification.
"""

import logging
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    from backend.config import API_DEBUG, API_HOST, API_PORT, FRONTEND_DIR
    from backend.logging_handler import log_visit
except ImportError:
    from config import API_DEBUG, API_HOST, API_PORT, FRONTEND_DIR
    from logging_handler import log_visit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"
)
logger = logging.getLogger("BYOD.Server")

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
# Enable CORS for all routes (allows frontend browser dashboard or extensions to interact with API)
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
    return jsonify({
        "status": "online",
        "service": "BYOD Productivity Logger API",
        "version": "1.0.0"
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
                "excess_time": record["excess_time"]
            }
        }), 200

    except Exception as e:
        logger.exception("Error processing visit log request:")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(f" 🚀 BYOD API Server starting at http://{API_HOST}:{API_PORT}")
    print("=" * 60 + "\n")
    app.run(host=API_HOST, port=API_PORT, debug=API_DEBUG)
