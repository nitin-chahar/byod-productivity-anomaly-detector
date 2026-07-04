from flask import Flask, request, jsonify
from logging_handler import log_visit
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows frontend (HTML, JS) to interact with backend

@app.route("/", methods=["GET"])
def home():
    """Test route to check if server is running."""
    return jsonify({"message": "Server is running!"})

@app.route("/log-visit", methods=["POST"])
def log_user_visit():
    """Receives form data and logs the URL visit using existing ML pipeline."""
    data = request.get_json()

    user_id = data.get("user_id")
    url = data.get("url")
    time_spent = data.get("time_spent")
    email = data.get("email")

    if not all([user_id, url, time_spent, email]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        log_visit(int(user_id), url, int(time_spent), email)  # Ensure correct data types
        return jsonify({"message": "Visit logged successfully!"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
