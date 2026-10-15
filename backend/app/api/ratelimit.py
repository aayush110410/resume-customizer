import time
from collections import defaultdict, deque
from typing import Any

from app.api.errors import AppError

_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def client_key(request: Any) -> str:
    """Render's proxy appends the real client IP as the last X-Forwarded-For entry; earlier ones come from the client."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Per-client sliding window, e.g. "20/hour". In-memory: one process per Render instance."""

    def __init__(self, spec: str):
        count, unit = spec.split("/")
        self.limit, self.window = int(count), _UNITS[unit.strip().rstrip("s")]
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, now: float) -> None:
        for key in [k for k, hits in self._hits.items() if not hits or now - hits[-1] > self.window]:
            del self._hits[key]

    def check(self, request: Any) -> None:
        now = time.monotonic()
        self._prune(now)
        hits = self._hits[client_key(request)]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            raise AppError("RATE_LIMITED", "Too many requests; please try again later.", 429, retryable=True)
        hits.append(now)
