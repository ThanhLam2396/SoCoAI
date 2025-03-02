import os
import logging
import asyncio
import requests
import tweepy
import discord
from src.utils.config_loader import CONFIG

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Path to news file
GENERATED_NEWS_FILE = "data/generated_market_news.txt"

class PostToSocialServices:
    """Service to post news to X (Twitter), Telegram (via HTTP API), and Discord."""

    def __init__(self):
        """Initialize APIs for each platform."""
        # Twitter API
        self.twitter_client = tweepy.Client(
            consumer_key=CONFIG["X_CONSUMER_KEY"],
            consumer_secret=CONFIG["X_CONSUMER_SECRET"],
            access_token=CONFIG["X_ACCESS_TOKEN"],
            access_token_secret=CONFIG["X_ACCESS_TOKEN_SECRET"]
        )

        # Telegram API (sử dụng HTTP API thay vì Application)
        self.telegram_bot_token = CONFIG["TELEGRAM_BOT_TOKEN"]
        self.telegram_chat_id = CONFIG["TELEGRAM_CHAT_ID"]
        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"

        # Discord API
        self.discord_bot_token = CONFIG["DISCORD_BOT_TOKEN"]
        self.discord_channel_id = int(CONFIG["DISCORD_CHANNEL_ID"])

    def load_news_content(self, news_file=GENERATED_NEWS_FILE):
        """Load content from news file."""
        if not os.path.exists(news_file):
            logging.warning(f"[⚠️] File {news_file} not found!")
            return None

        with open(news_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            logging.warning(f"[⚠️] File {news_file} is empty!")
            return None

        return content

    def post_to_x(self, news_content):
        """Post news to X (Twitter)."""
        if not news_content:
            logging.warning("[⚠️] No news to post to X!")
            return

        try:
            logging.info(f"[🚀] Posting news to X: {news_content[:50]}...")
            self.twitter_client.create_tweet(text=news_content)
            logging.info("[✅] Successfully posted news to X!")
        except Exception as e:
            logging.error(f"[❌] Error posting to X: {e}")

    def post_to_telegram(self, news_content):
        """Post news to Telegram using HTTP API."""
        if not news_content:
            logging.warning("[⚠️] No news to post to Telegram!")
            return

        try:
            logging.info(f"[🚀] Posting news to Telegram: {news_content[:50]}...")
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": news_content
            }
            response = requests.post(self.telegram_api_url, data=payload)
            response.raise_for_status()  # Raise exception nếu HTTP request thất bại
            logging.info("[✅] Successfully posted news to Telegram!")
        except Exception as e:
            logging.error(f"[❌] Error posting to Telegram: {e}")

    async def post_to_discord(self, news_content):
        """Post news to Discord."""
        if not news_content:
            logging.warning("[⚠️] No news to post to Discord!")
            return

        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        try:
            await client.login(self.discord_bot_token)
            channel = await client.fetch_channel(self.discord_channel_id)
            if channel:
                logging.info(f"[🚀] Sending news to Discord: {news_content[:50]}...")
                await channel.send(news_content)
                logging.info("[✅] Successfully sent news to Discord!")
        except Exception as e:
            logging.error(f"[❌] Error posting to Discord: {e}")
        finally:
            await client.close()

    def post_all(self, news_content=None):
        """Post news to all platforms."""
        if not news_content:
            news_content = self.load_news_content()

        if not news_content:
            logging.warning("[⚠️] No news to post to all platforms!")
            return

        # Post to X (Twitter)
        self.post_to_x(news_content)

        # Post to Telegram
        self.post_to_telegram(news_content)  # Không cần asyncio.run nữa

        # Post to Discord (run asynchronously)
        asyncio.run(self.post_to_discord(news_content))


# Run script
if __name__ == "__main__":
    poster = PostToSocialServices()
    poster.post_all()  # Post news from `generated_market_news.txt`