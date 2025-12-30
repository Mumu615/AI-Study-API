from redis import asyncio as aioredis
from typing import Optional
from .database import settings

class RedisClient:
    _instance: Optional[aioredis.Redis] = None

    @classmethod
    def get_instance(cls) -> aioredis.Redis:
        if cls._instance is None:
            # Initialize Redis connection
            cls._instance = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                username=settings.REDIS_USERNAME if settings.REDIS_USERNAME else None,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                decode_responses=True  # Automatically decode bytes to strings
            )
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None

# Dependency for FastAPI
async def get_redis() -> aioredis.Redis:
    return RedisClient.get_instance()
