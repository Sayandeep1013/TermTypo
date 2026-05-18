# TermTypo — PyPI Publishing Guide

Everything you need to know before, during, and after publishing.

---

## Is it free?

Yes. PyPI (pypi.org) is completely free. No hosting costs, no per-download fees, no subscriptions.
Your package lives there forever unless you delete it.

---

## Before You Publish — Checklist

### 1. Check the package name is available
Go to https://pypi.org/project/termtypo/ in your browser.
- If it shows "404 Not Found" → name is free, you can claim it.
- If it shows a package → someone else has it. You'd need a different name
  (e.g. `termtypo-game`, `typeterminal`, etc.) and update pyproject.toml + README.

### 2. Add extra OAuth ports to Supabase
Port 54321 is always registered. If a user's machine has it occupied, the app
now tries 54322–54325 automatically. But Supabase must allow ALL of them.

Go to: https://supabase.com/dashboard/project/gaaqylbllnwllcvawnbt/auth/url-configuration

Under **Redirect URLs**, add these (you already have 54321):
```
http://localhost:54322/auth/callback
http://localhost:54323/auth/callback
http://localhost:54324/auth/callback
http://localhost:54325/auth/callback
```

### 3. Create PyPI accounts
- **TestPyPI** (for dry-run): https://test.pypi.org/account/register/
- **PyPI** (real release):     https://pypi.org/account/register/

Enable 2FA on both — PyPI requires it for publishing.

### 4. Create API tokens (more secure than password)
- TestPyPI → Account Settings → API tokens → Add token (scope: "Entire account")
- PyPI     → Account Settings → API tokens → Add token (scope: "Entire account")

Save both tokens — you only see them once.

---

## Publishing Steps

### Step 1 — Install publishing tools (one-time)
```bash
pip install build twine
```

### Step 2 — Clean old builds
```bash
cd d:\Projects\TerminalTypingTest\client
Remove-Item -Recurse -Force dist, build   # PowerShell
# or: rm -rf dist/ build/               # bash
```

### Step 3 — Build the package
```bash
python -m build
```
This creates two files in `dist/`:
- `termtypo-0.1.0.tar.gz`   — source distribution
- `termtypo-0.1.0-py3-none-any.whl` — wheel (what pip installs)

### Step 4 — Dry-run on TestPyPI first
```bash
twine upload --repository testpypi dist/*
# Enter: __token__
# Enter: (paste your TestPyPI token)
```
Then test install from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ termtypo
termtypo
```
(The `--extra-index-url` is needed because our dependencies like `textual` aren't on TestPyPI.)

### Step 5 — Publish to real PyPI
Once TestPyPI install works:
```bash
twine upload dist/*
# Enter: __token__
# Enter: (paste your real PyPI token)
```

### Step 6 — Verify
```bash
pip install termtypo   # fresh install
termtypo               # should launch
```

---

## Version Management

### Semantic versioning: MAJOR.MINOR.PATCH
| Change | Version bump | Example |
|--------|-------------|---------|
| Bug fix, small improvement | PATCH | 0.1.0 → 0.1.1 |
| New feature (backwards compatible) | MINOR | 0.1.1 → 0.2.0 |
| Breaking change | MAJOR | 0.x.x → 1.0.0 |

### How to release a new version
1. Update version in TWO places:
   - `client/pyproject.toml` → `version = "0.2.0"`
   - `client/termtypo/__init__.py` → `__version__ = "0.2.0"`
2. Copy README if updated: `cp README.md client/README.md`
3. Clean + build + upload (Steps 2–5 above)

### Do users auto-update?
**No.** pip never auto-updates packages. Users must run:
```bash
pip install --upgrade termtypo
```
The app notifies them on startup when a new version is available on PyPI
(via the built-in update checker that polls https://pypi.org/pypi/termtypo/json).

---

## Edge Cases & What We've Handled

### Port conflicts (OAuth)
**Problem:** Port 54321 occupied by another app.
**Fix:** App automatically tries 54322, 54323, 54324, 54325.
**Your action:** Register all 5 ports in Supabase (see checklist above).
**What if all 5 are busy?** App shows: "Could not find a free port. Close apps
using ports 54321–54325 and try again."

### Expired access tokens
**Problem:** Supabase access tokens expire after 1 hour.
**Fix:** `get_authed_client()` automatically calls `refresh_session()` on failure.
Refresh tokens last 7 days. After 7 days without launching the app, the user
must log in again — the session is cleared and they're shown the login screen.

### Opponent disconnects mid-race
**Problem:** Player closes the app or loses internet during a race.
**Fix:** If no opponent progress update is received for 45 seconds, the remaining
player is declared the winner automatically.

### No internet connection
**Problem:** Supabase calls will fail.
**Current behavior:** Solo mode still works (word list is bundled locally).
Multiplayer/login/leaderboard fail with a timeout error from httpx.
**Future:** Add an offline detection banner.

### Python version too old
**Problem:** User has Python 3.9 or earlier.
**Fix:** pyproject.toml enforces `requires-python = ">=3.10"`. pip will refuse to
install and tell the user to upgrade Python.

### Windows cmd.exe vs Windows Terminal
**Problem:** cmd.exe has poor Unicode support — box-drawing characters may render as ??.
**Fix (current):** Textual handles this by detecting the terminal. Characters should
render fine in Windows Terminal, VS Code terminal, PowerShell 7+.
**Recommendation in README:** "Best experienced in Windows Terminal."

### Small terminal (< 80 columns)
**Problem:** Layout breaks on narrow terminals.
**Current behavior:** Textual wraps/clips — functional but ugly.
**Future:** Add a minimum size check on startup.

### Package name squatting
**Problem:** `termtypo` is taken on PyPI by someone else.
**Fix:** Change name in pyproject.toml, update README, pick alternative name.

### Word list not bundled
**Verify:** Already confirmed — `common_1000.txt` is present in the built wheel.
Run: `python -c "import zipfile; [print(f) for f in zipfile.ZipFile('dist/termtypo-0.1.0-py3-none-any.whl').namelist() if 'words' in f]"`

### Dependency version conflicts
**Problem:** User has incompatible versions of textual/supabase.
**Current:** No upper bounds set (flexible). If a future library update breaks things,
pin upper bounds: `"textual>=0.70.0,<1.0.0"` in pyproject.toml dependencies.

---

## After Publishing — Maintenance Checklist

When you ship a new version:
- [ ] Bump version in `pyproject.toml` AND `__init__.py`
- [ ] Update `client/README.md` (copy from root README.md)
- [ ] Clean `dist/` and rebuild
- [ ] Upload to PyPI
- [ ] Create a GitHub Release with the version tag and changelog
- [ ] Update `INTENT.md` DEVLOG with what changed
