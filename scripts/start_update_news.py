import sys
import os
import time
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.features.twitter_fetch_feature import TwitterFetchFeature
from src.services.twitter_transform_service import TwitterTransformService
from src.services.news_generation_service import NewsGenerationService
from src.services.post_to_x_service import PostToXService
from src.services.post_to_telegram_service import PostToTelegramService
from src.services.post_to_discord_service import PostToDiscordService
from src.services.post_to_sheets_service import PostToGoogleSheetsService
from src.utils.config_loader import CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class UpdateNewsService:
    def __init__(self):
        self.twitter_fetch_feature = TwitterFetchFeature()
        self.twitter_transform_service = TwitterTransformService()
        self.news_generation_service = NewsGenerationService()
        self.post_to_x_service = PostToXService()
        self.post_to_telegram_service = PostToTelegramService()
        self.post_to_discord_service = PostToDiscordService()
        self.post_to_sheets_service = PostToGoogleSheetsService()
        self.fetch_interval = CONFIG.get("TWEETS_FETCH_INTERVAL", 3600)
        self.generated_news_file = "data/generated_news.txt"

    def load_generated_news(self):
        """Load content from generated_news.txt and check if it's empty."""
        if not os.path.exists(self.generated_news_file):
            logging.warning(f"[⚠️] File {self.generated_news_file} not found!")
            return ""
        with open(self.generated_news_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                logging.warning(f"[⚠️] File {self.generated_news_file} is empty!")
            return content

    def run(self):
        """Run continuous news updates"""
        while True:
            try:
                logging.info("🔄 Fetching latest tweets...")
                self.twitter_fetch_feature.run()
                logging.info("✅ Tweets fetched.")

                logging.info("🔄 Transforming tweets...")
                self.twitter_transform_service.transform_tweets()
                logging.info("✅ Tweets transformed.")

                logging.info("🔄 Generating news...")
                self.news_generation_service.generate_news()
                logging.info("✅ News generated.")

                # Load and check generated news content
                news_content = self.load_generated_news()
                if not news_content:
                    logging.info("[INFO] No news content to post. Skipping posting steps.")
                else:
                    logging.info("🔄 Saving news to Google Sheets...")
                    self.post_to_sheets_service.save_news_to_google_sheet()
                    logging.info("✅ News saved.")

                    logging.info("🔄 Posting news to X...")
                    self.post_to_x_service.post_news()
                    logging.info("✅ News posted to X.")

                    logging.info("🔄 Posting news to Telegram...")
                    self.post_to_telegram_service.post_news()
                    logging.info("✅ News posted to Telegram.")

                    logging.info("🔄 Posting news to Discord...")
                    self.post_to_discord_service.post_news()
                    logging.info("✅ News posted to Discord.")

            except Exception as e:
                logging.error(f"[❌] Error in update_news: {e}")

            logging.info(f"⏳ Waiting {self.fetch_interval} seconds before next update...")
            time.sleep(self.fetch_interval)

if __name__ == "__main__":
    service = UpdateNewsService()
    service.run()