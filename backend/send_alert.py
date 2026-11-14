"""
Automated Email Alert Dispatcher for BYOD Anomaly Detection System.
Dispatches TLS/SSL encrypted SMTP notifications for threshold limits
and behavioral session anomalies.
"""

import logging
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple
import pandas as pd

try:
    from backend.config import (
        SMTP_SERVER,
        SMTP_PORT,
        SENDER_EMAIL,
        SENDER_PASSWORD,
        REAL_TIME_ANOMALIES_LOG,
        ALERT_THRESHOLD,
    )
except ImportError:
    from config import (
        SMTP_SERVER,
        SMTP_PORT,
        SENDER_EMAIL,
        SENDER_PASSWORD,
        REAL_TIME_ANOMALIES_LOG,
        ALERT_THRESHOLD,
    )

logger = logging.getLogger("BYOD.SendAlert")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _get_active_credentials() -> Tuple[str, int, str, str]:
    """Retrieves credentials from environment, normalizing spaces and ports."""
    server = os.environ.get("SMTP_SERVER", SMTP_SERVER or "smtp.gmail.com").strip()
    try:
        port = int(os.environ.get("SMTP_PORT", SMTP_PORT or 587))
    except (ValueError, TypeError):
        port = 587
    sender = os.environ.get("SMTP_SENDER_EMAIL", SENDER_EMAIL or "").strip()
    # Normalize Google App Passwords by removing all whitespace
    password = os.environ.get("SMTP_APP_PASSWORD", SENDER_PASSWORD or "").strip().replace(" ", "")
    return server, port, sender, password


def _dispatch_smtp(server_host: str, port: int, sender: str, password: str, recipient: str, msg_str: str) -> Tuple[bool, str]:
    """Sends email with automatic fallback between STARTTLS (587) and SSL (465)."""
    try:
        if port == 465:
            with smtplib.SMTP_SSL(server_host, port, timeout=10) as s:
                s.login(sender, password)
                s.sendmail(sender, recipient, msg_str)
            return True, "Delivered via SSL"
        else:
            with smtplib.SMTP(server_host, port, timeout=10) as s:
                s.starttls()
                s.login(sender, password)
                s.sendmail(sender, recipient, msg_str)
            return True, "Delivered via STARTTLS"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Authentication failed: Check email and 16-character App Password ({e})"
    except Exception as primary_err:
        # Fallback to alternate port
        alt_port = 465 if port != 465 else 587
        try:
            if alt_port == 465:
                with smtplib.SMTP_SSL(server_host, 465, timeout=10) as s:
                    s.login(sender, password)
                    s.sendmail(sender, recipient, msg_str)
                return True, "Delivered via fallback SSL"
            else:
                with smtplib.SMTP(server_host, 587, timeout=10) as s:
                    s.starttls()
                    s.login(sender, password)
                    s.sendmail(sender, recipient, msg_str)
                return True, "Delivered via fallback TLS"
        except Exception:
            return False, f"SMTP Connection error: {primary_err}"


def test_smtp_connection(test_recipient: Optional[str] = None) -> Tuple[bool, str]:
    """Tests SMTP connection and authentication with a verification email."""
    server_host, port, sender, password = _get_active_credentials()

    if not sender or not password:
        return False, "SMTP credentials missing. Set SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD."

    recipient = test_recipient or sender

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = "BYOD Sentinel: SMTP Verification"

    body = f"SMTP configuration test connection successful to {server_host}:{port}."
    msg.attach(MIMEText(body, "plain"))

    success, message = _dispatch_smtp(server_host, port, sender, password, recipient, msg.as_string())
    return success, message


def send_threshold_alert(
    recipient_email: str,
    user_id: int,
    url: str,
    category: str,
    time_spent: int,
    excess_time: any,
    threshold: int = 300,
) -> Tuple[bool, str]:
    """Sends notification when non-productive time limit is exceeded."""
    server_host, port, sender, password = _get_active_credentials()

    if not sender or not password:
        return False, "SMTP not configured"

    target_recipient = recipient_email if (recipient_email and "@" in recipient_email) else sender

    subject = f"Alert: Non-Productive Limit Exceeded (User {user_id})"
    plain_body = (
        f"User {user_id} exceeded allowed duration on {url} ({category}).\n"
        f"Time spent: {time_spent}s (Limit: {threshold}s, Excess: +{excess_time}s)."
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = target_recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(plain_body, "plain"))

    success, message = _dispatch_smtp(server_host, port, sender, password, target_recipient, msg.as_string())
    if success and sender != target_recipient:
        try:
            _dispatch_smtp(server_host, port, sender, password, sender, msg.as_string())
        except Exception:
            pass

    return success, message


def dispatch_threshold_alert_async(
    recipient_email: str,
    user_id: int,
    url: str,
    category: str,
    time_spent: int,
    excess_time: any,
    threshold: int = 300,
):
    """Fires threshold alert in background daemon thread."""
    thread = threading.Thread(
        target=send_threshold_alert,
        args=(recipient_email, user_id, url, category, time_spent, excess_time, threshold),
        daemon=True
    )
    thread.start()


def send_email(recipient_email: str, user_id: int, session_duration: int) -> bool:
    """Sends behavioral anomaly notification to user."""
    server_host, port, sender, password = _get_active_credentials()
    if not sender or not password:
        return False

    subject = f"Alert: Unusual Browsing Activity (User {user_id})"
    body = f"User {user_id} flagged for anomalous session pattern. Duration: {session_duration}s."

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    success, _ = _dispatch_smtp(server_host, port, sender, password, recipient_email, msg.as_string())
    return success


def send_anomaly_alerts(csv_path: Optional[str] = None) -> int:
    """Processes anomalies file and dispatches notifications for flagged sessions."""
    target_csv = str(csv_path or REAL_TIME_ANOMALIES_LOG)
    if not os.path.exists(target_csv):
        return 0

    try:
        anomalies_df = pd.read_csv(target_csv)
    except Exception as e:
        logger.error(f"Failed to read anomalies file {target_csv}: {e}")
        return 0

    if anomalies_df.empty:
        return 0

    condition = False
    if "Anomaly" in anomalies_df.columns:
        condition = (anomalies_df["Anomaly"] == 1)
    if "Z_Anomaly" in anomalies_df.columns:
        condition = condition | (anomalies_df["Z_Anomaly"] == 1)

    anomalous_users = anomalies_df[condition] if isinstance(condition, pd.Series) else pd.DataFrame()
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
    success, msg = test_smtp_connection()
    print("Test result:", success, msg)
