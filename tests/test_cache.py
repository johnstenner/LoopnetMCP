"""Tests for TTL cache."""

import time
from unittest.mock import patch

from loopnet_mcp.cache import TTLCache


def test_set_and_get():
    cache = TTLCache(ttl_seconds=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_get_missing_key():
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_ttl_expiration():
    cache = TTLCache(ttl_seconds=1)
    cache.set("key1", "value1")

    # Simulate time passing
    with patch("loopnet_mcp.cache.time") as mock_time:
        # First call (set) used real time, now mock for get
        mock_time.time.return_value = time.time() + 2
        assert cache.get("key1") is None


def test_overwrite_existing_key():
    cache = TTLCache()
    cache.set("key1", "value1")
    cache.set("key1", "value2")
    assert cache.get("key1") == "value2"


def test_max_entries_eviction():
    cache = TTLCache(ttl_seconds=60, max_entries=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert len(cache) == 3

    # Adding a 4th should evict the oldest
    cache.set("d", 4)
    assert len(cache) == 3
    assert cache.get("d") == 4


def test_clear():
    cache = TTLCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0
    assert cache.get("a") is None


def test_len():
    cache = TTLCache()
    assert len(cache) == 0
    cache.set("a", 1)
    assert len(cache) == 1
    cache.set("b", 2)
    assert len(cache) == 2


def test_complex_values():
    cache = TTLCache()
    data = {"properties": [{"name": "Test", "price": "$1M"}], "total": 1}
    cache.set("search_url", data)
    assert cache.get("search_url") == data
