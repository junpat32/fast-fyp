"""Per-user rate limit (T-13): a sliding window kept in memory.

Algorithm: for each user keep the times of their requests in the last `window` seconds (a queue).
On a request, drop times older than the window; if `limit` remain, refuse with the seconds until
the oldest one expires; otherwise record the request. O(1) amortised per request (each time is
added and removed once), memory O(limit) per active user.

Production vs coursework: one in-memory window per process is right for a single Render
instance. With several instances each would count separately, so limits would need a shared
store (e.g. Redis); idle users' queues are also only dropped on their next request.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window: float = 60.0, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> float | None:
        """None if the request is allowed (and counted), else the seconds to wait."""
        now = self.clock()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return self.window - (now - q[0])
            q.append(now)
            return None
