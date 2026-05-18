-- Fix finish_match: auto-determine loser from match_participants,
-- add idempotency guard so calling it twice doesn't double-update ELO.
-- Drop old signature first because we're changing the parameter list.

DROP FUNCTION IF EXISTS finish_match(UUID,UUID,UUID,DECIMAL,DECIMAL,DECIMAL,DECIMAL);

CREATE OR REPLACE FUNCTION finish_match(
  p_match_id   UUID,
  p_winner_id  UUID,
  p_winner_wpm DECIMAL DEFAULT 0,
  p_winner_acc DECIMAL DEFAULT 100,
  p_loser_wpm  DECIMAL DEFAULT 0,
  p_loser_acc  DECIMAL DEFAULT 100
) RETURNS VOID AS $$
DECLARE
  v_mode       TEXT;
  v_loser_id   UUID;
  v_winner_elo INTEGER;
  v_loser_elo  INTEGER;
BEGIN
  -- Idempotency: bail if already completed
  IF EXISTS (SELECT 1 FROM matches WHERE id = p_match_id AND status = 'completed') THEN
    RETURN;
  END IF;

  SELECT mode INTO v_mode FROM matches WHERE id = p_match_id;
  IF v_mode IS NULL THEN RETURN; END IF;

  -- Auto-determine loser from the other participant
  SELECT user_id INTO v_loser_id
  FROM match_participants
  WHERE match_id = p_match_id AND user_id != p_winner_id
  LIMIT 1;

  IF v_loser_id IS NULL THEN RETURN; END IF;

  -- Current ELOs (default 0 if no rating row yet)
  SELECT COALESCE((SELECT elo FROM user_ratings WHERE user_id = p_winner_id AND mode = v_mode), 0) INTO v_winner_elo;
  SELECT COALESCE((SELECT elo FROM user_ratings WHERE user_id = v_loser_id  AND mode = v_mode), 0) INTO v_loser_elo;

  -- Winner: +30, wins++
  INSERT INTO user_ratings (user_id, mode, elo, wins, losses)
  VALUES (p_winner_id, v_mode, GREATEST(0, v_winner_elo + 30), 1, 0)
  ON CONFLICT (user_id, mode) DO UPDATE
    SET elo = GREATEST(0, user_ratings.elo + 30),
        wins = user_ratings.wins + 1,
        updated_at = NOW();

  -- Loser: -30, losses++
  INSERT INTO user_ratings (user_id, mode, elo, wins, losses)
  VALUES (v_loser_id, v_mode, GREATEST(0, v_loser_elo - 30), 0, 1)
  ON CONFLICT (user_id, mode) DO UPDATE
    SET elo = GREATEST(0, user_ratings.elo - 30),
        losses = user_ratings.losses + 1,
        updated_at = NOW();

  -- Update match_participants with final stats
  UPDATE match_participants
  SET wpm = p_winner_wpm, accuracy = p_winner_acc,
      elo_after = GREATEST(0, v_winner_elo + 30),
      position = 1, finished_at = NOW()
  WHERE match_id = p_match_id AND user_id = p_winner_id;

  UPDATE match_participants
  SET wpm = p_loser_wpm, accuracy = p_loser_acc,
      elo_after = GREATEST(0, v_loser_elo - 30),
      position = 2, finished_at = NOW()
  WHERE match_id = p_match_id AND user_id = v_loser_id;

  -- Close the match
  UPDATE matches SET status = 'completed', completed_at = NOW() WHERE id = p_match_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
