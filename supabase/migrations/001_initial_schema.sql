-- TermTypo Initial Schema
-- Run once against the Supabase project database

-- ─────────────────────────────────────────────
-- Helpers
-- ─────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ─────────────────────────────────────────────
-- profiles  (extends auth.users)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS profiles (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username     TEXT UNIQUE NOT NULL,
  display_name TEXT,
  avatar_url   TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─────────────────────────────────────────────
-- user_ratings  (separate ELO per mode)
-- modes: words_10 | words_50 | words_100 | time_10 | time_30 | time_60
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_ratings (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  mode       TEXT NOT NULL,
  elo        INTEGER DEFAULT 0 NOT NULL CHECK (elo >= 0),
  wins       INTEGER DEFAULT 0 NOT NULL,
  losses     INTEGER DEFAULT 0 NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  UNIQUE(user_id, mode)
);

CREATE TRIGGER user_ratings_updated_at
  BEFORE UPDATE ON user_ratings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─────────────────────────────────────────────
-- solo_results
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS solo_results (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  mode             TEXT NOT NULL,
  wpm              DECIMAL(6,2) NOT NULL,
  raw_wpm          DECIMAL(6,2) NOT NULL,
  accuracy         DECIMAL(5,2) NOT NULL,
  consistency      DECIMAL(5,2),
  word_count       INTEGER,
  duration_seconds INTEGER,
  created_at       TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ─────────────────────────────────────────────
-- matches
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS matches (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mode         TEXT NOT NULL,
  passage      TEXT NOT NULL,
  status       TEXT DEFAULT 'waiting' NOT NULL
                 CHECK (status IN ('waiting','active','completed','cancelled')),
  is_ranked    BOOLEAN DEFAULT TRUE NOT NULL,
  room_code    TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  started_at   TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

-- ─────────────────────────────────────────────
-- match_participants
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS match_participants (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id    UUID REFERENCES matches(id) ON DELETE CASCADE NOT NULL,
  user_id     UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  wpm         DECIMAL(6,2),
  raw_wpm     DECIMAL(6,2),
  accuracy    DECIMAL(5,2),
  elo_before  INTEGER,
  elo_after   INTEGER,
  finished_at TIMESTAMPTZ,
  position    INTEGER,
  UNIQUE(match_id, user_id)
);

-- ─────────────────────────────────────────────
-- rooms  (private)
-- ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS rooms (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code       TEXT UNIQUE NOT NULL,
  host_id    UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  mode       TEXT DEFAULT 'words_50' NOT NULL,
  status     TEXT DEFAULT 'waiting' NOT NULL
               CHECK (status IN ('waiting','active','completed')),
  match_id   UUID REFERENCES matches(id),
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 hour') NOT NULL
);

-- ─────────────────────────────────────────────
-- Auto-create profile on signup
-- ─────────────────────────────────────────────

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  base_uname  TEXT;
  final_uname TEXT;
  counter     INTEGER := 0;
BEGIN
  base_uname := COALESCE(
    NEW.raw_user_meta_data->>'preferred_username',
    split_part(NEW.email, '@', 1)
  );
  base_uname  := regexp_replace(base_uname, '[^a-zA-Z0-9_]', '', 'g');
  base_uname  := left(base_uname, 20);
  final_uname := base_uname;

  LOOP
    BEGIN
      INSERT INTO profiles (id, username, display_name, avatar_url)
      VALUES (
        NEW.id,
        final_uname,
        COALESCE(
          NEW.raw_user_meta_data->>'full_name',
          NEW.raw_user_meta_data->>'name'
        ),
        NEW.raw_user_meta_data->>'avatar_url'
      );
      RETURN NEW;
    EXCEPTION WHEN unique_violation THEN
      counter     := counter + 1;
      final_uname := base_uname || '_' || counter::TEXT;
    END;
  END LOOP;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ─────────────────────────────────────────────
-- Row Level Security
-- ─────────────────────────────────────────────

ALTER TABLE profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_ratings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE solo_results      ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches           ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms             ENABLE ROW LEVEL SECURITY;

-- profiles
-- profiles
DROP POLICY IF EXISTS "profiles_select_all" ON profiles;
DROP POLICY IF EXISTS "profiles_update_own" ON profiles;
CREATE POLICY "profiles_select_all"  ON profiles FOR SELECT USING (true);
CREATE POLICY "profiles_update_own"  ON profiles FOR UPDATE USING (auth.uid() = id);

-- user_ratings
DROP POLICY IF EXISTS "ratings_select_all"  ON user_ratings;
DROP POLICY IF EXISTS "ratings_service_all" ON user_ratings;
CREATE POLICY "ratings_select_all"   ON user_ratings FOR SELECT USING (true);
CREATE POLICY "ratings_service_all"  ON user_ratings FOR ALL USING (auth.role() = 'service_role');

-- solo_results
DROP POLICY IF EXISTS "solo_select_own" ON solo_results;
DROP POLICY IF EXISTS "solo_insert_own" ON solo_results;
CREATE POLICY "solo_select_own"      ON solo_results FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "solo_insert_own"      ON solo_results FOR INSERT WITH CHECK (auth.uid() = user_id);

-- matches
DROP POLICY IF EXISTS "matches_select_auth" ON matches;
DROP POLICY IF EXISTS "matches_service_all" ON matches;
CREATE POLICY "matches_select_auth"  ON matches FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "matches_service_all"  ON matches FOR ALL USING (auth.role() = 'service_role');

-- match_participants
DROP POLICY IF EXISTS "mp_select_own"   ON match_participants;
DROP POLICY IF EXISTS "mp_service_all"  ON match_participants;
CREATE POLICY "mp_select_own"        ON match_participants FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "mp_service_all"       ON match_participants FOR ALL USING (auth.role() = 'service_role');

-- rooms
DROP POLICY IF EXISTS "rooms_select_auth" ON rooms;
DROP POLICY IF EXISTS "rooms_insert_own"  ON rooms;
DROP POLICY IF EXISTS "rooms_update_host" ON rooms;
CREATE POLICY "rooms_select_auth"    ON rooms FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "rooms_insert_own"     ON rooms FOR INSERT WITH CHECK (auth.uid() = host_id);
CREATE POLICY "rooms_update_host"    ON rooms FOR UPDATE USING (auth.uid() = host_id);
