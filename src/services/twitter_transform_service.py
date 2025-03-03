import json
import os
import redis
from src.utils.logger import setup_logger

logger = setup_logger("TwitterTransformService")

LATEST_TWEETS_FILE = "data/latest_tweets.json"
TRANSFORMED_TWEETS_FILE = "data/transformed_tweets.txt"

class TwitterTransformService:
    def __init__(self):
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        try:
            if self.redis_client.ping():
                logger.info("[✅] Successfully connected to Redis")
            else:
                logger.error("[❌] Failed to connect to Redis")
        except redis.ConnectionError as e:
            logger.error(f"[❌] Redis connection error: {e}")

    def load_user_cache(self):
        """Load user list from Redis."""
        try:
            user_cache_data = self.redis_client.get('user_cache')
            if not user_cache_data:
                logger.warning("[⚠️] user_cache not found in Redis!")
                return {}
            user_cache = json.loads(user_cache_data.decode('utf-8'))
            if not user_cache:
                logger.warning("[⚠️] Redis user cache is empty!")
                return {}
            logger.info(f"[📋] Loaded user cache with {len(user_cache)} users from Redis")
            return user_cache
        except redis.RedisError as e:
            logger.error(f"[❌] Error reading user_cache from Redis: {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"[❌] Error decoding user_cache from Redis: {e}")
            return {}

    @staticmethod
    def load_latest_tweets():
        """Load tweet list from `latest_tweets.json`."""
        if not os.path.exists(LATEST_TWEETS_FILE):
            logger.warning("[⚠️] latest_tweets.json not found!")
            return []
        try:
            with open(LATEST_TWEETS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[❌] Error reading latest_tweets.json: {e}")
            return []

    def transform_tweets(self):
        """Transform tweets by mapping `author_id` to `@username`, avoiding duplicates."""
        logger.info("[🔄] Starting tweet transformation...")
        user_cache = self.load_user_cache()
        tweets = self.load_latest_tweets()

        if not tweets:
            logger.warning("[⚠️] No tweets to transform! Clearing transformed_tweets.txt.")
            self.save_transformed_tweets([])
            return []

        transformed_tweets = []
        seen_ids = set()

        for tweet in tweets:
            if tweet["id"] in seen_ids:
                continue
            seen_ids.add(tweet["id"])

            author_id = tweet["author_id"]
            username = user_cache.get(author_id, f"unknown_{author_id}")
            text = tweet["text"]
            transformed_tweet = f"- @{username}: {text}"
            transformed_tweets.append(transformed_tweet)

        self.save_transformed_tweets(transformed_tweets)
        return transformed_tweets

    @staticmethod
    def save_transformed_tweets(transformed_tweets):
        """Save transformed tweets, overwriting the file. If empty, clear the file."""
        try:
            with open(TRANSFORMED_TWEETS_FILE, "w", encoding="utf-8") as f:
                if transformed_tweets:
                    for tweet in transformed_tweets:
                        f.write(tweet + "\n")
                else:
                    f.write("")  
            logger.info(f"[✅] Saved {len(transformed_tweets)} tweets to {TRANSFORMED_TWEETS_FILE}")
        except Exception as e:
            logger.error(f"[❌] Error saving transformed tweets: {e}")

if __name__ == "__main__":
    service = TwitterTransformService()
    transformed = service.transform_tweets()
    for tweet in transformed:
        print(tweet)