"""Changed-path boundary checks for cloud and local workers."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable, List, Sequence, Tuple

from .errors import BoundaryViolationError


def normalize_path(value: str) -> str:
    path = value.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    parts = PurePosixPath(path).parts
    if not path or not parts or path.startswith("/") or ".." in parts or ":" in parts[0]:
        raise BoundaryViolationError("unsafe changed path %r" % value)
    return "/".join(parts)


def _matches(path: str, pattern: str) -> bool:
    pattern = pattern.replace("\\", "/")
    while pattern.startswith("./"):
        pattern = pattern[2:]
    candidate = PurePosixPath(path)
    if candidate.match(pattern):
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return False


def check_changed_paths(
    changed: Iterable[str], allowed: Sequence[str], forbidden: Sequence[str]
) -> Tuple[List[str], List[str]]:
    outside: List[str] = []
    blocked: List[str] = []
    for raw in changed:
        path = normalize_path(raw)
        if any(_matches(path, pattern) for pattern in forbidden):
            blocked.append(path)
        elif not any(_matches(path, pattern) for pattern in allowed):
            outside.append(path)
    return outside, blocked


def enforce_changed_paths(changed: Iterable[str], allowed: Sequence[str], forbidden: Sequence[str]) -> None:
    outside, blocked = check_changed_paths(changed, allowed, forbidden)
    if outside or blocked:
        raise BoundaryViolationError("outside=%r forbidden=%r" % (outside, blocked))
