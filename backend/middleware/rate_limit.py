"""
Port of the express-rate-limit usage in routes/exhibitors.js, routes/
visitors.js, and routes/admin.js. A small self-contained fixed-window
limiter (no extra dependency needed) keyed by client IP — good enough for
this app's actual need (slowing down registration/login abuse), same as the
original's windowMs/max/message config.

FastAPI dependency usage:
    Depends(rate_limit("register-exhibitor", max_requests=10, window_seconds=15*60,
                        message="Too many registration attempts. Please try again later."))
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# bucket_key -> deque of request timestamps (monotonic seconds) within the
# current window. Process-local — fine for a single-instance deployment;
# for multi-instance deployments behind a load balancer, swap this for a
# Redis-backed limiter.
_buckets: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, *, max_requests: int, window_seconds: int, message: str):
    async def _dep(request: Request):
        key = f"{name}:{_client_ip(request)}"
        now = time.monotonic()
        bucket = _buckets[key]

        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()

        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail=message)

        bucket.append(now)

    return _dep
