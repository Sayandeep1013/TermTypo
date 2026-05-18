"""Mode selection modal — reused by ranked matchmaking and room creation."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static
from rich.text import Text

MODES: list[tuple[str, str]] = [
    ("words_10",  "Words  ·   10 words"),
    ("words_25",  "Words  ·   25 words"),
    ("words_50",  "Words  ·   50 words  (default)"),
    ("words_100", "Words  ·  100 words"),
    ("time_10",   "Timed  ·   10 seconds"),
    ("time_30",   "Timed  ·   30 seconds"),
    ("time_60",   "Timed  ·   60 seconds"),
]
_KEYS = [m[0] for m in MODES]


class ModeSelectScreen(ModalScreen[str]):
    """
    Returns the selected mode string on dismiss, or None if cancelled.
    Usage:
        self.app.push_screen(ModeSelectScreen(), callback)
    """

    BINDINGS = [
        Binding("up",     "prev",   show=False),
        Binding("k",      "prev",   show=False),
        Binding("down",   "next",   show=False),
        Binding("j",      "next",   show=False),
        Binding("enter",  "select", show=False),
        Binding("space",  "select", show=False),
        Binding("escape", "cancel", show=False),
    ]

    DEFAULT_CSS = """
    ModeSelectScreen {
        align: center middle;
    }
    #ms-box {
        width: 46;
        height: auto;
        border: round #7aa2f7;
        padding: 2 4;
        background: #24283b;
    }
    """

    def __init__(self, default: str = "words_50", **kwargs) -> None:
        super().__init__(**kwargs)
        self._cursor = _KEYS.index(default) if default in _KEYS else 2

    def compose(self) -> ComposeResult:
        with Static(id="ms-box"):
            yield Static(id="ms-content")
        yield Static("[↑↓ / j k] move   [enter] pick   [esc] cancel", classes="hint")

    def on_mount(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        t = Text()
        t.append("  SELECT MODE\n\n", style="bold #7aa2f7")
        for i, (key, label) in enumerate(MODES):
            if i == self._cursor:
                t.append("  ▶ ", style="bold #7aa2f7")
                t.append(f"{label}\n", style="bold #c0caf5")
            else:
                t.append("    ", style="")
                t.append(f"{label}\n", style="#565f89")
        self.query_one("#ms-content", Static).update(t)

    def action_prev(self) -> None:
        self._cursor = (self._cursor - 1) % len(MODES)
        self._rebuild()

    def action_next(self) -> None:
        self._cursor = (self._cursor + 1) % len(MODES)
        self._rebuild()

    def action_select(self) -> None:
        self.dismiss(_KEYS[self._cursor])

    def action_cancel(self) -> None:
        self.dismiss(None)
