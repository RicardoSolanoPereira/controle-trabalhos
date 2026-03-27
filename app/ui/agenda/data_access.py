from __future__ import annotations

from typing import Optional

import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.agendamentos_service import AgendamentosService


@st.cache_data(show_spinner=False, ttl=45)
def cached_processos(owner_user_id: int, version: int) -> list[Processo]:
    _ = version
    with get_session() as s:
        return (
            s.execute(
                select(Processo)
                .where(Processo.owner_user_id == owner_user_id)
                .order_by(Processo.id.desc())
            )
            .scalars()
            .all()
        )


@st.cache_data(show_spinner=False, ttl=45)
def cached_agendamentos_list(
    owner_user_id: int,
    version: int,
    processo_id: Optional[int],
    tipo: Optional[str],
    status: Optional[str],
    q: Optional[str],
    order: str,
    limit: int,
):
    _ = version
    with get_session() as s:
        return AgendamentosService.list(
            s,
            owner_user_id=owner_user_id,
            processo_id=processo_id,
            tipo=tipo,
            status=status,
            q=q,
            order=order,
            limit=limit,
        )


@st.cache_data(show_spinner=False, ttl=45)
def cached_agendamentos_edit_picker(
    owner_user_id: int,
    version: int,
    limit: int = 500,
):
    _ = version
    with get_session() as s:
        return AgendamentosService.list(
            s,
            owner_user_id=owner_user_id,
            processo_id=None,
            tipo=None,
            status=None,
            q=None,
            order="desc",
            limit=limit,
        )
