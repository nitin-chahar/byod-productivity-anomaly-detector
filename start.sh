#!/bin/sh
set -e

echo "Starting BYOD Anomaly Watcher in background..."
python backend/anomaly.py &

echo "Starting BYOD Gunicorn Web Server on port ${PORT:-5000}..."
exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 backend.server:app
