"""
Automated Email Alert Dispatcher for BYOD Anomaly Detection System.
Dispatches TLS-encrypted SMTP notifications to users or administrators
for both:
1. Instant Threshold Violations (exceeding time limits on non-productive sites)
2. Behavioral Session Anomalies (detected by Isolation Forest and Z-Score analysis)
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
    """Retrieves the latest SMTP credentials from environment or config."""
    server = os.environ.get("SMTP_SERVER", SMTP_SERVER or "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", SMTP_PORT or 587))
    sender = os.environ.get("SMTP_SENDER_EMAIL", SENDER_EMAIL or "").strip()
    password = os.environ.get("SMTP_APP_PASSWORD", SENDER_PASSWORD or "").strip()
    return server, port, sender, password


def test_smtp_connection(test_recipient: Optional[str] = None) -> Tuple[bool, str]:
    """
    Tests SMTP connection and authentication.
    Optionally sends a test verification email.
    Returns (success: bool, message: str).
    """
    server_host, port, sender, password = _get_active_credentials()

    if not sender or not password:
        return False, "SMTP credentials missing. Please set SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD in .env"

    recipient = test_recipient or sender

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = "✅ BYOD Sentinel: SMTP Email Dispatcher Verified"

        text_content = (
            "Hello,\n\n"
            "This is a test notification confirming that the BYOD Productivity "
            "and Anomaly Alert Dispatcher is successfully connected to your SMTP server.\n\n"
            "Alerts will be delivered automatically when students exceed policy thresholds."
        )

        html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 24px; margin: 0;">
  <div style="max-width: 560px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 28px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
    <div style="display: inline-block; background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px;">
      Connection Verified
    </div>
    <h2 style="margin: 0 0 12px 0; color: #ffffff; font-size: 22px;">SMTP Alert Dispatcher Online</h2>
    <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">
      Your BYOD monitoring system has successfully verified connection to <strong>{server_host}:{port}</strong>.
    </p>
    <div style="background: #0f172a; border-radius: 8px; padding: 16px; border: 1px solid #334155; margin-bottom: 20px;">
      <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">Configured Sender Account</div>
      <div style="font-size: 14px; font-weight: 600; color: #e2e8f0;">{sender}</div>
    </div>
    <p style="color: #64748b; font-size: 12px; margin: 0;">
      Generated automatically by BYOD Sentinel Monitoring Engine.
    </p>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(server_host, port, timeout=12) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())

        logger.info(f"Test email successfully delivered to {recipient}")
        return True, f"SMTP verified! Test alert sent to {recipient}"

    except smtplib.SMTPAuthenticationError as e:
        err = f"SMTP Authentication failed. If using Gmail, ensure you are using a 16-character App Password (not your personal password). Details: {e}"
        logger.error(err)
        return False, err
    except Exception as e:
        err = f"SMTP Connection error ({type(e).__name__}): {e}"
        logger.error(err)
        return False, err


def send_threshold_alert(
    recipient_email: str,
    user_id: int,
    url: str,
    category: str,
    time_spent: int,
    excess_time: any,
    threshold: int = 300,
) -> bool:
    """
    Sends an immediate email alert when a user exceeds the allowed time limit
    on a non-productive website.
    """
    server_host, port, sender, password = _get_active_credentials()

    if not sender or not password:
        logger.warning(
            "SMTP credentials not configured. Skipping threshold alert email. "
            "Set SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD in .env."
        )
        return False

    if not recipient_email or "@" not in str(recipient_email):
        recipient_email = sender

    subject = f"⚠️ BYOD Policy Alert: Non-Productive Limit Exceeded (User {user_id})"

    plain_body = f"""Dear User / Administrator,

A browsing policy violation has been detected for User {user_id}.

Violation Details:
- User ID: {user_id}
- Visited Website: {url}
- Category: {category}
- Monitored Duration: {time_spent} seconds
- Allowed Policy Limit: {threshold} seconds (5 minutes)
- Excess Time: +{excess_time} seconds

Please review this activity if unauthorized.

