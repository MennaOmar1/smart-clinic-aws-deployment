import redis
import json
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("✓ Redis connected successfully")
except Exception as e:
    print(f"⚠ Redis connection failed: {e}")
    print("⚠ Redis unavailable: using in-memory fallback for session storage")
    class MockRedis:
        def __init__(self):
            self._store = {}

        def get(self, key):
            return self._store.get(key)

        def set(self, key, value, *args, **kwargs):
            self._store[key] = value

        def delete(self, key):
            if key in self._store:
                del self._store[key]

    r = MockRedis()