"""Request correlation IDs and structured (JSON) access logs.

- Every response carries X-Request-ID. A caller-supplied X-Request-ID is reused only when it is
  1-64 characters of letters, digits, '-' or '_'; otherwise a new UUID is issued. This lets a
  client, the gateway and the API logs be joined without trusting arbitrary header content.
- One JSON log line per request on the "stn.access" logger: time, request_id, method, the route
  TEMPLATE (e.g. /v1/clients/{client_id}, never the concrete path), status and duration. No query
  strings, bodies, tokens, subjects or client identifiers are logged.
- Unhandled exceptions return a generic 500 {"detail", "request_id"} and log only the exception
  class, so no record content reaches the logs or the caller.
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

HEADER = "X-Request-ID"
_SAFE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
access_log = logging.getLogger("stn.access")
error_log = logging.getLogger("stn.error")


def request_id_for(request: Request) -> str:
    incoming = request.headers.get(HEADER, "")
    return incoming if _SAFE.match(incoming) else str(uuid.uuid4())


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


async def middleware(request: Request, call_next):
    rid = request_id_for(request)
    request.state.request_id = rid
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # last-resort handler: no detail leaves the process
        error_log.error(json.dumps({"event": "unhandled_exception", "request_id": rid,
                                    "exception": type(exc).__name__, "route": _route_template(request)}))
        response = JSONResponse({"detail": "Internal server error.", "request_id": rid}, status_code=500)
    response.headers[HEADER] = rid
    access_log.info(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(), "request_id": rid, "method": request.method,
        "route": _route_template(request), "status": response.status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }, separators=(",", ":")))
    return response
