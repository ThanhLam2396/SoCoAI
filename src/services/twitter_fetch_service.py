import json
import os
import requests
import time
from datetime import datetime, timezone, timedelta
import redis
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("TwitterFetchService")

# Define storage files
LATEST_TWEETS_FILE = "data/latest_tweets.json"
DAILY_TWEETS_FILE = "data/daily_tweets.json"

# List of sensitive words (can be customized)
SENSITIVE_WORDS = {"fuck", "bitch"}  # Add more sensitive words as needed

class UserCacheService:
    @staticmethod
    def load_user_ids():
        """Load user list from Redis."""
        redis_client = redis.Redis(host='redis', port=6379, db=0)
        try:
            user_cache_data = redis_client.get('user_cache')
            if not user_cache_data:
                logger.warning("[WARNING] user_cache not found in Redis!")
                return []
            user_data = json.loads(user_cache_data.decode('utf-8'))
            return list(user_data.keys())
        except redis.RedisError as e:
            logger.error(f"[ERROR] Error reading user cache from Redis: {e}")
            return []

class TweetStorageService:
    @staticmethod
    def save_latest_tweets(tweets):
        """Save the latest tweets by overwriting the file, even if empty."""
        try:
            with open(LATEST_TWEETS_FILE, "w") as f:
                json.dump(tweets, f, indent=2)
            logger.info(f"[INFO] Saved {len(tweets)} latest tweets to {LATEST_TWEETS_FILE}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save latest tweets: {e}")

    @staticmethod
    def save_daily_tweets(tweets):
        """Save tweets for the current day, appending only if there are new tweets."""
        if not tweets:
            logger.info("[INFO] No new tweets to append to daily_tweets.json")
            return
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            if os.path.exists(DAILY_TWEETS_FILE):
                with open(DAILY_TWEETS_FILE, "r") as f:
                    existing_data = json.load(f)
                    existing_tweets = existing_data.get("tweets", []) if existing_data.get("date") == today else []
            else:
                existing_tweets = []
            updated_tweets = existing_tweets + tweets
            with open(DAILY_TWEETS_FILE, "w") as f:
                json.dump({"date": today, "tweets": updated_tweets}, f, indent=2)
            logger.info(f"[INFO] Saved {len(updated_tweets)} tweets for today ({today}) to {DAILY_TWEETS_FILE}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save daily tweets: {e}")

class TwitterFetchService:
    def __init__(self):
        self.bearer_token = CONFIG["BEARER_TOKEN"]
        self.base_url = "https://api.x.com/2/tweets/search/recent"
        self.batch_size = 10  # Number of users per batch
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        self.sensitive_words = SENSITIVE_WORDS  # Sensitive words filter
        try:
            if self.redis_client.ping():
                logger.info("[✅] Successfully connected to Redis")
            else:
                logger.error("[❌] Failed to connect to Redis")
        except redis.ConnectionError as e:
            logger.error(f"[❌] Redis connection error: {e}")

    def filter_sensitive_tweets(self, tweets):
        """Filter out tweets containing sensitive words."""
        filtered_tweets = []
        skipped_count = 0
        for tweet in tweets:
            tweet_text = tweet['text'].lower()  # Convert to lowercase for checking
            if any(word in tweet_text for word in self.sensitive_words):
                logger.debug(f"[DEBUG] Skipped tweet due to sensitive content: {tweet['text']}")
                skipped_count += 1
            else:
                filtered_tweets.append(tweet)
        logger.info(f"[INFO] Filtered out {skipped_count} tweets with sensitive words.")
        return filtered_tweets

    def fetch_tweets_for_batch(self, user_ids):
        """Fetch original tweets for a batch of users from the last hour."""
        start_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        query = " OR ".join([f"from:{user_id}" for user_id in user_ids]) + " -is:reply -is:retweet -is:quote"
        params = {
            "query": query,
            "max_results": 50,  # Maximum number of tweets per batch
            "tweet.fields": "created_at,text,author_id",
            "start_time": start_time
        }
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        new_tweets = []

        logger.info(f"[DEBUG] Fetching tweets for batch {user_ids} since {start_time}")
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            logger.info(f"[DEBUG] API status for batch: {response.status_code}")
            if response.status_code == 429:
                wait_time = max(int(response.headers.get('x-rate-limit-reset', time.time() + 60)) - int(time.time()), 1)
                logger.warning(f"Rate limit reached. Retrying after {wait_time} seconds.")
                time.sleep(wait_time)
                return self.fetch_tweets_for_batch(user_ids)
            if response.status_code != 200:
                logger.error(f"[ERROR] API call failed for batch: {response.text}")
                return []

            data = response.json()
            raw_tweets = data.get("data", [])
            logger.info(f"[DEBUG] Original tweets for batch: {len(raw_tweets)}")

            for tweet in raw_tweets:
                tweet_date = datetime.fromisoformat(tweet['created_at'].replace("Z", "+00:00"))
                tweet_data = {
                    'id': tweet['id'],
                    'date': tweet_date.strftime("%Y-%m-%d %H:%M:%S"),
                    'text': tweet['text'],
                    'author_id': tweet['author_id']
                }
                new_tweets.append(tweet_data)

            # Filter sensitive words before returning
            filtered_tweets = self.filter_sensitive_tweets(new_tweets)
            logger.info(f"[INFO] Fetched and filtered {len(filtered_tweets)} original tweets for batch {user_ids}")
            return filtered_tweets
        except Exception as e:
            logger.error(f"[ERROR] Error fetching tweets for batch {user_ids}: {e}")
            return []

    def fetch_latest_tweets(self):
        """Fetch latest tweets for all users in the cache from the last hour."""
        user_ids = UserCacheService.load_user_ids()
        if not user_ids:
            logger.warning("[WARNING] No user IDs found in cache!")
            return []

        all_new_tweets = []
        user_batches = [user_ids[i:i + self.batch_size] for i in range(0, len(user_ids), self.batch_size)]

        for batch in user_batches:
            tweets = self.fetch_tweets_for_batch(batch)
            all_new_tweets.extend(tweets)
            logger.info(f"[DEBUG] Fetched {len(tweets)} new tweets for batch {batch}")

        # Save filtered tweets
        TweetStorageService.save_latest_tweets(all_new_tweets)
        TweetStorageService.save_daily_tweets(all_new_tweets)
        
        if not all_new_tweets:
            logger.info("[INFO] No new tweets fetched in the last hour.")
        else:
            logger.info(f"[INFO] Fetched and saved {len(all_new_tweets)} new tweets from the last hour.")

        return all_new_tweets

if __name__ == "__main__":
    service = TwitterFetchService()
    tweets = service.fetch_latest_tweets()
    print(f"Fetched {len(tweets)} tweets")