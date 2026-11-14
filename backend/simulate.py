"""
Batch Activity Simulation Utility for BYOD Productivity Monitoring.
Simulates real-world student browsing activity by replaying sample sessions
through the classification and logging pipeline.
"""

import sys
import time
from pathlib import Path

# Add project root and backend directory to path if run standalone
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from backend.logging_handler import log_visit
    from backend.config import STUDENT_ACTIVITY_LOG
except ImportError:
    from logging_handler import log_visit
    from config import STUDENT_ACTIVITY_LOG

# Load sample activity data
try:
    from data.sample.sample_urls import SAMPLE_BROWSING_ACTIVITY
except ImportError:
    SAMPLE_BROWSING_ACTIVITY = [
        (101, "https://www.github.com", 400, "student101@university.edu"),
        (102, "https://www.instagram.com", 600, "student102@university.edu"),
        (102, "https://www.youtube.com/wwe", 350, "student102@university.edu"),
        (101, "https://www.youtube.com/freecodecamp", 800, "student101@university.edu"),
        (102, "https://www.youtube.com/@bbkivines", 1000, "student102@university.edu"),
        (101, "https://www.geeksforgeeks.org/", 350, "student101@university.edu"),
        (102, "https://ums.lpu.in", 200, "student102@university.edu"),
    ]


def run_simulation(delay: float = 1.5, max_records: int = None):
    """
    Executes batch simulation by passing each sample browsing visit to log_visit.
    """
    records = SAMPLE_BROWSING_ACTIVITY[:max_records] if max_records else SAMPLE_BROWSING_ACTIVITY

    print("\n" + "=" * 65)
    print(" 🧪 Starting BYOD Student Browsing Simulation")
    print(f" Processing {len(records)} visits (Delay between requests: {delay}s)")
    print(f" Output Activity Log: {STUDENT_ACTIVITY_LOG}")
    print("=" * 65 + "\n")

    for i, (user_id, url, time_spent, email) in enumerate(records, 1):
        print(f"[{i}/{len(records)}] Logging visit: User {user_id} -> {url} ({time_spent}s)")
        try:
            log_visit(user_id, url, time_spent, email)
        except Exception as e:
            print(f"  ❌ Error logging visit: {e}")

        if i < len(records):
            time.sleep(delay)

    print("\n" + "=" * 65)
    print(" ✔️  Simulation Completed! Check 'data/logs/student_activity.csv'")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    delay_sec = 1.0
    if len(sys.argv) > 1:
        try:
            delay_sec = float(sys.argv[1])
        except ValueError:
            pass
    run_simulation(delay=delay_sec)

