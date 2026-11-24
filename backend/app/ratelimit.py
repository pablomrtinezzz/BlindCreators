"""Tiny in-process sliding-window limiter for expensive (AI) endpoints.

Good enough for a single API instance; swap for Redis if the API is ever scaled out.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.auth import CurrentUser
from app.config import Settings, get_settings

_hits: dict[int, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def ai_rate_limit(user: CurrentUser, settings: Settings = Depends(get_settings)) -> None:
    now = time.monotonic()
    with _lock:
        q = _hits[user.id]
        while q and now - q[0] > settings.ai_window_seconds:
            q.popleft()
        if len(q) >= settings.ai_requests_per_window:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many AI requests. Try again in a few minutes.",
            )
        q.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()
