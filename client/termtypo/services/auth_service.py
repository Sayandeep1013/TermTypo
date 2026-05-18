"""Google OAuth via Supabase — browser-based PKCE flow for terminal clients."""
from __future__ import annotations

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from termtypo.config import (
    CONFIG_DIR, OAUTH_CALLBACK_PORTS, clear_session,
    find_free_oauth_port, load_session, save_session,
)
from termtypo.services.supabase_client import get_client

_LOG = CONFIG_DIR / "auth.log"


def _log(msg: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with _LOG.open("a", encoding="utf-8") as f:
        import datetime
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")


# ── Session helpers ───────────────────────────────────────────────────────────

def current_user() -> dict | None:
    """Return user info from local session file — no network call needed."""
    data = load_session()
    if not data or "user_id" not in data:
        return None
    return {
        "id":    data["user_id"],
        "email": data.get("email", ""),
        "meta":  {"name": data.get("name"), "avatar_url": data.get("avatar_url")},
    }


def refresh_session() -> bool:
    """
    Try to refresh the access token using the stored refresh token.
    Supabase access tokens expire after 1 hour; refresh tokens last 7 days.
    Returns True if refresh succeeded, False if the user must log in again.
    """
    data = load_session()
    if not data or "refresh_token" not in data:
        return False
    try:
        client = get_client()
        response = client.auth.refresh_session(data["refresh_token"])
        if response and response.session:
            data["access_token"]  = response.session.access_token
            data["refresh_token"] = response.session.refresh_token
            save_session(data)
            _log("Token refreshed successfully")
            return True
    except Exception as e:
        _log(f"Token refresh failed: {e} — session cleared")
        clear_session()
    return False


def get_authed_client():
    """
    Return a Supabase client with the current session set.
    Automatically attempts a token refresh on the first 401-style failure.
    Returns None if the user is not logged in or refresh fails.
    """
    data = load_session()
    if not data:
        return None
    client = get_client()
    try:
        client.auth.set_session(data["access_token"], data["refresh_token"])
        return client
    except Exception:
        # Token may be expired — try a refresh
        if refresh_session():
            data = load_session()
            try:
                client.auth.set_session(data["access_token"], data["refresh_token"])
                return client
            except Exception:
                pass
    return None


def logout() -> None:
    try:
        get_client().auth.sign_out()
    except Exception:
        pass
    clear_session()


def auth_log_path() -> Path:
    return _LOG


# ── OAuth browser flow ────────────────────────────────────────────────────────

def _make_handler(bucket: dict):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            bucket["code"]  = params.get("code",  [None])[0]
            bucket["error"] = params.get("error", [None])[0]
            _log(
                f"Callback received  path={self.path!r}  "
                f"code={'YES' if bucket['code'] else 'NO'}  "
                f"error={bucket['error']}"
            )
            html = (
                b"<html><body style='background:#1a1b26;color:#c0caf5;"
                b"font-family:monospace;padding:2rem'>"
                b"<h2>Login successful!</h2>"
                b"<p>You can close this tab and return to TermTypo.</p>"
                b"</body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, *_):
            pass

    return Handler


def login_with_google(on_success=None, on_error=None) -> None:
    """
    Opens the browser for Google OAuth (PKCE flow).
    Non-blocking — calls on_success(user_dict) or on_error(message) from a
    daemon thread.

    Edge cases handled:
    - Port 54321 busy  → tries 54322-54325 automatically
    - All ports busy   → calls on_error with a clear message
    - Browser fails    → on_error
    - User cancels     → on_error after HTTP server receives empty callback
    - Exchange fails   → on_error with full exception message in auth.log
    """
    port = find_free_oauth_port()
    if port is None:
        msg = (
            f"Could not bind to any OAuth callback port "
            f"({', '.join(str(p) for p in OAUTH_CALLBACK_PORTS)}). "
            f"Close applications using those ports and try again."
        )
        _log(f"No free port found: {msg}")
        if on_error:
            on_error(msg)
        return

    redirect_url = f"http://localhost:{port}/auth/callback"
    client = get_client()

    try:
        res = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url,
                "scopes": "email profile",
            },
        })
    except Exception as exc:
        _log(f"sign_in_with_oauth failed: {exc}")
        if on_error:
            on_error(str(exc))
        return

    _log(f"OAuth URL generated on port {port} (PKCE={'code_challenge' in res.url})")

    bucket: dict = {}

    def _run():
        try:
            try:
                webbrowser.open(res.url)
            except Exception as e:
                _log(f"webbrowser.open failed: {e}")
                if on_error:
                    on_error(f"Could not open browser automatically. "
                             f"Please visit:\n{res.url}")
                return

            server = HTTPServer(("localhost", port), _make_handler(bucket))
            server.serve_forever()

            code  = bucket.get("code")
            error = bucket.get("error")

            if error:
                _log(f"OAuth provider error: {error}")
                if on_error:
                    on_error(f"OAuth error: {error}")
                return

            if not code:
                _log("Callback received but no code — user may have cancelled")
                if on_error:
                    on_error("Login cancelled or no auth code received.")
                return

            _log(f"Exchanging code (len={len(code)}) with redirect_to={redirect_url}")
            session = client.auth.exchange_code_for_session({
                "auth_code":   code,
                "redirect_to": redirect_url,
            })

            if session and session.session:
                meta = session.user.user_metadata if session.user else {}
                save_session({
                    "access_token":  session.session.access_token,
                    "refresh_token": session.session.refresh_token,
                    "user_id":       session.user.id,
                    "email":         session.user.email,
                    "name":          (meta.get("full_name") or
                                      meta.get("name") or
                                      session.user.email),
                    "avatar_url":    meta.get("avatar_url"),
                })
                _log(f"Session saved for {session.user.email}")
                if on_success:
                    on_success(current_user())
            else:
                _log("exchange_code_for_session returned no session")
                if on_error:
                    on_error("Session exchange failed — see auth.log for details.")

        except Exception as exc:
            _log(f"Exception in OAuth thread: {type(exc).__name__}: {exc}")
            if on_error:
                on_error(f"{type(exc).__name__}: {exc}")

    threading.Thread(target=_run, daemon=True).start()
