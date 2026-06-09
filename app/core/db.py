from typing import Optional

from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.asynchronous.database import AsyncDatabase

from app.core.settings import settings


class MongoConnection:
    """Process-local singleton for AsyncMongoClient + AsyncDatabase."""

    _instance: Optional["MongoConnection"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
            cls._instance._db = None
        return cls._instance

    async def connect(self) -> None:
        """Create the client and validate connectivity with a ping."""
        if self._client is not None:
            return
        print("Establishing MongoDB connection")
        try:
            self._client = AsyncMongoClient(
                settings.db_host,  # e.g. "mongodb://user:pass@host:27017/?authSource=admin"
                serverSelectionTimeoutMS=settings.db_timeout,  # e.g. 5000
                uuidRepresentation="standard",
            )
            # Validate connection (constructor is non-blocking)
            await self._client.admin.command("ping")
            self._db = self._client[settings.db_name]
            print("Connected to MongoDB successfully")
        except Exception:
            print("Connecting to MongoDB failed")
            await self.close()
            raise

    async def close(self) -> None:
        print("Closing MongoDB connection")
        if self._client is not None:
            await self._client.close()
        self._client = None
        self._db = None
        print("MongoDB disconnected successfully")

    async def get_client(self) -> AsyncMongoClient:
        if self._client is None:
            await self.connect()
        if self._client is None:
            raise RuntimeError("Failed to establish MongoDB connection")
        return self._client

    async def get_db(self) -> AsyncDatabase:
        if self._db is None:
            await self.connect()
        if self._db is None:
            raise RuntimeError("Failed to establish MongoDB connection")
        return self._db


# Global singleton
mongo_connection = MongoConnection()


# FastAPI dependencies
async def get_db() -> AsyncDatabase:
    return await mongo_connection.get_db()


async def get_client() -> AsyncMongoClient:
    return await mongo_connection.get_client()


async def db_health_check() -> bool:
    """Check if the database connection is alive (ping)."""
    try:
        db = await get_db()
        result = await db.command("ping")
        return result.get("ok", 0) == 1
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"MongoDB health check timeout/connection failure: {e}")
        return False
    except Exception as e:
        print(f"MongoDB health check failed: {e}")
        return False
