"""Matchmaking screen — searching for an opponent."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text


SPINNER = ["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"]


class MatchmakingScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    DEFAULT_CSS = """
    MatchmakingScreen {
        background: #1a1b26;
        align: center middle;
    }
    #mm-box {
        width: 50;
        height: auto;
        border: round #7aa2f7;
        padding: 2 4;
        background: #24283b;
    }
    """

    def __init__(self, mode: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode = mode
        self._watcher = None
        self._tick = 0
        self._match_id: str | None = None
        self._passage: str | None = None

    def compose(self) -> ComposeResult:
        with Static(id="mm-box"):
            yield Static(id="mm-content")
        yield Static("[esc] cancel", classes="hint")

    def on_mount(self) -> None:
        self._update_display()
        self._start_watcher()
        self.set_interval(0.15, self._tick_spinner)

    def _update_display(self, status: str = "searching") -> None:
        spin = SPINNER[self._tick % len(SPINNER)]
        t = Text()
        t.append("  RANKED MATCH\n\n", style="bold #7aa2f7")
        t.append("  mode   ", style="#565f89")
        t.append(f"{self._mode}\n\n", style="#c0caf5")
        if status == "searching":
            t.append(f"  {spin} ", style="#7aa2f7")
            t.append("searching for opponent…\n", style="#565f89")
        elif status == "found":
            t.append("  ✓ opponent found — loading race…\n", style="#9ece6a")
        elif status == "error":
            t.append("  ✗ error — press esc to go back\n", style="#f7768e")
        self.query_one("#mm-content", Static).update(t)

    def _tick_spinner(self) -> None:
        self._tick += 1
        if not self._match_id:
            self._update_display("searching")

    def _start_watcher(self) -> None:
        from termtypo.services.auth_service import current_user
        from termtypo.services.matchmaking_service import MatchmakingWatcher, join_queue
        from termtypo.services.race_service import get_user_elo

        user = current_user()
        if not user:
            return

        elo = get_user_elo(user["id"], self._mode)
        join_queue(user["id"], self._mode, elo)

        self._watcher = MatchmakingWatcher(
            user_id=user["id"],
            mode=self._mode,
            on_match_found=self._on_match_found,
            on_error=self._on_error,
        )
        self._watcher.start()

    def _on_match_found(self, match_id: str, passage: str) -> None:
        self._match_id = match_id
        self._passage = passage
        self.app.call_from_thread(self._enter_race)

    def _on_error(self, msg: str) -> None:
        self.app.call_from_thread(self._update_display, "error")
        self.app.call_from_thread(self.app.notify, f"Matchmaking error: {msg}", severity="error")

    def _enter_race(self) -> None:
        from termtypo.screens.race import RaceScreen
        from termtypo.services.auth_service import current_user
        user = current_user()
        if not user or not self._match_id:
            return
        self._update_display("found")
        self.app.push_screen(
            RaceScreen(self._match_id, self._passage or "", user["id"], self._mode, ranked=True)
        )

    def action_cancel(self) -> None:
        from termtypo.services.matchmaking_service import leave_queue
        from termtypo.services.auth_service import current_user
        if self._watcher:
            self._watcher.stop()
        user = current_user()
        if user:
            leave_queue(user["id"])
        self.app.pop_screen()
