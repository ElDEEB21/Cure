from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.redis import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        if not settings.RATE_LIMIT_ENABLED or not redis_client:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"ratelimit:{client_ip}:{path}"

        current = await redis_client.get(key)
        if current is not None and int(current) >= settings.RATE_LIMIT_DEFAULT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"},
            )

        pipe = redis_client.pipeline()
        await pipe.incr(key, 1)
        await pipe.expire(key, 60)
        await pipe.execute()

        return await call_next(request)
