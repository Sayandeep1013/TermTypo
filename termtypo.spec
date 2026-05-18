# termtypo.spec  — PyInstaller build for Windows (.exe) and macOS (binary)
#
# Build commands:
#   Windows:  pyinstaller termtypo.spec
#   macOS:    pyinstaller termtypo.spec
#
# Output:  dist/termtypo.exe  (Windows)
#          dist/termtypo      (macOS / Linux)

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT   = Path(SPECPATH)          # project root (where this .spec lives)
CLIENT = ROOT / "client"

block_cipher = None

# Collect all Textual and Rich data files (CSS, themes, fonts, etc.)
textual_datas, textual_bins, textual_hidden = collect_all("textual")
rich_datas,    rich_bins,    rich_hidden    = collect_all("rich")

a = Analysis(
    [str(CLIENT / "termtypo" / "__main__.py")],
    pathex=[str(CLIENT)],
    binaries=textual_bins + rich_bins,
    datas=[
        # Word list assets
        (str(CLIENT / "termtypo" / "assets"), "termtypo/assets"),
        # Textual + Rich internal data (CSS, themes, etc.)
        *textual_datas,
        *rich_datas,
    ],
    hiddenimports=[
        # All termtypo modules (PyInstaller can miss dynamically-imported screens)
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
        # Third-party
        "platformdirs",
        "dotenv",
        "httpx",
        "httpx._transports.default",
        "supabase",
        "supabase_auth",
        "postgrest",
        "realtime",
        "storage3",
        "websockets",
        "websockets.legacy",
        "pydantic",
        "pydantic.v1",
        "yarl",
        *textual_hidden,
        *rich_hidden,
    ],
    hookspath=[],
    runtime_hooks=[],
    # Strip heavy unused packages to keep binary small
    excludes=["tkinter", "PyQt5", "PyQt6", "wx", "gi", "PySide2", "PySide6",
              "matplotlib", "numpy", "pandas", "scipy", "PIL"],
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
    console=True,          # MUST be True — this is a terminal/console app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
