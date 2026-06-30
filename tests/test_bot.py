import asyncio
import unittest
import time
# Import modules under test
from bot.config import config
from bot.db import (
    fetch_history,
    save_history,
    _history_cache,
)
import bot.db as db
from bot.ai import (
    limit_concurrency,
    ConcurrencyLimitError,
    _user_semaphores,
)
import bot.ai as ai
from main import _secrets_equal


class TestBotLogic(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Clear cache and semaphores
        _history_cache.clear()
        _user_semaphores.clear()
        ai._global_sem = None

        # Save original db handlers
        self.original_fetch = db._fetch_history_sync
        self.original_save = db._save_history_sync

        # Fake db store
        self.db_store = []

        # Define fake handlers
        def fake_fetch(user_id, group_id, limit):
            matched = [
                row for row in self.db_store
                if row["user_id"] == user_id and row["group_id"] == group_id
            ]
            return matched[-limit:]

        def fake_save(user_id, group_id, role, message):
            self.db_store.append({
                "user_id": user_id,
                "group_id": group_id,
                "role": role,
                "message": message,
                "created_at": "2026-06-30T12:00:00Z"
            })

        db._fetch_history_sync = fake_fetch
        db._save_history_sync = fake_save

    def tearDown(self):
        # Restore original handlers
        db._fetch_history_sync = self.original_fetch
        db._save_history_sync = self.original_save

    def test_secrets_equal(self):
        self.assertTrue(_secrets_equal("secret123", "secret123"))
        self.assertFalse(_secrets_equal("secret123", "different"))
        self.assertFalse(_secrets_equal("secret123", ""))

    async def test_history_cache_hit_and_ttl(self):
        user_id, group_id = 111, 222

        # Prepopulate cache with old entry (expired)
        config.HISTORY_CACHE_TTL_SECONDS = 1
        _history_cache[(user_id, group_id)] = {
            "timestamp": time.time() - 5.0,  # 5 seconds ago
            "history": [{"role": "user", "message": "cached_old"}]
        }

        # Since cache is expired, calling fetch_history should fall back to DB
        # DB is empty initially, so it should return empty list
        history = await fetch_history(user_id, group_id)
        self.assertEqual(history, [])

        # Save some history to DB (which also updates cache)
        await save_history(user_id, group_id, "user", "hello")

        # Verify it was cached with current timestamp
        self.assertIn((user_id, group_id), _history_cache)
        entry = _history_cache[(user_id, group_id)]
        self.assertEqual(
            entry["history"],
            [{"role": "user", "message": "hello"}]
        )

        # Direct cache hit: modify cache and see if fetch returns it
        entry["history"] = [{"role": "user", "message": "cached_new"}]
        history = await fetch_history(user_id, group_id)
        self.assertEqual(history, [{"role": "user", "message": "cached_new"}])

    async def test_history_cache_lru_eviction(self):
        # Set MAX_CACHE_SIZE temporarily to 2
        import bot.db as db_mod
        original_max = db_mod.MAX_CACHE_SIZE
        db_mod.MAX_CACHE_SIZE = 2

        try:
            # We fetch history for 3 different keys
            # Key 1
            await fetch_history(1, 1)
            # Key 2
            await fetch_history(2, 2)
            # Key 3
            await fetch_history(3, 3)

            # Key 1 should have been evicted because size limit is 2
            self.assertNotIn((1, 1), _history_cache)
            self.assertIn((2, 2), _history_cache)
            self.assertIn((3, 3), _history_cache)

            # Hit Key 2 to make it most recently used
            await fetch_history(2, 2)

            # Fetch Key 4
            await fetch_history(4, 4)

            # Key 3 should be evicted (as Key 2 was recently used)
            self.assertNotIn((3, 3), _history_cache)
            self.assertIn((2, 2), _history_cache)
            self.assertIn((4, 4), _history_cache)

        finally:
            db_mod.MAX_CACHE_SIZE = original_max

    async def test_concurrency_limiter_per_user(self):
        user_id = 999
        config.PER_USER_MAX_CONCURRENT = 2

        # First request
        async with limit_concurrency(user_id):
            self.assertEqual(_user_semaphores[user_id], 1)

            # Second request (same user)
            async with limit_concurrency(user_id):
                self.assertEqual(_user_semaphores[user_id], 2)

                # Third request should raise ConcurrencyLimitError
                with self.assertRaises(ConcurrencyLimitError):
                    async with limit_concurrency(user_id):
                        pass

        # After exiting, count should be 0 and key removed
        self.assertNotIn(user_id, _user_semaphores)

    async def test_concurrency_limiter_global(self):
        original_global_max = config.LLM_MAX_CONCURRENT
        config.LLM_MAX_CONCURRENT = 2
        # Allow users to make multiple requests
        config.PER_USER_MAX_CONCURRENT = 5

        try:
            # Initialize semaphore
            ai._global_sem = None

            entered = []

            async def worker(uid, idx):
                async with limit_concurrency(uid):
                    entered.append(idx)
                    await asyncio.sleep(0.1)

            # Start 3 workers for different users (to bypass per-user limit)
            task1 = asyncio.create_task(worker(1, 1))
            task2 = asyncio.create_task(worker(2, 2))
            task3 = asyncio.create_task(worker(3, 3))

            # Yield to let tasks run
            await asyncio.sleep(0.02)

            # Task 1 and 2 should have entered
            self.assertEqual(set(entered), {1, 2})

            # Finish tasks
            await asyncio.gather(task1, task2, task3)

            # Task 3 should have eventually entered after others finished
            self.assertEqual(set(entered), {1, 2, 3})

        finally:
            config.LLM_MAX_CONCURRENT = original_global_max
