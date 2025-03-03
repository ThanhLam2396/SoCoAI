import json
import os
import requests
import time
from datetime import datetime, timezone, timedelta
import redis
from difflib import SequenceMatcher
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger
from src.services.twitter_transform_service import TwitterTransformService  

logger = setup_logger("TwitterFetchService")

LATEST_TWEETS_FILE = "data/latest_tweets.json"
DAILY_TWEETS_FILE = "data/daily_tweets.json"

SENSITIVE_WORDS = {"fuck", "bitch"}
MIN_TWEET_LENGTH = 50

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
        """Save tweets for the current day, appending only unique tweets."""
        if not tweets:
            logger.info("[INFO] No new tweets to append to daily_tweets.json")
            return
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            existing_ids = set()
            if os.path.exists(DAILY_TWEETS_FILE):
                with open(DAILY_TWEETS_FILE, "r") as f:
                    existing_data = json.load(f)
                    if existing_data.get("date") == today:
                        existing_ids = {tweet["id"] for tweet in existing_data.get("tweets", [])}
                    else:
                        existing_ids = set()
            else:
                existing_ids = set()

            new_tweets = [tweet for tweet in tweets if tweet["id"] not in existing_ids]
            if not new_tweets:
                logger.info("[INFO] No unique tweets to append.")
                return

            existing_tweets = existing_data.get("tweets", []) if os.path.exists(DAILY_TWEETS_FILE) and existing_data.get("date") == today else []
            updated_tweets = existing_tweets + new_tweets
            with open(DAILY_TWEETS_FILE, "w") as f:
                json.dump({"date": today, "tweets": updated_tweets}, f, indent=2)
            logger.info(f"[INFO] Saved {len(updated_tweets)} tweets for today ({today}) to {DAILY_TWEETS_FILE}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save daily tweets: {e}")

class TwitterFetchService:
    def __init__(self):
        self.bearer_token = CONFIG["BEARER_TOKEN"]
        self.base_url = "https://api.x.com/2/tweets/search/recent"
        self.batch_size = 10
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)
        self.sensitive_words = SENSITIVE_WORDS
        self.min_tweet_length = MIN_TWEET_LENGTH
        try:
            if self.redis_client.ping():
                logger.info("[✅] Successfully connected to Redis")
            else:
                logger.error("[❌] Failed to connect to Redis")
        except redis.ConnectionError as e:
            logger.error(f"[❌] Redis connection error: {e}")

    def is_duplicate(self, new_tweet, existing_tweets):
        """Check if the new tweet is a duplicate based on content similarity."""
        for tweet in existing_tweets:
            if SequenceMatcher(None, new_tweet['text'], tweet['text']).ratio() > 0.9:
                return True
        return False

    def filter_tweets(self, tweets, existing_tweets=None):
        """Filter tweets and remove duplicates."""
        if existing_tweets is None:
            existing_tweets = []
        
        filtered_tweets = []
        skipped_sensitive = 0
        skipped_short = 0
        skipped_referenced = 0
        skipped_duplicates = 0

        for tweet in tweets:
            tweet_text = tweet['text'].lower()
            tweet_length = len(tweet['text'])

            if 'referenced_tweets' in tweet and tweet['referenced_tweets']:
                skipped_referenced += 1
                continue
            if any(word in tweet_text for word in self.sensitive_words):
                skipped_sensitive += 1
                continue
            if tweet_length < self.min_tweet_length:
                skipped_short += 1
                continue
            if self.is_duplicate(tweet, existing_tweets + filtered_tweets):
                skipped_duplicates += 1
                continue

            filtered_tweets.append(tweet)

        logger.info(f"[INFO] Filtered out {skipped_referenced} replies/retweets/quotes, {skipped_sensitive} sensitive, {skipped_short} short, {skipped_duplicates} duplicates.")
        return filtered_tweets

    def fetch_tweets_for_batch(self, user_ids):
        """Fetch tweets for a batch of users from the last hour only."""
        current_time = datetime.now(timezone.utc)
        start_time = (current_time - timedelta(hours=1)).isoformat()
        query = " OR ".join([f"from:{user_id}" for user_id in user_ids]) + " -is:reply -is:retweet -is:quote"
        params = {
            "query": query,
            "max_results": 50,
            "tweet.fields": "created_at,text,author_id,referenced_tweets",
            "start_time": start_time
        }
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        new_tweets = []

        logger.info(f"[DEBUG] Fetching tweets for batch {user_ids} from {start_time} to {current_time}")
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            if response.status_code == 429:
                wait_time = max(int(response.headers.get('x-rate-limit-reset', time.time() + 60)) - int(time.time()), 1)
                logger.warning(f"Rate limit reached. Retrying after {wait_time} seconds.")
                time.sleep(wait_time)
                return self.fetch_tweets_for_batch(user_ids)
            if response.status_code != 200:
                logger.error(f"[ERROR] API call failed: {response.text}")
                return []

            data = response.json()
            raw_tweets = data.get("data", [])
            logger.info(f"[DEBUG] Retrieved {len(raw_tweets)} tweets for batch.")

            for tweet in raw_tweets:
                tweet_date = datetime.fromisoformat(tweet['created_at'].replace("Z", "+00:00"))
                tweet_data = {
                    'id': tweet['id'],
                    'date': tweet_date.strftime("%Y-%m-%d %H:%M:%S"),
                    'text': tweet['text'],
                    'author_id': tweet['author_id'],
                    'referenced_tweets': tweet.get('referenced_tweets', [])
                }
                new_tweets.append(tweet_data)

            return new_tweets
        except Exception as e:
            logger.error(f"[ERROR] Error fetching tweets for batch {user_ids}: {e}")
            return []

    def fetch_latest_tweets(self):
        """Fetch latest tweets for all users from the last hour, with deduplication."""
        user_ids = UserCacheService.load_user_ids()
        if not user_ids:
            logger.warning("[WARNING] No user IDs found in cache!")
            return []

        all_new_tweets = []
        user_batches = [user_ids[i:i + self.batch_size] for i in range(0, len(user_ids), self.batch_size)]

        for batch in user_batches:
            tweets = self.fetch_tweets_for_batch(batch)
            filtered_tweets = self.filter_tweets(tweets, all_new_tweets)
            all_new_tweets.extend(filtered_tweets)
            logger.info(f"[DEBUG] Fetched and filtered {len(filtered_tweets)} tweets for batch {batch}")

        TweetStorageService.save_latest_tweets(all_new_tweets)
        TweetStorageService.save_daily_tweets(all_new_tweets)
        
        if not all_new_tweets:
            logger.info("[INFO] No new tweets fetched in the last hour. Clearing transformed_tweets.txt.")
            TwitterTransformService.save_transformed_tweets([])  
        
        logger.info(f"[INFO] Fetched and saved {len(all_new_tweets)} unique tweets from the last hour.")
        return all_new_tweets

if __name__ == "__main__":
    service = TwitterFetchService()
    tweets = service.fetch_latest_tweets()
    print(f"Fetched {len(tweets)} tweets")