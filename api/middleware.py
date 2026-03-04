"""Middleware for rate limiting, error handling, and request logging."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

logger = logging.getLogger("dou.api.middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per client IP.

    Uses a sliding window counter. For production, replace with
    Redis-backed rate limiting via slowapi.
    """

    def __init__(self, app, rpm: int = 120):
        super().__init__(app)
        self.rpm = rpm
        self.window = 60  # seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window

        # prune old entries
        self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
        self._hits[ip].append(now)

        return len(self._hits[ip]) > self.rpm

    async def dispatch(self, request: Request, call_next):
        # skip rate limiting for static files
        if request.url.path.startswith(("/static", "/favicon")):
            return await call_next(request)

        ip = self._get_client_ip(request)

        if self._is_rate_limited(ip):
            logger.warning("Rate limit exceeded for %s", ip)
            return Response(
                content='{"error": "rate limit exceeded", "retry_after": 60}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        # log slow requests
        if duration > 5.0:
            logger.warning(
                "Slow request: %s %s took %.2fs",
                request.method, request.url.path, duration,
            )

        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return clean JSON errors."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except ConnectionError as exc:
            logger.error("Gateway connection error: %s", exc)
            return Response(
                content='{"error": "douyin API unreachable", "detail": "all endpoints exhausted"}',
                status_code=502,
                media_type="application/json",
            )
        except Exception as exc:
            logger.exception("Unhandled error: %s", exc)
            return Response(
                content='{"error": "internal server error"}',
                status_code=500,
                media_type="application/json",
            )
