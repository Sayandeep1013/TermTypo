"""Global leaderboard — top players by ELO per mode."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text
from rich.table import Table
from rich import box

MODES = ["words_10", "words_25", "words_50", "words_100", "time_10", "time_30", "time_60"]
DEFAULT_MODE = "words_50"

TIER_THRESHOLDS = [
    (1500, "Master",   "#e0af68"),
    (1200, "Diamond",  "#7dcfff"),
    (900,  "Platinum", "#9ece6a"),
    (600,  "Gold",     "#e0af68"),
    (300,  "Silver",   "#c0caf5"),
    (0,    "Bronze",   "#bb9af7"),
]


def _rank(elo: int) -> tuple[str, str]:
    """Returns (label, colour)."""
    for threshold, name, colour in TIER_THRESHOLDS:
        if elo >= threshold:
            sub = min((elo - threshold) // 100 + 1, 3)
            has_sub = threshold < 1200
            label = f"{name} {'I' * sub}" if has_sub else name
            return label, colour
    return "Bronze I", "#bb9af7"


class LeaderboardScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back",   "Back",      show=False),
        Binding("right",  "next_mode", "Next mode", show=False),
        Binding("left",   "prev_mode", "Prev mode", show=False),
    ]

    DEFAULT_CSS = """
    LeaderboardScreen {
        background: #1a1b26;
        layout: vertical;
    }
    #lb-header {
        height: 3;
        padding: 1 4;
        background: #24283b;
        color: #7aa2f7;
    }
    #lb-body {
        height: 1fr;
        padding: 1 4;
    }
    #lb-content {
        width: 100%;
        height: auto;
    }
    #lb-hint {
        height: 1;
        dock: bottom;
        padding: 0 4;
        color: #565f89;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode = DEFAULT_MODE
        self._rows: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Static(id="lb-header")
        with VerticalScroll(id="lb-body"):
            yield Static(id="lb-content")
        yield Static("[esc] back   [← →] change mode", id="lb-hint")

    def on_mount(self) -> None:
        self._update_header()
        self._load()

    def _update_header(self) -> None:
        t = Text()
        t.append("  LEADERBOARD   ", style="bold #7aa2f7")
        for m in MODES:
            if m == self._mode:
                t.append(m, style="bold #7aa2f7 underline")
            else:
                t.append(m, style="#565f89")
            t.append("  ")
        self.query_one("#lb-header", Static).update(t)

    def _load(self) -> None:
        self.query_one("#lb-content", Static).update(
            Text("  Loading…", style="#565f89")
        )
        self.run_worker(self._fetch, exclusive=True, thread=True)

    def _fetch(self) -> None:
        from termtypo.services.supabase_client import get_client
        from termtypo.services.auth_service import current_user
        try:
            client = get_client()
            res = (
                client.table("user_ratings")
                .select("elo, wins, losses, user_id, profiles(username, display_name)")
                .eq("mode", self._mode)
                .order("elo", desc=True)
                .limit(25)
                .execute()
            )
            self._rows = res.data or []
            me = current_user()
            self._my_id = me["id"] if me else None
        except Exception as e:
            self._rows = []
            self._my_id = None
        self.app.call_from_thread(self._update_display)

    def _update_display(self) -> None:
        if not self._rows:
            self.query_one("#lb-content", Static).update(
                Text("  No players ranked yet in this mode.\n\n  "
                     "Complete a ranked match to appear here.", style="#565f89")
            )
            return

        table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold #565f89",
            border_style="#24283b",
            padding=(0, 1),
        )
        table.add_column("#",        style="#565f89", width=4,  justify="right")
        table.add_column("Player",   style="#c0caf5", width=20)
        table.add_column("Rank",     style="#7aa2f7", width=14)
        table.add_column("ELO",      style="#c0caf5", width=6,  justify="right")
        table.add_column("W",        style="#9ece6a", width=5,  justify="right")
        table.add_column("L",        style="#f7768e", width=5,  justify="right")
        table.add_column("W/L",      style="#565f89", width=7,  justify="right")

        for i, row in enumerate(self._rows, 1):
            profile = row.get("profiles") or {}
            name    = profile.get("display_name") or profile.get("username") or "—"
            elo     = row["elo"]
            wins    = row["wins"]
            losses  = row["losses"]
            wl      = f"{wins/(wins+losses)*100:.0f}%" if (wins + losses) > 0 else "—"
            rank_label, rank_colour = _rank(elo)

            is_me = (row.get("user_id") == getattr(self, "_my_id", None))
            row_style = "bold" if is_me else ""

            pos_text = f"{'→' if is_me else ' '}{i}"
            table.add_row(
                pos_text, name,
                Text(rank_label, style=rank_colour),
                str(elo), str(wins), str(losses), wl,
                style=row_style,
            )

        self.query_one("#lb-content", Static).update(table)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_next_mode(self) -> None:
        idx = MODES.index(self._mode)
        self._mode = MODES[(idx + 1) % len(MODES)]
        self._update_header()
        self._load()

    def action_prev_mode(self) -> None:
        idx = MODES.index(self._mode)
        self._mode = MODES[(idx - 1) % len(MODES)]
        self._update_header()
        self._load()
