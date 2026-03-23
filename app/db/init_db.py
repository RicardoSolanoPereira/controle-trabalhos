from __future__ import annotations

from db.connection import Base, get_engine


def init_db() -> None:
    """Cria as tabelas no banco, se ainda não existirem."""
    from db import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
