"""Request trace_id middleware (E-00-S07, TDS-010 §14)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

TRACE_HEADER = "X-Trace-Id"
_log = logging.getLogger(__name__)


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Generate or accept trace_id; attach to logs and response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(TRACE_HEADER)
        trace_id = (
            incoming.strip() if incoming and incoming.strip() else str(uuid.uuid4())
        )
        request.state.trace_id = trace_id

        _log.info(
            "request_started",
            extra={"trace_id": trace_id},
        )
        response = await call_next(request)
        response.headers[TRACE_HEADER] = trace_id
        _log.info(
            "request_completed",
            extra={"trace_id": trace_id},
        )
        return response
