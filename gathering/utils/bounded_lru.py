"""Bounded LRU dictionary for in-memory caches."""

from collections import OrderedDict
from typing import TypeVar

V = TypeVar("V")


class BoundedLRUDict(OrderedDict):
    """OrderedDict with configurable max size and LRU eviction.

    On insertion beyond max_size, the least-recently-used entry is evicted.
    On access (__getitem__), the accessed entry is moved to most-recent position.
    """

    def __init__(self, max_size: int = 1000, *args, **kwargs):
        self._max_size = max_size
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        while len(self) > self._max_size:
            self.popitem(last=False)  # Evict LRU

    def __getitem__(self, key):
        self.move_to_end(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in self:
            self.move_to_end(key)
            return super().__getitem__(key)
        return default

    @property
    def max_size(self) -> int:
        return self._max_size
