"""Account / auth screen — login, logout, profile display."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text

from termtypo.services.auth_service import current_user, login_with_google, logout, auth_log_path


class AuthScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back",   show=False),
        Binding("l",      "login",   "Login",  show=False),
        Binding("o",      "logout",  "Logout", show=False),
    ]

    DEFAULT_CSS = """
    AuthScreen {
        background: #1a1b26;
        align: center middle;
    }
    #auth-panel {
        width: 50;
        height: auto;
        border: round #7aa2f7;
        padding: 2 4;
        background: #24283b;
    }
    """

    def compose(self) -> ComposeResult:
        with Static(id="auth-panel"):
            yield Static(id="auth-content")
        yield Static("  [esc] back", id="hint", classes="hint")

    def on_mount(self) -> None:
        self._update_auth_view()

    def on_screen_resume(self) -> None:
        self._update_auth_view()

    def _update_auth_view(self) -> None:
        user = current_user()
        content = self.query_one("#auth-content", Static)
        text = Text()
        text.append("  ACCOUNT\n\n", style="bold #7aa2f7")
        if user:
            name = user.get("meta", {}).get("name") or user.get("email", "")
            email = user.get("email", "")
            text.append(f"  Name    {name}\n", style="#c0caf5")
            text.append(f"  Email   {email}\n\n", style="#c0caf5")
            text.append("  [o] Logout\n", style="#e0af68")
        else:
            text.append("  Not logged in.\n\n", style="#565f89")
            text.append("  [l] Login with Google\n", style="#9ece6a")
            text.append("\n  Your browser will open for OAuth.\n", style="#565f89")
            text.append("  Stats and multiplayer require login.\n", style="#565f89")
        content.update(text)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_login(self) -> None:
        if current_user():
            self.app.notify("Already logged in.", severity="information")
            return
        self.app.notify(
            "Browser opening… complete Google login then return here.",
            severity="information",
            timeout=60,
        )
        login_with_google(
            on_success=self._on_login_success,
            on_error=self._on_login_error,
        )

    def _on_login_success(self, user: dict) -> None:
        name = user.get("meta", {}).get("name") or user.get("email", "")
        self.app.call_from_thread(self.app.notify, f"Welcome, {name}!", severity="information")
        self.app.call_from_thread(self._update_auth_view)

    def _on_login_error(self, msg: str) -> None:
        log = auth_log_path()
        full = f"Login failed: {msg}\n  Details in: {log}"
        self.app.call_from_thread(self.app.notify, full, severity="error", timeout=15)

    def action_logout(self) -> None:
        logout()
        self.app.notify("Logged out.", severity="information")
        self._update_auth_view()
