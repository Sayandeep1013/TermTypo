-- join_private_room: lets a guest join a room atomically.
-- Runs as SECURITY DEFINER so it bypasses the matches/participants RLS
-- policies (which only allow service_role to insert ranked matches).

CREATE OR REPLACE FUNCTION join_private_room(
  p_code     TEXT,
  p_guest_id UUID,
  p_passage  TEXT
) RETURNS JSONB AS $$
DECLARE
  v_room_id  UUID;
  v_host_id  UUID;
  v_mode     TEXT;
  v_match_id UUID;
BEGIN
  -- Verify room exists and is still open
  SELECT id, host_id, mode
    INTO v_room_id, v_host_id, v_mode
    FROM public.rooms
   WHERE code = upper(p_code) AND status = 'waiting';

  IF NOT FOUND THEN
    RETURN jsonb_build_object('error', 'Room not found or already started');
  END IF;

  -- Don't let the host join their own room as guest
  IF v_host_id = p_guest_id THEN
    RETURN jsonb_build_object('error', 'You cannot join your own room');
  END IF;

  -- Create the match
  INSERT INTO public.matches (mode, passage, status, is_ranked)
  VALUES (v_mode, p_passage, 'active', false)
  RETURNING id INTO v_match_id;

  -- Add both participants
  INSERT INTO public.match_participants (match_id, user_id, elo_before)
  VALUES (v_match_id, v_host_id,  0),
         (v_match_id, p_guest_id, 0);

  -- Mark room as active
  UPDATE public.rooms
     SET status   = 'active',
         match_id = v_match_id
   WHERE id = v_room_id;

  RETURN jsonb_build_object(
    'match_id', v_match_id,
    'host_id',  v_host_id,
    'mode',     v_mode
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
