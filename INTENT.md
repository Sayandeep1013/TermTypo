# TermTypo — Project Intent Document

> **Living document.** Every major decision, architectural choice, and devlog entry lives here.
> If you're an agent or developer picking this up cold — read this first.

---

## 1. What Is TermTypo?

TermTypo is a **terminal-first multiplayer typing test** with a heavy ASCII art aesthetic
inspired by LazyVim's visual style. It is simultaneously:

- A **pip-installable Python package** — `pip install termtypo` → type `termtypo` in any terminal to launch
- A **standalone executable** — distributed via GitHub Releases for Windows (and later macOS) for users without Python
- A **website** — terminal-themed, same backend, playable in browser for users who don't want to install anything

All three surfaces share a single backend and a single account system. A user's rank, stats,
and match history are identical whether they play from the terminal app or the website.

---

## 2. Core Philosophy

- **Terminal is the primary experience.** The TUI should feel as polished as a GUI app.
- **ASCII art is not decoration — it is the UI.** Everything from menus to progress bars is art.
- **Guests are welcome, but accounts unlock the world.** Solo practice requires no login. Ranked and room multiplayer require a logged-in account.
- **Free infrastructure only** — every service used must have a free tier sufficient for a hobby/early-growth project.
- **Simultaneous build** — solo mode and multiplayer are developed together, not sequentially.

---

## 3. Feature Set

### 3.1 Solo Mode (available to guests and logged-in users)

| Feature | Detail |
|---|---|
| Time modes | 10s, **30s (default)**, 60s |
| Word modes | 10, **50 (default)**, 100 words |
| Stats shown | WPM, accuracy, raw WPM, consistency |
| Stat persistence | Logged-in users only |
| Typing validation | Same checks as MonkeyType — backspace-only correction, no copy-paste, accurate keystroke tracking |
| History | WPM over time graph (ASCII), personal bests per mode |

### 3.2 Ranked Multiplayer

- **Format:** Word-count race — both players type the **same passage** simultaneously; the first to complete it wins. (Rationale: clearest win condition, most dramatic, best fit for progress-bar visualization. Time-based races produce ties and ambiguous results in multiplayer.)
- **Default ranked mode:** 50-word race
- **Separate ELO per mode** — following the chess.com model, each mode (10w / 50w / 100w / 30s / 60s) has its own independent ELO ladder. This is a schema decision — not complex to implement; just additional columns per user.
- **Matchmaking:** Opponent is drawn from a shared queue of players waiting for the same mode. For v1, no ELO-based matchmaking — purely FIFO. ELO-aware matchmaking is a future feature.
- Requires logged-in account.

### 3.3 Private Rooms

- Any logged-in user can create a room and get a **6-character room code**.
- Share the code with a friend; they enter it to join.
- Room host picks the mode; both players confirm ready.
- No ELO change in private room matches (unranked).

### 3.4 Live Race Visualization

- Both players' progress is shown as **pip-style download progress bars** (e.g. `████████░░░░ 67%`) with their username and live WPM next to it.
- Updates every ~200ms via Supabase Realtime Broadcast.
- Post-race screen shows final WPM, accuracy, ELO delta, and a replay of both progress curves.

---

## 4. Ranking System

### Tier Structure

```
ELO Range    Rank
---------    ----
0   – 299    Bronze  (Bronze 1: 0-99 | Bronze 2: 100-199 | Bronze 3: 200-299)
300 – 599    Silver  (Silver 1: 300-399 | Silver 2: 400-499 | Silver 3: 500-599)
600 – 899    Gold    (Gold 1: 600-699 | Gold 2: 700-799 | Gold 3: 800-899)
900 – 1199   Platinum
1200 – 1499  Diamond
1500+        Master
```

### ELO Delta (v1)
- **Win:** +30
- **Loss:** -30
- **Floor:** 0 (cannot go negative)
- ELO is tracked separately per mode.
- Future: variable delta based on ELO difference between players (standard ELO formula).

---

## 5. Tech Stack

### 5.1 Terminal Client

