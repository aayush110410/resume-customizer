"""Tiny async LRU so identical inputs (same resume / JD / prompt version) don't re-hit free-tier LLMs."""

import hashlib
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any


def cache_key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


class AsyncLRU:
    def __init__(self, maxsize: int = 256):
        self.maxsize = maxsize
        self._data: OrderedDict[str, Any] = OrderedDict()

    async def get_or_compute(self, key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        value = await factory()  # failures propagate and are not cached
        self._data[key] = value
        if len(self._data) > self.maxsize:
            self._data.popitem(last=False)
        return value
