from __future__ import annotations

from typing import Any

import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.prazos_service import PrazosService


def prazo_proc_to_dict(prazo: Any, proc: Any) -> dict[str, Any]:
    return {
        "prazo": {
            "id": int(getattr(prazo, "id", 0) or 0),
            "evento": str(getattr(prazo, "evento", "") or ""),
            "data_limite": getattr(prazo, "data_limite", None),
            "prioridade": str(getattr(prazo, "prioridade", "Média") or "Média"),
            "concluido": bool(getattr(prazo, "concluido", False)),
            "origem": getattr(prazo, "origem", None),
            "referencia": getattr(prazo, "referencia", None),
            "observacoes": getattr(prazo, "observacoes", None),
            "processo_id": int(getattr(prazo, "processo_id", 0) or 0),
        },
        "proc": {
            "id": int(getattr(proc, "id", 0) or 0),
            "numero_processo": str(getattr(proc, "numero_processo", "") or ""),
            "tipo_acao": getattr(proc, "tipo_acao", None),
            "comarca": getattr(proc, "comarca", None),
            "vara": getattr(proc, "vara", None),
            "contratante": getattr(proc, "contratante", None),
            "papel": getattr(proc, "papel", None),
        },
    }


@st.cache_data(show_spinner=False, ttl=45)
def cached_processos(owner_user_id: int, version: int) -> list[dict[str, Any]]:
    _ = version

    with get_session() as s:
        procs = (
            s.execute(
                select(Processo)
                .where(Processo.owner_user_id == owner_user_id)
                .order_by(Processo.id.desc())
            )
            .scalars()
            .all()
        )

    out: list[dict[str, Any]] = []
    for p in procs:
        out.append(
            {
                "id": int(p.id),
                "numero_processo": str(p.numero_processo or ""),
                "tipo_acao": p.tipo_acao,
                "comarca": p.comarca,
                "vara": p.vara,
                "contratante": p.contratante,
                "papel": p.papel,
            }
        )
    return out


@st.cache_data(show_spinner=False, ttl=45)
def cached_prazos_list_all(owner_user_id: int, version: int) -> list[dict[str, Any]]:
    _ = version

    with get_session() as s:
        rows_all = PrazosService.list_all(s, owner_user_id, status="all")

    out: list[dict[str, Any]] = []
    for prazo, proc in rows_all:
        if prazo is None or proc is None:
            continue
        out.append(prazo_proc_to_dict(prazo, proc))
    return out
