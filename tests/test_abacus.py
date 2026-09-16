import asyncio
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from abacus.main import app
from abacus.settings import get_settings


@pytest.fixture
async def client(tmp_path) -> AsyncIterator[AsyncClient]:
    get_settings.cache_clear()
    db_path = tmp_path / "abacus.db"
    import os

    os.environ["ABACUS_STORE"] = "sqlite"
    os.environ["ABACUS_SQLITE_PATH"] = str(db_path)
    os.environ["ABACUS_NODE_NAME"] = "test-node"
    get_settings.cache_clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_add_get_reset(client: AsyncClient) -> None:
    reset = await client.delete("/abacus/sum")
    assert reset.status_code == 200
    assert reset.json()["sum"] == 0

    first = await client.post("/abacus/number", json={"number": 5})
    assert first.status_code == 200
    assert first.json()["sum"] == 5

    second = await client.post("/abacus/number", json={"number": 7})
    assert second.json()["sum"] == 12

    current = await client.get("/abacus/sum")
    assert current.json()["sum"] == 12

    reset = await client.delete("/abacus/sum")
    assert reset.json()["sum"] == 0
    current = await client.get("/abacus/sum")
    assert current.json()["sum"] == 0


@pytest.mark.asyncio
async def test_negative_and_float(client: AsyncClient) -> None:
    await client.delete("/abacus/sum")
    await client.post("/abacus/number", json={"number": 1.5})
    await client.post("/abacus/number", json={"number": -0.5})
    current = await client.get("/abacus/sum")
    assert current.json()["sum"] == 1.0


@pytest.mark.asyncio
async def test_concurrent_adds(client: AsyncClient) -> None:
    await client.delete("/abacus/sum")
    count = 100
    results = await asyncio.gather(
        *[client.post("/abacus/number", json={"number": 1}) for _ in range(count)]
    )
    assert all(r.status_code == 200 for r in results)
    current = await client.get("/abacus/sum")
    assert current.json()["sum"] == count
