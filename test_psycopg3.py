import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH, override=True)

host = os.getenv("PGHOST")
dbname = os.getenv("PGDATABASE")
user = os.getenv("PGUSER")
password = os.getenv("PGPASSWORD")
port = int(os.getenv("PGPORT", "5432"))
sslmode = os.getenv("PGSSLMODE", "require")

print("USANDO:")
print("  host =", host)
print("  db   =", dbname)
print("  user =", user)
print("  port =", port)
print("  ssl  =", sslmode)
print("  pass_len =", len(password or ""), " last_char =", (password or "")[-1:])

conn = psycopg.connect(
    host=host,
    dbname=dbname,
    user=user,
    password=password,
    port=port,
    sslmode=sslmode,
    connect_timeout=10,
)

with conn.cursor() as cur:
    cur.execute("select 1;")
    print("OK:", cur.fetchone())

conn.close()
print("✅ CONECTOU (psycopg3)")
