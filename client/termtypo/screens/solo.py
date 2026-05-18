"""Solo typing test screen."""
from __future__ import annotations

import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text

from termtypo.screens.results import ResultsModal
from termtypo.services.word_service import get_timed_words, get_words
from termtypo.widgets.typing_area import TypingArea, TypingState

DEFAULT_MODE = "words_50"
WORD_COUNTS  = [10, 25, 50, 100]
TIME_SECONDS = [10, 30, 60]


# ── mode tabs ─────────────────────────────────────────────────────────────────

class ModeTabs(Static):
    """Visual mode selector — two rows: category (words/time) + values."""

    DEFAULT_CSS = """
    ModeTabs {
        height: 4;
        padding: 1 4;
        background: #1a1b26;
        color: #565f89;
    }
    """

    def __init__(self, mode: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode = mode

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._rebuild()

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        kind = "words" if self._mode.startswith("words_") else "time"
        val  = int(self._mode.split("_")[1])
        t = Text()

        # Row 1: category
        for cat in ("words", "time"):
            if cat == kind:
                t.append(cat, style="bold #7aa2f7 underline")
            else:
                t.append(cat, style="#565f89")
            t.append("   ")
        t.append("\n")

        # Row 2: options
        options = WORD_COUNTS if kind == "words" else TIME_SECONDS
        suffix  = "" if kind == "words" else "s"
        for opt in options:
            label = f"{opt}{suffix}"
            if opt == val:
                t.append(label, style="bold #7aa2f7")
            else:
                t.append(label, style="#565f89")
            t.append("   ")

        self.update(t)


# ── live stats bar (shown only while typing) ──────────────────────────────────

class StatsBar(Static):
    DEFAULT_CSS = """
    StatsBar {
        height: 1;
        padding: 0 4;
        background: #1a1b26;
        color: #565f89;
        display: none;
    }
    """

    def show_stats(self, wpm: float, acc: float, elapsed: float, time_limit: int | None) -> None:
        self.display = True
        t = Text()
        if time_limit:
            remaining = max(0.0, time_limit - elapsed)
            clr = "#e0af68" if remaining < 5 else "#7dcfff"
            t.append(f"{remaining:.1f}s  ", style=clr)
            t.append("│  ", style="#24283b")
        t.append(f"{wpm:.0f} wpm", style="#9ece6a")
        t.append("  │  ", style="#24283b")
        t.append(f"{acc:.0f}%", style="#7dcfff")
        self.update(t)


# ── waiting hint (hidden once typing starts) ──────────────────────────────────

class WaitingHint(Static):
    DEFAULT_CSS = """
    WaitingHint {
        height: 2;
        content-align: center middle;
        color: #565f89;
        padding-top: 1;
    }
    """

    def on_mount(self) -> None:
        self.update(Text("start typing to begin", style="italic #565f89"))


# ── hint bar ──────────────────────────────────────────────────────────────────

class HintBar(Static):
    DEFAULT_CSS = """
    HintBar {
        height: 1;
        dock: bottom;
        padding: 0 4;
        background: #1a1b26;
        color: #565f89;
    }
    """

    def on_mount(self) -> None:
        self.update(Text(
            "[esc] back   [tab] restart   [← →] cycle mode",
            style="#565f89",
        ))


# ── solo screen ───────────────────────────────────────────────────────────────

class SoloScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back",   "Back",    show=False),
        Binding("tab",    "restart",   "Restart", show=False),
        # Plain arrows — ctrl+arrows are intercepted by Windows Terminal
        Binding("right",  "next_mode", "Next",    show=False),
        Binding("left",   "prev_mode", "Prev",    show=False),
    ]

    DEFAULT_CSS = """
    SoloScreen {
        background: #1a1b26;
        layout: vertical;
    }
    ModeTabs {
        width: 100%;
    }
    #center-col {
        width: 100%;
        height: 1fr;
        align: center middle;
        padding: 0 6;
    }
    #typing-box {
        width: 90%;
        max-width: 110;
        height: auto;
        border: round #2a2b3d;
        padding: 1 3;
        background: #1a1b26;
    }
    WaitingHint {
        width: 100%;
    }
    StatsBar {
        width: 100%;
    }
    """

    _all_modes: list[str] = (
        [f"words_{n}" for n in WORD_COUNTS] +
        [f"time_{t}"  for t in TIME_SECONDS]
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_mode = DEFAULT_MODE
        self._timer_handle = None

    def compose(self) -> ComposeResult:
        yield ModeTabs(self._current_mode, id="mode-tabs")
        with Static(id="center-col"):
            with Static(id="typing-box"):
                yield TypingArea(self._words_for_mode(self._current_mode), id="typing-area")
            yield WaitingHint(id="waiting-hint")
        yield StatsBar(id="stats-bar")
        yield HintBar()

    def on_mount(self) -> None:
        self.query_one(TypingArea).focus()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _words_for_mode(self, mode: str) -> list[str]:
        if mode.startswith("words_"):
            return get_words(int(mode.split("_")[1]))
        return get_timed_words(int(mode.split("_")[1]))

    def _time_limit(self) -> int | None:
        if self._current_mode.startswith("time_"):
            return int(self._current_mode.split("_")[1])
        return None

    # ── message handlers ──────────────────────────────────────────────────────

    def on_typing_area_started(self, _: TypingArea.Started) -> None:
        self.query_one(WaitingHint).display = False
        self.query_one(StatsBar).display = True
        limit = self._time_limit()
        if limit:
            self._timer_handle = self.set_interval(0.1, self._tick_timer)

    def on_typing_area_word_advanced(self, _: TypingArea.WordAdvanced) -> None:
        self._push_stats()

    def on_typing_area_finished(self, msg: TypingArea.Finished) -> None:
        self._stop_timer()
        self._open_results(msg.state)

    def _tick_timer(self) -> None:
        area = self.query_one(TypingArea)
        s = area.state
        limit = self._time_limit()
        if limit and s.elapsed >= limit:
            self._stop_timer()
            s.finished = True
            s.end_time = time.monotonic()
            area.refresh()
            self._open_results(s)
            return
        self._push_stats()

    def _push_stats(self) -> None:
        s = self.query_one(TypingArea).state
        self.query_one(StatsBar).show_stats(
            s.wpm(), s.accuracy(), s.elapsed, self._time_limit()
        )

    def _stop_timer(self) -> None:
        if self._timer_handle:
            self._timer_handle.stop()
            self._timer_handle = None

    def _open_results(self, s: TypingState) -> None:
        self._maybe_save(s)

        def on_dismiss(result: str | None) -> None:
            if result == "retry":
                self.action_restart()

        self.app.push_screen(ResultsModal(s), on_dismiss)

    def _maybe_save(self, s: TypingState) -> None:
        from termtypo.services.auth_service import current_user, get_authed_client
        user = current_user()
        if not user:
            return
        client = get_authed_client()
        if not client:
            return
        try:
            client.table("solo_results").insert({
                "user_id":          user["id"],
                "mode":             self._current_mode,
                "wpm":              round(s.wpm(), 2),
                "raw_wpm":          round(s.raw_wpm(), 2),
                "accuracy":         round(s.accuracy(), 2),
                "word_count":       s.current_word,
                "duration_seconds": int(s.elapsed),
            }).execute()
        except Exception as e:
            self.app.notify(f"Result not saved: {str(e)[:60]}", severity="warning", timeout=6)

    # ── actions ───────────────────────────────────────────────────────────────

    def action_go_back(self) -> None:
        self._stop_timer()
        self.app.pop_screen()

    def action_restart(self) -> None:
        self._stop_timer()
        area = self.query_one(TypingArea)
        area.reset(self._words_for_mode(self._current_mode))
        self.query_one(WaitingHint).display = True
        self.query_one(StatsBar).display = False
        area.focus()

    def action_next_mode(self) -> None:
        if self.query_one(TypingArea).state.started:
            return  # don't change mode mid-test
        idx = self._all_modes.index(self._current_mode)
        self._current_mode = self._all_modes[(idx + 1) % len(self._all_modes)]
        self.query_one(ModeTabs).set_mode(self._current_mode)
        self.action_restart()

    def action_prev_mode(self) -> None:
        if self.query_one(TypingArea).state.started:
            return
        idx = self._all_modes.index(self._current_mode)
        self._current_mode = self._all_modes[(idx - 1) % len(self._all_modes)]
        self.query_one(ModeTabs).set_mode(self._current_mode)
        self.action_restart()
