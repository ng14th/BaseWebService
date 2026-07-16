from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, ClassVar

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.asynchronous.collection import AsyncCollection

from app.settings import settings


class MongoClientSingleton:
    """Async singleton pattern for AsyncIOMotorClient to reuse connections."""

    _instance: ClassVar["MongoClientSingleton" | None] = None
    _lock: ClassVar[asyncio.Lock | None] = None

    def __init__(self, uri: str | None = None, max_pool_size: int = 5) -> None:
        timeout_ms = settings.mongo_timeout_ms
        self._client = AsyncIOMotorClient(
            uri or settings.mongo_uri,
            maxPoolSize=max_pool_size,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms,
            socketTimeoutMS=timeout_ms,
            waitQueueTimeoutMS=timeout_ms,
        )

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    async def get_client(
        cls,
        uri: str | None = None,
        max_pool_size: int = 100,
    ) -> AsyncIOMotorClient:
        """Get or create AsyncIOMotorClient instance."""
        if cls._instance is None:
            async with cls._get_lock():
                if cls._instance is None:
                    cls._instance = cls(uri, max_pool_size)
        return cls._instance.client

    @classmethod
    def reset(cls) -> None:
        """Clear the cached instance so the next call creates a fresh client.

        Call this after an asyncio event loop is closed (e.g. in a Celery task
        via ``run_async``) to prevent Motor from reusing a client that is bound
        to a dead loop.
        """
        cls._instance = None
        cls._lock = None
        MongoSystemEventLogger.clear_collection_cache()

    @classmethod
    def close(cls) -> None:
        """Close the cached Mongo client and clear collection caches."""
        if cls._instance is not None:
            cls._instance.client.close()
        cls.reset()

    @property
    def client(self) -> AsyncIOMotorClient:
        """Return the shared Mongo client."""
        return self._client


class MongoSystemEventLogger:
    """System event logger backed by MongoDB."""

    _collections: ClassVar[OrderedDict[tuple[str, str], AsyncCollection]] = (
        OrderedDict()
    )

    @classmethod
    def clear_collection_cache(cls) -> None:
        cls._collections.clear()

    def __init__(self, table: str, body: Any | None = None) -> None:
        self.database = settings.mongo_db
        self.table = table
        self.body = body
        self.uri = settings.mongo_uri
        self._pool_size = settings.pool_size

    async def _get_client(self) -> AsyncIOMotorClient:
        return await MongoClientSingleton.get_client(self.uri, self._pool_size)

    async def _get_collection(self) -> AsyncCollection:
        """Get MongoDB collection using async singleton client."""
        cache_key = (self.database, self.table)
        collection = self._collections.get(cache_key)
        if collection is None:
            client = await self._get_client()
            collection = client[self.database][self.table]
            self._collections[cache_key] = collection  # type: ignore
        return collection  # type: ignore

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Any]:
        """Open a Mongo transaction and rollback on any exception."""
        client = await self._get_client()
        async with await client.start_session() as session, session.start_transaction():
            yield session

    async def get_connection(self) -> AsyncCollection:
        """Return the Mongo collection."""
        return await self._get_collection()

    @classmethod
    async def get_connection_by_table(cls, table: str) -> AsyncCollection:
        """Return a cached Mongo collection without constructing a logger body."""
        return await cls(table).get_connection()

    async def update_action(
        self,
        query_filter: dict[str, Any],
        value_update: dict[str, Any],
        session: Any | None = None,
    ) -> bool:
        """Update one document."""
        collection = await self._get_collection()
        result = await collection.update_one(
            query_filter,
            {"$set": value_update},
            session=session,
        )
        return result.modified_count == 1

    async def insert_action(self, session: Any | None = None) -> str:
        """Insert one document and return its id."""
        collection = await self._get_collection()
        _id = await collection.insert_one(self.body, session=session)
        return str(_id.inserted_id)

    async def insert_many_action(self, session: Any | None = None) -> Any:
        """Insert multiple documents."""
        collection = await self._get_collection()
        return await collection.insert_many(self.body, session=session)  # type: ignore

    async def find_one_action(
        self,
        filter: dict[str, Any],
        session: Any | None = None,
    ) -> dict[str, Any] | None:
        """Find one document."""
        collection = await self._get_collection()
        return await collection.find_one(filter, session=session)
