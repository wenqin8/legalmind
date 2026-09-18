"""Redis-only runtime history, fenced locks and atomic message-pair writes."""

import math
import time
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from app.core.errors import AppError

HISTORY_TTL = 86400
HISTORY_EXPIRED_WARNING = "历史内容已过期或尚未保存，待补任务与确认摘要也已过期，请重新补充；本次咨询将从空上下文开始。"


class SessionStoreUnavailable(AppError):
    def __init__(self):
        super().__init__(status_code=503, code="SESSION_STORE_UNAVAILABLE", message="会话存储暂时不可用，请稍后重试")


class SessionBusy(AppError):
    def __init__(self):
        super().__init__(status_code=409, code="SESSION_BUSY", message="该咨询正在处理中，请稍后重试")


@dataclass(frozen=True)
class HistorySnapshot:
    messages: list[str]
    expires_at: float | None


def history_key(user_id: UUID, session_id: UUID) -> str:
    return f"conversation:{user_id}:{session_id}:messages"


class SessionStore(Protocol):
    async def acquire(self, key: str, seconds: float) -> str: ...
    async def release(self, key: str, token: str) -> None: ...
    async def snapshot(self, key: str, token: str) -> HistorySnapshot: ...
    async def append_pair(self, key: str, token: str, messages: list[str]) -> None: ...
    async def restore(self, key: str, token: str, snapshot: HistorySnapshot) -> None: ...
    async def delete(self, key: str, token: str) -> None: ...
    async def exists_many(self, keys: list[str]) -> list[bool]: ...
    async def aclose(self) -> None: ...


FENCE = "if redis.call('GET', KEYS[2]) ~= ARGV[1] then return redis.error_reply('LOCK_LOST') end\n"
SNAPSHOT = FENCE + "return {redis.call('LRANGE', KEYS[1], 0, -1), redis.call('PTTL', KEYS[1])}"
APPEND = FENCE + """
redis.call('RPUSH', KEYS[1], ARGV[2], ARGV[3])
redis.call('LTRIM', KEYS[1], -20, -1)
redis.call('EXPIRE', KEYS[1], 86400)
return 1
"""
RESTORE = FENCE + """
redis.call('DEL', KEYS[1])
local ttl = tonumber(ARGV[2])
if ttl > 0 and #ARGV > 2 then
  for i = 3, #ARGV do redis.call('RPUSH', KEYS[1], ARGV[i]) end
  redis.call('PEXPIRE', KEYS[1], ttl)
end
return 1
"""


class RedisSessionStore:
    def __init__(self, url: str):
        self.client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2, retry=Retry(NoBackoff(), 0))

    async def _eval(self, script: str, key: str, token: str, *args):
        try:
            return await self.client.eval(script, 2, key, key + ":lock", token, *args)
        except (RedisError, ValueError, OSError) as exc:
            raise SessionStoreUnavailable() from exc

    async def acquire(self, key: str, seconds: float) -> str:
        token = uuid4().hex
        try:
            acquired = await self.client.set(key + ":lock", token, nx=True, ex=math.ceil(seconds))
        except (RedisError, ValueError, OSError) as exc:
            raise SessionStoreUnavailable() from exc
        if not acquired:
            raise SessionBusy()
        return token

    async def release(self, key: str, token: str) -> None:
        await self._eval("if redis.call('GET', KEYS[2]) == ARGV[1] then return redis.call('DEL', KEYS[2]) end return 0", key, token)

    async def snapshot(self, key: str, token: str) -> HistorySnapshot:
        rows, ttl = await self._eval(SNAPSHOT, key, token)
        if rows and (ttl <= 0 or len(rows) % 2):
            raise SessionStoreUnavailable()
        return HistorySnapshot(rows, time.monotonic() + ttl / 1000 if ttl > 0 else None)

    async def append_pair(self, key: str, token: str, messages: list[str]) -> None:
        if len(messages) != 2:
            raise ValueError("A complete user/assistant pair is required")
        await self._eval(APPEND, key, token, *messages)

    async def restore(self, key: str, token: str, snapshot: HistorySnapshot) -> None:
        ttl = max(0, int(((snapshot.expires_at or 0) - time.monotonic()) * 1000))
        await self._eval(RESTORE, key, token, ttl, *snapshot.messages)

    async def delete(self, key: str, token: str) -> None:
        await self._eval(FENCE + "return redis.call('DEL', KEYS[1])", key, token)

    async def exists_many(self, keys: list[str]) -> list[bool]:
        if not keys:
            return []
        try:
            async with self.client.pipeline(transaction=False) as pipeline:
                for key in keys:
                    pipeline.exists(key)
                return [bool(value) for value in await pipeline.execute()]
        except (RedisError, ValueError, OSError) as exc:
            raise SessionStoreUnavailable() from exc

    async def aclose(self) -> None:
        await self.client.aclose()
