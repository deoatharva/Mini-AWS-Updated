from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 5 * 60


class LoginThrottle:
    """Small in-memory failure window for local sign-in endpoints.

    Keys never contain passwords. The process-local state is intentionally
    simple and resets when the local API restarts.
    """

    def __init__(
        self,
        *,
        max_failures: int = LOGIN_MAX_FAILURES,
        window_seconds: int = LOGIN_WINDOW_SECONDS,
    ) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _current(self, key: str) -> deque[float]:
        now = time.monotonic()
        values = self._failures[key]
        while values and now - values[0] > self.window_seconds:
            values.popleft()
        return values

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._current(key)) >= self.max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            values = self._current(key)
            values.append(time.monotonic())
            # Bound memory if many malformed or unknown identities are attempted.
            if len(self._failures) > 2000:
                self._failures.clear()
                self._failures[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_throttle = LoginThrottle()
