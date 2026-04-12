# Task: Thread-Safe Rate Limiter

Your goal is to implement a robust, thread-safe rate limiter decorator in Python.

### Requirements:
1.  Create a decorator named `@rate_limit(max_calls, period)`.
2.  `max_calls`: Maximum number of allowed calls within the `period`.
3.  `period`: Time window in seconds (float).
4.  **Thread Safety**: The implementation must be 100% safe for concurrent access from multiple threads. Use `threading.Lock` where necessary to prevent race conditions when updating call history or counters.
5.  **Behavior**: If the limit is exceeded, the decorator must raise a custom exception named `RateLimitError` (which you must also define).
6.  The code should be placed in a file named `limiter.py`.

### Definition of Done:
- `limiter.py` contains the exception class and the decorator.
- The implementation is thread-safe.
- All required parameters are handled correctly.
- An Implementation Report (`vN_IRP.md`) is produced.
