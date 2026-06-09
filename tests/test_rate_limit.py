import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_normal_request_passes_rate_limit(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_rate_limit_exceeded_returns_429(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.middleware.rate_limit as rl_mod
    import app.core.redis as redis_mod

    class CounterRedis:
        def __init__(self):
            self._count = 0

        async def get(self, key: str) -> str | None:
            return str(self._count)

        async def incr(self, key: str, amount: int) -> None:
            self._count += amount

        async def expire(self, key: str, time: int) -> None:
            pass

        def pipeline(self) -> "CounterRedis":
            return self

        async def execute(self) -> None:
            pass

    fake_redis = CounterRedis()
    monkeypatch.setattr(redis_mod, "redis_client", fake_redis)
    monkeypatch.setattr(rl_mod, "redis_client", fake_redis)
    monkeypatch.setattr(settings, "RATE_LIMIT_DEFAULT", 3)

    for _ in range(3):
        resp = await client.get("/")
        assert resp.status_code == 200

    resp = await client.get("/")
    assert resp.status_code == 429
    assert "Too many requests" in resp.json()["detail"]
