"""
TermTypo release script — one command does everything.

Usage:
    python release.py           # patch bump  (0.1.x -> 0.1.x+1)
    python release.py minor     # minor bump  (0.x.y -> 0.x+1.0)
    python release.py major     # major bump  (x.y.z -> x+1.0.0)

What it does (in order):
    1. Bump __version__ in __init__.py and pyproject.toml
    2. Sync README.md into client/
    3. Build PyPI wheel + sdist
    4. Upload to PyPI  (reads token from .pypi_token)
    5. git commit "Release vX.Y.Z"
    6. git tag  vX.Y.Z
    7. git push + git push --tags
       → GitHub Actions auto-builds Windows .exe + macOS binary
         and attaches them to a GitHub Release page.
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
        _die(f".pypi_token not found.\nCreate it with your PyPI API token on a single line.")
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
    if kind == "major": return f"{major + 1}.0.0"
    if kind == "minor": return f"{major}.{minor + 1}.0"
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


def _run(cmd: str, cwd: Path = ROOT, check: bool = True) -> int:
    result = subprocess.run(cmd, shell=True, cwd=str(cwd))
    if check and result.returncode != 0:
        _die(f"Command failed: {cmd}")
    return result.returncode


def _has_remote() -> bool:
    r = subprocess.run("git remote get-url origin", shell=True, cwd=str(ROOT),
                       capture_output=True)
    return r.returncode == 0


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
    tag         = f"v{new_version}"
    has_remote  = _has_remote()

    print(f"\n  TermTypo release")
    print(f"  {old_version}  ->  {new_version}  ({bump_kind})")
    if has_remote:
        print(f"  Will push tag {tag} → GitHub Actions builds exe/binary")
    else:
        print(f"  No git remote — skipping git push (add origin to enable)")
    print()

    answer = input("  Proceed? [y/N] ").strip().lower()
    if answer != "y":
        print("  Cancelled.")
        sys.exit(0)

    # ── 1. Version bump ───────────────────────────────────────────────────────
    _write_version(new_version)
    print(f"  [1/7] Version bumped to {new_version}")

    # ── 2. Sync README ────────────────────────────────────────────────────────
    shutil.copy(README_SRC, README_DST)
    print(f"  [2/7] README synced")

    # ── 3. Build PyPI artefacts ───────────────────────────────────────────────
    for d in [CLIENT / "dist", CLIENT / "build"]:
        if d.exists():
            shutil.rmtree(d)
    _run("python -m build", cwd=CLIENT)
    print(f"  [3/7] Package built")

    # ── 4. Upload to PyPI ─────────────────────────────────────────────────────
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = token
    result = subprocess.run("twine upload dist/*", shell=True, cwd=str(CLIENT), env=env)
    if result.returncode != 0:
        _die("PyPI upload failed — check token and internet connection.")
    print(f"  [4/7] Published to PyPI")

    # ── 5–7. Git commit + tag + push (triggers GitHub Actions) ───────────────
    if not has_remote:
        print(f"\n  Skipped git steps (no remote configured).")
        print(f"  To enable auto-builds, run:")
        print(f"    git remote add origin <your-github-url>")
    else:
        _run("git add -A", cwd=ROOT)
        _run(f'git commit -m "Release {tag}"', cwd=ROOT)
        print(f"  [5/7] Committed")

        _run(f"git tag {tag}", cwd=ROOT)
        print(f"  [6/7] Tagged {tag}")

        _run("git push", cwd=ROOT)
        _run(f"git push origin {tag}", cwd=ROOT)
        print(f"  [7/7] Pushed → GitHub Actions building exe + macOS binary")

    print(f"\n  termtypo {tag} released!")
    print(f"  PyPI:    https://pypi.org/project/termtypo/{new_version}/")
    if has_remote:
        print(f"  Builds:  https://github.com/Sayandeep1013/TermTypo/actions")
        print(f"  Release: https://github.com/Sayandeep1013/TermTypo/releases/tag/{tag}")
    print()


if __name__ == "__main__":
    main()
