from __future__ import annotations

import streamlit as st

from db.connection import get_session
from services.prazos_service import PrazoUpdate, PrazosService
from services.utils import date_to_br_datetime, ensure_br, now_br
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
from ui.components.sections import section_card


def editar_excluir_prazo(items, owner_user_id: int) -> None:
    if not items:
        st.info("Nenhum prazo disponível para editar.")
        return

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

    with st.form(f"form_prazo_edit_{prazo_id}"):
        c1, c2, c3 = st.columns(3)
        evento_e = c1.text_input("Evento *", value=str(getattr(pz, "evento", "") or ""))
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
            index=(list(ORIGENS).index(origem_atual) if origem_atual in ORIGENS else 0),
        )
        referencia_e = c5.text_input(
            "Referência",
            value=str(getattr(pz, "referencia", "") or ""),
        )

        concl = st.checkbox("Concluído", value=bool(getattr(pz, "concluido", False)))
        obs_e = st.text_area(
            "Observações",
            value=str(getattr(pz, "observacoes", "") or ""),
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
    with st.container(border=True):
        section_card(
            "Editar / Excluir",
            "Selecione um prazo e ajuste os campos necessários.",
        )

        all_rows = dicts_to_dataclass(cached_prazos_list_all(owner_user_id, version))
        editar_excluir_prazo(all_rows, owner_user_id)
