"""Clock-controlled test double. Never imported by production code."""

import time
from uuid import uuid4

from app.services.session_store import HistorySnapshot, SessionBusy, SessionStoreUnavailable


class FakeSessionStore:
    def __init__(self):
        self.rows: dict[str, HistorySnapshot] = {}
        self.locks: dict[str, str] = {}
        self.available = True

    def check(self, key=None, token=None):
        if not self.available or (token and self.locks.get(key) != token):
            raise SessionStoreUnavailable()

    async def acquire(self, key, seconds):
        self.check()
        if key in self.locks:
            raise SessionBusy()
        token = uuid4().hex
        self.locks[key] = token
        return token

    async def release(self, key, token):
        self.check()
        if self.locks.get(key) == token:
            del self.locks[key]

    async def snapshot(self, key, token):
        self.check(key, token)
        row = self.rows.get(key, HistorySnapshot([], None))
        return row if row.expires_at and row.expires_at > time.monotonic() else HistorySnapshot([], None)

    async def append_pair(self, key, token, messages):
        old = await self.snapshot(key, token)
        self.rows[key] = HistorySnapshot((old.messages + messages)[-20:], time.monotonic() + 86400)

    async def restore(self, key, token, snapshot):
        self.check(key, token)
        if snapshot.messages:
            self.rows[key] = snapshot
        else:
            self.rows.pop(key, None)

    async def delete(self, key, token):
        self.check(key, token)
        self.rows.pop(key, None)

    async def exists_many(self, keys):
        self.check()
        return [bool(self.rows.get(key) and (self.rows[key].expires_at or 0) > time.monotonic()) for key in keys]

    async def aclose(self):
        pass
