import time
import threading
import unittest
from limiter import rate_limit, RateLimitError

class TestRateLimiter(unittest.TestCase):

    def test_basic_limit(self):
        @rate_limit(max_calls=3, period=1.0)
        def my_func():
            return True

        # First 3 calls should succeed
        for _ in range(3):
            self.assertTrue(my_func())
        
        # 4th call should fail
        with self.assertRaises(RateLimitError):
            my_func()

    def test_time_window_reset(self):
        @rate_limit(max_calls=2, period=0.5)
        def my_func():
            return True

        self.assertTrue(my_func())
        self.assertTrue(my_func())
        
        with self.assertRaises(RateLimitError):
            my_func()
            
        # Wait for period to expire
        time.sleep(0.6)
        
        # Should succeed again
        self.assertTrue(my_func())

    def test_thread_safety(self):
        max_calls = 50
        period = 2.0
        
        @rate_limit(max_calls=max_calls, period=period)
        def my_func():
            return True

        results = []
        errors = []

        def worker():
            try:
                if my_func():
                    results.append(1)
            except RateLimitError:
                errors.append(1)

        threads = []
        # Spawn more threads than max_calls
        num_threads = 100
        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(results), max_calls)
        self.assertEqual(len(errors), num_threads - max_calls)

    def test_independent_limits(self):
        @rate_limit(max_calls=2, period=1.0)
        def func_a():
            return "A"

        @rate_limit(max_calls=5, period=1.0)
        def func_b():
            return "B"

        # func_a hits limit
        self.assertEqual(func_a(), "A")
        self.assertEqual(func_a(), "A")
        with self.assertRaises(RateLimitError):
            func_a()

        # func_b should still be fine
        for _ in range(5):
            self.assertEqual(func_b(), "B")
        with self.assertRaises(RateLimitError):
            func_b()

    def test_metadata_preservation(self):
        @rate_limit(max_calls=1, period=1.0)
        def my_documented_func():
            """This is a docstring."""
            return True

        self.assertEqual(my_documented_func.__name__, "my_documented_func")
        self.assertEqual(my_documented_func.__doc__, "This is a docstring.")

if __name__ == '__main__':
    unittest.main()
