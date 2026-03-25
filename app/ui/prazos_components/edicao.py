from __future__ import annotations

import streamlit as st

from db.connection import get_session
from services.prazos_service import PrazoUpdate, PrazosService
from services.utils import date_to_br_datetime, ensure_br, format_date_br, now_br
from ui.layout import compact_gap, section_surface
from ui.theme import card, pill, status_banner
from ui_state import bump_data_version
from ui.prazos_components.cache import cached_prazos_list_all
from ui.prazos_components.constants import ORIGENS, PRIORIDADES
from ui.prazos_components.helpers import (
    dicts_to_dataclass,
    dias_restantes,
    norm,
    priority_rank,
    safe_str,
    status_label,
)


def _build_options(items) -> tuple[list[str], dict[str, int]]:
    options: list[str] = []
    id_by_label: dict[str, int] = {}

    ordered = sorted(
        items,
        key=lambda r: (
            r.concluido,
            dias_restantes(r.data_limite),
            priority_rank(r.prioridade),
            ensure_br(r.data_limite),
        ),
    )

    for row in ordered:
        label = (
            f"[{row.prazo_id}] {row.processo_numero} — "
            f"{row.evento} — {ensure_br(row.data_limite).strftime('%d/%m/%Y')} — "
            f"{status_label(dias_restantes(row.data_limite), row.concluido)}"
        )
        options.append(label)
        id_by_label[label] = int(row.prazo_id)

    return options, id_by_label


def _tone_for_row(row) -> str:
    dias = dias_restantes(row.data_limite)
    if getattr(row, "concluido", False):
        return "success"
    if dias < 0:
        return "danger"
    if dias == 0:
        return "warning"
    if dias <= 7:
        return "warning"
    return "info"


def _render_selected_summary(pz) -> None:
    dias = dias_restantes(pz.data_limite)
    status = status_label(dias, bool(getattr(pz, "concluido", False)))
    tone = _tone_for_row(pz)

    with section_surface(
        "Resumo do prazo selecionado",
        subtitle="Confira o status atual antes de editar ou excluir.",
    ):
        status_banner(
            "Prazo carregado para edição",
            f"{safe_str(getattr(pz, 'evento', ''))} • {format_date_br(getattr(pz, 'data_limite', None))}",
            tone=tone,
        )

        compact_gap()

        c1, c2, c3 = st.columns(3)
        with c1:
            card(
                "Data limite",
                format_date_br(getattr(pz, "data_limite", None)),
                "vencimento registrado",
                tone=tone,
            )
        with c2:
            card(
                "Status",
                status,
                "situação operacional",
                tone=tone,
            )
        with c3:
            card(
                "Prioridade",
                safe_str(getattr(pz, "prioridade", "")) or "—",
                "classificação atual",
                tone="neutral",
            )

        compact_gap()

        meta_cols = st.columns(3)
        origem_atual = safe_str(getattr(pz, "origem", "") or "")
        referencia_atual = safe_str(getattr(pz, "referencia", "") or "")
        concluido_atual = bool(getattr(pz, "concluido", False))

        with meta_cols[0]:
            if origem_atual:
                pill(f"Origem: {origem_atual}", tone="neutral")
        with meta_cols[1]:
            if referencia_atual:
                pill(f"Ref.: {referencia_atual}", tone="neutral")
        with meta_cols[2]:
            pill(
                "Concluído" if concluido_atual else "Em aberto",
                tone="success" if concluido_atual else tone,
            )


def editar_excluir_prazo(items, owner_user_id: int) -> None:
    if not items:
        status_banner(
            "Nenhum prazo disponível para edição.",
            "Cadastre um prazo primeiro para poder atualizá-lo ou excluí-lo.",
            tone="info",
        )
        return

    options, id_by_label = _build_options(items)

    with section_surface(
        "Selecionar prazo",
        subtitle="Escolha o item que deseja editar ou excluir.",
    ):
        selected = st.selectbox(
            "Selecione um prazo para editar",
            options,
            key="pz_edit_select",
        )

    prazo_id = id_by_label[selected]

    with get_session() as s:
        pz = PrazosService.get(s, owner_user_id, int(prazo_id))

    if not pz:
        st.error("Prazo não encontrado.")
        return

    try:
        pz_date = ensure_br(pz.data_limite).date()
    except Exception:
        pz_date = now_br().date()

    _render_selected_summary(pz)

    with section_surface(
        "Editar prazo",
        subtitle="Atualize os campos necessários e salve com segurança.",
    ):
        with st.form(f"form_prazo_edit_{prazo_id}"):
            c1, c2, c3 = st.columns(3)
            evento_e = c1.text_input(
                "Evento *", value=str(getattr(pz, "evento", "") or "")
            )
            data_e = c2.date_input("Data limite *", value=pz_date)
            prio_e = c3.selectbox(
                "Prioridade",
                list(PRIORIDADES),
                index=(
                    list(PRIORIDADES).index(pz.prioridade)
                    if pz.prioridade in PRIORIDADES
                    else 1
                ),
            )

            c4, c5 = st.columns(2)
            origem_atual = getattr(pz, "origem", "") or ""
            origem_e = c4.selectbox(
                "Origem",
                list(ORIGENS),
                index=(
                    list(ORIGENS).index(origem_atual) if origem_atual in ORIGENS else 0
                ),
            )
            referencia_e = c5.text_input(
                "Referência",
                value=str(getattr(pz, "referencia", "") or ""),
            )

            concl = st.checkbox(
                "Concluído", value=bool(getattr(pz, "concluido", False))
            )
            obs_e = st.text_area(
                "Observações",
                value=str(getattr(pz, "observacoes", "") or ""),
                placeholder="Atualize orientações internas, contexto do prazo ou observações operacionais.",
            )

            b1, b2 = st.columns(2)
            salvar = b1.form_submit_button(
                "Salvar alterações",
                type="primary",
                use_container_width=True,
            )
            excluir = b2.form_submit_button(
                "Excluir (irreversível)",
                use_container_width=True,
            )

    if salvar:
        if not safe_str(evento_e):
            st.error("Evento não pode ficar vazio.")
            return

        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(
                        evento=safe_str(evento_e),
                        data_limite=date_to_br_datetime(data_e),
                        prioridade=prio_e,
                        concluido=concl,
                        origem=norm(origem_e),
                        referencia=norm(referencia_e),
                        observacoes=norm(obs_e),
                    ),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo atualizado.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    if excluir:
        try:
            with get_session() as s:
                PrazosService.delete(s, owner_user_id, int(prazo_id))
            bump_data_version(owner_user_id)
            st.warning("Prazo excluído.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")


def render_editar(owner_user_id: int, version: int) -> None:
    all_rows = dicts_to_dataclass(cached_prazos_list_all(owner_user_id, version))
    editar_excluir_prazo(all_rows, owner_user_id)
