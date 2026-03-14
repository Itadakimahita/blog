from __future__ import annotations

from django.core.cache import cache


PUBLISHED_POSTS_LIST_VERSION_KEY = "blog:published_posts:list:version"
PUBLISHED_POSTS_LIST_KEY_PREFIX = "blog:published_posts:list"


def get_published_posts_list_version() -> int:
    try:
        version = cache.get(PUBLISHED_POSTS_LIST_VERSION_KEY)
        if version is None:
            cache.set(PUBLISHED_POSTS_LIST_VERSION_KEY, 1, timeout=None)
            return 1
        return int(version)
    except Exception:
        # Redis might be unavailable in local dev; treat version as 1.
        return 1


def bump_published_posts_list_version() -> int:
    """
    Invalidate published posts list cache for all variants by bumping a version.
    """
    try:
        if cache.add(PUBLISHED_POSTS_LIST_VERSION_KEY, 1, timeout=None):
            return 1
        return int(cache.incr(PUBLISHED_POSTS_LIST_VERSION_KEY))
    except Exception:
        # Redis might be unavailable in local dev; treat as best-effort invalidation.
        return 1


def published_posts_list_cache_key(*, language: str, timezone_name: str) -> str:
    version = get_published_posts_list_version()
    return f"{PUBLISHED_POSTS_LIST_KEY_PREFIX}:v{version}:lang:{language}:tz:{timezone_name}"
