import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

env_path = Path(__file__).resolve().parent / ".env"
print("LENDO .env EM:", env_path)

load_dotenv(dotenv_path=env_path, override=True)

print("HOST:", os.environ.get("PGHOST"))
print("DB  :", os.environ.get("PGDATABASE"))
print("USER:", os.environ.get("PGUSER"))
print("SSL :", os.environ.get("PGSSLMODE"))

pw = os.environ.get("PGPASSWORD", "")
print("PASS LEN:", len(pw))  # não mostra senha

conn = psycopg2.connect(
    host=os.environ["PGHOST"],
    dbname=os.environ["PGDATABASE"],
    user=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    sslmode=os.environ.get("PGSSLMODE", "require"),
)

cur = conn.cursor()
cur.execute("select 1;")
print("OK select 1 =", cur.fetchone()[0])
cur.close()
conn.close()
