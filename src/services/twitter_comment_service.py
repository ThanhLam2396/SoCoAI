import os
import json
import redis
import tweepy
import openai
import time
from datetime import datetime, timezone
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("AutoCommentService")

# === Configuration ===
TIME_FRAME_MINUTES = 5  # Only scan posts within this time frame
REDIS_TTL = 30 * 24 * 60 * 60  # 30 days
USER_ID_TTL = 6 * 60 * 60  # 6 hours

# === Redis Config ===
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

class AutoCommentService:
    def __init__(self):
        """Initialize AutoCommentService with Twitter and OpenAI"""
        self.client = tweepy.Client(
            bearer_token=CONFIG["BEARER_TOKEN"],
            consumer_key=CONFIG["X_CONSUMER_KEY"],
            consumer_secret=CONFIG["X_CONSUMER_SECRET"],
            access_token=CONFIG["X_ACCESS_TOKEN"],
            access_token_secret=CONFIG["X_ACCESS_TOKEN_SECRET"]
        )
        self.openai_client = openai.Client(api_key=CONFIG["OPENAI_API_KEY"])
        self.user_list = CONFIG.get("LIST_USERS", [])
        self.prompt_data = self.load_prompt("config/auto_comment_prompt.json")

        # Create list of trigger keywords
        self.trigger_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("trigger_keywords", []))
        self.banned_keywords = set(self.prompt_data.get("specific_mention_handling", {}).get("banned_keywords", []))
        # logger.info(f"Trigger keywords loaded: {self.trigger_keywords}")
        # logger.info(f"Banned keywords loaded: {self.banned_keywords}")

    def load_prompt(self, prompt_file: str) -> dict:
        """Load prompt from JSON file"""
        if hasattr(self, "_cached_prompt"):  # If already cached, reuse it
            return self._cached_prompt
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                self._cached_prompt = json.load(f)  # Cache the data
                # logger.info(f"Successfully loaded prompt from {prompt_file}: {json.dumps(self._cached_prompt, indent=2)}")
                return self._cached_prompt
        except FileNotFoundError:
            logger.error(f"Prompt file {prompt_file} not found!")
            return {}
        except Exception as e:
            logger.error(f"Error loading prompt file {prompt_file}: {e}")
            return {}

    def update_user_ids(self):
        """Update list of user_ids from usernames and store in Redis as a hash table."""
        for username in self.user_list:
            user_id = r.hget("user_ids", username)
            if not user_id:
                try:
                    user = self.client.get_user(username=username, user_fields=["id"])
                    if user and user.data:
                        user_id = user.data.id
                        r.hset("user_ids", username, user_id)
                except Exception as e:
                    logger.error(f"[❌] Error fetching user ID for {username}: {e}")
        r.expire("user_ids", USER_ID_TTL)

    def get_user_id(self, username):
        """Retrieve user_id from Redis."""
        return r.hget("user_ids", username)

    def has_commented(self, tweet_id):
        """Check if the tweet has already been commented on."""
        return r.sismember("commented_tweets", tweet_id)

    def save_commented(self, tweet_id):
        """Save the commented tweet to Redis."""
        r.sadd("commented_tweets", tweet_id)
        r.expire("commented_tweets", REDIS_TTL)

    def get_recent_posts(self, user_id):
        """Fetch recent posts from a user with minimal requests."""
        try:
            tweets = self.client.get_users_tweets(
                id=user_id,
                tweet_fields=["id", "text", "created_at", "referenced_tweets"],
                max_results=5
            )
            if not tweets.data:
                logger.info(f"No recent tweets found for user ID {user_id}")
                return []

            now = datetime.now(timezone.utc)
            filtered_tweets = [
                tweet for tweet in tweets.data
                if (now - tweet.created_at).total_seconds() / 60 <= TIME_FRAME_MINUTES
                and (tweet.referenced_tweets is None or not any(ref['type'] == 'replied_to' for ref in tweet.referenced_tweets))
            ]
            logger.info(f"Found {len(filtered_tweets)} recent original or quoted tweets for user ID {user_id}")
            return filtered_tweets[:1]
        except Exception as e:
            logger.error(f"[❌] Error fetching posts for user {user_id}: {e}")
            return []

    def generate_comment(self, post_text):
        """Generate a comment from OpenAI based on post content."""
        contains_trigger = any(keyword.lower() in post_text.lower() for keyword in self.trigger_keywords)
        contains_banned = any(keyword.lower() in post_text.lower() for keyword in self.banned_keywords)
        # logger.info(f"Processing tweet: {post_text}")
        # logger.info(f"Contains trigger: {contains_trigger}, Contains banned: {contains_banned}")

        if contains_banned:
            # logger.info("Banned keyword detected, returning sassy response")
            return "Oh dear, such unrefined words! I'm a classy bot, let’s keep it fun and drama-free, okay? 😤"

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
            # logger.info(f"Added specific handling strategy: {' '.join(strategy)}")

        messages.append({"role": "user", "content": f"Post content: {post_text}"})
        # logger.info(f"Messages sent to OpenAI: {json.dumps(messages, indent=2)}")

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=100,
                temperature=0.9  # Increase creativity
            )
            comment = response.choices[0].message.content.strip()
            # logger.info(f"Generated comment: {comment}")
            return comment
        except Exception as e:
            logger.error(f"[❌] OpenAI error: {str(e)}", exc_info=True)
            return "A witty comment stops here!"

    def comment_on_post(self, tweet_id, comment_text):
        """Post a comment on a tweet."""
        try:
            self.client.create_tweet(text=comment_text, in_reply_to_tweet_id=tweet_id)
            self.save_commented(tweet_id)
            logger.info(f"[✅] Commented on tweet {tweet_id}")
        except Exception as e:
            logger.error(f"[❌] Error commenting on tweet {tweet_id}: {e}")

    def process_users(self):
        """Process users and comment on their recent posts."""
        self.update_user_ids()
        for username in self.user_list:
            user_id = self.get_user_id(username)
            if not user_id:
                logger.warning(f"No user ID found for {username}, skipping.")
                continue
            posts = self.get_recent_posts(user_id)
            for post in posts:
                if self.has_commented(post.id):
                    logger.info(f"[♻️] Already commented on tweet {post.id}, skipping.")
                    continue
                comment_text = self.generate_comment(post.text)
                if comment_text:
                    self.comment_on_post(post.id, comment_text)

if __name__ == "__main__":
    service = AutoCommentService()
    service.process_users()