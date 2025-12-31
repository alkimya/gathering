"""
Cache module for Gathering workspace.

Provides Redis-based caching for:
- File trees
- Git data (commits, status, branches)
- LSP responses
- File contents
"""

from .redis_cache import (
    RedisCache,
    get_cache,
    cached,
    cache_file_tree,
    get_cached_file_tree,
    cache_git_commits,
    get_cached_git_commits,
    cache_git_status,
    get_cached_git_status,
    invalidate_workspace_cache,
)

__all__ = [
    "RedisCache",
    "get_cache",
    "cached",
    "cache_file_tree",
    "get_cached_file_tree",
    "cache_git_commits",
    "get_cached_git_commits",
    "cache_git_status",
    "get_cached_git_status",
    "invalidate_workspace_cache",
]
