# TermTypo — Release Automation Guide

Everything needed to ship a new version: PyPI package + Windows exe + macOS binary.

---

## One-command release

```bash
release.bat           # patch bump  0.1.x → 0.1.x+1
release.bat minor     # minor bump  0.x.y → 0.x+1.0
release.bat major     # major bump  x.y.z → x+1.0.0
```

That single command does **all 7 steps** automatically:

| Step | What happens |
|------|-------------|
| 1 | Bumps `__version__` in `client/termtypo/__init__.py` AND `version` in `client/pyproject.toml` |
| 2 | Copies `README.md` → `client/README.md` (PyPI needs it inside the package dir) |
| 3 | Cleans old build artefacts, runs `python -m build` → creates `.whl` + `.tar.gz` in `client/dist/` |
| 4 | Uploads to PyPI via `twine` using the token in `.pypi_token` |
| 5 | `git commit -m "Release vX.Y.Z"` |
| 6 | `git tag vX.Y.Z` |
| 7 | `git push && git push origin vX.Y.Z` → **triggers GitHub Actions** |

After step 7, GitHub Actions takes over automatically (see below).

---

## GitHub Actions — what happens after the push

File: `.github/workflows/release.yml`

Triggered by: any tag matching `v*.*.*`

Two jobs run **in parallel**:

```
tag v0.1.12 pushed
      │
      ├── build-windows (windows-latest runner)
      │   ├── pip install pyinstaller + termtypo
      │   ├── pyinstaller termtypo.spec
      │   ├── rename → termtypo-windows.exe
      │   └── attach to GitHub Release
      │
      └── build-macos (macos-latest runner)
          ├── pip install pyinstaller + termtypo
          ├── pyinstaller termtypo.spec
          ├── rename → termtypo-macos
          └── attach to GitHub Release
```

When both finish (~5 min), the GitHub Release page at
`github.com/Sayandeep1013/TermTypo/releases` has:
- `termtypo-windows.exe` — double-click to run, no Python needed
- `termtypo-macos` — same for Mac
- Auto-generated release notes from commit history

**No secrets needed** — `GITHUB_TOKEN` is provided automatically by GitHub.

---

## One-time setup (already done, documented for reference)

### Local machine
1. Create `.pypi_token` in the project root with your PyPI API token:
   ```
   pypi-AgEI...your-token-here
   ```
2. This file is in `.gitignore` — never committed.

### GitHub repo
No extra secrets needed. The `GITHUB_TOKEN` for creating releases is provided
automatically by GitHub Actions.

---

## Files involved

| File | Purpose |
|------|---------|
| `release.py` | Full release automation script |
| `release.bat` | Windows shortcut: `python release.py %1` |
| `.pypi_token` | PyPI API token (gitignored, lives only on your machine) |
| `termtypo.spec` | PyInstaller build config for exe/binary |
| `.github/workflows/release.yml` | GitHub Actions: builds binaries on tag push |

---

## If something goes wrong

### PyPI upload failed
The version was bumped in files but NOT committed. Fix the issue, then
run `release.bat` again — it will detect the already-bumped version and try again.
Or revert manually:
```bash
git checkout client/termtypo/__init__.py client/pyproject.toml
```

### GitHub Actions build failed
Check the Actions tab on GitHub. Common causes:
- `pyinstaller termtypo.spec` error — usually a missing hidden import
- Dependency install failure — transient network issue, re-run the job

The `termtypo.spec` file controls what gets bundled. If a new dependency needs
to be added, add it to the `hiddenimports` list in the spec.

### PyPI version conflict
PyPI doesn't allow re-uploading the same version. If the upload was partial,
bump to the next patch version and try again.

---

## Versioning rules

```
MAJOR.MINOR.PATCH

0.1.x  →  Bug fix, small improvement    (release.bat patch)
0.x.0  →  New feature                   (release.bat minor)
x.0.0  →  Breaking change               (release.bat major)
```

The in-app update checker polls `https://pypi.org/pypi/termtypo/json` on
startup and notifies users when a newer version is available.

---

## For users — how to install / update

```bash
# Install
pip install termtypo
termtypo

# Update
pip install --upgrade termtypo

# Windows without Python — download termtypo-windows.exe from:
# https://github.com/Sayandeep1013/TermTypo/releases/latest
```