Regards,
BYOD Sentinel Security Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 24px; margin: 0;">
  <div style="max-width: 580px; margin: 0 auto; background: #131d31; border-radius: 14px; padding: 32px; border: 1px solid rgba(239, 68, 68, 0.3); box-shadow: 0 14px 35px rgba(0,0,0,0.4);">
    
    <div style="display: inline-block; background: rgba(239, 68, 68, 0.18); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); padding: 5px 14px; border-radius: 999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 18px;">
      Policy Threshold Violation
    </div>

    <h2 style="margin: 0 0 10px 0; color: #ffffff; font-size: 24px; font-weight: 700;">
      Non-Productive Usage Exceeded
    </h2>
    
    <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
      User <strong>#{user_id}</strong> has exceeded the permitted browsing threshold on a non-productive destination during active monitoring.
    </p>

    <!-- Details Table -->
    <div style="background: #0b1120; border-radius: 10px; border: 1px solid #1e293b; padding: 18px; margin-bottom: 24px;">
      <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <tr>
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Destination URL:</td>
          <td style="padding: 8px 0; color: #60a5fa; font-weight: 600; word-break: break-all;">{url}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Classification:</td>
          <td style="padding: 8px 0; color: #f43f5e; font-weight: 700;">{category}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Allowed Threshold:</td>
          <td style="padding: 8px 0; color: #cbd5e1; font-weight: 600;">{threshold}s (5 minutes)</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Duration Recorded:</td>
          <td style="padding: 8px 0; color: #cbd5e1; font-weight: 600;">{time_spent} seconds</td>
        </tr>
        <tr style="border-top: 1px solid #1e293b;">
          <td style="padding: 10px 0 2px 0; color: #f87171; font-weight: 600;">Excess Duration:</td>
          <td style="padding: 10px 0 2px 0; color: #f87171; font-weight: 700; font-size: 15px;">+{excess_time} seconds</td>
        </tr>
      </table>
    </div>

    <p style="color: #64748b; font-size: 12px; line-height: 1.5; margin: 0;">
      This automated alert was dispatched by the BYOD Sentinel Productivity Logger.
    </p>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(server_host, port, timeout=12) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient_email, msg.as_string())
            # If recipient is student, also notify sender admin
            if sender != recipient_email:
                try:
                    server.sendmail(sender, sender, msg.as_string())
                except Exception:
                    pass

        logger.info(f"✔ Threshold alert email sent to {recipient_email} for URL {url}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to dispatch threshold alert to {recipient_email}: {e}")
        return False


def dispatch_threshold_alert_async(
    recipient_email: str,
    user_id: int,
    url: str,
    category: str,
    time_spent: int,
    excess_time: any,
    threshold: int = 300,
):
    """Fires the threshold email alert in a background daemon thread to prevent API lag."""
    thread = threading.Thread(
        target=send_threshold_alert,
        args=(recipient_email, user_id, url, category, time_spent, excess_time, threshold),
        daemon=True
    )
    thread.start()


def send_email(recipient_email: str, user_id: int, session_duration: int) -> bool:
    """
    Sends an anomaly alert email to a user via SMTP TLS (multi-variable anomaly).
    """
    server_host, port, sender, password = _get_active_credentials()

    if not sender or not password:
        logger.warning(
            "SMTP credentials not configured. Skipping email dispatch. "
            "Configure SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD in .env."
        )
        return False

    subject = f"⚠️ Alert: Unusual Browsing Pattern Detected (User {user_id})"
    body = f"""Dear User {user_id},

Our automated monitoring system has detected unusual browsing patterns during your active session.

Session Details:
- User ID: {user_id}
- Total Monitored Duration: {session_duration} seconds
- Flagged by: Behavioral multi-variable analysis (Isolation Forest / Outlier frequency).

If this activity was not authorized by you, please notify institutional security immediately.

Regards,
BYOD Sentinel Security Team
"""

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(server_host, port, timeout=12) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient_email, msg.as_string())
        logger.info(f"✔ Behavioral anomaly alert email dispatched to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to dispatch behavioral email to {recipient_email}: {e}")
        return False


def send_anomaly_alerts(csv_path: Optional[str] = None) -> int:
    """
    Reads detected anomalies from CSV and dispatches email alerts for flagged sessions.
    """
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

    # Flag users if Isolation Forest detected Anomaly==1 OR Z_Anomaly==1 OR Total_Alerts >= 2
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
    test_smtp_connection()
