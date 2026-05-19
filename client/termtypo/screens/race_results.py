"""Race results screen — shown after a 1v1 finishes."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text

from termtypo.services.race_service import get_user_elo


TIER_THRESHOLDS = [
    (1500, "Master"),
    (1200, "Diamond"),
    (900,  "Platinum"),
    (600,  "Gold"),
    (300,  "Silver"),
    (0,    "Bronze"),
]


def _rank_label(elo: int) -> str:
    for threshold, name in TIER_THRESHOLDS:
        if elo >= threshold:
            sub = min((elo - threshold) // 100 + 1, 3)
            has_sub = threshold < 1200
            return f"{name} {'I' * sub}" if has_sub else name
    return "Bronze I"


class RaceResultsScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_home",  "Home",   show=False),
        Binding("r",      "rematch",  "Rematch", show=False),
    ]

    DEFAULT_CSS = """
    RaceResultsScreen {
        background: #1a1b26;
        align: center middle;
    }
    #results-box {
        width: 52;
        height: auto;
        border: round #7aa2f7;
        padding: 2 4;
        background: #24283b;
    }
    """

    def __init__(
        self,
        match_id: str,
        ranked: bool,
        i_won: bool,
        my_wpm: float,
        my_acc: float,
        opp_wpm: float,
        mode: str,
        user_id: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._match_id = match_id
        self._ranked = ranked
        self._i_won = i_won
        self._my_wpm = my_wpm
        self._my_acc = my_acc
        self._opp_wpm = opp_wpm
        self._mode = mode
        self._user_id = user_id

    def compose(self) -> ComposeResult:
        with Static(id="results-box"):
            yield Static(id="content")

    def on_mount(self) -> None:
        new_elo = get_user_elo(self._user_id, self._mode) if self._ranked else None
        old_elo = new_elo - (30 if self._i_won else -30) if new_elo is not None else None
        self._build(new_elo, old_elo)

    def _build(self, new_elo: int | None, old_elo: int | None) -> None:
        t = Text()

        if self._i_won:
            t.append("  VICTORY\n\n", style="bold #9ece6a")
        else:
            t.append("  DEFEAT\n\n", style="bold #f7768e")

        t.append(f"  your wpm   ", style="#565f89")
        t.append(f"{self._my_wpm:.1f}\n", style="bold #c0caf5")
        t.append(f"  accuracy   ", style="#565f89")
        t.append(f"{self._my_acc:.1f}%\n", style="#c0caf5")
        t.append(f"  opp wpm    ", style="#565f89")
        t.append(f"{self._opp_wpm:.1f}\n\n", style="#565f89")

        if self._ranked and new_elo is not None and old_elo is not None:
            delta = new_elo - old_elo
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            delta_style = "#9ece6a" if delta > 0 else "#f7768e"
            t.append(f"  elo   ", style="#565f89")
            t.append(f"{old_elo}", style="#c0caf5")
            t.append(f"  →  ", style="#565f89")
            t.append(f"{new_elo}", style="#c0caf5")
            t.append(f"  ({delta_str})\n", style=delta_style)
            t.append(f"  rank  ", style="#565f89")
            t.append(f"{_rank_label(new_elo)}\n\n", style="bold #7aa2f7")
        elif not self._ranked:
            t.append("  (unranked match — no ELO change)\n\n", style="#565f89")

        t.append("  [r] rematch    [esc] home\n", style="#565f89")
        self.query_one("#content", Static).update(t)

    def action_go_home(self) -> None:
        n = len(self.app.screen_stack) - 1
        for _ in range(n):
            self.app.pop_screen()

    def action_rematch(self) -> None:
        n = len(self.app.screen_stack) - 1
        for _ in range(n):
            self.app.pop_screen()
        from termtypo.screens.matchmaking import MatchmakingScreen
        self.app.push_screen(MatchmakingScreen(mode=self._mode))
