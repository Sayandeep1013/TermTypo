"""Live 1v1 race screen — typed words + opponent progress bars."""
from __future__ import annotations

import time

OPPONENT_TIMEOUT_SECONDS = 45  # declare win if no opponent update for this long

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text

from termtypo.widgets.keyboard_widget import KeyboardWidget
from termtypo.widgets.typing_area import TypingArea, TypingState


def _progress_bar(filled: float, total: float, width: int = 30) -> str:
    frac = min(filled / max(total, 1), 1.0)
    n = int(frac * width)
    return "━" * n + "░" * (width - n)


class PlayerBar(Static):
    DEFAULT_CSS = """
    PlayerBar {
        height: 3;
        padding: 0 4;
    }
    """

    def __init__(self, label: str, is_self: bool, total_words: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._is_self = is_self
        self._total = total_words
        self._typed = 0
        self._wpm = 0.0
        self._finished = False

    def update_progress(self, typed: int, wpm: float, finished: bool) -> None:
        self._typed = typed
        self._wpm = wpm
        self._finished = finished
        self._rebuild()

    def _rebuild(self) -> None:
        t = Text()
        label_style = "bold #7aa2f7" if self._is_self else "#c0caf5"
        t.append(f"  {self._label:<18}", style=label_style)
        bar_style = "#7aa2f7" if self._is_self else "#565f89"
        t.append(_progress_bar(self._typed, self._total), style=bar_style)
        pct = int(min(self._typed / max(self._total, 1), 1.0) * 100)
        t.append(f"  {pct:>3}%", style="#565f89")
        t.append(f"  {self._wpm:.0f} wpm", style="#9ece6a" if self._is_self else "#565f89")
        if self._finished:
            t.append("  ✓", style="#9ece6a")
        self.update(t)


class RaceScreen(Screen):
    BINDINGS = [Binding("escape", "forfeit", "Forfeit", show=False)]

    DEFAULT_CSS = """
    RaceScreen {
        background: #1a1b26;
        layout: vertical;
    }
    #race-header {
        height: 3;
        padding: 1 4;
        background: #24283b;
        color: #565f89;
    }
    #bars-container {
        height: 7;
        padding: 0 0;
        background: #1a1b26;
        border-bottom: solid #24283b;
    }
    #typing-zone {
        height: 1fr;
        align: center middle;
        padding: 1 4;
    }
    #typing-box {
        width: 90%;
        max-width: 110;
        height: auto;
        border: round #2a2b3d;
        padding: 1 3;
        background: #1a1b26;
    }
    #waiting-hint {
        height: 2;
        content-align: center middle;
        color: #565f89;
    }
    #hint-bar {
        height: 1;
        dock: bottom;
        padding: 0 4;
        color: #565f89;
    }
    """

    def __init__(
        self,
        match_id: str,
        passage: str,
        user_id: str,
        mode: str,
        ranked: bool = True,
        opponent_name: str = "Opponent",
        my_name: str = "You",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._match_id = match_id
        self._passage = passage
        self._user_id = user_id
        self._mode = mode
        self._ranked = ranked
        self._my_name = my_name
        self._opponent_name = opponent_name
        self._words = passage.split()
        self._race_channel = None
        self._opponent_data: dict = {"typed": 0, "wpm": 0.0, "finished": False}
        self._broadcast_handle = None
        self._disconnect_handle = None
        self._last_opponent_update: float = time.monotonic()
        self._finished = False
        self._opponent_finished_data: dict | None = None

    def compose(self) -> ComposeResult:
        yield Static(id="race-header")
        with Static(id="bars-container"):
            yield PlayerBar(self._my_name, is_self=True,
                            total_words=len(self._words), id="my-bar")
            yield PlayerBar(self._opponent_name, is_self=False,
                            total_words=len(self._words), id="opp-bar")
        with Static(id="typing-zone"):
            with Static(id="typing-box"):
                yield TypingArea(self._words, id="typing-area")
            yield Static("start typing to race!", id="waiting-hint")
        yield KeyboardWidget(id="keyboard")
        yield Static("[esc] forfeit", id="hint-bar")

    def on_typing_area_key_typed(self, msg: TypingArea.KeyTyped) -> None:
        self.query_one(KeyboardWidget).set_key(msg.char, msg.correct)

    def on_mount(self) -> None:
        self._update_header()
        self._start_race_channel()
        self.query_one(TypingArea).focus()

        # Passage or names missing (common in cross-client races where the
        # other client's broadcast didn't include them) — fetch from DB.
        if not self._words or self._opponent_name == "Opponent":
            self.run_worker(self._fetch_race_data, thread=True, exclusive=True)

    def _fetch_race_data(self) -> None:
        """Fetch passage and participant names from DB — fills in cross-client gaps."""
        from termtypo.services.auth_service import get_authed_client
        client = get_authed_client()
        if not client:
            return
        try:
            # Passage
            if not self._words:
                res = client.table("matches").select("passage, mode").eq("id", self._match_id).maybe_single().execute()
                data = (res.data or {}) if res else {}
                passage = data.get("passage", "")
                if passage:
                    self._passage = passage
                    self._words   = passage.split()
                    self.app.call_from_thread(
                        lambda: self.query_one(TypingArea).reset(self._words)
                    )

            # Participant names — fetch user_ids first, then query profiles directly
            parts = client.table("match_participants").select("user_id").eq("match_id", self._match_id).execute()
            for p in (parts.data or []):
                uid = p["user_id"]
                prof_res = client.table("profiles").select("username, display_name").eq("id", uid).maybe_single().execute()
                profile  = (prof_res.data or {}) if prof_res else {}
                name     = profile.get("display_name") or profile.get("username") or ""
                if not name:
                    continue
                if uid == self._user_id:
                    self._my_name = name
                else:
                    self._opponent_name = name

            # Refresh bars with updated names
            def _update_bars():
                my_bar  = self.query_one("#my-bar",  PlayerBar)
                opp_bar = self.query_one("#opp-bar", PlayerBar)
                my_bar._label  = self._my_name
                opp_bar._label = self._opponent_name
                my_bar._rebuild()
                opp_bar._rebuild()
            self.app.call_from_thread(_update_bars)
        except Exception:
            pass

    def _update_header(self, elapsed: float = 0.0, wpm: float = 0.0) -> None:
        t = Text()
        t.append(f"  {'RANKED' if self._ranked else 'PRIVATE'} RACE", style="bold #7aa2f7")
        t.append(f"   {self._mode}", style="#565f89")
        if elapsed > 0:
            t.append(f"   {elapsed:.1f}s", style="#7dcfff")
            t.append(f"   {wpm:.0f} wpm", style="#9ece6a")
        self.query_one("#race-header", Static).update(t)

    # ── realtime ──────────────────────────────────────────────────────────────

    def _start_race_channel(self) -> None:
        from termtypo.services.race_service import RaceChannel
        self._race_channel = RaceChannel(
            match_id=self._match_id,
            user_id=self._user_id,
            on_opponent_progress=self._on_opponent_progress,
        )
        self._race_channel.start()

    def _on_opponent_progress(self, data: dict) -> None:
        self._opponent_data = data
        self._last_opponent_update = time.monotonic()
        self.app.call_from_thread(self._refresh_opponent_bar)
        if data.get("finished") and not self._opponent_finished_data:
            self._opponent_finished_data = data

    def _check_opponent_alive(self) -> None:
        if self._finished:
            return
        silence = time.monotonic() - self._last_opponent_update
        if silence >= OPPONENT_TIMEOUT_SECONDS:
            self._stop_handles()
            self.app.notify(
                f"Opponent disconnected after {OPPONENT_TIMEOUT_SECONDS}s — you win!",
                severity="information",
                timeout=8,
            )
            s = self.query_one(TypingArea).state
            self._finished = True
            self._resolve_race(my_state=s, forfeit_win=True)

    def _refresh_opponent_bar(self) -> None:
        d = self._opponent_data
        self.query_one("#opp-bar", PlayerBar).update_progress(
            d.get("words_typed", 0), d.get("wpm", 0.0), d.get("finished", False)
        )

    # ── typing area messages ──────────────────────────────────────────────────

    def on_typing_area_started(self, _: TypingArea.Started) -> None:
        self.query_one("#waiting-hint", Static).display = False
        self._broadcast_handle   = self.set_interval(0.2, self._broadcast_progress)
        self._disconnect_handle  = self.set_interval(5.0, self._check_opponent_alive)

    def on_typing_area_word_advanced(self, _: TypingArea.WordAdvanced) -> None:
        self._update_my_bar()
        self._update_header(
            self.query_one(TypingArea).state.elapsed,
            self.query_one(TypingArea).state.wpm(),
        )

    def _stop_handles(self) -> None:
        if self._broadcast_handle:
            self._broadcast_handle.stop()
            self._broadcast_handle = None
        if self._disconnect_handle:
            self._disconnect_handle.stop()
            self._disconnect_handle = None

    def on_typing_area_finished(self, msg: TypingArea.Finished) -> None:
        if self._finished:
            return
        self._finished = True
        self._update_my_bar()
        self._stop_handles()
        # Final broadcast
        s = msg.state
        if self._race_channel:
            self._race_channel.broadcast(s.current_word, s.wpm(), len(s.words), True)
        self._resolve_race(my_state=s)

    def _update_my_bar(self) -> None:
        s = self.query_one(TypingArea).state
        self.query_one("#my-bar", PlayerBar).update_progress(
            s.current_word, s.wpm(), s.finished
        )

    def _broadcast_progress(self) -> None:
        s = self.query_one(TypingArea).state
        if self._race_channel:
            self._race_channel.broadcast(s.current_word, s.wpm(), len(s.words), False)
        self._update_header(s.elapsed, s.wpm())

    # ── race resolution ───────────────────────────────────────────────────────

    def _resolve_race(self, my_state: TypingState, forfeit_win: bool = False) -> None:
        opp = self._opponent_data
        i_won = not opp.get("finished", False)  # opponent not finished yet = I won

        if self._ranked:
            try:
                from termtypo.services.race_service import finish_match
                if i_won:
                    finish_match(
                        self._match_id,
                        winner_id=self._user_id,
                        loser_id=opp.get("user_id", ""),
                        winner_wpm=my_state.wpm(),
                        loser_wpm=opp.get("wpm", 0.0),
                        winner_acc=my_state.accuracy(),
                        loser_acc=100.0,
                    )
                # else: the winner already called finish_match
            except Exception:
                pass

        self.app.push_screen(
            self._make_results(my_state, i_won)
        )

    def _make_results(self, my_state: TypingState, i_won: bool):
        from termtypo.screens.race_results import RaceResultsScreen
        return RaceResultsScreen(
            match_id=self._match_id,
            ranked=self._ranked,
            i_won=i_won,
            my_wpm=my_state.wpm(),
            my_acc=my_state.accuracy(),
            opp_wpm=self._opponent_data.get("wpm", 0.0),
            mode=self._mode,
            user_id=self._user_id,
        )

    # ── actions ───────────────────────────────────────────────────────────────

    def action_forfeit(self) -> None:
        if self._finished:
            return
        if self._race_channel:
            self._race_channel.stop()
        self._stop_handles()
        from termtypo.services.matchmaking_service import leave_queue
        from termtypo.services.auth_service import current_user
        user = current_user()
        if user:
            leave_queue(user["id"])
        self.app.pop_screen()
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()  # also pop matchmaking screen
