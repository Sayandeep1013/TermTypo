"""Live keyboard visualisation — highlights each key as you type it."""
from __future__ import annotations

from textual.app import RenderResult
from textual.reactive import reactive
from textual.widget import Widget
from rich.text import Text

# Standard QWERTY layout
_ROWS: list[list[str]] = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]

# Top-row number keys (shown as a 4th row for completeness)
_INDENT = ["  ", "   ", "     "]   # stagger per row


class KeyboardWidget(Widget):
    """Shows a compact QWERTY keyboard that highlights the last typed key."""

    DEFAULT_CSS = """
    KeyboardWidget {
        height: 5;
        content-align: center middle;
    }
    """

    # Reactive so Textual schedules a refresh whenever they change
    last_char:    reactive[str]  = reactive("")
    last_correct: reactive[bool] = reactive(True)

    def set_key(self, char: str, correct: bool) -> None:
        self.last_char    = char.lower()
        self.last_correct = correct

    def render(self) -> RenderResult:
        t = Text(justify="center")

        for ri, row in enumerate(_ROWS):
            t.append(_INDENT[ri])
            for key in row:
                if key == self.last_char:
                    clr = "#9ece6a" if self.last_correct else "#f7768e"
                    t.append(f"[{key.upper()}]", style=f"bold {clr}")
                else:
                    t.append(f" {key.upper()} ", style="#2a2b3d" if key not in "etaoins" else "#565f89")
            t.append("\n")

        # Space bar
        space_clr = ""
        if self.last_char == " ":
            space_clr = "#9ece6a" if self.last_correct else "#f7768e"
            t.append("       [        space        ]     ", style=f"bold {space_clr}")
        else:
            t.append("       [        space        ]     ", style="#2a2b3d")

        return t
