import secrets
from typing import Optional

from redis.asyncio import Redis


class CallbackStorage:
    def __init__(self, prefix: str = "cb:", ttl_days: int = 1):
        self.redis = Redis(host='localhost', port=6379, db=0)
        self.prefix = prefix
        self.ttl_seconds = ttl_days * 86400

    async def store(self, payload: str) -> str:
        key = secrets.token_urlsafe(6)
        full_key = f"{self.prefix}{key}"
        await self.redis.set(full_key, payload, ex=self.ttl_seconds)
        return full_key


    async def get(self, key: str) -> Optional[str]:
        value = await self.redis.get(key)
        if value is None:
            return None
        return value.decode('utf-8')

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    def get_prefix(self) -> str:
        return self.prefix

callback_storage = CallbackStorage()
