"""Bounded per-client rate limiting for the single-worker local deployment."""

from collections import OrderedDict
from time import monotonic
from math import ceil

from starlette.requests import Request
from starlette.types import ASGIApp, Scope, Receive, Send

from app.core.errors import error_response


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, *, auth_limit: int, business_limit: int, window_seconds: int = 60):
        self.app = app
        self.auth_limit = auth_limit
        self.business_limit = business_limit
        self.window_seconds = window_seconds
        self.clients: OrderedDict[tuple[str, str], tuple[float, int]] = OrderedDict()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http' or scope['method'] == 'OPTIONS' or not scope['path'].startswith('/api/v1/') or scope['path'] == '/api/v1/health':
            await self.app(scope, receive, send)
            return
        group = 'auth' if scope['path'] in {'/api/v1/auth/login', '/api/v1/auth/register'} else 'business'
        limit = self.auth_limit if group == 'auth' else self.business_limit
        client = (scope.get('client') or ('unknown', 0))[0]
        key = (client, group)
        now = monotonic()
        # Fixed windows and a bounded LRU prevent unbounded client storage.
        start, count = self.clients.get(key, (now, 0))
        if now - start >= self.window_seconds:
            start, count = now, 0
        self.clients[key] = (start, count + 1)
        self.clients.move_to_end(key)
        while len(self.clients) > 4096:
            self.clients.popitem(last=False)
        if count >= limit:
            response = error_response(Request(scope), status_code=429, code='RATE_LIMITED',
                message='请求过于频繁，请稍后再试', headers={'Retry-After': str(max(1, ceil(self.window_seconds - (now - start))))})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
