"""Fail closed on external HTTP/DNS during offline evaluation and pytest runs."""

import ipaddress
import json
import os
import socket
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import httpx


class OfflineNetworkError(RuntimeError):
    pass


def is_loopback(host):
    if isinstance(host, bytes):
        host = host.decode('ascii', errors='replace')
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


class OfflineGuard:
    """Allow local HTTP stream tests and mocked transports; deny remote traffic.

    This is a test guard for the project's HTTP/DNS clients, not an OS firewall.
    No URL path, query string, credentials, headers, or request bodies are logged.
    """
    def __init__(self):
        self.attempts = []
        self.stack = ExitStack()

    def check(self, host):
        if not is_loopback(host):
            self.attempts.append({'blocked': True})
            raise OfflineNetworkError('External network access is disabled in offline evaluation')

    def check_request(self, request):
        # Even a loopback proxy must not turn an offline run into paid inference.
        if request.url.path.rstrip('/').endswith('/chat/completions'):
            self.attempts.append({'blocked': True})
            raise OfflineNetworkError('Live model requests are disabled in offline evaluation')
        self.check(request.url.host)

    def __enter__(self):
        async_http = httpx.AsyncHTTPTransport.handle_async_request
        sync_http = httpx.HTTPTransport.handle_request
        resolve = socket.getaddrinfo
        connect = socket.socket.connect
        connect_ex = socket.socket.connect_ex
        guard = self

        async def guarded_async(transport, request):
            guard.check_request(request)
            return await async_http(transport, request)

        def guarded_sync(transport, request):
            guard.check_request(request)
            return sync_http(transport, request)

        def guarded_resolve(host, *args, **kwargs):
            guard.check(host)
            return resolve(host, *args, **kwargs)

        def guarded_connect(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                guard.check(address[0])
            return connect(sock, address)

        def guarded_connect_ex(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                guard.check(address[0])
            return connect_ex(sock, address)

        for target, value in [
            ('httpx.AsyncHTTPTransport.handle_async_request', guarded_async),
            ('httpx.HTTPTransport.handle_request', guarded_sync),
            ('socket.getaddrinfo', guarded_resolve),
            ('socket.socket.connect', guarded_connect),
            ('socket.socket.connect_ex', guarded_connect_ex),
        ]:
            self.stack.enter_context(patch(target, value))
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)


_pytest_guard = None


def pytest_sessionstart(session):
    global _pytest_guard
    _pytest_guard = OfflineGuard()
    _pytest_guard.__enter__()


def pytest_sessionfinish(session, exitstatus):
    if _pytest_guard is None:
        return
    _pytest_guard.__exit__(None, None, None)
    target = os.environ.get('LEGALMIND_OFFLINE_NETWORK_REPORT')
    if target:
        Path(target).write_text(json.dumps({'blocked_attempts': len(_pytest_guard.attempts)}), encoding='utf-8')
    if _pytest_guard.attempts:
        session.exitstatus = 1
