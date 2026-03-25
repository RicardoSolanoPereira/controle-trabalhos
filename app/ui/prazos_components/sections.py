from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

from services.utils import ensure_br, format_date_br
from ui.layout import section_surface
from ui.theme import card, muted, pill, status_banner, subtle_divider
from ui.prazos_components.constants import KEY_LIST_ACTIVE, KEY_LIST_SELECTOR
from ui.prazos_components.helpers import (
    dias_restantes,
    priority_rank,
    safe_str,
    status_label,
)
from ui.prazos_components.types import PrazoRow


def render_html(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def section_tabs(key: str) -> str:
    tabs = ["Cadastrar", "Lista", "Editar / Excluir"]
    current = st.session_state.get(key, tabs[0])

    cols = st.columns(len(tabs), gap="small")
    for col, label in zip(cols, tabs):
        with col:
            is_active = current == label
            if st.button(
                label,
                key=f"{key}_{label}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state[key] = label
                current = label

    return current


def list_tabs_selector() -> str:
    tabs = ["Abertos", "Hoje", "Atrasados", "Vencem (7 dias)", "Concluídos"]
    current = st.session_state.get(KEY_LIST_SELECTOR, tabs[0])

    cols = st.columns(len(tabs), gap="small")
    for col, label in zip(cols, tabs):
        with col:
            is_active = current == label
            if st.button(
                label,
                key=f"{KEY_LIST_SELECTOR}_{label}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state[KEY_LIST_SELECTOR] = label
                current = label

    st.session_state[KEY_LIST_ACTIVE] = current
    return current


def render_df(df: pd.DataFrame, cols: list[str], height: int) -> None:
    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True,
        height=height,
    )


def render_summary_kpis(
    abertos: int,
    hoje: int,
    atrasados: int,
    vencem7: int,
    concluidos: int,
) -> None:
    c1, c2 = st.columns(2)
    with c1:
        card("Abertos", f"{abertos}", "em acompanhamento", tone="info")
    with c2:
        card("Hoje", f"{hoje}", "vencem hoje", tone="warning" if hoje else "neutral")

    c3, c4 = st.columns(2)
    with c3:
        card(
            "Atrasados",
            f"{atrasados}",
            "ação imediata",
            tone="danger" if atrasados else "neutral",
        )
    with c4:
        card(
            "7 dias",
            f"{vencem7}",
            "janela curta",
            tone="warning" if vencem7 else "neutral",
        )

    c5, _ = st.columns(2)
    with c5:
        card("Concluídos", f"{concluidos}", "histórico finalizado", tone="neutral")


def count_proc_open_metrics(
    proc_id: int, rows: list[PrazoRow]
) -> tuple[int, int, str | None]:
    abertos = [r for r in rows if r.processo_id == proc_id and not r.concluido]
    atrasados = [r for r in abertos if dias_restantes(r.data_limite) < 0]
    proximos = sorted(abertos, key=lambda r: ensure_br(r.data_limite))
    prox_txt = format_date_br(proximos[0].data_limite) if proximos else None
    return len(abertos), len(atrasados), prox_txt


def _tone_for_priority_context(atrasados: int, abertos: int) -> str:
    if atrasados > 0:
        return "danger"
    if abertos > 0:
        return "info"
    return "neutral"


def render_contexto_trabalho(
    proc: dict[str, Any] | None, all_rows: list[PrazoRow]
) -> None:
    if not proc:
        return

    numero = safe_str(proc.get("numero_processo"))
    tipo_acao = safe_str(proc.get("tipo_acao"))
    comarca = safe_str(proc.get("comarca"))
    vara = safe_str(proc.get("vara"))
    contratante = safe_str(proc.get("contratante"))
    papel = safe_str(proc.get("papel"))
    proc_id = int(proc.get("id") or 0)

    abertos, atrasados, prox_txt = count_proc_open_metrics(proc_id, all_rows)
    tone = _tone_for_priority_context(atrasados, abertos)

    subtitle_parts: list[str] = []
    if numero:
        subtitle_parts.append(numero)
    if tipo_acao:
        subtitle_parts.append(tipo_acao)
    if comarca:
        subtitle_parts.append(comarca)
    if vara:
        subtitle_parts.append(vara)

    subtitle = " • ".join(subtitle_parts) if subtitle_parts else "Trabalho selecionado."

    with section_surface("Contexto do trabalho"):
        status_banner(
            "Visão rápida do trabalho selecionado",
            subtitle,
            tone=tone,
        )

        subtle_divider()

        meta_cols = st.columns([1, 1, 1, 1])
        if papel:
            with meta_cols[0]:
                pill(f"Papel: {papel}", tone="neutral")
        if contratante:
            with meta_cols[1]:
                pill(f"Contratante: {contratante}", tone="neutral")
        if abertos:
            with meta_cols[2]:
                pill(f"{abertos} prazo(s) abertos", tone="info")
        if atrasados:
            with meta_cols[3]:
                pill(f"{atrasados} atrasado(s)", tone="danger")

        if prox_txt:
            st.caption(f"Próximo vencimento: {prox_txt}")

        col1, col2 = st.columns([0.82, 0.18])
        with col2:
            if st.button("Limpar", key="pz_clear_pref_ctx", use_container_width=True):
                for key in ("pref_processo_id", "pref_processo_ref"):
                    st.session_state.pop(key, None)
                st.rerun()


def render_priority_queue(filtered: list[PrazoRow]) -> None:
    open_rows = [r for r in filtered if not r.concluido]
    top_items = sorted(
        open_rows,
        key=lambda r: (
            dias_restantes(r.data_limite),
            priority_rank(r.prioridade),
            ensure_br(r.data_limite),
        ),
    )[:5]

    st.markdown("#### Fila prioritária")
    st.caption("Veja primeiro o que exige ação imediata ou merece atenção próxima.")

    if not top_items:
        status_banner(
            "Nenhum prazo aberto com os filtros atuais.",
            "Ajuste os filtros ou cadastre um novo prazo para acompanhar itens nesta fila.",
            tone="success",
        )
        return

    for row in top_items:
        dias = dias_restantes(row.data_limite)
        status = status_label(dias, row.concluido)

        if dias < 0:
            urgencia_txt = f"{abs(dias)} dia(s) em atraso"
            tone = "danger"
        elif dias == 0:
            urgencia_txt = "vence hoje"
            tone = "warning"
        elif dias <= 7:
            urgencia_txt = f"vence em {dias} dia(s)"
            tone = "warning"
        else:
            urgencia_txt = f"{dias} dia(s) restantes"
            tone = "info"

        with section_surface():
            c1, c2 = st.columns([2.2, 1.2])

            with c1:
                st.markdown(f"**{safe_str(row.evento)}**")
                muted(f"Data: {format_date_br(row.data_limite)}")

            with c2:
                pill(status, tone=tone)
                st.caption(f"Prioridade: {safe_str(row.prioridade)}")
                st.caption(urgencia_txt)


def render_soft_empty(message: str) -> None:
    status_banner(
        "Sem resultados",
        message,
        tone="info",
    )
