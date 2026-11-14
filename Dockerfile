# Multi-stage / lightweight Python container for BYOD Monitoring Platform
FROM python:3.11-slim

# Prevent Python from writing .pyc files & buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV API_HOST=0.0.0.0

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure start script has execution permissions
RUN chmod +x /app/start.sh

# Expose web port
EXPOSE 5000

# Run both the Anomaly Watcher and the Flask API
CMD ["/app/start.sh"]
