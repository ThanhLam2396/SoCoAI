import sys
import os
import time
import logging
import schedule

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.twitter_comment_service import AutoCommentService
from src.utils.config_loader import CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AutoCommentJob:
    """Service to check Twitter posts and automatically comment on a schedule"""

    def __init__(self):
        self.auto_comment_service = AutoCommentService()
        self.fetch_interval = CONFIG.get("AUTO_COMMENT_INTERVAL", 300)  # Default is 300 seconds (5 minutes)

    def run(self):
        """Run the Twitter posts check every 5 minutes"""
        logging.info("🔄 Starting Auto Comment Service...")
        schedule.every(5).minutes.do(self.process_posts)  # Check every 5 minutes

        while True:
            schedule.run_pending()
            time.sleep(30)  # Wait 30 seconds before checking again to avoid busy-wait loop

    def process_posts(self):
        """Call the posts processing function to automatically comment"""
        try:
            logging.info("🔄 Checking for new Twitter posts...")
            self.auto_comment_service.process_users()
            logging.info("✅ Auto comments processed successfully.")
        except Exception as e:
            logging.error(f"[❌] Error in AutoCommentJob: {e}")

if __name__ == "__main__":
    service = AutoCommentJob()
    service.run()