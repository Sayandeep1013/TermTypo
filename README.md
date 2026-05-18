# TermTypo

A terminal-first multiplayer typing test with ASCII art aesthetic. Ranked matchmaking, live 1v1 races, private rooms, and a global leaderboard — all in your terminal.

```
 ████████╗███████╗██████╗ ███╗   ███╗
    ██╔══╝██╔════╝██╔══██╗████╗ ████║
    ██║   █████╗  ██████╔╝██╔████╔██║
    ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║
    ██║   ███████╗██║  ██║██║ ╚═╝ ██║
    ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝
 ████████╗██╗   ██╗██████╗  ██████╗
    ██╔══╝╚██╗ ██╔╝██╔══██╗██╔═══██╗
    ██║    ╚████╔╝ ██████╔╝██║   ██║
    ██║     ╚██╔╝  ██╔═══╝ ██║   ██║
    ██║      ██║   ██║     ╚██████╔╝
    ╚═╝      ╚═╝   ╚═╝      ╚═════╝
```

## Install

```bash
pip install termtypo
termtypo
```

Requires Python 3.10+.

## Features

- **Solo practice** — words (10/25/50/100) and timed (10s/30s/60s) modes
- **Ranked matchmaking** — automatic 1v1 matching, ELO ladder (Bronze → Master)
- **Private rooms** — share a 6-character code with a friend
- **Live race** — real-time progress bars powered by Supabase Realtime
- **Global leaderboard** — top players per mode
- **Profile & stats** — WPM history, personal bests, rank progress

## Controls

| Key | Action |
|-----|--------|
| `s` | Solo practice |
| `r` | Ranked match (login required) |
| `c` | Create private room |
| `j` | Join private room |
| `l` | Leaderboard |
| `a` | Profile / Login |
| `q` | Quit |

**In solo / race:** `Tab` restart · `← →` cycle mode · `Esc` back · `Backspace` works across word boundaries

## Login

Login is optional. Guest users can use solo practice. Ranked and rooms require a Google account.

On first login, your browser opens for Google OAuth. The app starts a temporary local server on port 54321 to receive the callback — no data is sent anywhere else.

## Update

```bash
pip install --upgrade termtypo
```

The app notifies you on startup when a new version is available.

## License

MIT
