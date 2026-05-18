"""Supabase Realtime for live races — runs async in a background thread."""
from __future__ import annotations

import asyncio
import threading
from typing import Callable

from termtypo.config import SUPABASE_URL, SUPABASE_ANON_KEY, load_session


class RaceChannel:
    """
    Manages the Realtime broadcast channel for one match.
    Runs its own asyncio event loop in a daemon thread so it doesn't
    conflict with Textual's event loop.
    """

    def __init__(
        self,
        match_id: str,
        user_id: str,
        on_opponent_progress: Callable[[dict], None],
    ) -> None:
        self.match_id = match_id
        self.user_id = user_id
        self._on_progress = on_opponent_progress
        self._loop: asyncio.AbstractEventLoop | None = None
        self._channel = None
        self._ready = threading.Event()
        self._stopped = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        t = threading.Thread(target=self._thread_main, daemon=True)
        t.start()
        self._ready.wait(timeout=10)

    def stop(self) -> None:
        # Set the flag; the sleep loop exits on its own — no forced loop.stop().
        self._stopped = True

    # ── thread entry ──────────────────────────────────────────────────────────

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._async_main())
        finally:
            loop.close()

    async def _async_main(self) -> None:
        from supabase import acreate_client
        client = await acreate_client(SUPABASE_URL, SUPABASE_ANON_KEY)

        data = load_session()
        if data:
            await client.auth.set_session(data["access_token"], data["refresh_token"])

        channel = client.realtime.channel(f"match:{self.match_id}")
        channel.on_broadcast("progress", self._handle_broadcast)
        await channel.subscribe()
        self._channel = channel
        self._ready.set()

        # Keep channel alive until stop() is called
        try:
            while not self._stopped:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    # ── handlers ──────────────────────────────────────────────────────────────

    def _handle_broadcast(self, payload: dict) -> None:
        data = payload.get("payload", payload)
        if data.get("user_id") != self.user_id:
            self._on_progress(data)

    # ── outbound ──────────────────────────────────────────────────────────────

    def broadcast(self, words_typed: int, wpm: float, total_words: int, finished: bool) -> None:
        if not self._loop or not self._channel:
            return
        asyncio.run_coroutine_threadsafe(
            self._channel.send_broadcast("progress", {
                "user_id":     self.user_id,
                "words_typed": words_typed,
                "total_words": total_words,
                "wpm":         round(wpm, 1),
                "finished":    finished,
            }),
            self._loop,
        )


# ── DB helpers (sync, called from Textual workers) ───────────────────────────

def finish_match(
    match_id: str,
    winner_id: str,
    winner_wpm: float = 0,
    winner_acc: float = 100,
    loser_wpm: float  = 0,
    loser_acc: float  = 100,
    # loser_id no longer needed — DB auto-determines from match_participants
    **_ignored,
) -> None:
    from termtypo.services.auth_service import get_authed_client
    client = get_authed_client()
    if not client:
        return
    client.rpc("finish_match", {
        "p_match_id":   match_id,
        "p_winner_id":  winner_id,
        "p_winner_wpm": round(winner_wpm, 2),
        "p_winner_acc": round(winner_acc, 2),
        "p_loser_wpm":  round(loser_wpm, 2),
        "p_loser_acc":  round(loser_acc, 2),
    }).execute()


def get_user_elo(user_id: str, mode: str) -> int:
    from termtypo.services.auth_service import get_authed_client
    client = get_authed_client()
    if not client:
        return 0
    try:
        res = client.table("user_ratings").select("elo").eq("user_id", user_id).eq("mode", mode).maybe_single().execute()
        return (res.data or {}).get("elo", 0) if res else 0
    except Exception:
        return 0
