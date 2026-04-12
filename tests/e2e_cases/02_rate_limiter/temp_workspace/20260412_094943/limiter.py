
import time
import threading
from typing import Callable, Any

class RateLimitError(Exception):
    """Custom exception for rate limiting exceeded."""
    pass

def rate_limit(max_calls: int, period: float) -> Callable:
    """Decorator to limit the rate of function calls.

    Args:
        max_calls: Maximum number of allowed calls within the period.
        period: Time window in seconds (float).

    Returns:
        The decorator function.
    """
    def decorator(func: Callable) -> Callable:
        calls: list[float] = []
        lock = threading.Lock()

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with lock:
                now = time.time()
                # Remove timestamps older than the period
                nonlocal calls
                calls = [t for t in calls if now - t < period]

                if len(calls) >= max_calls:
                    raise RateLimitError(f"Rate limit exceeded. Maximum {max_calls} calls per {period} seconds allowed.")
                
                calls.append(now)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
