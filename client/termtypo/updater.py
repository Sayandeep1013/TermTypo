"""Check PyPI for a newer version of termtypo and notify the user."""
from __future__ import annotations

import threading
from typing import Callable


def check_for_update(on_update_available: Callable[[str], None]) -> None:
    """
    Non-blocking. Queries PyPI JSON API in a daemon thread.
    Calls on_update_available(latest_version) if a newer version exists.
    Silently ignores all network/parse errors — never crashes the app.
    """
    def _check():
        try:
            import httpx
            from termtypo import __version__

            resp = httpx.get(
                "https://pypi.org/pypi/termtypo/json",
                timeout=4,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return

            latest = resp.json()["info"]["version"]

            # Simple version comparison (works for semver X.Y.Z)
            def _parse(v: str) -> tuple[int, ...]:
                try:
                    return tuple(int(x) for x in v.split("."))
                except ValueError:
                    return (0,)

            if _parse(latest) > _parse(__version__):
                on_update_available(latest)

        except Exception:
            pass  # Network down, JSON error, etc. — all silently ignored

    threading.Thread(target=_check, daemon=True).start()
