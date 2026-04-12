import time
import threading

class RateLimitError(Exception):
    """Custom exception raised when the rate limit is exceeded."""
    pass

def rate_limit(max_calls: int, period: float):
    """
    Decorator to enforce a rate limit on function calls.

    Args:
        max_calls: Maximum number of allowed calls within the period.
        period: Time window in seconds (float).
    """
    if not isinstance(max_calls, int) or max_calls <= 0:
        raise ValueError("max_calls must be a positive integer")
    if not isinstance(period, (int, float)) or period <= 0:
        raise ValueError("period must be a positive number")

    def decorator(func):
        call_timestamps = []
        lock = threading.Lock()

        def wrapper(*args, **kwargs):
            with lock:
                current_time = time.time()
                # Remove timestamps older than the period
                nonlocal call_timestamps
                call_timestamps = [ts for ts in call_timestamps if ts > current_time - period]

                if len(call_timestamps) >= max_calls:
                    raise RateLimitError(f"Rate limit exceeded. Max calls: {max_calls}, Period: {period}s")

                call_timestamps.append(current_time)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
