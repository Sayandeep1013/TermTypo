"""One-time script to apply the initial schema to Supabase."""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).parent / ".env")

SQL = (Path(__file__).parent / "supabase" / "migrations" / "001_initial_schema.sql").read_text()

raw = os.environ["SUPABASE_DB_URL"]
url = raw.replace(":6543/", ":5432/")  # session mode for DDL

print("Connecting to Supabase…")
conn = psycopg2.connect(url)
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute(SQL)
    print("Migration applied successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    cur.close()
    conn.close()
