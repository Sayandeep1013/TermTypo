"""Private room — create or join."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static, Input
from rich.text import Text

from termtypo.services.auth_service import current_user
from termtypo.services.matchmaking_service import create_room, get_room, create_private_match


class RoomScreen(Screen):
    """Combined create/join room screen."""

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=False),
    ]

    DEFAULT_CSS = """
    RoomScreen {
        background: #1a1b26;
        align: center middle;
    }
    #room-box {
        width: 52;
        height: auto;
        border: round #7aa2f7;
        padding: 2 4;
        background: #24283b;
    }
    #join-input {
        margin: 1 0;
        background: #1a1b26;
        border: round #565f89;
        color: #c0caf5;
    }
    #join-input:focus {
        border: round #7aa2f7;
    }
    """

    def __init__(self, mode: str = "words_50", **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode = mode
        self._view = "menu"   # "menu" | "create_waiting" | "join"
        self._room_code: str | None = None
        self._poll_handle = None

    def compose(self) -> ComposeResult:
        with Static(id="room-box"):
            yield Static(id="room-content")
            # Input starts non-focusable and hidden — only activated in join mode
            yield Input(placeholder="enter room code…", id="join-input",
                        disabled=True)
        yield Static("[esc] back", classes="hint")

    def on_mount(self) -> None:
        inp = self.query_one(Input)
        inp.display = False
        inp.disabled = True
        self._show_menu()

    # ── rendering ─────────────────────────────────────────────────────────────

    def _show_menu(self) -> None:
        self._view = "menu"
        t = Text()
        t.append("  PRIVATE ROOM\n\n", style="bold #7aa2f7")
        t.append(f"  mode   {self._mode}\n\n", style="#565f89")
        t.append("  [c] Create room\n", style="#9ece6a")
        t.append("  [j] Join room\n", style="#7dcfff")
        self.query_one("#room-content", Static).update(t)
        inp = self.query_one(Input)
        inp.display = False
        inp.disabled = True

    def _show_waiting(self, code: str) -> None:
        self._view = "create_waiting"
        t = Text()
        t.append("  PRIVATE ROOM\n\n", style="bold #7aa2f7")
        t.append("  Share this code with your friend:\n\n", style="#565f89")
        t.append(f"      {code}\n\n", style="bold #9ece6a")
        t.append("  Waiting for them to join…\n", style="#565f89")
        t.append("  [esc] cancel\n", style="#565f89")
        self.query_one("#room-content", Static).update(t)

    def _show_join(self) -> None:
        self._view = "join"
        t = Text()
        t.append("  JOIN ROOM\n\n", style="bold #7aa2f7")
        t.append("  Enter the 6-character room code:\n", style="#565f89")
        self.query_one("#room-content", Static).update(t)
        inp = self.query_one(Input)
        inp.display = True
        inp.disabled = False
        inp.value = ""
        inp.focus()

    # ── key handling (menu only — Input handles its own keys in join mode) ─────

    def on_key(self, event) -> None:
        if self._view != "menu":
            return
        if event.key == "c":
            self._do_create()
            event.stop()
        elif event.key == "j":
            self._show_join()
            event.stop()

    def on_input_changed(self, event: Input.Changed) -> None:
        # Auto-uppercase as the user types
        val = event.value.upper()
        if val != event.value:
            event.input.value = val

    def on_input_submitted(self, event: Input.Submitted) -> None:
        code = event.value.strip().upper()
        if len(code) == 6:
            self._do_join(code)
        else:
            self.app.notify("Code must be 6 characters.", severity="warning")

    # ── create ────────────────────────────────────────────────────────────────

    def _do_create(self) -> None:
        user = current_user()
        if not user:
            self.app.notify("Login required.", severity="warning")
            return
        from termtypo.screens.mode_select import ModeSelectScreen

        def _on_mode(mode: str | None) -> None:
            if not mode:
                return
            self._mode = mode
            code = create_room(user["id"], mode)
            if not code:
                self.app.notify("Failed to create room — are you logged in?", severity="error")
                return
            self._room_code = code
            self._show_waiting(code)
            self._poll_handle = self.set_interval(2.0, lambda: self._poll_for_guest(code, user["id"]))

        self.app.push_screen(ModeSelectScreen(default=self._mode), _on_mode)

    def _poll_for_guest(self, code: str, host_id: str) -> None:
        from termtypo.services.auth_service import get_authed_client
        client = get_authed_client()
        if not client:
            return
        try:
            room_res = client.table("rooms").select("match_id, status").eq("code", code).maybe_single().execute()
            if not room_res or not room_res.data:
                return
            room = room_res.data
            if room.get("status") == "active" and room.get("match_id"):
                match_id = room["match_id"]
                parts_res = client.table("match_participants").select("user_id").eq("match_id", match_id).execute()
                guest_id = next((p["user_id"] for p in (parts_res.data or []) if p["user_id"] != host_id), None)
                if guest_id:
                    if self._poll_handle:
                        self._poll_handle.stop()
                    self._enter_race(match_id, host_id, self._mode)
        except Exception:
            pass

    # ── join ──────────────────────────────────────────────────────────────────

    def _do_join(self, code: str) -> None:
        user = current_user()
        if not user:
            self.app.notify("Login required.", severity="warning")
            return
        from termtypo.services.auth_service import get_authed_client
        from termtypo.services.word_service import get_words, get_timed_words
        client = get_authed_client()
        if not client:
            self.app.notify("Not logged in properly — please re-login.", severity="error")
            return

        # Generate passage client-side (PG can't access our word lists)
        room = get_room(code)
        if not room:
            self.app.notify("Room not found or already started.", severity="error")
            return
        mode = room.get("mode", "words_50")
        if mode.startswith("words_"):
            passage = " ".join(get_words(int(mode.split("_")[1])))
        else:
            passage = " ".join(get_timed_words(int(mode.split("_")[1])))

        try:
            res = client.rpc("join_private_room", {
                "p_code":     code.upper(),
                "p_guest_id": user["id"],
                "p_passage":  passage,
            }).execute()
            data = res.data or {}
            if "error" in data:
                self.app.notify(f"Join failed: {data['error']}", severity="error")
                return
            match_id = data.get("match_id")
            mode = data.get("mode", mode)
            if not match_id:
                self.app.notify("Failed to start match.", severity="error")
                return
            self._enter_race(match_id, user["id"], mode)
        except Exception as e:
            self.app.notify(f"Failed to start match: {str(e)[:50]}", severity="error")

    # ── enter race ────────────────────────────────────────────────────────────

    def _enter_race(self, match_id: str, my_id: str, mode: str) -> None:
        from termtypo.screens.race import RaceScreen
        from termtypo.services.auth_service import get_authed_client
        client = get_authed_client()
        passage = ""
        if client:
            try:
                res = client.table("matches").select("passage").eq("id", match_id).maybe_single().execute()
                passage = (res.data or {}).get("passage", "") if res else ""
            except Exception:
                pass
        self.app.push_screen(RaceScreen(match_id, passage, my_id, mode, ranked=False))

    # ── actions ───────────────────────────────────────────────────────────────

    def action_go_back(self) -> None:
        if self._poll_handle:
            self._poll_handle.stop()
        self.app.pop_screen()
