from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# =========================================================
# CARREGA .env (sempre o da raiz do projeto, com override)
# =========================================================
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=True)

DEBUG = os.environ.get("DEBUG", "0") == "1"


# =========================================================
# HELPERS
# =========================================================
def _mask_db_url(db_url: str) -> str:
    return re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1***\3", db_url)


def _remove_channel_binding(db_url: str) -> str:
    db_url = re.sub(
        r"(&|\?)channel_binding=require",
        lambda m: "?" if m.group(1) == "?" else "",
        db_url,
    )

    db_url = db_url.replace("?&", "?")
    db_url = db_url.replace("??", "?")

    if db_url.endswith("?"):
        db_url = db_url[:-1]

    return db_url


def get_db_url() -> str:
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        raise RuntimeError(
            "DATABASE_URL não configurado. "
            "Defina no .env ou nas variáveis do ambiente."
        )

    db_url = db_url.strip()
    db_url = _remove_channel_binding(db_url)

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    elif db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)

    elif db_url.startswith("postgresql+psycopg://"):
        pass

    else:
        raise RuntimeError(
            f"Esquema inválido em DATABASE_URL: {db_url.split(':', 1)[0]!r}"
        )

    if "sslmode=" not in db_url:
        join = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{join}sslmode=require"

    return db_url


# =========================================================
# BASE
# =========================================================
class Base(DeclarativeBase):
    pass


# =========================================================
# ENGINE / SESSION (Singleton)
# =========================================================
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _engine, _SessionLocal

    if _engine is None:
        db_url = get_db_url()

        _engine = create_engine(
            db_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "1800")),
            pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
            max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "5")),
            connect_args={
                "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))
            },
        )

        _SessionLocal = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

        if DEBUG:
            print("BANCO EM USO:", _mask_db_url(db_url))
            print("ENV:", str(ENV_PATH))

    return _engine


def get_session():
    global _SessionLocal

    if _SessionLocal is None:
        get_engine()

    assert _SessionLocal is not None
    return _SessionLocal()


@contextmanager
def session_scope():
    s = get_session()

    try:
        yield s
        s.commit()

    except Exception:
        s.rollback()
        raise

    finally:
        s.close()


def db_healthcheck() -> None:
    engine = get_engine()

    with engine.connect() as conn:
        ok = conn.execute(text("select 1")).scalar()
        info = conn.execute(
            text(
                "select current_database(), current_user, inet_server_addr(), version()"
            )
        ).one()

        if DEBUG:
            print("DB OK select 1 =", ok)
            print("DB INFO =", info)


__all__ = [
    "Base",
    "get_db_url",
    "get_engine",
    "get_session",
    "session_scope",
    "db_healthcheck",
]
