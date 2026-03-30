"""
middleware/usage_logger.py
===========================
FastAPI middleware for request-level logging.

CURRENT:  Logs every request with method, path, status, duration.
FUTURE:   Add per-user request counting for analytics dashboard.
"""

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000)

        # Don't log health checks — too noisy
        if request.url.path not in ("/health", "/favicon.ico"):
            log.info(
                f"{request.method} {request.url.path} "
                f"→ {response.status_code} ({duration}ms)"
            )

        return response
