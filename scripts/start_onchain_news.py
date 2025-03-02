import sys
import os
import time
import logging
import schedule
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.data_onchain_service import OnchainDataService
from src.services.post_to_social_service import PostToSocialServices

# Configuration for schedule intervals (easily adjustable)
FETCH_DATA_INTERVAL_MINUTES = 5  # Fetch data every 5 minutes
GENERATE_NEWS_INTERVAL_HOURS = 12  # Generate news every 8 hours

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class OnchainNewsJob:
    """Schedule fetching on-chain data, generating news, and posting to social media."""

    def __init__(self):
        self.onchain_service = OnchainDataService()
        self.post_service = PostToSocialServices()
        self.fetch_interval_minutes = FETCH_DATA_INTERVAL_MINUTES
        self.generate_interval_hours = GENERATE_NEWS_INTERVAL_HOURS

    def run(self):
        """Run the job on a schedule: fetch data every 5 minutes, generate news every 8 hours."""
        logging.info("Starting the On-Chain news fetching & social media posting service...")
        
        # Run once immediately on startup (both fetch and generate)
        self.fetch_and_post_news()

        # Schedule data fetching every 5 minutes
        schedule.every(self.fetch_interval_minutes).minutes.do(self.fetch_data)

        # Schedule news generation every 8 hours
        schedule.every(self.generate_interval_hours).hours.do(self.generate_and_post_news)

        while True:
            schedule.run_pending()
            logging.info(f"Waiting for the next run... (Fetch: {self.fetch_interval_minutes} minutes, Generate: {self.generate_interval_hours} hours)")
            time.sleep(60)  # Avoid excessive CPU usage

    def fetch_data(self):
        """Fetch on-chain data from all sources and save it."""
        try:
            logging.info("Fetching on-chain data...")
            onchain_data = {
                **self.onchain_service.fetch_injective_data(),
                **self.onchain_service.fetch_gov_params(),
                **self.onchain_service.fetch_supply_and_staking(),
                **self.onchain_service.fetch_web_data()  # Thêm fetch_web_data để lấy dữ liệu từ injscan.com
            }
            self.onchain_service.save_onchain_data(onchain_data)
            logging.info("On-chain data updated successfully.")
        except Exception as e:
            logging.error(f"[ERROR] Failed to fetch on-chain data: {e}")

    def generate_and_post_news(self):
        """Generate news from on-chain data and post to social media."""
        try:
            logging.info("Generating on-chain news...")
            # Assume data is saved from the latest fetch
            with open("data/onchain_data.json", "r", encoding="utf-8") as f:
                onchain_data = json.load(f)  # Use json.load to read JSON file

            news_content = self.onchain_service.generate_news(onchain_data)

            if news_content:
                logging.info("News generated successfully, preparing to post to social media...")
                self.post_service.post_all(news_content)
                logging.info("News posted to X, Telegram, and Discord.")
            else:
                logging.warning("[WARNING] No news to post!")

        except Exception as e:
            logging.error(f"[ERROR] Failed to generate and post news: {e}")

    def fetch_and_post_news(self):
        """Run the full process: fetch data, generate news, and post."""
        try:
            self.fetch_data()  # Fetch data first
            self.generate_and_post_news()  # Generate news and post afterward
        except Exception as e:
            logging.error(f"[ERROR] Error in fetch_and_post_news: {e}")

if __name__ == "__main__":
    service = OnchainNewsJob()
    service.run()  # Run the schedule