import time
from collections import defaultdict, deque

from fastapi import Request

from app.api.errors import AppError

_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


class RateLimiter:
    """Per-client sliding window, e.g. "20/hour". In-memory: one process per Render instance."""

    def __init__(self, spec: str):
        count, unit = spec.split("/")
        self.limit, self.window = int(count), _UNITS[unit.strip().rstrip("s")]
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now, hits = time.monotonic(), self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            raise AppError("RATE_LIMITED", "Too many requests; please try again later.", 429, retryable=True)
        hits.append(now)
