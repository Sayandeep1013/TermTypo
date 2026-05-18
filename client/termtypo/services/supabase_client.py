from __future__ import annotations
from functools import lru_cache
from supabase import create_client, Client
from termtypo.config import SUPABASE_URL, SUPABASE_ANON_KEY


@lru_cache(maxsize=1)
def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
