from typing import Any

from django.core.cache import cache


def get(key: str, default: Any = None) -> Any:
    return cache.get(key, default)


def set(
    key: str,
    value: Any,
    timeout: int | None = None,
) -> None:
    cache.set(key, value, timeout)


def delete(key: str) -> None:
    cache.delete(key)


def exists(key: str) -> bool:
    return cache.has_key(key)


def delete_pattern(pattern: str) -> None:
    cache.delete_pattern(pattern)