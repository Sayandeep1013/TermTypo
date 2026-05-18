"""Player profile & stats — logged-in user's personal dashboard."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static
from rich.console import Group
from rich.text import Text
from rich.table import Table
from rich import box

TIER_THRESHOLDS = [
    (1500, "Master",   "#e0af68"),
    (1200, "Diamond",  "#7dcfff"),
    (900,  "Platinum", "#9ece6a"),
    (600,  "Gold",     "#e0af68"),
    (300,  "Silver",   "#c0caf5"),
    (0,    "Bronze",   "#bb9af7"),
]

MODE_ORDER = ["words_10", "words_25", "words_50", "words_100", "time_10", "time_30", "time_60"]


def _rank(elo: int) -> tuple[str, str]:
    for threshold, name, colour in TIER_THRESHOLDS:
        if elo >= threshold:
            sub = min((elo - threshold) // 100 + 1, 3)
            has_sub = threshold < 1200
            label = f"{name} {'I' * sub}" if has_sub else name
            return label, colour
    return "Bronze I", "#bb9af7"


def _bar(value: float, max_val: float, width: int = 20) -> str:
    filled = int((value / max(max_val, 1)) * width)
    filled = min(filled, width)
    return "━" * filled + "░" * (width - filled)


class ProfileScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back", show=False),
        Binding("l",      "logout",  "Logout", show=False),
    ]

    DEFAULT_CSS = """
    ProfileScreen {
        background: #1a1b26;
        layout: vertical;
    }
    #profile-header {
        height: 5;
        padding: 1 4;
        background: #24283b;
    }
    #profile-body {
        height: 1fr;
        padding: 1 4;
    }
    #profile-content {
        width: 100%;
        height: auto;
    }
    #profile-hint {
        height: 1;
        dock: bottom;
        padding: 0 4;
        color: #565f89;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="profile-header")
        with VerticalScroll(id="profile-body"):
            yield Static(id="profile-content")
        yield Static("[esc] back   [l] logout", id="profile-hint")

    def on_mount(self) -> None:
        from termtypo.services.auth_service import current_user
        user = current_user()
        if not user:
            self.query_one("#profile-header", Static).update(
                Text("  Not logged in.", style="#565f89")
            )
            return
        self._user = user
        self._render_header(user)
        self.run_worker(self._fetch, exclusive=True, thread=True)

    def _render_header(self, user: dict) -> None:
        name  = user.get("meta", {}).get("name") or user.get("email", "")
        email = user.get("email", "")
        t = Text()
        t.append(f"  {name}\n", style="bold #7aa2f7")
        t.append(f"  {email}\n", style="#565f89")
        self.query_one("#profile-header", Static).update(t)

    def _fetch(self) -> None:
        from termtypo.services.auth_service import get_authed_client
        client = get_authed_client()
        if not client:
            return
        uid = self._user["id"]
        try:
            ratings_res = (
                client.table("user_ratings")
                .select("mode, elo, wins, losses")
                .eq("user_id", uid)
                .execute()
            )
            self._ratings = {r["mode"]: r for r in (ratings_res.data or [])}

            solo_res = (
                client.table("solo_results")
                .select("mode, wpm, raw_wpm, accuracy, created_at")
                .eq("user_id", uid)
                .order("created_at", desc=True)
                .limit(10)
                .execute()
            )
            self._recent = solo_res.data or []

            pb_res = (
                client.table("solo_results")
                .select("mode, wpm")
                .eq("user_id", uid)
                .order("wpm", desc=True)
                .limit(1)
                .execute()
            )
            self._best_wpm = pb_res.data[0]["wpm"] if pb_res.data else None
            self._best_mode = pb_res.data[0]["mode"] if pb_res.data else None

        except Exception:
            self._ratings = {}
            self._recent  = []
            self._best_wpm = None
            self._best_mode = None

        self.app.call_from_thread(self._render_body)

    def _render_body(self) -> None:
        parts = []

        # Personal best
        if self._best_wpm:
            pb = Text()
            pb.append("  personal best  ", style="#565f89")
            pb.append(f"{self._best_wpm:.1f} wpm", style="bold #9ece6a")
            pb.append(f"  ({self._best_mode})\n\n", style="#565f89")
            parts.append(pb)

        # Ratings heading
        parts.append(Text("  RATINGS\n", style="bold #7aa2f7"))

        # Ratings table
        ratings_table = Table(
            box=box.SIMPLE, show_header=True,
            header_style="bold #565f89",
            padding=(0, 1),
        )
        ratings_table.add_column("Mode",     width=12)
        ratings_table.add_column("Rank",     width=14)
        ratings_table.add_column("ELO",      width=6,  justify="right")
        ratings_table.add_column("W",        width=4,  justify="right")
        ratings_table.add_column("L",        width=4,  justify="right")
        ratings_table.add_column("Progress", width=22)

        for mode in MODE_ORDER:
            r = self._ratings.get(mode)
            if r:
                elo    = r["elo"]
                wins   = r["wins"]
                losses = r["losses"]
                label, colour = _rank(elo)
                tier_progress = (elo % 300) / 300
                bar = _bar(tier_progress, 1.0, 18)
                ratings_table.add_row(
                    mode,
                    Text(label, style=colour),
                    str(elo), str(wins), str(losses),
                    Text(bar, style="#7aa2f7"),
                )
            else:
                ratings_table.add_row(
                    mode,
                    Text("Unranked", style="#565f89"),
                    "—", "0", "0", "",
                )

        parts.append(ratings_table)
        parts.append(Text("\n  RECENT SOLO\n", style="bold #7aa2f7"))

        if self._recent:
            solo_table = Table(
                box=box.SIMPLE, show_header=True,
                header_style="bold #565f89",
                padding=(0, 1),
            )
            solo_table.add_column("Mode", width=12)
            solo_table.add_column("WPM",  width=7, justify="right")
            solo_table.add_column("Raw",  width=7, justify="right")
            solo_table.add_column("Acc",  width=7, justify="right")
            for r in self._recent:
                solo_table.add_row(
                    r["mode"],
                    f"{r['wpm']:.1f}",
                    f"{r['raw_wpm']:.1f}",
                    f"{r['accuracy']:.1f}%",
                )
            parts.append(solo_table)
        else:
            parts.append(Text("  No solo results yet.\n", style="#565f89"))

        self.query_one("#profile-content", Static).update(Group(*parts))

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_logout(self) -> None:
        from termtypo.services.auth_service import logout
        logout()
        self.app.notify("Logged out.", severity="information")
        self.app.pop_screen()
