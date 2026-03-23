from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.utils import ensure_br, format_date_br
from ui.theme import card
from ui.layout import section_surface
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
    return st.radio(
        "Seção",
        ["Cadastrar", "Lista", "Editar / Excluir"],
        horizontal=True,
        label_visibility="collapsed",
        key=key,
    )


def list_tabs_selector() -> str:
    selected = st.radio(
        "Visão",
        ["Abertos", "Hoje", "Atrasados", "Vencem (7 dias)", "Concluídos"],
        horizontal=True,
        label_visibility="collapsed",
        key=KEY_LIST_SELECTOR,
    )
    st.session_state[KEY_LIST_ACTIVE] = selected
    return selected


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


def chip(text: str) -> str:
    value = safe_str(text)
    if not value:
        return ""
    return (
        "<span style='display:inline-block;padding:6px 10px;border-radius:999px;"
        "background:rgba(17,25,40,0.06);font-size:12px;font-weight:700;"
        "margin-right:6px;margin-bottom:6px;'>"
        f"{value}</span>"
    )


def count_proc_open_metrics(
    proc_id: int, rows: list[PrazoRow]
) -> tuple[int, int, str | None]:
    abertos = [r for r in rows if r.processo_id == proc_id and not r.concluido]
    atrasados = [r for r in abertos if dias_restantes(r.data_limite) < 0]
    proximos = sorted(abertos, key=lambda r: ensure_br(r.data_limite))
    prox_txt = format_date_br(proximos[0].data_limite) if proximos else None
    return len(abertos), len(atrasados), prox_txt


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

    chips = []
    if numero:
        chips.append(chip(f"📄 {numero}"))
    if tipo_acao:
        chips.append(chip(f"🗂️ {tipo_acao}"))
    if papel:
        chips.append(chip(f"⚖️ {papel}"))
    if comarca:
        chips.append(chip(f"🏛 {comarca}"))
    if vara:
        chips.append(chip(f"🏢 {vara}"))
    if contratante:
        chips.append(chip(f"👤 {contratante}"))

    abertos, atrasados, prox_txt = count_proc_open_metrics(proc_id, all_rows)
    if abertos:
        chips.append(chip(f"📋 {abertos} abertos"))
    if atrasados:
        chips.append(chip(f"🔴 {atrasados} atrasados"))
    if prox_txt:
        chips.append(chip(f"📅 Próximo: {prox_txt}"))

    chips_html = " ".join([c for c in chips if c])

    with section_surface("Contexto do trabalho"):
        render_html(
            f"""
            <div>
                {chips_html if chips_html else "<span class='pz-muted'>—</span>"}
            </div>
            """
        )

        col1, col2 = st.columns([0.8, 0.2])
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
        render_html(
            """
            <div class="pz-priority-empty">
                Nenhum prazo aberto com os filtros atuais.
            </div>
            """
        )
        return

    for row in top_items:
        dias = dias_restantes(row.data_limite)
        status = status_label(dias, row.concluido)

        if dias < 0:
            urgencia_txt = f"{abs(dias)} dia(s) em atraso"
            css_class = "pz-priority-card is-overdue"
        elif dias == 0:
            urgencia_txt = "vence hoje"
            css_class = "pz-priority-card is-today"
        elif dias <= 7:
            urgencia_txt = f"vence em {dias} dia(s)"
            css_class = "pz-priority-card is-soon"
        else:
            urgencia_txt = f"{dias} dia(s) restantes"
            css_class = "pz-priority-card"

        badges = [
            f"<span class='pz-badge'>{status}</span>",
            f"<span class='pz-badge'>Prioridade: {row.prioridade}</span>",
            f"<span class='pz-badge'>{urgencia_txt}</span>",
        ]

        render_html(
            f"""
            <div class="{css_class}">
                <div style="font-weight:800;font-size:1rem;margin-bottom:4px;">
                    {row.evento}
                </div>
                <div class="pz-meta" style="margin-bottom:8px;">
                    Data: {format_date_br(row.data_limite)}
                </div>
                <div>{" ".join(badges)}</div>
            </div>
            """
        )


def render_soft_empty(message: str) -> None:
    render_html(f'<div class="pz-soft-empty">{message}</div>')


from collections.abc import Callable
