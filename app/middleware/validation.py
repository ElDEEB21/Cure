import json
import re

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

MAX_BODY_SIZE = 100 * 1024

SQL_INJECTION_PATTERNS = [
    re.compile(r"(\bSELECT\b.*\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bDROP\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bDELETE\b\s+\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bINSERT\b\s+\bINTO\b)", re.IGNORECASE),
    re.compile(r"(\bUPDATE\b\s+\w+\s+\bSET\b)", re.IGNORECASE),
    re.compile(r"(\bALTER\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bCREATE\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bEXEC\b|\bEXECUTE\b)", re.IGNORECASE),
    re.compile(r"(\bUNION\b\s+\bSELECT\b)", re.IGNORECASE),
    re.compile(r"(--|\bOR\b\s+\d+=\d+|\bAND\b\s+\d+=\d+)", re.IGNORECASE),
]

HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(value: str) -> str:
    return HTML_TAG_RE.sub("", value)


def contains_sql_injection(value: str) -> bool:
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(value):
            return True
    return False


def sanitize_value(value, path: str = "") -> tuple:
    if isinstance(value, str):
        if contains_sql_injection(value):
            return None, f"SQL injection pattern detected at {path}"
        return strip_html(value), None
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            sanitized, error = sanitize_value(v, f"{path}.{k}" if path else k)
            if error:
                return None, error
            result[k] = sanitized
        return result, None
    if isinstance(value, list):
        result = []
        for i, v in enumerate(value):
            sanitized, error = sanitize_value(v, f"{path}[{i}]")
            if error:
                return None, error
            result.append(sanitized)
        return result, None
    return value, None


class SanitizationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        if request.method in ("GET", "HEAD", "DELETE", "OPTIONS"):
            return await call_next(request)

        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            return JSONResponse(
                status_code=400,
                content={"detail": "Request body exceeds maximum size of 100KB"},
            )

        if not body:
            return await call_next(request)

        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return await call_next(request)

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return await call_next(request)

        sanitized, error = sanitize_value(parsed)
        if error:
            return JSONResponse(status_code=400, content={"detail": error})

        sanitized_body = json.dumps(sanitized).encode("utf-8")

        async def receive():
            return {"type": "http.request", "body": sanitized_body, "more_body": False}

        request._receive = receive
        return await call_next(request)
