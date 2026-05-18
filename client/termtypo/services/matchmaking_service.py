"""Matchmaking queue and match creation — uses sync DB + async Realtime."""
from __future__ import annotations

import asyncio
import random
import threading
from typing import Callable

from termtypo.config import SUPABASE_URL, SUPABASE_ANON_KEY, load_session
from termtypo.services.word_service import get_words, get_timed_words


def _passage_for_mode(mode: str) -> str:
    if mode.startswith("words_"):
        return " ".join(get_words(int(mode.split("_")[1])))
    return " ".join(get_timed_words(int(mode.split("_")[1])))


def join_queue(user_id: str, mode: str, elo: int) -> bool:
    """Insert player into matchmaking_queue. Returns True on success."""
    from termtypo.services.auth_service import get_authed_client
    client = get_authed_client()
    if not client:
        return False
    try:
        # Remove any stale queue entry first
        client.table("matchmaking_queue").delete().eq("user_id", user_id).execute()
        client.table("matchmaking_queue").insert({
            "user_id": user_id,
            "mode": mode,
            "elo": elo,
        }).execute()
        return True
    except Exception:
        return False


def leave_queue(user_id: str) -> None:
    from termtypo.services.auth_service import get_authed_client
    client = get_authed_client()
    if client:
        try:
            client.table("matchmaking_queue").delete().eq("user_id", user_id).execute()
        except Exception:
            pass


def create_room(user_id: str, mode: str) -> str | None:
    """Create a private room and return the 6-char code."""
    from termtypo.services.auth_service import get_authed_client
    client = get_authed_client()
    if not client:
        return None
    try:
        res = client.rpc("create_room", {"p_host_id": user_id, "p_mode": mode}).execute()
        return res.data
    except Exception:
        return None


def get_room(code: str) -> dict | None:
    """Look up a room by code."""
    from termtypo.services.auth_service import get_authed_client
    client = get_authed_client()
    if not client:
        return None
    try:
        res = client.table("rooms").select("*").eq("code", code.upper()).eq("status", "waiting").maybe_single().execute()
        return res.data if res else None
    except Exception:
        return None


def create_private_match(host_id: str, guest_id: str, mode: str) -> str | None:
    """Create an unranked match for a private room."""
    from termtypo.services.auth_service import get_authed_client
    client = get_authed_client()
    if not client:
        return None
    try:
        passage = _passage_for_mode(mode)
        match_res = client.table("matches").insert({
            "mode": mode,
            "passage": passage,
            "status": "active",
            "is_ranked": False,
        }).execute()
        match_id = match_res.data[0]["id"]
        client.table("match_participants").insert([
            {"match_id": match_id, "user_id": host_id, "elo_before": 0},
            {"match_id": match_id, "user_id": guest_id, "elo_before": 0},
        ]).execute()
        client.table("rooms").update({"status": "active", "match_id": match_id}).eq("host_id", host_id).eq("status", "waiting").execute()
        return match_id
    except Exception:
        return None


# ── Async matchmaking watcher ─────────────────────────────────────────────────

class MatchmakingWatcher:
    """
    Watches the matchmaking queue via Supabase Realtime.
    Runs its own event loop in a daemon thread.

    When two players are in the queue:
      - The player with the lexicographically smaller user_id creates the match.
      - The other receives the match_id via Broadcast on the queue channel.
    """

    def __init__(
        self,
        user_id: str,
        mode: str,
        on_match_found: Callable[[str, str], None],  # (match_id, passage)
        on_error: Callable[[str], None],
    ) -> None:
        self.user_id = user_id
        self.mode = mode
        self._on_match_found = on_match_found
        self._on_error = on_error
        self._loop: asyncio.AbstractEventLoop | None = None
        self._channel = None
        self._stopped = False

    def start(self) -> None:
        t = threading.Thread(target=self._thread_main, daemon=True)
        t.start()

    def stop(self) -> None:
        # Just set the flag — the while loop exits within 0.5 s on its own.
        # Calling loop.stop() while asyncio.sleep() is pending raises
        # "Event loop stopped before Future completed".
        self._stopped = True

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(self._async_main())
        except Exception as e:
            self._on_error(str(e))
        finally:
            loop.close()

    async def _async_main(self) -> None:
        from supabase import acreate_client
        client = await acreate_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        data = load_session()
        if data:
            await client.auth.set_session(data["access_token"], data["refresh_token"])

        channel = client.realtime.channel(f"queue:{self.mode}")
        self._channel = channel

        # Listen for match_found broadcast (sent by the "host" player)
        channel.on_broadcast("match_found", self._handle_match_broadcast)

        # on_presence_join fires when a NEW user joins.
        # on_presence_sync fires on initial state load AND on every change.
        # We need BOTH: if we are the second player to arrive, only sync fires
        # for us (showing the first player already present).
        channel.on_presence_join(self._handle_presence_change)
        channel.on_presence_sync(self._handle_presence_change)

        await channel.subscribe()
        await channel.track({
            "user_id": self.user_id,
            "mode": self.mode,
        })

        try:
            while not self._stopped:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    def _extract_user_ids(self, state: dict) -> list[str]:
        ids = []
        for _, presences in state.items():
            items = presences if isinstance(presences, list) else [presences]
            for p in items:
                uid = (p.get("user_id")
                       or p.get("payload", {}).get("user_id")
                       or (p.get("state") or {}).get("user_id"))
                if uid:
                    ids.append(uid)
        return list(set(ids))

    def _handle_presence_change(self, payload=None) -> None:
        if self._stopped:
            return
        state = self._channel.presence_state()
        user_ids = self._extract_user_ids(state)

        if len(user_ids) >= 2 and min(user_ids) == self.user_id:
            opponent_id = next(u for u in user_ids if u != self.user_id)
            # Run in a separate thread — sync HTTP calls must not block the asyncio loop
            t = threading.Thread(target=self._try_create_match, args=(opponent_id,), daemon=True)
            t.start()

    def _try_create_match(self, opponent_id: str) -> None:
        from termtypo.services.auth_service import get_authed_client
        client = get_authed_client()
        if not client:
            return
        try:
            passage = _passage_for_mode(self.mode)
            res = client.rpc("create_match_from_queue", {
                "p_user1_id": self.user_id,
                "p_user2_id": opponent_id,
                "p_mode":     self.mode,
                "p_passage":  passage,
            }).execute()
            match_id = res.data
            if match_id:
                # Broadcast match_id to the queue channel so opponent knows too
                if self._loop and self._channel:
                    asyncio.run_coroutine_threadsafe(
                        self._channel.send_broadcast("match_found", {
                            "match_id": match_id,
                            "passage":  passage,
                        }),
                        self._loop,
                    )
                self._stopped = True
                self._on_match_found(match_id, passage)
        except Exception as e:
            self._on_error(str(e))

    def _handle_match_broadcast(self, payload: dict) -> None:
        if self._stopped:
            return
        data = payload.get("payload", payload)
        match_id = data.get("match_id")
        passage = data.get("passage", "")
        if match_id:
            self._stopped = True
            self._on_match_found(match_id, passage)
