"""Deterministic recorded LLM I/O, with no provider or fallback implementation."""

import hashlib
import json

from app.core.errors import ModelUnavailableError
from app.llm.base import LLMClient


def prompt_digest(system: str) -> str:
    return hashlib.sha256(system.encode('utf-8')).hexdigest()


class ReplayMismatchError(RuntimeError):
    pass


class RecordedLLM(LLMClient):
    def __init__(self, calls, *, allow_unverified_prompt=False, chunk_size=17):
        self.calls = list(calls)
        self.index = 0
        self.allow_unverified_prompt = allow_unverified_prompt
        self.prompt_verified = all(c.get('system_prompt_sha256') for c in self.calls)
        self.chunk_size = chunk_size
        if chunk_size < 1:
            raise ValueError('Positive replay chunk size required')

    def take(self, messages):
        if self.index >= len(self.calls):
            raise ReplayMismatchError('No recorded response; replay never calls a provider')
        call = self.calls[self.index]
        try:
            incoming = json.loads(messages[1].content)
        except (ValueError, IndexError) as exc:
            raise ReplayMismatchError('Request is not a recorded JSON payload') from exc
        canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        if call['task'] != messages[0].content.split('\n')[0] or canonical(call['input']) != canonical(incoming):
            raise ReplayMismatchError('Recorded task or input differs; record a new fixture explicitly')
        expected = call.get('system_prompt_sha256')
        if expected and expected != prompt_digest(messages[0].content):
            raise ReplayMismatchError('System prompt changed; old output cannot validate the new prompt')
        if not expected and not self.allow_unverified_prompt:
            raise ReplayMismatchError('Legacy trace has no prompt digest; explicit legacy replay is required')
        self.index += 1
        return call

    @staticmethod
    def check_error(call):
        if call.get('error_type'):
            if call['error_type'] == 'ModelUnavailableError':
                raise ModelUnavailableError()
            raise ReplayMismatchError('Unsupported recorded error type')

    async def complete(self, messages):
        call = self.take(messages)
        self.check_error(call)
        return call['output']

    async def stream(self, messages):
        call = self.take(messages)
        output = call['output']
        chunks = call.get('chunks')
        if chunks is None:
            # Synthetic boundaries for old traces are never reported as original timing.
            chunks = [output[i:i+self.chunk_size] for i in range(0, len(output), self.chunk_size)]
        if ''.join(chunks) != output:
            raise ReplayMismatchError('Recorded stream chunks do not match its output')
        for chunk in chunks:
            yield chunk
        self.check_error(call)

    def assert_exhausted(self):
        if self.index != len(self.calls):
            raise ReplayMismatchError('Recorded calls remain unused; workflow path changed')
