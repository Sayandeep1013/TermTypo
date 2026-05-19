from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static
from textual.binding import Binding
from rich.text import Text
from rich.align import Align

from termtypo.widgets.ascii_header import AsciiHeader
from termtypo.services.auth_service import current_user


MENU_ITEMS = [
    ("s", "Solo Practice",   "solo"),
    ("r", "Ranked Match",    "ranked"),
    ("c", "Create Room",     "create_room"),
    ("j", "Join Room",       "join_room"),
    ("l", "Leaderboard",     "leaderboard"),
    ("a", "Profile / Login", "account"),
    ("q", "Quit",            "quit"),
]


class HomeMenu(Static):
    DEFAULT_CSS = """
    HomeMenu {
        height: auto;
        padding: 0 4;
        content-align: center middle;
    }
    """

    def render(self):
        user = current_user()
        text = Text()
        for key, label, _ in MENU_ITEMS:
            if key == "a" and user:
                label = "Profile / Logout"
            text.append(f"  {label:<30}", style="#c0caf5")
            text.append(f"{key}\n", style="bold #7aa2f7")
        return Align(text, align="center")


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        padding: 0 2;
        color: #565f89;
        background: #1a1b26;
    }
    """

    def on_mount(self) -> None:
        self._refresh_user()

    def _refresh_user(self) -> None:
        user = current_user()
        from termtypo import __version__
        if user:
            email = user.get("email", "")
            name = user.get("meta", {}).get("name") or email
            self.update(f"  ⚡ Logged in as {name}  ·  v{__version__}")
        else:
            self.update(f"  ⚡ Guest mode — login to access multiplayer  ·  v{__version__}")


class HomeScreen(Screen):
    BINDINGS = [
        Binding("s", "go_solo",        "Solo",        show=False),
        Binding("r", "go_ranked",      "Ranked",      show=False),
        Binding("c", "go_create_room", "Create Room", show=False),
        Binding("j", "go_join_room",   "Join Room",   show=False),
        Binding("l", "go_leaderboard", "Leaderboard", show=False),
        Binding("a", "go_account",     "Account",     show=False),
        Binding("q", "quit",           "Quit",        show=False),
    ]

    DEFAULT_CSS = """
    HomeScreen {
        background: #1a1b26;
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield AsciiHeader()
        yield HomeMenu()
        yield StatusBar()

    def on_screen_resume(self) -> None:
        self.query_one(StatusBar)._refresh_user()
        self.query_one(HomeMenu).refresh()

    # ── actions ──────────────────────────────────────────────────────────────

    def action_go_solo(self) -> None:
        self.app.push_screen("solo")

    def action_go_ranked(self) -> None:
        user = current_user()
        if not user:
            self.app.notify("Login required for Ranked mode.", severity="warning")
            return
        from termtypo.screens.mode_select import ModeSelectScreen
        from termtypo.screens.matchmaking import MatchmakingScreen

        def _on_mode(mode: str | None) -> None:
            if mode:
                self.app.push_screen(MatchmakingScreen(mode=mode))

        self.app.push_screen(ModeSelectScreen(default="words_50"), _on_mode)

    def action_go_create_room(self) -> None:
        user = current_user()
        if not user:
            self.app.notify("Login required to create a room.", severity="warning")
            return
        from termtypo.screens.room import RoomScreen
        self.app.push_screen(RoomScreen())

    def action_go_join_room(self) -> None:
        user = current_user()
        if not user:
            self.app.notify("Login required to join a room.", severity="warning")
            return
        from termtypo.screens.room import RoomScreen
        room = RoomScreen()
        self.app.push_screen(room)
        # Immediately put them in join view
        def _set_join():
            room._show_join()
        self.app.call_after_refresh(_set_join)

    def action_go_leaderboard(self) -> None:
        self.app.push_screen("leaderboard")

    def action_go_account(self) -> None:
        user = current_user()
        if user:
            self.app.push_screen("profile")
        else:
            self.app.push_screen("auth")

    def action_quit(self) -> None:
        self.app.exit()