| Choice | Rationale |
|---|---|
| **Python** | Cross-platform, pip ecosystem, PyInstaller for .exe, large community |
| **Textual** (by Textualize) | Modern TUI framework — CSS-like styling, animations, reactive data binding, much more capable than raw `curses`. Used by production tools. LazyVim-style aesthetics are achievable. |
| **Rich** | Ships with Textual; used for ASCII art rendering, progress bars, tables, syntax coloring |

### 5.2 Backend & Infrastructure (all free tier)

| Service | Usage | Free Tier Limits |
|---|---|---|
| **Supabase** | PostgreSQL DB, Auth (Google OAuth), Realtime (WebSocket relay), Storage | 500MB DB, 50MB storage, 2M Realtime messages/day, 200 concurrent connections |
| **Supabase Auth** | Google OAuth — user used this in a prior project, known working | — |
| **Supabase Realtime Broadcast** | Live race progress sync (keystrokes → progress bar updates). Each player broadcasts their state to a match channel. ~600 messages per race at 200ms intervals. At 2M/day limit, supports ~3,300 races/day on free tier. | 2M messages/day |
| **Supabase Edge Functions** | Matchmaking queue logic, ELO update after match, anti-cheat WPM validation | 500K invocations/month |
| **Render / Fly.io** | Only needed if Edge Functions are insufficient for matchmaking state. Deferred — try pure Supabase first. | Render: free tier (spins down); Fly.io: 3 shared VMs |

### 5.3 Website

| Choice | Rationale |
|---|---|
| **Next.js** (or plain Vite + React) | Terminal-theme CSS, connects to same Supabase backend, same Google OAuth flow |
| Hosted on **Vercel** | Free tier, auto-deploys from GitHub |

### 5.4 Distribution

| Channel | Format | Notes |
|---|---|---|
| **PyPI** | `pip install termtypo` → `termtypo` command | Pure Python users; requires Python 3.10+ |
| **GitHub Releases** | `.exe` (Windows), `.app` / binary (macOS) | Built with PyInstaller via GitHub Actions CI |
| **Website** | Browser-based play | No install required; shares backend |

The PyPI package and the executable are the **same codebase** — PyInstaller just bundles the interpreter alongside it. The release workflow in GitHub Actions will build both automatically on tag push.

---

## 6. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                              │
│                                                             │
│  Terminal App (Python/Textual)    Website (Next.js)         │
│  pip install termtypo             vercel deployment         │
│  OR .exe from GitHub Releases                               │
└──────────────────────┬──────────────────────────────────────┘
                       │  HTTPS + WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                      SUPABASE                               │
