from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from termtypo.screens.home import HomeScreen
from termtypo.screens.solo import SoloScreen
from termtypo.screens.auth import AuthScreen
from termtypo.screens.results import ResultsModal
from termtypo.screens.matchmaking import MatchmakingScreen
from termtypo.screens.race import RaceScreen
from termtypo.screens.race_results import RaceResultsScreen
from termtypo.screens.room import RoomScreen
from termtypo.screens.leaderboard import LeaderboardScreen
from termtypo.screens.profile import ProfileScreen


class TermTypoApp(App):
    """TermTypo — terminal multiplayer typing test."""

    CSS = """
    Screen {
        background: #1a1b26;
        color: #c0caf5;
    }
    .hint {
        color: #565f89;
        height: 1;
        dock: bottom;
        padding: 0 2;
    }
    """

    # Only screens that never need constructor args go in SCREENS.
    # Screens that need args (MatchmakingScreen, RaceScreen, etc.) are pushed directly.
    SCREENS = {
        "home":        HomeScreen,
        "solo":        SoloScreen,
        "auth":        AuthScreen,
        "room":        RoomScreen,
        "leaderboard": LeaderboardScreen,
        "profile":     ProfileScreen,
    }

    BINDINGS = [Binding("ctrl+c", "quit", "Quit", show=False)]

    def on_mount(self) -> None:
        self.push_screen("home")
        from termtypo.updater import check_for_update
        check_for_update(self._on_update_available)

    def _on_update_available(self, latest: str) -> None:
        from termtypo import __version__
        self.call_from_thread(
            self.notify,
            f"Update available: v{latest} (you have v{__version__})"
            f" — run: pip install --upgrade termtypo",
            severity="information",
            timeout=12,
        )
