"""
middleware/latency.py — Request timing middleware.

Times every request wall-clock and logs:
    {endpoint, company_id (if in path), response_time_ms, tag, status_code}
into the query_logs table.
"""

import time
import re
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import text

log = logging.getLogger(__name__)

# Regex to extract company_id UUID from paths like /companies/{uuid}/risk
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


class LatencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Records wall-clock time for every HTTP request
    2. Inserts a row into query_logs (fire-and-forget, non-blocking path)
    3. Adds X-Response-Time header to every response for frontend display
    """

    def __init__(self, app, db_engine, tag: str = "live"):
        super().__init__(app)
        self.engine = db_engine
        self.tag = tag

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)

        # Add timing header
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        # Extract company_id from path if present
        path = request.url.path
        match = UUID_RE.search(path)
        company_id = match.group() if match else None

        # Skip health/docs/static endpoints
        if any(path.startswith(p) for p in ["/docs", "/redoc", "/openapi", "/health"]):
            return response

        # Async log to DB (best-effort — don't fail the request if logging fails)
        try:
            self._log_query(
                endpoint       = path,
                company_id     = company_id,
                response_time  = elapsed_ms,
                status_code    = response.status_code,
                tag            = self.tag,
            )
        except Exception as exc:
            log.warning(f"Latency logging failed (non-fatal): {exc}")

        return response

    def _log_query(
        self,
        endpoint: str,
        company_id: str | None,
        response_time: float,
        status_code: int,
        tag: str,
    ) -> None:
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO query_logs
                        (endpoint, company_id, response_time_ms, status_code, tag)
                    VALUES
                        (:endpoint, CAST(:company_id AS uuid), :response_time_ms, :status_code, :tag)
                """),
                {
                    "endpoint":        endpoint,
                    "company_id":      company_id,
                    "response_time_ms": response_time,
                    "status_code":     status_code,
                    "tag":             tag,
                },
            )
            conn.commit()