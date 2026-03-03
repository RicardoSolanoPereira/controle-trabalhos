# connection.py
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
# Ajuste: este arquivo está em db/connection.py, então a raiz é parents[1]
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH, override=True)

DEBUG = os.environ.get("DEBUG", "0") == "1"


# =========================================================
# HELPERS
# =========================================================
def _mask_db_url(db_url: str) -> str:
    """Mascara a senha para não vazar em logs."""
    return re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1***\3", db_url)


def _remove_channel_binding(db_url: str) -> str:
    """Remove channel_binding=require (não é necessário e pode causar dor de cabeça)."""
    # remove tanto "&channel_binding=require" quanto "?channel_binding=require"
    db_url = re.sub(
        r"(&|\?)channel_binding=require",
        lambda m: "?" if m.group(1) == "?" else "",
        db_url,
    )
    # se ficou "??" ou "?&" em casos raros, normaliza
    db_url = db_url.replace("?&", "?")
    db_url = db_url.replace("??", "?")
    # se ficou terminando com "?" por remoção, remove
    if db_url.endswith("?"):
        db_url = db_url[:-1]
    return db_url


def get_db_url() -> str:
    """
    Lê DATABASE_URL do ambiente e garante compatibilidade com Neon.

    - Padroniza para SQLAlchemy + psycopg (v3): postgresql+psycopg://
    - Garante sslmode=require.
    - Remove channel_binding=require, se existir.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL não configurado. "
            "Defina no .env ou nas variáveis do ambiente."
        )

    db_url = db_url.strip()
    db_url = _remove_channel_binding(db_url)

    # Normaliza para psycopg (v3)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql+psycopg2://"):
        # força psycopg v3
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql+psycopg://"):
        pass
    else:
        raise RuntimeError(
            f"Esquema inválido em DATABASE_URL: {db_url.split(':', 1)[0]!r}. "
            "Use postgres://, postgresql://, postgresql+psycopg2:// ou postgresql+psycopg://"
        )

    # Neon exige SSL
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
    """
    Retorna uma Session SQLAlchemy.
    Ex:
        with get_session() as s:
            ...
    """
    global _SessionLocal
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


@contextmanager
def session_scope():
    """
    Context manager seguro para transações:
        with session_scope() as s:
            ...
    Faz commit no sucesso e rollback em exceção, garantindo close().
    """
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
    """
    Teste rápido: rode uma vez para confirmar que conectou no Neon.
    """
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
