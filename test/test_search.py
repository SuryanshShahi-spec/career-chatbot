import sys
import json
import types
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

# Project root on path for any other imports
PROJECT_ROOT = Path(__file__).parent.parent
SEARCH_PATH = str(PROJECT_ROOT / "ai_job_s" / "search.py")


def _load_search_module(mock_redis, module_name="search_mod"):
    """Load search.py with a mocked redis_client injected via sys.modules."""
    fake_my_redis = types.ModuleType("my_redis")
    fake_my_redis.redis_client = mock_redis
    sys.modules["my_redis"] = fake_my_redis

    spec = importlib.util.spec_from_file_location(module_name, SEARCH_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cache_miss_fetches_from_db():
    """Cache miss: should query DB and store results in Redis."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # Simulate cache miss

    search_mod = _load_search_module(mock_redis, "search_miss")
    results = search_mod.get_search_results("Python")

    # Redis.get was called to check cache
    mock_redis.get.assert_called_once()
    # Redis.set was called to store fresh results
    mock_redis.set.assert_called_once()
    # Results must be a non-empty list
    assert isinstance(results, list) and len(results) > 0
    print("PASS - cache miss test:", results)


def test_cache_hit_returns_cached_data():
    """Cache hit: should return cached data and NOT write to Redis again."""
    cached_jobs = [{"job_title": "Cached Dev", "company": "CachedCorp"}]
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(cached_jobs)  # Simulate cache hit

    search_mod = _load_search_module(mock_redis, "search_hit")
    results = search_mod.get_search_results("Remote")

    mock_redis.set.assert_not_called()          # Should NOT re-cache
    assert results == cached_jobs               # Should return exact cached data
    print("PASS - cache hit test:", results)


def test_database_search_simulation_returns_results():
    """database_search_simulation should embed the query in job titles."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    search_mod = _load_search_module(mock_redis, "search_sim")
    results = search_mod.database_search_simulation("Django")

    assert len(results) == 2
    assert any("Django" in r["job_title"] for r in results)
    print("PASS - DB simulation test:", results)


if __name__ == "__main__":
    test_cache_miss_fetches_from_db()
    test_cache_hit_returns_cached_data()
    test_database_search_simulation_returns_results()
    print("\nAll search tests passed!")
