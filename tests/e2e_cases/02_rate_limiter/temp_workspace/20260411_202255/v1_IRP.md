# Implementation Report

## Summary of Changes

Implemented a thread-safe rate limiter decorator (`@rate_limit`) and a custom exception (`RateLimitError`) in Python. The decorator enforces a maximum number of calls within a specified period, using `threading.Lock` to ensure thread safety.

## List of Modified Files

- `limiter.py`