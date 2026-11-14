"""
Automated Email Alert Dispatcher for BYOD Anomaly Detection System.
Dispatches TLS-encrypted SMTP notifications to users or administrators
when behavioral anomalies are flagged.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import pandas as pd

try:
    from backend.config import (
        SMTP_SERVER,
        SMTP_PORT,
        SENDER_EMAIL,
        SENDER_PASSWORD,
        REAL_TIME_ANOMALIES_LOG,
    )
except ImportError:
    from config import (
        SMTP_SERVER,
        SMTP_PORT,
        SENDER_EMAIL,
        SENDER_PASSWORD,
        REAL_TIME_ANOMALIES_LOG,
    )

logger = logging.getLogger("BYOD.SendAlert")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def send_email(recipient_email: str, user_id: int, session_duration: int) -> bool:
    """
    Sends an anomaly alert email to a user via SMTP TLS.
    Returns True if sent successfully, False otherwise.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        logger.warning(
            "SMTP credentials not configured. Skipping email dispatch. "
            "To enable email alerts, configure SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD in your .env file."
        )
        return False

    subject = f"⚠️ Alert: Unusual Activity Detected (User {user_id})"
    body = f"""Dear User {user_id},

Our automated monitoring system has detected unusual browsing patterns during your active session.

Session Details:
- User ID: {user_id}
- Total Monitored Duration: {session_duration} seconds
- Classification: Flagged anomalous based on behavioral multi-variable analysis (Isolation Forest / Outlier frequency).

If this session was not authorized by you, please notify institutional security immediately.

Regards,
BYOD Security & Monitoring Team
"""

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        logger.info(f"✔ Alert email dispatched successfully to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to dispatch email to {recipient_email}: {e}")
        return False


def send_anomaly_alerts(csv_path: Optional[str] = None) -> int:
    """
    Reads detected anomalies from CSV and dispatches email alerts for flagged sessions.
    Returns the count of dispatched emails.
    """
    target_csv = str(csv_path or REAL_TIME_ANOMALIES_LOG)
    if not os.path.exists(target_csv):
        logger.info(f"No anomaly log file found at {target_csv}. Nothing to alert.")
        return 0

    try:
        anomalies_df = pd.read_csv(target_csv)
    except Exception as e:
        logger.error(f"Failed to read anomalies file {target_csv}: {e}")
        return 0

    if anomalies_df.empty or "Anomaly" not in anomalies_df.columns:
        logger.info("No anomalies detected in the log file.")
        return 0

    anomalous_users = anomalies_df[anomalies_df["Anomaly"] == 1]
    dispatched_count = 0

    for _, row in anomalous_users.iterrows():
        email = row.get("E_mail")
        user_id = row.get("User_Id")
        duration = row.get("Session_Duration", 0)

        if pd.notna(email) and email:
            if send_email(str(email), user_id, int(duration)):
                dispatched_count += 1

    return dispatched_count


if __name__ == "__main__":
    send_anomaly_alerts()
