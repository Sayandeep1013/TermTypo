-- Fix handle_new_user: handle empty username + never block signup on any error

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  base_uname  TEXT;
  final_uname TEXT;
  counter     INTEGER := 0;
BEGIN
  BEGIN  -- outer block — catches everything so signup is NEVER blocked

    base_uname := COALESCE(
      NULLIF(
        regexp_replace(
          COALESCE(
            NEW.raw_user_meta_data->>'preferred_username',
            split_part(COALESCE(NEW.email, ''), '@', 1)
          ),
          '[^a-zA-Z0-9_]', '', 'g'
        ),
        ''  -- NULLIF treats '' as null so the fallback fires
      ),
      'user_' || substring(replace(gen_random_uuid()::text, '-', ''), 1, 8)
    );
    base_uname  := left(base_uname, 20);
    final_uname := base_uname;

    LOOP
      BEGIN
        INSERT INTO public.profiles (id, username, display_name, avatar_url)
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

  EXCEPTION WHEN OTHERS THEN
    -- Profile creation failed but we must not block the user signup
    RETURN NEW;
  END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
