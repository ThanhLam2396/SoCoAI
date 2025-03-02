import os
import requests
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("PostToTelegramService")

GENERATED_NEWS_FILE = "data/generated_news.txt"
DAILY_NEWS_FILE = "data/daily_generate_news.txt"  # File for Daily Recap
TELEGRAM_BOT_TOKEN = CONFIG["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = CONFIG["TELEGRAM_CHAT_ID"]
TWEET_BATCH_SIZE = 10  # Each post will contain up to 10 news items
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

class PostToTelegramService:
    """Service to post news to Telegram with each post containing up to 10 news items using HTTP API."""

    def __init__(self):
        """Initialize Telegram API URL."""
        self.telegram_api_url = TELEGRAM_API_URL
        self.chat_id = TELEGRAM_CHAT_ID

    def load_news(self, file_path):
        """Load content from file and group news items."""
        if not os.path.exists(file_path):
            logger.warning(f"[⚠️] File {file_path} not found!")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            news_list = [line.strip() for line in f.read().strip().split("\n\n")]

        if file_path == GENERATED_NEWS_FILE:
            return [news_list[i:i + TWEET_BATCH_SIZE] for i in range(0, len(news_list), TWEET_BATCH_SIZE)]

        return [news_list]  # Daily Recap is a single post

    def post_news_to_telegram(self, file_path, is_daily_recap=False):
        """Send news to Telegram from file using HTTP API."""
        news_batches = self.load_news(file_path)
        if not news_batches:
            logger.warning(f"[⚠️] No news to post from {file_path}!")
            return
        
        for batch in news_batches:
            message_content = "\n\n".join(batch)
            try:
                logger.info(f"[🚀] Sending {'Daily Recap' if is_daily_recap else 'news'} to Telegram: {message_content[:50]}...")
                payload = {
                    "chat_id": self.chat_id,
                    "text": message_content,
                    "disable_web_page_preview": True
                }
                response = requests.post(self.telegram_api_url, data=payload)
                response.raise_for_status()  # Raise exception nếu HTTP request thất bại
                logger.info("[✅] Successfully sent to Telegram!")
            except Exception as e:
                logger.error(f"[❌] Error sending message: {e}")

    def post_news(self):
        """Send regular news from generated_news.txt."""
        self.post_news_to_telegram(GENERATED_NEWS_FILE)

    def post_daily_recap(self):
        """Send Daily Recap from daily_generate_news.txt."""
        self.post_news_to_telegram(DAILY_NEWS_FILE, is_daily_recap=True)

if __name__ == "__main__":
    service = PostToTelegramService()

    # Post regular news
    service.post_news()

    # Post Daily Recap
    service.post_daily_recap()