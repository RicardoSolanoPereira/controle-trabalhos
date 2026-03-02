import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

load_dotenv()

url = os.environ["DATABASE_URL"].strip()
p = urlparse(url)

print("SCHEME:", p.scheme)
print("USER:", p.username)
print("HOST:", p.hostname)
print("DB  :", p.path.lstrip("/"))

if p.hostname and "@" in p.hostname:
    raise RuntimeError("ERRO: seu HOST está com '@' dentro. Corrija a DATABASE_URL.")

engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    print("OK select 1 =", conn.execute(text("select 1")).scalar())
