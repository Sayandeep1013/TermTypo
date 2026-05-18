import os
import json
import socket
from pathlib import Path
from dotenv import load_dotenv
from platformdirs import user_config_dir

# Load .env (dev only — not present in installed packages)
_here = Path(__file__).parent
for _candidate in [_here.parent.parent / ".env", _here.parent / ".env", Path(".env")]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break

# ── Public credentials ────────────────────────────────────────────────────────
# The anon key is a read-only public key gated by RLS policies.
# Safe to ship with the app — developers can override via .env.
SUPABASE_URL: str = os.environ.get(
    "SUPABASE_URL",
    "https://gaaqylbllnwllcvawnbt.supabase.co",
)
SUPABASE_ANON_KEY: str = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdhYXF5bGJsbG53bGxjdmF3bmJ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkwMjQ4NDMsImV4cCI6MjA5NDYwMDg0M30"
    ".U9OwpQH9BpYW2cYRXdE8HWgt1NArpBn_tNFFNn_Orz0",
)

# ── OAuth callback ports ──────────────────────────────────────────────────────
# We try each in order and use the first free one.
# ALL of these must be registered in Supabase Auth → URL Configuration → Redirect URLs
# as:  http://localhost:<port>/auth/callback
OAUTH_CALLBACK_PORTS = [54321, 54322, 54323, 54324, 54325]


def find_free_oauth_port() -> int | None:
    """Return the first port from OAUTH_CALLBACK_PORTS that is not in use."""
    for port in OAUTH_CALLBACK_PORTS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return None


# ── Local config dir ──────────────────────────────────────────────────────────
APP_NAME   = "termtypo"
CONFIG_DIR = Path(user_config_dir(APP_NAME, APP_NAME))
SESSION_FILE = CONFIG_DIR / "session.json"


def save_session(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(data), encoding="utf-8")


def load_session() -> dict | None:
    if not SESSION_FILE.exists():
        return None
    try:
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
