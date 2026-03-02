from __future__ import annotations

from .connection import get_engine
from .models import Base


def init_db() -> None:
    """Cria as tabelas no banco, se ainda não existirem."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
