import sys
import os
import time
import logging
import schedule

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.market_news_service import MarketNewsService
from src.services.post_to_social_service import PostToSocialServices

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class MarketNewsJob:
    """Schedule fetching market data, generating news, and posting to social media."""

    def __init__(self):
        self.market_news_service = MarketNewsService()
        self.post_service = PostToSocialServices()
        self.fetch_interval = 43200  # Every 12 hours (10800 seconds)

    def run(self):
        """Run the job on a schedule every 12 hours."""
        logging.info("🔄 Starting the news fetching & social media posting service...")
        
        # Run once immediately on startup
        self.fetch_and_post_news()

        # Schedule to run every 12 hours
        schedule.every(12).hours.do(self.fetch_and_post_news)

        while True:
            schedule.run_pending()
            time.sleep(30)  # Avoid excessive CPU usage

    def fetch_and_post_news(self):
        """Fetch market data, generate news, and post to social media."""
        try:
            logging.info("🔄 Fetching market data...")
            self.market_news_service.fetch_token_market_data()
            logging.info("✅ Market data updated successfully.")

            logging.info("📰 Generating market news...")
            news_content = self.market_news_service.generate_market_news()

            if news_content:
                logging.info("✅ News generated successfully, preparing to post to social media...")
                self.post_service.post_all(news_content)
                logging.info("✅ News posted to X, Telegram, and Discord.")
            else:
                logging.warning("[⚠️] No news to post!")

        except Exception as e:
            logging.error(f"[❌] Error in MarketNewsJob: {e}")

if __name__ == "__main__":
    service = MarketNewsJob()
    service.run()  # Run the schedule every 3 hours