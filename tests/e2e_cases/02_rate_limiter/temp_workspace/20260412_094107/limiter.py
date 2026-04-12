
import time
import threading
from collections import deque

class RateLimitError(Exception):
    """Custom exception raised when the rate limit is exceeded."""
    pass

def rate_limit(max_calls: int, period: float):
    def decorator(func):
        calls = deque()
        lock = threading.Lock()

        def wrapper(*args, **kwargs):
            with lock:
                now = time.time()
                # Remove timestamps older than the period
                while calls and calls[0] <= now - period:
                    calls.popleft()

                # Check if the limit is exceeded
                if len(calls) >= max_calls:
                    raise RateLimitError(f"Rate limit exceeded. Maximum {max_calls} calls per {period} seconds.")

                # Record the current call time
                calls.append(now)

            # Call the original function outside the lock to avoid blocking
            # other threads unnecessarily if the function is slow.
            return func(*args, **kwargs)

        return wrapper
    return decorator
