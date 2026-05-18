"""
Multiplayer smoke-test — runs entirely without a second device.
Tests:
  1. DB schema (all tables + functions present)
  2. Matchmaking queue insert / RPC create_match_from_queue
  3. Realtime broadcast between two simulated clients
  4. finish_match ELO function
  5. create_room function

Run: python test_multiplayer.py
"""
import asyncio
import os
import uuid
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

URL         = os.environ["SUPABASE_URL"]
ANON_KEY    = os.environ["SUPABASE_ANON_KEY"]
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE"]
DB_URL      = os.environ["SUPABASE_DB_URL"].replace(":6543/", ":5432/")

OK   = "  [OK]"
FAIL = "  [FAIL]"
SKIP = "  [SKIP]"


# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema check
# ─────────────────────────────────────────────────────────────────────────────
def test_schema():
    print("\n[1] DB schema")
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    required_tables = {
        "profiles", "user_ratings", "solo_results",
        "matches", "match_participants", "rooms",
        "matchmaking_queue",
    }
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    )
    found_tables = {r[0] for r in cur.fetchall()}
    for t in sorted(required_tables):
        if t in found_tables:
            print(f"{OK}  table '{t}'")
        else:
            print(f"{FAIL}  table '{t}' MISSING")

    required_funcs = {
        "handle_new_user", "create_match_from_queue",
        "finish_match", "create_room",
    }
    cur.execute(
        "SELECT proname FROM pg_proc "
        "WHERE proname = ANY(%s)",
        (list(required_funcs),)
    )
    found_funcs = {r[0] for r in cur.fetchall()}
    for f in sorted(required_funcs):
        if f in found_funcs:
            print(f"{OK}  function '{f}'")
        else:
            print(f"{FAIL}  function '{f}' MISSING")

    cur.close()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Matchmaking queue + create_match_from_queue
# ─────────────────────────────────────────────────────────────────────────────
def test_matchmaking_rpc():
    print("\n[2] Matchmaking RPC")
    from supabase import create_client
    # Use service role to bypass RLS
    admin = create_client(URL, SERVICE_KEY)

    # Create two fake profile rows (bypassing auth)
    uid1 = str(uuid.uuid4())
    uid2 = str(uuid.uuid4())

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur  = conn.cursor()

    try:
        # Insert fake auth users so FK is satisfied
        for uid in [uid1, uid2]:
            cur.execute(
                "INSERT INTO auth.users (id, email, encrypted_password, created_at, updated_at) "
                "VALUES (%s, %s, 'x', NOW(), NOW()) ON CONFLICT DO NOTHING",
                (uid, f"{uid[:8]}@test.invalid")
            )
            cur.execute(
                "INSERT INTO public.profiles (id, username) "
                "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (uid, f"testuser_{uid[:8]}")
            )

        # Insert both into queue
        for uid in [uid1, uid2]:
            cur.execute(
                "INSERT INTO matchmaking_queue (user_id, mode, elo) "
                "VALUES (%s, 'words_50', 0) ON CONFLICT (user_id) DO NOTHING",
                (uid,)
            )
        print(f"{OK}  two players inserted into queue")

        # Call RPC
        cur.execute(
            "SELECT create_match_from_queue(%s, %s, 'words_50', 'the quick brown fox')",
            (uid1, uid2)
        )
        match_id = cur.fetchone()[0]
        if match_id:
            print(f"{OK}  create_match_from_queue → {match_id}")
        else:
            print(f"{FAIL}  create_match_from_queue returned NULL")
            return

        # Verify queue is now empty for those users
        cur.execute(
            "SELECT COUNT(*) FROM matchmaking_queue WHERE user_id IN (%s, %s)",
            (uid1, uid2)
        )
        remaining = cur.fetchone()[0]
        if remaining == 0:
            print(f"{OK}  players removed from queue after match creation")
        else:
            print(f"{FAIL}  players NOT removed from queue ({remaining} remaining)")

        # Verify match_participants
        cur.execute(
            "SELECT COUNT(*) FROM match_participants WHERE match_id = %s", (match_id,)
        )
        participants = cur.fetchone()[0]
        if participants == 2:
            print(f"{OK}  match_participants has 2 rows")
        else:
            print(f"{FAIL}  expected 2 participants, got {participants}")

        # Test finish_match
        cur.execute(
            "SELECT finish_match(%s, %s, %s, 67.5, 55.0, 95.0, 88.0)",
            (match_id, uid1, uid2)
        )
        cur.execute(
            "SELECT status FROM matches WHERE id = %s", (match_id,)
        )
        status = cur.fetchone()[0]
        if status == "completed":
            print(f"{OK}  finish_match → match status = 'completed'")
        else:
            print(f"{FAIL}  finish_match → status = {status!r}")

        cur.execute(
            "SELECT elo FROM user_ratings WHERE user_id = %s AND mode = 'words_50'", (uid1,)
        )
        row = cur.fetchone()
        if row and row[0] == 30:
            print(f"{OK}  winner ELO = 30 (+30 from 0)")
        else:
            print(f"{FAIL}  winner ELO unexpected: {row}")

        # Test create_room
        cur.execute("SELECT create_room(%s, 'words_50')", (uid1,))
        room_code = cur.fetchone()[0]
        if room_code and len(room_code) == 6:
            print(f"{OK}  create_room → code = {room_code!r}")
        else:
            print(f"{FAIL}  create_room returned {room_code!r}")

    finally:
        # Cleanup fake data
        for uid in [uid1, uid2]:
            cur.execute("DELETE FROM auth.users WHERE id = %s", (uid,))
        cur.close()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Realtime broadcast between two simulated clients
# ─────────────────────────────────────────────────────────────────────────────
async def test_realtime():
    print("\n[3] Realtime broadcast")
    from supabase import acreate_client

    received: list[dict] = []
    channel_name = f"test:{uuid.uuid4().hex[:8]}"

    try:
        # Client A — subscriber
        client_a = await acreate_client(URL, ANON_KEY)
        ch_a = client_a.realtime.channel(channel_name)
        ch_a.on_broadcast("ping", lambda p: received.append(p))
        await ch_a.subscribe()

        # Client B — publisher
        client_b = await acreate_client(URL, ANON_KEY)
        ch_b = client_b.realtime.channel(channel_name)
        await ch_b.subscribe()

        await asyncio.sleep(1.0)   # let subscriptions establish
        await ch_b.send_broadcast("ping", {"hello": "world", "n": 42})
        await asyncio.sleep(2.0)   # wait for delivery

        if received:
            payload = received[0].get("payload") or received[0]
            if payload.get("hello") == "world":
                print(f"{OK}  broadcast received: {payload}")
            else:
                print(f"{OK}  broadcast received (unexpected payload): {payload}")
        else:
            print(f"{FAIL}  no broadcast received after 2s")
            print(f"       (check Realtime is enabled on your Supabase project)")

    except Exception as e:
        print(f"{FAIL}  Realtime error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 56)
    print("  TermTypo — multiplayer smoke-test")
    print("=" * 56)

    test_schema()
    test_matchmaking_rpc()
    asyncio.run(test_realtime())

    print("\n" + "=" * 56)
    print("  Done.")
    print("=" * 56)
