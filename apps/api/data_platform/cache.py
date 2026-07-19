from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class CacheStats:
    entries: int
    bytes: int
    hits: int
    misses: int
    evictions: int


@dataclass
class _Entry:
    value: Any
    expires_at: float
    size: int


class VersionedResultCache:
    """Bounded in-process TTL/LRU cache for compact dashboard responses.

    Callers include the immutable release key in every key. Publication therefore
    invalidates results by construction, while TTL and LRU bounds prevent large
    analytical responses from consuming unbounded API memory.
    """

    def __init__(self, *, ttl_seconds: int, max_entries: int, max_bytes: int) -> None:
        self.ttl_seconds = max(0, ttl_seconds)
        self.max_entries = max(0, max_entries)
        self.max_bytes = max(0, max_bytes)
        self._items: OrderedDict[str, _Entry] = OrderedDict()
        self._bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at <= now:
                self._remove(key)
                self._misses += 1
                return None
            self._items.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any) -> None:
        if self.ttl_seconds == 0 or self.max_entries == 0 or self.max_bytes == 0:
            return
        encoded = json.dumps(value, default=str, separators=(",", ":")).encode("utf-8")
        size = len(encoded)
        if size > self.max_bytes:
            return
        with self._lock:
            if key in self._items:
                self._remove(key)
            self._items[key] = _Entry(
                value=value,
                expires_at=time.monotonic() + self.ttl_seconds,
                size=size,
            )
            self._bytes += size
            while len(self._items) > self.max_entries or self._bytes > self.max_bytes:
                oldest, _entry = self._items.popitem(last=False)
                self._bytes -= _entry.size
                self._evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._bytes = 0

    def stats(self) -> CacheStats:
        with self._lock:
            self._prune_expired()
            return CacheStats(
                entries=len(self._items),
                bytes=self._bytes,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
            )

    def _prune_expired(self) -> None:
        now = time.monotonic()
        expired = [key for key, entry in self._items.items() if entry.expires_at <= now]
        for key in expired:
            self._remove(key)

    def _remove(self, key: str) -> None:
        entry = self._items.pop(key, None)
        if entry is not None:
            self._bytes -= entry.size

