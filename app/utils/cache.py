"""
In-memory audit result cache with TTL expiry.

Thread-safe cache keyed on (url, enable_ai) pairs.
Entries are evicted automatically after AUDIT_CACHE_TTL_SECONDS seconds.
The cache lives in process memory — each worker process has its own cache.
"""

import time
import hashlib
import threading


class AuditCache:
    """Thread-safe TTL cache for SEO audit results."""

    def __init__(self, ttl_seconds: int = 3600):
        self._store: dict[str, tuple[float, dict]] = {}
        self._ttl   = ttl_seconds
        self._lock  = threading.Lock()

    # ── Public interface ──────────────────────────────────────────────────────

    def get(self, url: str, enable_ai: bool) -> dict | None:
        """
        Return a cached audit result, or None if absent or expired.

        Parameters:
            url:       The audited URL (part of cache key).
            enable_ai: Whether AI analysis was requested (part of cache key).
        """
        key = self._make_key(url, enable_ai)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, result = entry
            if time.time() - ts > self._ttl:
                del self._store[key]
                return None
            return result

    def set(self, url: str, enable_ai: bool, result: dict) -> None:
        """Store an audit result in the cache under (url, enable_ai)."""
        key = self._make_key(url, enable_ai)
        with self._lock:
            self._store[key] = (time.time(), result)

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """Return the number of currently cached entries."""
        with self._lock:
            return len(self._store)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _make_key(url: str, enable_ai: bool) -> str:
        raw = f"{url.strip()}:{enable_ai}"
        return hashlib.md5(raw.encode()).hexdigest()
