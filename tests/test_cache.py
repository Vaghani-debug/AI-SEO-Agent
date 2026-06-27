"""
Tests for app/utils/cache.py
"""

import time
import pytest
from unittest.mock import patch

from app.utils.cache import AuditCache


class TestAuditCache:
    def test_miss_on_empty_cache(self):
        cache = AuditCache()
        assert cache.get("https://example.com", False) is None

    def test_set_and_get_returns_stored_result(self):
        cache = AuditCache()
        result = {"success": True, "score": 95}
        cache.set("https://example.com", False, result)
        assert cache.get("https://example.com", False) == result

    def test_ai_flag_creates_separate_cache_entries(self):
        cache = AuditCache()
        cache.set("https://example.com", False, {"ai": False})
        cache.set("https://example.com", True,  {"ai": True})
        assert cache.get("https://example.com", False) == {"ai": False}
        assert cache.get("https://example.com", True)  == {"ai": True}

    def test_different_urls_do_not_collide(self):
        cache = AuditCache()
        cache.set("https://a.com", False, {"url": "a"})
        cache.set("https://b.com", False, {"url": "b"})
        assert cache.get("https://a.com", False) == {"url": "a"}
        assert cache.get("https://b.com", False) == {"url": "b"}

    def test_ttl_expiry_returns_none(self):
        cache = AuditCache(ttl_seconds=100)
        cache.set("https://example.com", False, {"result": 1})
        with patch("app.utils.cache.time.time", return_value=time.time() + 200):
            assert cache.get("https://example.com", False) is None

    def test_expired_entry_evicted_from_store(self):
        cache = AuditCache(ttl_seconds=100)
        cache.set("https://example.com", False, {"result": 1})
        assert cache.size() == 1
        with patch("app.utils.cache.time.time", return_value=time.time() + 200):
            cache.get("https://example.com", False)
        assert cache.size() == 0

    def test_fresh_entry_not_evicted(self):
        cache = AuditCache(ttl_seconds=3600)
        cache.set("https://example.com", False, {"result": 1})
        assert cache.get("https://example.com", False) is not None

    def test_clear_removes_all_entries(self):
        cache = AuditCache()
        cache.set("https://a.com", False, {})
        cache.set("https://b.com", False, {})
        cache.clear()
        assert cache.size() == 0
        assert cache.get("https://a.com", False) is None

    def test_size_tracks_entry_count(self):
        cache = AuditCache()
        assert cache.size() == 0
        cache.set("https://a.com", False, {})
        assert cache.size() == 1
        cache.set("https://b.com", False, {})
        assert cache.size() == 2

    def test_overwrite_updates_value(self):
        cache = AuditCache()
        cache.set("https://example.com", False, {"v": 1})
        cache.set("https://example.com", False, {"v": 2})
        assert cache.get("https://example.com", False) == {"v": 2}
        assert cache.size() == 1
