import time
import threading
from functools import wraps

class RateLimitError(Exception):
    """Custom exception raised when the rate limit is exceeded."""
    pass

# Store call timestamps and locks per decorated function.
# The key will be the decorated function object.
# Value will be a dict: {'timestamps': list[float], 'lock': threading.Lock()}
_rate_limit_data = {}

def rate_limit(max_calls: int, period: float):
    """
    Decorator to limit the rate at which a function can be called.

    Args:
        max_calls: Maximum number of allowed calls within the period.
        period: Time window in seconds (float).

    Raises:
        RateLimitError: If the rate limit is exceeded.
    """
    def decorator(func):
        # Get or create the data entry for this function
        if func not in _rate_limit_data:
            _rate_limit_data[func] = {
                'timestamps': [],
                'lock': threading.Lock()
            }
        
        func_data = _rate_limit_data[func]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            with func_data['lock']:
                now = time.time()
                
                # Remove timestamps older than the period
                func_data['timestamps'] = [
                    ts for ts in func_data['timestamps'] if ts > now - period
                ]
                
                # Check if limit is exceeded
                if len(func_data['timestamps']) >= max_calls:
                    raise RateLimitError(f"Rate limit exceeded. Max calls: {max_calls} per {period}s.")
                
                # Record the current call
                func_data['timestamps'].append(now)
            
            # Execute the original function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
