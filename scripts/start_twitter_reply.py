import sys
import os
import time
import logging
import schedule

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.twitter_reply_service import TwitterReplyService
from src.utils.config_loader import CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class TwitterReplyJob:
    """Service to check Twitter mentions and reply on a schedule"""

    def __init__(self):
        self.twitter_reply_service = TwitterReplyService()
        self.fetch_interval = CONFIG.get("TWITTER_REPLY_INTERVAL", 300)  # Default is 300 seconds (5 minutes)

    def run(self):
        """Run the Twitter mentions check every 5 minutes"""
        logging.info("🔄 Starting Twitter Reply Service...")
        schedule.every(5).minutes.do(self.process_mentions)  # Check every 5 minutes

        while True:
            schedule.run_pending()
            time.sleep(30)  # Wait 30 seconds before checking again to avoid busy-wait loop

    def process_mentions(self):
        """Call the mentions processing function"""
        try:
            logging.info("🔄 Checking for Twitter mentions...")
            self.twitter_reply_service.process_mentions()
            logging.info("✅ Twitter mentions processed successfully.")
        except Exception as e:
            logging.error(f"[❌] Error in TwitterReplyJob: {e}")

if __name__ == "__main__":
    service = TwitterReplyJob()
    service.run()