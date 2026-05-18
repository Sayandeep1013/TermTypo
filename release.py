"""
TermTypo release script.

Usage:
    python release.py           # bump patch  (0.1.1 -> 0.1.2)
    python release.py minor     # bump minor  (0.1.x -> 0.2.0)
    python release.py major     # bump major  (0.x.x -> 1.0.0)

Reads PyPI token from .pypi_token (never committed to git).
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT   = Path(__file__).parent
CLIENT = ROOT / "client"

INIT_FILE  = CLIENT / "termtypo" / "__init__.py"
TOML_FILE  = CLIENT / "pyproject.toml"
TOKEN_FILE = ROOT / ".pypi_token"
README_SRC = ROOT / "README.md"
README_DST = CLIENT / "README.md"


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_token() -> str:
    if not TOKEN_FILE.exists():
        _die(f".pypi_token not found at {TOKEN_FILE}\n"
             "Create it with your PyPI API token on a single line.")
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        _die(".pypi_token is empty.")
    return token


def _read_version() -> str:
    text = INIT_FILE.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\'](.+?)["\']', text)
    if not m:
        _die("Could not find __version__ in __init__.py")
    return m.group(1)


def _bump(version: str, kind: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _write_version(new: str) -> None:
    for path, pattern in [
        (INIT_FILE, r'(__version__\s*=\s*["\'])(.+?)(["\'])'),
        (TOML_FILE, r'(^version\s*=\s*["\'])(.+?)(["\'])'),
    ]:
        text = path.read_text(encoding="utf-8")
        text = re.sub(pattern, lambda m: m.group(1) + new + m.group(3), text,
                      flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")


def _run(cmd: str, cwd: Path) -> None:
    result = subprocess.run(cmd, shell=True, cwd=str(cwd))
    if result.returncode != 0:
        _die(f"Command failed: {cmd}")


def _die(msg: str) -> None:
    print(f"\n  ERROR: {msg}\n")
    sys.exit(1)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    bump_kind = sys.argv[1].lower() if len(sys.argv) > 1 else "patch"
    if bump_kind not in ("patch", "minor", "major"):
        print("Usage: python release.py [patch|minor|major]")
        sys.exit(1)

    token       = _read_token()
    old_version = _read_version()
    new_version = _bump(old_version, bump_kind)

    print(f"\n  TermTypo release")
    print(f"  {old_version}  ->  {new_version}  ({bump_kind} bump)")
    print()

    # Confirm
    answer = input("  Proceed? [y/N] ").strip().lower()
    if answer != "y":
        print("  Cancelled.")
        sys.exit(0)

    # 1. Bump version in both files
    _write_version(new_version)
    print(f"  [1/4] Version bumped to {new_version}")

    # 2. Sync README into the package folder
    shutil.copy(README_SRC, README_DST)
    print("  [2/4] README synced")

    # 3. Clean old build artefacts and rebuild
    for d in [CLIENT / "dist", CLIENT / "build"]:
        if d.exists():
            shutil.rmtree(d)
    _run("python -m build", cwd=CLIENT)
    print("  [3/4] Package built")

    # 4. Upload to PyPI (token passed via env vars — no interactive prompt)
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = token
    result = subprocess.run(
        "twine upload dist/*",
        shell=True,
        cwd=str(CLIENT),
        env=env,
    )
    if result.returncode != 0:
        _die("Upload failed — check your token and internet connection.")

    print(f"  [4/4] Uploaded\n")
    print(f"  termtypo v{new_version} is live on PyPI.")
    print(f"  Users update with:  pip install --upgrade termtypo\n")


if __name__ == "__main__":
    main()
