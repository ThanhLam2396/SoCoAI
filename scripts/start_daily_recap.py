import sys
import os
import time
import logging
import schedule

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.news_generation_service import NewsGenerationService
from src.services.post_to_x_service import PostToXService
from src.services.post_to_telegram_service import PostToTelegramService
from src.services.post_to_discord_service import PostToDiscordService
from src.services.post_to_sheets_service import PostToGoogleSheetsService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DailyRecapService:
    """Generate daily news recap and post to various platforms."""

    def __init__(self):
        self.news_generation_service = NewsGenerationService()
        self.post_to_x_service = PostToXService()
        self.post_to_telegram_service = PostToTelegramService()
        self.post_to_discord_service = PostToDiscordService()
        self.post_to_sheets_service = PostToGoogleSheetsService()

    def run_daily_recap(self):
        """Run the daily news recap"""
        try:
            logging.info("🔄 Generating Daily Recap...")
            self.news_generation_service.run_daily_recap()
            logging.info("✅ Daily Recap generated.")

            logging.info("🔄 Posting Daily Recap to X...")
            self.post_to_x_service.post_daily_recap()
            logging.info("✅ Daily Recap posted to X.")

            logging.info("🔄 Posting Daily Recap to Telegram...")
            self.post_to_telegram_service.post_daily_recap()
            logging.info("✅ Daily Recap posted to Telegram.")

            logging.info("🔄 Posting Daily Recap to Discord...")
            self.post_to_discord_service.post_daily_recap()
            logging.info("✅ Daily Recap posted to Discord.")

        except Exception as e:
            logging.error(f"[❌] Error in daily_recap: {e}")

    def start_scheduler(self):
        """Schedule the recap to run daily at 23:50."""
        schedule.every().day.at("23:50").do(self.run_daily_recap)

        logging.info("⏳ Daily Recap scheduler started. Waiting for 23:50...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check the schedule every minute

if __name__ == "__main__":
    service = DailyRecapService()
    service.start_scheduler()