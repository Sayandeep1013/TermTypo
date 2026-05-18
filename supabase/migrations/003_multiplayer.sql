-- TermTypo M3 — Multiplayer: matchmaking queue, match creation, ELO update
-- Idempotent (safe to re-run)

-- ─────────────────────────────────────────────────────────────────
-- Matchmaking queue
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS matchmaking_queue (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id   UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  mode      TEXT NOT NULL,
  elo       INTEGER DEFAULT 0 NOT NULL,
  joined_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  UNIQUE(user_id)   -- a player can only be in one queue at a time
);

ALTER TABLE matchmaking_queue ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "queue_select" ON matchmaking_queue;
DROP POLICY IF EXISTS "queue_insert" ON matchmaking_queue;
DROP POLICY IF EXISTS "queue_delete" ON matchmaking_queue;
CREATE POLICY "queue_select" ON matchmaking_queue FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "queue_insert" ON matchmaking_queue FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "queue_delete" ON matchmaking_queue FOR DELETE USING (auth.uid() = user_id);

-- Allow Realtime subscriptions on this table
ALTER PUBLICATION supabase_realtime ADD TABLE matchmaking_queue;

-- ─────────────────────────────────────────────────────────────────
-- Atomic match creation from queue (called via RPC)
-- Returns match_id on success, NULL if either player left the queue
-- ─────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION create_match_from_queue(
  p_user1_id UUID,
  p_user2_id UUID,
  p_mode     TEXT,
  p_passage  TEXT
) RETURNS UUID AS $$
DECLARE
  v_match_id UUID;
  v_elo1     INTEGER;
  v_elo2     INTEGER;
BEGIN
  -- Verify both players are still in queue for this mode
  IF NOT EXISTS (SELECT 1 FROM matchmaking_queue WHERE user_id = p_user1_id AND mode = p_mode)
  OR NOT EXISTS (SELECT 1 FROM matchmaking_queue WHERE user_id = p_user2_id AND mode = p_mode)
  THEN
    RETURN NULL;
  END IF;

  -- Grab current ELOs (default 0 if no rating row yet)
  SELECT COALESCE((SELECT elo FROM user_ratings WHERE user_id = p_user1_id AND mode = p_mode), 0) INTO v_elo1;
  SELECT COALESCE((SELECT elo FROM user_ratings WHERE user_id = p_user2_id AND mode = p_mode), 0) INTO v_elo2;

  -- Create the match
  INSERT INTO matches (mode, passage, status, is_ranked)
  VALUES (p_mode, p_passage, 'active', TRUE)
  RETURNING id INTO v_match_id;

  -- Add both participants
  INSERT INTO match_participants (match_id, user_id, elo_before)
  VALUES (v_match_id, p_user1_id, v_elo1),
         (v_match_id, p_user2_id, v_elo2);

  -- Remove both from queue
  DELETE FROM matchmaking_queue WHERE user_id IN (p_user1_id, p_user2_id);

  RETURN v_match_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ─────────────────────────────────────────────────────────────────
-- ELO update after a match completes
-- ─────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION finish_match(
  p_match_id   UUID,
  p_winner_id  UUID,
  p_loser_id   UUID,
  p_winner_wpm DECIMAL,
  p_loser_wpm  DECIMAL,
  p_winner_acc DECIMAL,
  p_loser_acc  DECIMAL
) RETURNS VOID AS $$
DECLARE
  v_mode       TEXT;
  v_winner_elo INTEGER;
  v_loser_elo  INTEGER;
BEGIN
  SELECT mode INTO v_mode FROM matches WHERE id = p_match_id;

  SELECT COALESCE((SELECT elo FROM user_ratings WHERE user_id = p_winner_id AND mode = v_mode), 0) INTO v_winner_elo;
  SELECT COALESCE((SELECT elo FROM user_ratings WHERE user_id = p_loser_id  AND mode = v_mode), 0) INTO v_loser_elo;

  -- Upsert winner rating
  INSERT INTO user_ratings (user_id, mode, elo, wins, losses)
  VALUES (p_winner_id, v_mode, GREATEST(0, v_winner_elo + 30), 1, 0)
  ON CONFLICT (user_id, mode) DO UPDATE
    SET elo = GREATEST(0, user_ratings.elo + 30),
        wins = user_ratings.wins + 1,
        updated_at = NOW();

  -- Upsert loser rating
  INSERT INTO user_ratings (user_id, mode, elo, wins, losses)
  VALUES (p_loser_id, v_mode, GREATEST(0, v_loser_elo - 30), 0, 1)
  ON CONFLICT (user_id, mode) DO UPDATE
    SET elo = GREATEST(0, user_ratings.elo - 30),
        losses = user_ratings.losses + 1,
        updated_at = NOW();

  -- Update match_participants
  UPDATE match_participants
  SET wpm = p_winner_wpm, accuracy = p_winner_acc,
      elo_after = GREATEST(0, v_winner_elo + 30), position = 1, finished_at = NOW()
  WHERE match_id = p_match_id AND user_id = p_winner_id;

  UPDATE match_participants
  SET wpm = p_loser_wpm, accuracy = p_loser_acc,
      elo_after = GREATEST(0, v_loser_elo - 30), position = 2, finished_at = NOW()
  WHERE match_id = p_match_id AND user_id = p_loser_id;

  -- Close match
  UPDATE matches SET status = 'completed', completed_at = NOW() WHERE id = p_match_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ─────────────────────────────────────────────────────────────────
-- Room helpers
-- ─────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION create_room(
  p_host_id UUID,
  p_mode    TEXT
) RETURNS TEXT AS $$
DECLARE
  v_code TEXT;
  v_attempt INTEGER := 0;
BEGIN
  LOOP
    v_code := upper(substring(replace(gen_random_uuid()::text, '-', ''), 1, 6));
    BEGIN
      INSERT INTO rooms (code, host_id, mode) VALUES (v_code, p_host_id, p_mode);
      RETURN v_code;
    EXCEPTION WHEN unique_violation THEN
      v_attempt := v_attempt + 1;
      IF v_attempt > 10 THEN RAISE; END IF;
    END;
  END LOOP;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
