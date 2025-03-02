import schedule
import time
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.dapps_tracker_service import DappActivityTracker

def run_tracker():
    print("[INFO] Running DappActivityTracker...")
    tracker = DappActivityTracker()
    tracker.run()
    print("[INFO] DappActivityTracker execution completed.")

# Schedule to run daily at 23:59
schedule.every().day.at("23:59").do(run_tracker)

if __name__ == "__main__":
    print("[INFO] DappActivityTracker scheduled to run daily at 23:59")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute to run the task