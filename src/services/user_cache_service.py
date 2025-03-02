import requests
import json
import time
from datetime import datetime, timezone
import redis
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("CacheUserService")

API_URL_TEMPLATE = "https://api.x.com/2/lists/{}/members"  # API to fetch users from a list
BATCH_SIZE = 100  # Maximum number of users per request (Twitter limit is 100)

class CacheUserService:
    """Manage caching of user lists from multiple list IDs to avoid excessive API calls."""

    def __init__(self):
        self.bearer_token = CONFIG["BEARER_TOKEN"]
        self.list_ids = CONFIG.get("LIST_IDS", [])  # Retrieve LIST_IDS from settings.json
        self.redis_client = redis.Redis(host='redis', port=6379, db=0)  # Kết nối Redis

        # Kiểm tra kết nối Redis
        try:
            if self.redis_client.ping():
                logger.info("[✅] Successfully connected to Redis")
            else:
                logger.error("[❌] Failed to connect to Redis")
                raise redis.ConnectionError("Redis connection failed")
        except redis.ConnectionError as e:
            logger.error(f"[❌] Redis connection error: {e}")
            raise  # Ném lỗi để dừng nếu không kết nối được Redis

        # Load user cache và kiểm tra dữ liệu ngay khi khởi tạo
        self.user_cache = self.load_user_cache()
        if not self.user_cache:  # Nếu không có dữ liệu trong Redis
            logger.info("[⚠️] No data in Redis at startup. Fetching user cache immediately...")
            self.refresh_user_cache()  # Lấy dữ liệu ngay lần đầu
            self.user_cache = self.load_user_cache()  # Cập nhật lại sau khi refresh
            if not self.user_cache:
                logger.critical("[💥] Failed to fetch initial user cache. Data still empty!")
            else:
                logger.info("[✅] Initial user cache loaded successfully at startup.")

    def load_user_cache(self):
        """Load user cache from Redis."""
        try:
            user_cache_data = self.redis_client.get('user_cache')
            if not user_cache_data:
                logger.info("[⚠️] No user cache found in Redis.")
                return {}
            
            user_cache = json.loads(user_cache_data.decode('utf-8'))
            if not user_cache:
                logger.warning("[⚠️] Redis user cache is empty!")
                return {}
            
            logger.info(f"[📋] Loaded user cache with {len(user_cache)} users from Redis")
            return user_cache
        except redis.RedisError as e:
            logger.error(f"[❌] Error loading user cache from Redis: {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"[❌] Error decoding user cache from Redis: {e}")
            return {}

    def save_user_cache(self):
        """Save user cache to Redis."""
        try:
            self.redis_client.set('user_cache', json.dumps(self.user_cache))
            logger.info("[💾] Successfully saved user cache to Redis")
        except redis.RedisError as e:
            logger.error(f"[❌] Error saving user cache to Redis: {e}")

    def fetch_users_from_list(self, list_id):
        """Call X API to fetch user list from a list ID (supports pagination)."""
        logger.info(f"🔄 Fetching users from List ID: {list_id}...")

        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "max_results": BATCH_SIZE,  # API allows up to 100 users per request
            "user.fields": "id,username"
        }

        url = API_URL_TEMPLATE.format(list_id)
        total_users_fetched = 0  # Count of fetched users

        try:
            while True:
                response = requests.get(url, headers=headers, params=params)
                logger.info(f"[DEBUG] API Response Status: {response.status_code}")

                # If rate-limited, wait and retry
                if response.status_code == 429:
                    reset_time = int(response.headers.get('x-rate-limit-reset', time.time() + 60)) - int(time.time())
                    wait_time = max(reset_time, 60)  # Default to 60 seconds if no header
                    logger.warning(f"⚠️ Rate limit reached. Retrying after {wait_time} seconds.")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    logger.error(f"[ERROR] API call failed: {response.text}")
                    return

                data = response.json()
                users = {user['id']: user['username'] for user in data.get('data', [])}
                self.user_cache.update(users)
                total_users_fetched += len(users)

                # Handle pagination if user list exceeds 100
                if 'next_token' in data.get('meta', {}):
                    params['pagination_token'] = data['meta']['next_token']
                else:
                    break  # No more users, exit loop

        except Exception as e:
            logger.error(f"❌ Error fetching user list: {e}")

        logger.info(f"✅ Done! Total users fetched from List {list_id}: {total_users_fetched}")

    def refresh_user_cache(self):
        """Refresh user cache by fetching from all LIST_IDS."""
        logger.info("🔄 Refreshing user cache from LIST_IDS...")

        if not self.list_ids:
            logger.warning("⚠️ No LIST_IDS found in settings.json!")
            return

        for list_id in self.list_ids:
            self.fetch_users_from_list(list_id)

        # Save cache after updating
        self.save_user_cache()

if __name__ == "__main__":
    service = CacheUserService()
    print(f"User cache: {service.user_cache}")