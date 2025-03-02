import json
import os
from collections import defaultdict
from datetime import datetime
import redis

class DappActivityTracker:
    def __init__(self, data_dir="data"):
        """Initialize the class with paths to data files and Redis connection."""
        self.daily_tweets_file = os.path.join(data_dir, "daily_tweets.json")
        self.dapps_activity_file = os.path.join(data_dir, "dapps_activity.json")
        self.total_dapps_activity_file = os.path.join(data_dir, "total_dapps_activity.json")
        
        # Kết nối Redis
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)

        # Kiểm tra kết nối Redis
        try:
            if self.redis_client.ping():
                print("[✅] Successfully connected to Redis")
            else:
                print("[❌] Failed to connect to Redis")
        except redis.ConnectionError as e:
            print(f"[❌] Redis connection error: {e}")

        # Load data from files
        self.daily_tweets = self.load_json(self.daily_tweets_file, {"tweets": []})
        self.dapps_activity = self.load_json(self.dapps_activity_file, [])
        self.total_activity = self.load_json(self.total_dapps_activity_file, [])

    def load_json(self, file_path, default=None):
        """Load JSON from file or return default value if file does not exist."""
        if default is None:
            default = {}
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        return default

    def save_json(self, file_path, data):
        """Save JSON data to file."""
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def load_user_cache_from_redis(self):
        """Load user cache from Redis."""
        try:
            user_cache_data = self.redis_client.get('user_cache')
            if not user_cache_data:
                print("[⚠️] No user cache found in Redis!")
                return {}
            
            user_cache = json.loads(user_cache_data.decode('utf-8'))
            if not user_cache:
                print("[⚠️] Redis user cache is empty!")
                return {}
            
            print(f"[📋] Loaded user cache with {len(user_cache)} users from Redis")
            return user_cache
        except redis.RedisError as e:
            print(f"[❌] Error loading user cache from Redis: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"[❌] Error decoding user cache from Redis: {e}")
            return {}

    def update_dapps_activity(self):
        """Update post counts per user and save to dapps_activity.json."""
        activity_map = {entry["name"]: entry["activity"] for entry in self.dapps_activity}
        user_cache = self.load_user_cache_from_redis()  # Lấy user cache từ Redis

        # Count posts per user
        author_activity = defaultdict(int)
        for tweet in self.daily_tweets.get("tweets", []):
            author_id = tweet["author_id"]
            username = f"@{user_cache.get(author_id, author_id)}"  # Nếu không tìm thấy, dùng author_id
            author_activity[username] += 1

        # Update activity_map
        for username, count in author_activity.items():
            activity_map[username] = activity_map.get(username, 0) + count

        # Convert to list for saving
        self.dapps_activity = [{"name": name, "activity": count} for name, count in activity_map.items()]
        self.save_json(self.dapps_activity_file, self.dapps_activity)
        print("✅ Dapps activity updated successfully.")

    def update_total_activity(self):
        """Update total post count by date and save to total_dapps_activity.json."""
        date_str = self.daily_tweets.get("date", "")
        if not date_str:
            print("⚠️ No date found in daily_tweets.json")
            return

        formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
        tweet_count = len(self.daily_tweets.get("tweets", []))

        # Check if this date already has data; if so, add to it, otherwise create new entry
        existing_entry = next((entry for entry in self.total_activity if entry["date"] == formatted_date), None)
        if existing_entry:
            existing_entry["activity"] += tweet_count
        else:
            self.total_activity.append({"date": formatted_date, "activity": tweet_count})

        self.save_json(self.total_dapps_activity_file, self.total_activity)
        print("✅ Total dapps activity updated successfully.")

    def run(self):
        """Run all updates."""
        self.update_dapps_activity()
        self.update_total_activity()

if __name__ == "__main__":
    tracker = DappActivityTracker()
    tracker.run()