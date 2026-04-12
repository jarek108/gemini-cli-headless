
import time
import threading
import unittest
from limiter import rate_limit, RateLimitError

class TestRateLimiter(unittest.TestCase):
    def test_basic_limit(self):
        @rate_limit(max_calls=2, period=0.5)
        def limited_func():
            return True

        self.assertTrue(limited_func())
        self.assertTrue(limited_func())
        with self.assertRaises(RateLimitError):
            limited_func()

    def test_reset_after_period(self):
        @rate_limit(max_calls=1, period=0.1)
        def limited_func():
            return True

        self.assertTrue(limited_func())
        with self.assertRaises(RateLimitError):
            limited_func()
        
        time.sleep(0.15)
        self.assertTrue(limited_func())

    def test_thread_safety(self):
        max_calls = 50
        period = 1.0
        
        @rate_limit(max_calls=max_calls, period=period)
        def limited_func():
            return True

        results = []
        errors = []

        def worker():
            try:
                if limited_func():
                    results.append(1)
            except RateLimitError:
                errors.append(1)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), max_calls)
        self.assertEqual(len(errors), 100 - max_calls)

    def test_slow_function_concurrency(self):
        # Verify that slow functions don't block the rate limiter logic for other threads
        entry_times = []
        @rate_limit(max_calls=10, period=1.0)
        def slow_func():
            entry_times.append(time.time())
            time.sleep(0.2)
            return True

        t1 = threading.Thread(target=slow_func)
        t2 = threading.Thread(target=slow_func)
        
        t1.start()
        time.sleep(0.05)
        t2.start()
        
        t1.join()
        t2.join()
        
        # t2 should have entered almost immediately after t1 started (approx 0.05s delay we added),
        # not waiting 0.2s for t1 to finish.
        self.assertLess(entry_times[1] - entry_times[0], 0.1)

if __name__ == "__main__":
    unittest.main()