│                                                             │
│  Auth          ──  Google OAuth, JWT sessions               │
│  PostgreSQL    ──  users, matches, rankings, word_lists      │
│  Realtime      ──  Broadcast channels per match (progress)  │
│                    Presence channels (matchmaking queue)    │
│  Edge Functions──  matchmaking logic, ELO updates           │
└─────────────────────────────────────────────────────────────┘
```

### Key Data Flows

**Ranked matchmaking:**
1. Client joins Supabase Realtime Presence channel `queue:{mode}`
2. Edge Function detects 2 players in queue → creates a match row in DB → notifies both via Broadcast
3. Both clients receive match ID + shared word list → race begins
4. Each client broadcasts progress to channel `match:{match_id}` every 200ms
5. First to finish sends completion event → Edge Function validates WPM, updates ELO, closes match

**Private room:**
1. Host calls Edge Function `create_room` → returns 6-char code
2. Guest joins via `join_room:{code}` Presence channel
3. Host triggers start → same race flow as ranked

---

## 7. Repository Structure (Planned)

```
termtypo/
├── client/                  # Python TUI application
│   ├── termtypo/
│   │   ├── __main__.py      # Entry point: python -m termtypo
│   │   ├── app.py           # Textual App root
│   │   ├── screens/         # Home, Solo, Lobby, Race, Results, Leaderboard
│   │   ├── widgets/         # ProgressRace, TypingBox, AsciiHeader, RankBadge
│   │   ├── services/        # supabase_client.py, matchmaking.py, auth.py
│   │   └── assets/          # ASCII art files, word lists
│   ├── pyproject.toml       # pip package config; scripts: termtypo = termtypo.__main__:main
│   └── build/               # PyInstaller spec files
│
├── supabase/
│   ├── migrations/          # DB schema migrations
│   └── functions/           # Edge Functions (matchmaking, elo_update, validate_wpm)
│
├── web/                     # Next.js website
│   └── ...
│
├── .github/
│   └── workflows/
│       ├── release.yml      # Build .exe + .app + publish to PyPI on tag
│       └── deploy-web.yml   # Deploy web to Vercel
│
└── INTENT.md                # This document
```

---

## 8. Open Questions (To Resolve Before / During Build)

| # | Question | Status |
|---|---|---|
| 1 | Word list source — random common English words, or curated? Include punctuation/numbers in modes? | Open |
| 2 | Guest play in private rooms — should guests be allowed to join a friend's room without an account? | Open |
| 3 | Anti-cheat: what WPM ceiling triggers a flag? (e.g. >220 WPM is statistically impossible) | Open |
| 4 | Spectator mode for rooms? | Deferred |
| 5 | Mobile/tablet on website — responsive or desktop-only? | Open |
| 6 | Sound effects (terminal bell, keystroke feedback)? | Open |

---

## 9. Design Reference

- **Primary aesthetic:** LazyVim dashboard — dark background, pixel-font ASCII headers, minimal color, box-drawing characters for borders, subtle glow effects via color layering
- **Color palette:** TBD — likely dark navy/black bg, cyan/teal for primary, amber for warnings, red for errors, white for body text
- **Progress bars:** Mimic `pip install` animation — `━━━━━━━━━━` fill style with percentage and live WPM

---

## 10. Milestones

| Milestone | Scope |
|---|---|
| **M1 — Foundation** | Supabase project setup, DB schema, Auth working, basic Textual app shell with ASCII art home screen |
| **M2 — Solo Mode** | Typing engine, time/word modes, WPM/accuracy calculation, stat persistence for logged-in users |
| **M3 — Multiplayer Core** | Matchmaking queue, race room, live progress bars via Supabase Realtime |
| **M4 — Ranked Ladder** | ELO system, rank tiers, leaderboard screen |
| **M5 — Private Rooms** | Room creation/join, unranked races between friends |
| **M6 — Packaging** | PyPI publish, PyInstaller builds, GitHub Actions release pipeline |
| **M7 — Website** | Next.js terminal-theme site, same backend, guest + auth play |
| **M8 — Polish** | ASCII art screens, sound (optional), onboarding flow, replay viewer |

---

---

# DEVLOG

---

## Entry 001 — Project Inception
**Date:** 2026-05-17
**Status:** Pre-code, design phase

### What Was Decided

Kicked off the TermTypo project. Spent the first session going from a raw idea
("terminal multiplayer typing test with ASCII art") to a fully-defined architecture.

Key decisions made and why:

**Race format → Word-count, first-to-finish:**
Chose this over time-based races because it produces a clear winner without a tiebreaker,
creates genuine dramatic tension as players converge on the finish line, and maps naturally
to a progress bar (you always know how far both players are). Time-based races work better
for solo practice — they stay as the solo mode format.

**Backend → Pure Supabase:**
The developer has prior Supabase experience (Auth + Realtime in a previous project).
Supabase Realtime's Broadcast feature is essentially a free WebSocket relay — each match
gets a channel, players broadcast their progress every 200ms. At the free tier limit of
2M messages/day, this supports ~3,300 races/day, more than enough for early growth.
No separate WebSocket server needed. This keeps the entire backend on one free-tier service.

**Separate ELO per mode:**
Mirrors chess.com's time-control separation. Architecturally trivial — a separate row in
a `user_ratings` table keyed by `(user_id, mode)`. Decided early so the schema reflects
it from the start rather than being bolted on.

**TUI Framework → Textual:**
Raw `curses` would produce the same terminal output but with 10x the code and no component
model. Textual has reactive state, CSS-like layout, built-in animation, and is used in
production TUI tools. It also ships Rich, which handles progress bars, ASCII tables,
and styled text natively. LazyVim's aesthetic is fully reproducible in Textual.

**Distribution → Both pip package AND executable:**
- `pip install termtypo` for developers and Python users — cleanest experience
- `.exe` / binary via PyInstaller for everyone else — same codebase, bundled interpreter
- Website via Next.js on Vercel — zero install, same backend
GitHub Actions handles building both binary targets on release tag push.

**ELO ladder structure:**
+30/-30 flat for v1. Tiers every 300 ELO, sub-tiers every 100.
Floor at 0. Simple enough to ship fast, structured enough to add variable delta later.

### What's Next

- M1: Set up Supabase project, define DB schema, scaffold Textual app shell
- First screen: Home / dashboard in LazyVim style with ASCII "TermTypo" header
- Auth flow: Google OAuth via Supabase, token stored locally on client

### Challenges Anticipated

- Supabase Realtime free tier connection limit (200 concurrent) could become a bottleneck
  if the game gains significant traction. Mitigation: each match only holds a channel open
  for its duration (~60-90 seconds), so 200 connections supports far more than 200
  simultaneous users.
- PyInstaller builds on Windows vs macOS require separate CI runners — the GitHub Actions
  matrix strategy will handle this but needs testing.
- Textual's CSS layout has a learning curve. Expect iteration on screen layouts before
  they feel right.

---

## Entry 002 — M1 + M2 + M3 Complete (Terminal App Fully Working)
**Date:** 2026-05-18
**Version:** 0.1.8 (PyPI)
**Status:** All core features shipped, bug-fix cycle complete

### What Was Built

**M1 — Foundation (DB schema + auth + home screen)**
- Full PostgreSQL schema on Supabase: `profiles`, `user_ratings`, `solo_results`, `matches`, `match_participants`, `rooms`, `matchmaking_queue`
- Google OAuth via browser PKCE flow — terminal opens browser, local HTTP server (ports 54321-54325) catches callback, saves session to `%APPDATA%\termtypo\termtypo\session.json`
- Auto-profile trigger on signup: generates username from email prefix with uniqueness loop
- LazyVim-style home screen with ASCII art TERM/TYPO logo and keyboard-shortcut menu

**M2 — Solo Mode**
- Words mode (10/25/50/100) and timed mode (10/30/60s)
- Real-time WPM/accuracy display — stats bar appears only after first keystroke
- MonkeyType-style typing engine: green/red per-character colouring, backspace across word boundary
- Results modal (Rich `Group` of `Text` + `Table`) — shows WPM, raw WPM, accuracy bar
- Mode selector with tabs (← → arrows to cycle)
- Results saved to `solo_results` table for logged-in users

**M3 — Multiplayer**
- Ranked matchmaking: queue via Supabase DB (`matchmaking_queue`) + Realtime Presence on `queue:{mode}` channel
- Match creation via `create_match_from_queue()` PostgreSQL RPC — atomic, removes both players from queue
- Live race: pip-style progress bars (`━━━━░░░░`) synced every 200ms via Supabase Realtime Broadcast on `match:{match_id}` channel
- ELO update via `finish_match()` PostgreSQL RPC — +30 win / -30 loss, floor 0
- Private rooms: 6-char code via `create_room()` PG function, polling for guest join
- 45-second opponent disconnect timeout → auto-win declaration
- Mode selector (all 7 modes) for both ranked and room — shown as modal before queueing

**Leaderboard + Profile**
- Global leaderboard: top 25 per mode, rank tier labels, W/L ratio, your row highlighted with →
- Profile screen: personal best, per-mode ELO progress bars, recent solo results table

**PyPI publishing**
- Package live at https://pypi.org/project/termtypo
- `release.bat` / `release.py` automation — reads token from `.pypi_token`, bumps version in both files, builds, uploads
- In-app update notifier: polls PyPI JSON API on startup

---

### Bugs Found and Fixed (in order)

| Bug | Root cause | Fix |
|---|---|---|
| Login "Database error saving new user" | `handle_new_user` trigger crashed on empty username | Added `NULLIF` + `WHEN OTHERS THEN RETURN NEW` safety net |
| Ranked screen crash `visual=None` | Custom `_render()` / `_render_content()` methods shadowed Textual's internal `Widget._render()` | Renamed all our private methods; added AST scan to catch collisions |
| Matchmaking subclass crash | CSS type-selector `MatchmakingScreen {}` didn't match `_RankedMatchmaking` subclass in Textual 8.x | Removed subclass, push `MatchmakingScreen(mode=...)` directly |
| `maybe_single().execute()` returns None | supabase-py 2.30 returns `None` (not a response object) when no row exists | Added `if res else 0` / `if res else None` guards throughout |
| Event loop stopped before future | `loop.stop()` called while `asyncio.sleep()` pending → `RuntimeError` | Removed `loop.stop()` calls; rely on `_stopped` flag and natural loop exit |
| Leaderboard crash `WorkerError` | Textual 8.x `run_worker` requires `thread=True` for sync functions | Added `thread=True` to all sync worker calls |
| Room create nothing happens | `Input` widget got focus on mount even when `display=False`; consumed 'c' keypress silently | Set `disabled=True` on Input until join mode; enabled only in `_show_join()` |
| Profile `TypeError: Only str or Text can be appended` | `Text.append()` doesn't accept `rich.Table` | Switched to `rich.console.Group(*parts)` for mixed renderable content |
| Solo save silent failures | `except Exception: pass` swallowed all DB errors | Now shows `notify()` with error text for visibility |
| Logo shadow offset on TYPO | `╝╚` adjacency between T and Y in row 2 created horizontal bar | Changed Y's row-2 start from `╚` to space — one character fix |

---

### Architecture Learnings

1. **Textual 8.x breaking changes from 0.x:**
   - `run_worker` now defaults to async; sync functions need `thread=True`
   - `Screen.render()` must return a valid `Visual` — any private method named `_render*` that returns `None` causes crash
   - CSS type selectors match exact class name only, not subclasses
   - `call_from_thread` is the only safe way to update UI from a thread worker

2. **Supabase-py 2.30 quirks:**
   - `maybe_single().execute()` returns `None` (not a response with `data=None`) on no match
   - `set_session()` doesn't validate token expiry; expired tokens only fail at query time
   - Google OAuth PKCE: `redirect_to` must be passed to both `sign_in_with_oauth` AND `exchange_code_for_session`

3. **Realtime architecture:**
   - Broadcast channels are reliable for 200ms progress updates
   - Presence for matchmaking queue works but `presence_state()` dict structure varies — defensive parsing needed
   - Running Realtime in a separate thread with its own asyncio loop avoids conflicts with Textual's event loop

---

### Milestone Status

| Milestone | Status | Notes |
|---|---|---|
| M1 — Foundation | ✅ Done | Schema, auth, home screen |
| M2 — Solo Mode | ✅ Done | All modes, results, save |
| M3 — Multiplayer | ✅ Done | Ranked, rooms, ELO |
| M4 — Ranked Ladder | ✅ Done | Leaderboard, profile, ELO tiers |
| M5 — Private Rooms | ✅ Done | 6-char codes, polling |
| M6 — Packaging | ✅ Done | PyPI live, release.bat automation |
| M7 — Website | 🔲 Next | Next.js, Vercel, same Supabase |
| M8 — Executables | 🔲 Next | PyInstaller, GitHub Actions |
| M9 — Polish | 🔲 Next | Better word lists, sound, replay |

---

### What's Next

**Immediate next steps (in order):**
1. **Windows .exe + macOS binary** — PyInstaller spec file, GitHub Actions matrix build on tag push
2. **Website** — Next.js on Vercel, terminal theme CSS, same Supabase backend
3. **Word list improvement** — quotes mode, code snippets mode, language packs
4. **GitHub repo setup** — README, releases section, issue templates

_End of Entry 002_

---

_End of Entry 001_

---
