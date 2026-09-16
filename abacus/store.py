from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import aiosqlite
from redis.asyncio import Redis

from abacus.settings import Settings


def as_json_number(value: float | int) -> int | float:
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


class SumStore(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def add(self, amount: float) -> float: ...

    @abstractmethod
    async def get(self) -> float: ...

    @abstractmethod
    async def reset(self) -> float: ...


class SQLiteSumStore(SumStore):
    """Process-safe, strongly consistent sum via a shared SQLite file.

    Each write uses its own connection and BEGIN IMMEDIATE so concurrent
    POSTs from many nodes serialize on the database lock. WAL + FULL sync
    keeps durability without sacrificing a single linearizable sum.
    """

    def __init__(self, path: str) -> None:
        self._path = Path(path)

    async def _open(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self._path)
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=FULL")
        await db.execute("PRAGMA busy_timeout=10000")
        return db

    async def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        db = await self._open()
        try:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS abacus (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    value REAL NOT NULL
                )
                """
            )
            await db.execute(
                "INSERT OR IGNORE INTO abacus (id, value) VALUES (1, 0)"
            )
            await db.commit()
        finally:
            await db.close()

    async def close(self) -> None:
        return

    async def add(self, amount: float) -> float:
        db = await self._open()
        try:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "UPDATE abacus SET value = value + ? WHERE id = 1 RETURNING value",
                (float(amount),),
            )
            row = await cursor.fetchone()
            await db.commit()
            assert row is not None
            return float(row[0])
        finally:
            await db.close()

    async def get(self) -> float:
        db = await self._open()
        try:
            cursor = await db.execute("SELECT value FROM abacus WHERE id = 1")
            row = await cursor.fetchone()
            return float(row[0]) if row else 0.0
        finally:
            await db.close()

    async def reset(self) -> float:
        db = await self._open()
        try:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute("UPDATE abacus SET value = 0 WHERE id = 1")
            await db.commit()
            return 0.0
        finally:
            await db.close()


class RedisSumStore(SumStore):
    """Linearizable sum on a single Redis primary.

    INCRBY / INCRBYFLOAT / GET / SET are each atomic. Redis executes
    commands single-threaded on one shard, so mixed add/get/reset from
    N API nodes observe one monotonically consistent sum.
    """

    def __init__(self, url: str, key: str) -> None:
        self._url = url
        self._key = key
        self._redis: Redis | None = None

    async def connect(self) -> None:
        self._redis = Redis.from_url(self._url, decode_responses=True)
        await self._redis.ping()

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    def _client(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("Redis store is not connected")
        return self._redis

    async def add(self, amount: float) -> float:
        client = self._client()
        if float(amount).is_integer():
            value = await client.incrby(self._key, int(amount))
            return float(value)
        value = await client.incrbyfloat(self._key, float(amount))
        return float(value)

    async def get(self) -> float:
        raw = await self._client().get(self._key)
        if raw is None:
            return 0.0
        return float(raw)

    async def reset(self) -> float:
        await self._client().set(self._key, 0)
        return 0.0


def build_store(settings: Settings) -> SumStore:
    if settings.store == "redis":
        return RedisSumStore(settings.redis_url, settings.redis_key)
    return SQLiteSumStore(settings.sqlite_path)
