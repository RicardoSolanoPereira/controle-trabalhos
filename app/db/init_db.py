from __future__ import annotations

from .connection import Base, get_engine


def init_db() -> None:
    """Cria as tabelas no banco, se ainda não existirem."""
    from . import models  # noqa: F401  (registra models no metadata)

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
