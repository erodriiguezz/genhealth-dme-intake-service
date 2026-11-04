import time
from collections import defaultdict, deque

from fastapi import Request

from app.errors import ApiError


class RateLimiter:
    """In-memory sliding window, per process. Resets on deploy (Redis is backlog B8)."""

    def __init__(self, limit: int, window_s: float = 60.0):
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> int | None:
        """Record a hit. Returns None if allowed, else seconds until the next slot."""
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window_s:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1, int(self.window_s - (now - hits[0])) + 1)
        hits.append(now)
        return None


def client_ip(request: Request) -> str:
    # The rightmost X-Forwarded-For entry is the one our own proxy appended.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def auth_rate_limit(request: Request) -> None:
    retry_after = request.app.state.auth_limiter.check(client_ip(request))
    if retry_after is not None:
        raise ApiError(
            429,
            "rate_limited",
            "Too many attempts. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
