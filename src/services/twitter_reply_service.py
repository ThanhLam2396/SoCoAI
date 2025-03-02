import os
import json
import redis
import tweepy
import openai
from datetime import datetime, timezone
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger
import time

logger = setup_logger("TwitterReplyService")

PROMPT_FILE = "config/reply_comments_prompt.json"
TIME_FRAME_MINUTES = 5
MAX_REPLIES_PER_PARENT = 5
MAX_REPLIES_PER_CHILD = 3
REDIS_TTL = 30 * 24 * 60 * 60

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

class TwitterReplyService:
    """Bot to reply to comments/mentions on X (Twitter) naturally and efficiently."""

    def __init__(self):
        """Initialize connection to Twitter API and OpenAI API"""
        self.client = tweepy.Client(
            bearer_token=CONFIG["BEARER_TOKEN"],
            consumer_key=CONFIG["X_CONSUMER_KEY"],
            consumer_secret=CONFIG["X_CONSUMER_SECRET"],
            access_token=CONFIG["X_ACCESS_TOKEN"],
            access_token_secret=CONFIG["X_ACCESS_TOKEN_SECRET"]
        )
        self.openai_client = openai.Client(api_key=CONFIG["OPENAI_API_KEY"])
        self.twitter_id = self.get_twitter_user_id()
        self.prompt_data = self.load_prompt(PROMPT_FILE)
        self.trigger_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("trigger_keywords", []))
        self.banned_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("banned_keywords", []))
        if not self.twitter_id:
            logger.error("[❌] Unable to fetch TWITTER_USER_ID. Check API Keys!")
            exit(1)

    def load_prompt(self, prompt_file: str) -> dict:
        """Load prompt from JSON file"""
        if hasattr(self, "_cached_prompt"):
            return self._cached_prompt
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                self._cached_prompt = json.load(f)
                return self._cached_prompt
        except FileNotFoundError:
            logger.error(f"Prompt file {prompt_file} not found!")
            return {}
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return {}

    def has_replied(self, tweet_id):
        """Check if this tweet has already been replied to."""
        return r.sismember("replied_tweets", tweet_id)

    def save_replied(self, tweet_id):
        """Save the replied tweet to Redis."""
        r.sadd("replied_tweets", tweet_id)
        r.expire("replied_tweets", REDIS_TTL)

    def can_reply(self, root_post_id, child_post_id=None):
        """Check if the bot can continue replying to the parent or child post."""
        if child_post_id:
            count = r.hget("reply_count_child", child_post_id)
            return int(count) < MAX_REPLIES_PER_CHILD if count else True
        else:
            count = r.hget("reply_count", root_post_id)
            return int(count) < MAX_REPLIES_PER_PARENT if count else True

    def increment_reply_count(self, root_post_id, child_post_id=None):
        """Increment the reply count for parent or child post."""
        if child_post_id:
            r.hincrby("reply_count_child", child_post_id, 1)
            r.expire("reply_count_child", REDIS_TTL)
        else:
            r.hincrby("reply_count", root_post_id, 1)
            r.expire("reply_count", REDIS_TTL)

    def load_last_mention_id(self):
        """Retrieve the most recently processed tweet ID."""
        return r.get("last_mention_id")

    def save_last_mention_id(self, tweet_id):
        """Save the most recent tweet ID to avoid duplicates."""
        r.set("last_mention_id", tweet_id)

    def get_twitter_user_id(self):
        """Fetch the bot's Twitter user ID from the Twitter API."""
        try:
            user = self.client.get_me()
            twitter_id = user.data.id if user.data else None
            if twitter_id:
                logger.info(f"[✅] Retrieved Twitter User ID: {twitter_id}")
            return twitter_id
        except Exception as e:
            logger.error(f"[❌] Error fetching TWITTER_USER_ID: {e}")
            return None

    def get_recent_mentions(self):
        """Fetch the latest comments/mentions, retrieving only the most recent unprocessed tweets."""
        try:
            since_id = self.load_last_mention_id()
            tweets = self.client.get_users_mentions(
                id=self.twitter_id,
                tweet_fields=["id", "text", "author_id", "created_at", "referenced_tweets"],
                max_results=10,
                since_id=since_id
            )

            if not tweets.data:
                logger.info("[⚡] No new mentions.")
                return []

            now = datetime.now(timezone.utc)
            filtered_mentions = [
                tweet for tweet in tweets.data
                if (now - tweet.created_at).total_seconds() / 60 <= TIME_FRAME_MINUTES
            ]

            if filtered_mentions:
                max_id = max(tweet.id for tweet in filtered_mentions)
                self.save_last_mention_id(max_id)
                logger.info(f"[📥] Retrieved {len(filtered_mentions)} new mentions: {[tweet.id for tweet in filtered_mentions]}")
            else:
                logger.info("[📥] No mentions within time frame.")

            return filtered_mentions
        except Exception as e:
            logger.error(f"[❌] Error fetching mentions: {e}")
            return []

    def get_root_post_id(self, tweet):
        """Trace back to the actual root post of the conversation."""
        while tweet.referenced_tweets:
            parent_id = tweet.referenced_tweets[0]["id"]
            tweet = self.client.get_tweet(parent_id, tweet_fields=["id", "referenced_tweets"]).data
            if not tweet:
                break
        return str(tweet.id)

    def generate_reply(self, tweet_text):
        """Generate response from OpenAI based on tweet content."""
        contains_trigger = any(keyword.lower() in tweet_text.lower() for keyword in self.trigger_keywords)
        contains_banned = any(keyword.lower() in tweet_text.lower() for keyword in self.banned_keywords)

        if contains_banned:
            return "Oh dear, such unrefined language! I'm a classy bot, let's keep it fun and drama-free. 😤"

        messages = [
            {
                "role": "system",
                "content": f"{self.prompt_data.get('role', 'You are an AI assistant.')}\n\n{self.prompt_data.get('context', '')}"
            }
        ]

        for example in self.prompt_data.get("example_conversations", []):
            messages.append({"role": "user", "content": example["User:"]})
            messages.append({"role": "assistant", "content": example["Assistant:"]})

        if contains_trigger:
            strategy = self.prompt_data.get("specific_mention_handling", {}).get("response_strategy", [])
            messages.append({"role": "system", "content": " ".join(strategy)})

        messages.append({"role": "user", "content": tweet_text})

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=100,
                temperature=0.9
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[❌] OpenAI error: {e}")
            return "Sorry, I can't respond at the moment. 😏"

    def reply_to_tweet(self, tweet_id, reply_text, root_post_id):
        """Reply to a tweet."""
        try:
            self.client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet_id)
            self.save_replied(tweet_id)
            self.increment_reply_count(root_post_id)
            logger.info(f"[✅] Replied to tweet {tweet_id} (Parent post {root_post_id})")
        except Exception as e:
            logger.error(f"[❌] Error replying to tweet {tweet_id}: {e}")

    def process_mentions(self):
        """Process mentions and reply to them."""
        logger.info("🔄 Checking for Twitter mentions...")
        mentions = self.get_recent_mentions()
        if not mentions:
            logger.info("✅ Twitter mentions processed successfully.")
            return

        for tweet in mentions:
            try:
                root_post_id = self.get_root_post_id(tweet)
                tweet_id = str(tweet.id)

                if not self.can_reply(root_post_id):
                    logger.info(f"[⛔] Reply limit reached for parent post {root_post_id}")
                    continue

                if self.has_replied(tweet_id):
                    logger.info(f"[♻️] Already replied to tweet {tweet_id}, skipping.")
                    continue

                reply_text = self.generate_reply(tweet.text)
                if reply_text:
                    self.reply_to_tweet(tweet_id, reply_text, root_post_id)

            except Exception as e:
                logger.error(f"[🔥] Error processing tweet {tweet.id}: {e}")
        logger.info("✅ Twitter mentions processed successfully.")

if __name__ == "__main__":
    service = TwitterReplyService()
    while True:
        service.process_mentions()
        time.sleep(300)