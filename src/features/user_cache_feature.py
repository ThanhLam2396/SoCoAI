import threading
import time
from src.services.user_cache_service import CacheUserService
from src.utils.config_loader import CONFIG
from src.utils.logger import setup_logger

logger = setup_logger("UserCacheFeature")

class UserCacheFeature:
    """Manage the automatic user cache update loop."""

    def __init__(self):
        self.cache_service = CacheUserService()
        # Thay đổi từ 3600 (1 giờ) thành 10800 (3 giờ)
        self.fetch_interval = CONFIG.get("USERS_FETCH_INTERVAL", 10800)  # Retrieved from settings.json, mặc định 3 giờ
        self.stop_event = threading.Event()  # Used to safely stop the thread
    
    def initialize_user_cache(self):
        """Initialize user cache on first run."""
        logger.info("🔄 Initializing user cache...")

        # Check if cache already has data
        user_cache = self.cache_service.load_user_cache()

        if user_cache:
            logger.info("✅ User cache already exists. Loading from cache.")
        else:
            logger.info("⚠️ User cache is empty. Fetching from API...")
            self.cache_service.refresh_user_cache()
    
    def scheduled_fetch_users(self):
        """Run a loop to automatically fetch user list."""
        logger.info("🔄 Starting scheduled user cache refresh...")

        # Run the first time immediately
        self.initialize_user_cache()

        while not self.stop_event.is_set():
            try:
                # Cập nhật thông báo để phản ánh 3 giờ (180 phút)
                logger.info(f"⏳ Waiting {self.fetch_interval // 60} minutes (3 hours) before next update...")
                time.sleep(self.fetch_interval)  # Wait 3 hours (or value from config)
                
                logger.info("🔄 Updating user cache from API...")
                self.cache_service.refresh_user_cache()  # Fetch and update cache
                
            except Exception as e:
                logger.error(f"❌ Error in scheduled_fetch_users: {e}")

    def start(self):
        """Start the user cache update loop in a separate thread."""
        thread = threading.Thread(target=self.scheduled_fetch_users, daemon=True)
        thread.start()
        return thread

    def stop(self):
        """Stop the user cache update loop."""
        logger.info("🛑 Stopping user cache refresh thread...")
        self.stop_event.set()

if __name__ == "__main__":
    feature = UserCacheFeature()
    feature.start()
    try:
        while True:
            time.sleep(1)  # Giữ chương trình chạy để kiểm tra thread
    except KeyboardInterrupt:
        feature.stop()