import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.features.user_cache_feature import UserCacheFeature  # 🔄 Bỏ `src.` nếu `PYTHONPATH` đã đúng

if __name__ == "__main__":
    user_cache = UserCacheFeature()
    user_cache.scheduled_fetch_users()
