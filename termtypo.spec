# termtypo.spec — PyInstaller build config
#
# Build:  pyinstaller termtypo.spec --clean
# Output: dist/termtypo.exe  (Windows)
#         dist/termtypo      (macOS / Linux)
#
# pyinstaller-hooks-contrib (installed as a PyInstaller dep) provides
# automatic hooks for textual, rich, supabase, etc. — no collect_all needed.

import sys
from pathlib import Path

ROOT   = Path(SPECPATH)          # directory containing this .spec file
CLIENT = ROOT / "client"
ENTRY  = str(CLIENT / "termtypo" / "__main__.py")

block_cipher = None

a = Analysis(
    [ENTRY],
    pathex=[str(CLIENT)],
    binaries=[],
    datas=[
        # Word list assets must be explicitly included
        (str(CLIENT / "termtypo" / "assets"), "termtypo/assets"),
    ],
    hiddenimports=[
        # All termtypo screens/services/widgets (dynamically loaded, PyInstaller misses them)
        "termtypo",
        "termtypo.app",
        "termtypo.config",
        "termtypo.updater",
        "termtypo.screens.home",
        "termtypo.screens.solo",
        "termtypo.screens.auth",
        "termtypo.screens.results",
        "termtypo.screens.matchmaking",
        "termtypo.screens.race",
        "termtypo.screens.race_results",
        "termtypo.screens.room",
        "termtypo.screens.leaderboard",
        "termtypo.screens.profile",
        "termtypo.screens.mode_select",
        "termtypo.widgets.ascii_header",
        "termtypo.widgets.typing_area",
        "termtypo.services.auth_service",
        "termtypo.services.matchmaking_service",
        "termtypo.services.race_service",
        "termtypo.services.supabase_client",
        "termtypo.services.word_service",
        # Third-party (hooks-contrib may not cover all of these)
        "platformdirs",
        "dotenv",
        "httpx",
        "httpx._transports.default",
        "httpx._transports.asgi",
        "supabase",
        "supabase_auth",
        "postgrest",
        "realtime",
        "storage3",
        "websockets",
        "websockets.legacy",
        "websockets.legacy.client",
        "pydantic",
        "pydantic.v1",
        "yarl",
        "aiohttp",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "PyQt5", "PyQt6", "wx", "gi",
        "PySide2", "PySide6", "matplotlib", "numpy",
        "pandas", "scipy", "PIL",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="termtypo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,      # MUST be True — terminal app
    icon=None,
)
