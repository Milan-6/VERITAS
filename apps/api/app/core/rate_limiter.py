import collections
import logging
import threading
import time
import uuid
from typing import Dict, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    High-performance sliding-window rate limiter.
    Primary backend: Redis sorted sets.
    Fallback backend: Thread-safe in-memory sliding window deque.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client = None
        self._redis_failed = False
        self._lock = threading.Lock()
        # In-memory storage: key -> list of float timestamps
        self._memory_store: Dict[str, list] = collections.defaultdict(list)

    def _get_redis(self):
        if self._redis_failed:
            return None
        if self._redis_client is not None:
            return self._redis_client

        try:
            import redis
            client = redis.from_url(
                self.redis_url,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                decode_responses=True,
            )
            # Ping to test connectivity
            client.ping()
            self._redis_client = client
            logger.info(f"Connected to Redis rate limiter at {self.redis_url}")
            return self._redis_client
        except Exception as e:
            logger.info(f"Redis not available for rate limiting ({e}); using thread-safe in-memory sliding window.")
            self._redis_failed = True
            self._redis_client = None
            return None

    def reset_cache(self):
        """Clears in-memory storage (primarily for test isolation)."""
        with self._lock:
            self._memory_store.clear()

    def check_rate_limit(
        self,
        client_id: str,
        limit_tier: str = "default",
        custom_limit: Optional[int] = None,
        custom_window: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, str], int]:
        """
        Evaluates sliding window rate limit for client_id.

        Returns:
            (is_allowed, headers_dict, retry_after_seconds)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, {
                "X-RateLimit-Limit": "unlimited",
                "X-RateLimit-Remaining": "9999",
                "X-RateLimit-Reset": str(int(time.time() + 60)),
            }, 0

        # Determine limits
        if custom_limit is not None and custom_window is not None:
            max_requests = custom_limit
            window_seconds = custom_window
        elif limit_tier == "heavy":
            max_requests = settings.RATE_LIMIT_HEAVY_REQUESTS
            window_seconds = settings.RATE_LIMIT_HEAVY_WINDOW
        else:
            max_requests = settings.RATE_LIMIT_DEFAULT_REQUESTS
            window_seconds = settings.RATE_LIMIT_DEFAULT_WINDOW

        now = time.time()
        key = f"ratelimit:{client_id}:{limit_tier}"

        # 1. Attempt Redis sliding window
        r = self._get_redis()
        if r is not None:
            try:
                pipe = r.pipeline()
                cutoff = now - window_seconds
                # Remove expired requests
                pipe.zremrangebyscore(key, 0, cutoff)
                # Count current requests in window
                pipe.zcard(key)
                # Query oldest remaining timestamp to calculate reset
                pipe.zrange(key, 0, 0, withscores=True)
                _, count, oldest_items = pipe.execute()

                if count >= max_requests:
                    oldest_ts = oldest_items[0][1] if oldest_items else (now - window_seconds)
                    reset_time = int(oldest_ts + window_seconds)
                    retry_after = max(1, int(reset_time - now))
                    headers = {
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(retry_after),
                    }
                    return False, headers, retry_after

                # Request is allowed; add current timestamp to sorted set
                member = f"{now}:{uuid.uuid4().hex[:6]}"
                pipe = r.pipeline()
                pipe.zadd(key, {member: now})
                pipe.expire(key, window_seconds * 2)
                pipe.execute()

                remaining = max(0, max_requests - (count + 1))
                reset_time = int(now + window_seconds)
                headers = {
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                }
                return True, headers, 0

            except Exception as e:
                logger.warning(f"Redis rate limit call failed ({e}); falling back to memory.")
                self._redis_failed = True
                # Fall through to in-memory

        # 2. In-memory sliding window fallback
        with self._lock:
            cutoff = now - window_seconds
            timestamps = self._memory_store[key]

            # Prune expired timestamps
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            self._memory_store[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                oldest_ts = valid_timestamps[0]
                reset_time = int(oldest_ts + window_seconds)
                retry_after = max(1, int(reset_time - now))
                headers = {
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(retry_after),
                }
                return False, headers, retry_after

            # Allowed
            valid_timestamps.append(now)
            remaining = max(0, max_requests - len(valid_timestamps))
            reset_time = int(now + window_seconds)
            headers = {
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
            }
            return True, headers, 0


rate_limiter = SlidingWindowRateLimiter()
