"""Word list loader and passage generator."""
from __future__ import annotations

import random
import sys
from pathlib import Path


def _assets_dir() -> Path:
    # When frozen by PyInstaller, sys._MEIPASS is the temp extraction dir.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "termtypo" / "assets" / "words"
    return Path(__file__).parent.parent / "assets" / "words"


_ASSETS = _assets_dir()

_cache: dict[str, list[str]] = {}


def _load(name: str) -> list[str]:
    if name not in _cache:
        path = _ASSETS / f"{name}.txt"
        _cache[name] = path.read_text(encoding="utf-8").split()
    return _cache[name]


def get_words(count: int) -> list[str]:
    pool = _load("common_1000")
    return random.sample(pool, min(count, len(pool)))


def get_timed_words(seconds: int) -> list[str]:
    """Pre-generate enough words for a timed test (generous buffer)."""
    estimates = {10: 30, 30: 80, 60: 150}
    count = estimates.get(seconds, seconds * 3)
    pool = _load("common_1000")
    words = []
    while len(words) < count:
        words.extend(random.sample(pool, min(count, len(pool))))
    return words[:count]
