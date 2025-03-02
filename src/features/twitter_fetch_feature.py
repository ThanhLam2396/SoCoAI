import json
import traceback
import redis
from src.services.twitter_fetch_service import TwitterFetchService
from src.utils.logger import setup_logger

logger = setup_logger("TwitterFetchFeature")

class TwitterFetchFeature:
    """Coordinate the fetching of tweets when called."""

    def __init__(self):
        self.twitter_fetch_service = TwitterFetchService()
        self.max_errors = 5  # Maximum number of consecutive errors before stopping
        self.error_count = 0  # Error counter
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)  # Kết nối Redis

        # Kiểm tra kết nối Redis
        try:
            if self.redis_client.ping():
                logger.info("[✅] Successfully connected to Redis")
            else:
                logger.error("[❌] Failed to connect to Redis")
        except redis.ConnectionError as e:
            logger.error(f"[❌] Redis connection error: {e}")

    def load_user_ids(self):
        """Load user list from Redis."""
        try:
            user_cache_data = self.redis_client.get('user_cache')
            if not user_cache_data:
                logger.warning("[⚠️] user_cache not found in Redis! Waiting for the next update.")
                return []

            user_data = json.loads(user_cache_data.decode('utf-8'))
            user_ids = list(user_data.keys())  # Get list of user IDs
            if not user_ids:
                logger.warning("[⚠️] Redis cache contains no users!")
            return user_ids
        except redis.RedisError as e:
            logger.error(f"[❌] Error reading user_cache from Redis: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"[❌] Error decoding user_cache from Redis: {e}")
            return []

    def run(self):
        """Fetch tweets from the user_cache list using batch processing for efficiency."""
        try:
            logger.info("[🚀] Starting TwitterFetchFeature...")

            # Get user list from Redis
            user_ids = self.load_user_ids()
            if not user_ids:
                logger.warning("[⚠️] No users in cache. Skipping this fetch cycle.")
                return

            # Fetch tweets using the optimized TwitterFetchService
            all_new_tweets = self.twitter_fetch_service.fetch_latest_tweets()

            if not all_new_tweets:
                logger.warning("[⚠️] No new tweets found in the last hour.")
                return

            self.error_count = 0  # Reset error count if fetch succeeds
            logger.info(f"[✅] Fetch and tweet storage completed. Total new tweets: {len(all_new_tweets)}")

        except Exception as e:
            self.error_count += 1
            logger.error(f"[❌] Error in run(): {e}")
            logger.error(traceback.format_exc())

            if self.error_count >= self.max_errors:
                logger.critical(f"[💥] Reached {self.max_errors} consecutive errors. Stopping fetch process.")
                return

if __name__ == "__main__":
    fetcher = TwitterFetchFeature()
    fetcher.run()