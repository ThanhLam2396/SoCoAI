import tweepy
import os
from math import ceil
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("PostToXService")

GENERATED_NEWS_FILE = "data/generated_news.txt"
DAILY_NEWS_FILE = "data/daily_generate_news.txt"  # File for Daily Recap
TWEET_BATCH_SIZE = 5  # Each post will contain up to 5 news items
MAX_POSTS = 3  # Limit to a maximum of 3 posts

class PostToXService:
    """Service to post news to X (Twitter) with each post containing up to TWEET_BATCH_SIZE news items."""

    def __init__(self):
        self.client = tweepy.Client(
            consumer_key=CONFIG["X_CONSUMER_KEY"],
            consumer_secret=CONFIG["X_CONSUMER_SECRET"],
            access_token=CONFIG["X_ACCESS_TOKEN"],
            access_token_secret=CONFIG["X_ACCESS_TOKEN_SECRET"]
        )

    def load_news(self):
        """Load content from generated_news.txt and split news into balanced batches."""
        if not os.path.exists(GENERATED_NEWS_FILE):
            logger.warning("[⚠️] File generated_news.txt not found!")
            return []

        with open(GENERATED_NEWS_FILE, "r", encoding="utf-8") as f:
            news_list = [line.strip() for line in f.read().strip().split("\n\n")]

        total_news = len(news_list)
        if total_news == 0:
            return []

        # If news items are fewer than batch size -> create just 1 post
        if total_news <= TWEET_BATCH_SIZE:
            return [news_list]

        # Limit the number of posts to MAX_POSTS
        num_batches = min(MAX_POSTS, ceil(total_news / TWEET_BATCH_SIZE))

        # Split news into batches with even distribution
        avg_batch_size = ceil(total_news / num_batches)
        news_batches = [news_list[i:i + avg_batch_size] for i in range(0, total_news, avg_batch_size)]

        return news_batches

    def load_daily_recap(self):
        """Load Daily Recap content from daily_generate_news.txt."""
        if not os.path.exists(DAILY_NEWS_FILE):
            logger.warning("[⚠️] File daily_generate_news.txt not found!")
            return None

        with open(DAILY_NEWS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()  # Retrieve entire content

    def format_tweet(self, batch):
        """Format a post from a batch of news items, using double line breaks as separators."""
        return "\n\n".join(batch)  # Use double line breaks to separate news items

    def post_news(self):
        """Post tweets to X, each containing up to TWEET_BATCH_SIZE news items."""
        news_batches = self.load_news()
        if not news_batches:
            logger.warning("[⚠️] No news to post!")
            return

        for batch in news_batches:
            tweet_content = self.format_tweet(batch)
            try:
                logger.info(f"[🚀] Posting: {tweet_content[:50]}...")
                self.client.create_tweet(text=tweet_content)
                logger.info("[✅] Successfully posted!")
            except Exception as e:
                logger.error(f"[❌] Error posting: {e}")

    def post_daily_recap(self):
        """Post the Daily Recap news summary to X."""
        daily_recap_content = self.load_daily_recap()
        if not daily_recap_content:
            logger.warning("[⚠️] No Daily Recap content to post!")
            return

        try:
            logger.info(f"[🚀] Posting Daily Recap: {daily_recap_content[:50]}...")
            self.client.create_tweet(text=daily_recap_content)
            logger.info("[✅] Successfully posted Daily Recap!")
        except Exception as e:
            logger.error(f"[❌] Error posting Daily Recap: {e}")

if __name__ == "__main__":
    service = PostToXService()
    service.post_news()  # Post regular news
    service.post_daily_recap()  # Post Daily Recap