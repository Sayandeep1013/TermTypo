"""Results modal — shown after a solo or race finishes."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static
from rich.text import Text

from termtypo.widgets.typing_area import TypingState


def _bar(value: float, max_val: float, width: int = 28) -> str:
    filled = int((value / max(max_val, 1)) * width)
    filled = min(filled, width)
    return "━" * filled + "░" * (width - filled)


class ResultsModal(ModalScreen):
    BINDINGS = [
        Binding("tab",    "retry",   "Retry",   show=False),
        Binding("escape", "dismiss", "Back",    show=False),
        Binding("r",      "retry",   "Retry",   show=False),
    ]

    DEFAULT_CSS = """
    ResultsModal {
        align: center middle;
    }
    #results-box {
        width: 44;
        height: auto;
        background: #24283b;
        border: round #7aa2f7;
        padding: 2 4;
    }
    """

    def __init__(self, state: TypingState) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        with Static(id="results-box"):
            yield Static(id="content")

    def on_mount(self) -> None:
        s = self._state
        wpm  = s.wpm()
        raw  = s.raw_wpm()
        acc  = s.accuracy()
        elapsed = s.elapsed

        correct_words = sum(
            1 for i, w in enumerate(s.words[:s.current_word])
            if "".join(s.typed[i]) == w
        )
        total_words = s.current_word

        t = Text()
        t.append("  RESULTS\n\n", style="bold #7aa2f7")

        # Big WPM
        t.append(f"  {wpm:>6.1f}", style="bold #9ece6a")
        t.append("  wpm\n\n", style="#565f89")

        t.append(f"  raw wpm   ", style="#565f89")
        t.append(f"{raw:.1f}\n",  style="#c0caf5")
        t.append(f"  accuracy  ", style="#565f89")
        t.append(f"{acc:.1f}%\n", style="#c0caf5")
        t.append(f"  time      ", style="#565f89")
        t.append(f"{elapsed:.1f}s\n", style="#c0caf5")
        t.append(f"  words     ", style="#565f89")
        t.append(f"{correct_words}/{total_words}\n", style="#c0caf5")

        # Accuracy bar
        t.append(f"\n  ", style="")
        t.append(_bar(acc, 100), style="#7aa2f7")
        t.append(f"  {acc:.0f}%\n", style="#565f89")

        t.append(f"\n  [tab / r] retry    [esc] back\n", style="#565f89")

        self.query_one("#content", Static).update(t)

    def action_retry(self) -> None:
        self.dismiss("retry")
