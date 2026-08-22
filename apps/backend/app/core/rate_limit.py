"""Small process-local rate limiter for authentication abuse protection."""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from math import ceil
from threading import Lock


class InMemoryRateLimiter:
    """Thread-safe sliding-window limiter for a single application process."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> int | None:
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if not attempts:
                del self._attempts[key]
            if len(attempts) >= limit:
                return max(1, ceil(attempts[0] + window_seconds - now))
            attempts.append(now)
            self._attempts[key] = attempts
            return None

    def reset(self) -> None:
        """Clear process-local state, primarily for isolated regression tests."""
        with self._lock:
            self._attempts.clear()
