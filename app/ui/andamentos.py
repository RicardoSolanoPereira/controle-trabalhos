# app/ui/andamentos.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.andamentos_service import (
    AndamentosService,
    AndamentoCreate,
    AndamentoUpdate,
)

from app.ui.theme import inject_global_css, card
from app.ui.page_header import page_header


# -------------------------
# Helpers / Models
# -------------------------
@dataclass(frozen=True)
class ProcMaps:
    labels: List[str]
    label_to_id: Dict[str, int]
    label_by_id: Dict[int, str]


def _proc_label(p: Processo) -> str:
    tipo = (p.tipo_acao or "").strip()
    papel = (p.papel or "").strip()
    base = f"[{p.id}] {p.numero_processo}"
    if tipo:
        base += f" – {tipo}"
    if papel:
        base += f"  •  {papel}"
    return base


def _combine_date_time(d: date, t: Optional[time]) -> datetime:
    hhmm = t if t is not None else time(0, 0)
    return datetime(d.year, d.month, d.day, hhmm.hour, hhmm.minute, 0)


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")


def _and_label(a, proc_label_by_id: Dict[int, str]) -> str:
    proc = proc_label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    dt = _format_dt(a.data_evento)
    titulo = (a.titulo or "").strip()
    return f"[#{a.id}] {dt} — {proc} — {titulo}"


def _parse_andamento_id_from_label(label: str) -> int:
    # "[#123] ...."
    head = label.split("]")[0]  # "[#123"
    return int(head.replace("[#", "").strip())


def _load_processos(owner_user_id: int) -> List[Processo]:
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


def _build_proc_maps(processos: List[Processo]) -> ProcMaps:
    labels = [_proc_label(p) for p in processos]
    label_to_id = {_proc_label(p): int(p.id) for p in processos}
    label_by_id = {int(p.id): _proc_label(p) for p in processos}
    return ProcMaps(labels=labels, label_to_id=label_to_id, label_by_id=label_by_id)


def _apply_pref_processo_defaults(proc_maps: ProcMaps) -> None:
    """
    Integra com Trabalhos/Prazos/Agenda:
    - se vier st.session_state["pref_processo_id"], pré-seleciona no cadastro e no filtro.
    Não sobrescreve se o usuário já escolheu algo.
    """
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return
    try:
        pref_id_int = int(pref_id)
    except Exception:
        return

    pref_label = proc_maps.label_by_id.get(pref_id_int)
    if not pref_label:
        return

    st.session_state.setdefault("and_create_proc", pref_label)
    st.session_state.setdefault("and_list_filtro_proc", pref_label)


def _load_andamentos_for_list(
    owner_user_id: int,
    *,
    processo_id: Optional[int],
    q: Optional[str],
    limit: int,
):
    with get_session() as s:
        return AndamentosService.list(
            s,
            owner_user_id=owner_user_id,
            processo_id=processo_id,
            q=q,
            limit=limit,
        )


def _load_andamentos_for_edit_picker(owner_user_id: int, limit: int = 500):
    """
    Picker de edição independente dos filtros da lista.
    Evita: “tenho 2 cadastrados mas no editar só aparece 1”.
    """
    with get_session() as s:
        return AndamentosService.list(
            s,
            owner_user_id=owner_user_id,
            processo_id=None,
            q=None,
            limit=limit,
        )


# -------------------------
# Sections
# -------------------------
def _section_create(owner_user_id: int, proc_maps: ProcMaps) -> None:
    with st.container(border=True):
        st.markdown("#### ➕ Novo andamento")
        st.caption("Registre um evento vinculado a um trabalho (andamento).")

        with st.form("form_andamento_create", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 1, 1])

            proc_lbl = c1.selectbox(
                "Trabalho *", proc_maps.labels, key="and_create_proc"
            )
            d = c2.date_input("Data *", value=date.today(), key="and_create_date")

            usar_hora = c3.toggle("Usar hora", value=True, key="and_create_use_time")
            hora: Optional[time] = None
            if usar_hora:
                hora = c3.time_input(
                    "Hora",
                    value=datetime.now().replace(second=0, microsecond=0).time(),
                    key="and_create_time",
                )

            titulo = st.text_input(
                "Título *",
                placeholder="Ex.: Juntada de petição / Intimação / Despacho",
                key="and_create_titulo",
            )
            descricao = st.text_area("Descrição", key="and_create_desc")

            submitted = st.form_submit_button(
                "Salvar andamento", type="primary", use_container_width=True
            )

        if not submitted:
            return

        if not (titulo or "").strip():
            st.error("Informe o **Título**.")
            return

        try:
            processo_id = int(proc_maps.label_to_id[proc_lbl])
            dt_evento = _combine_date_time(d, hora)

            payload = AndamentoCreate(
                processo_id=processo_id,
                data_evento=dt_evento,
                titulo=titulo.strip(),
                descricao=(descricao or "").strip() or None,
            )

            with get_session() as s:
                AndamentosService.create(s, owner_user_id, payload)

            st.success("Andamento criado.")
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao criar andamento: {e}")


def _section_list(
    owner_user_id: int,
    proc_maps: ProcMaps,
) -> Tuple[List, Optional[pd.DataFrame]]:
    with st.container(border=True):
        st.markdown("#### 📋 Lista")
        st.caption("Filtre e visualize rapidamente.")

        cF1, cF2, cF3 = st.columns([3, 2, 1])
        filtro_proc = cF1.selectbox(
            "Trabalho",
            ["(Todos)"] + proc_maps.labels,
            index=0,
            key="and_list_filtro_proc",
        )
        filtro_q = cF2.text_input("Buscar texto", value="", key="and_list_busca")
        filtro_limit = cF3.selectbox(
            "Limite", [100, 200, 300, 500], index=1, key="and_list_limit"
        )

        processo_id = None
        if filtro_proc != "(Todos)":
            processo_id = int(proc_maps.label_to_id[filtro_proc])

        andamentos = _load_andamentos_for_list(
            owner_user_id,
            processo_id=processo_id,
            q=(filtro_q or "").strip() or None,
            limit=int(filtro_limit),
        )

        total = len(andamentos or [])
        com_texto = sum(1 for a in (andamentos or []) if (a.descricao or "").strip())

        k1, k2, k3 = st.columns(3)
        with k1:
            card("Total", f"{total}", "nos filtros", tone="info")
        with k2:
            card("Com descrição", f"{com_texto}", "detalhados", tone="neutral")
        with k3:
            card(
                "Sem descrição",
                f"{max(total - com_texto, 0)}",
                "rápidos",
                tone="neutral",
            )

        st.write("")
        if not andamentos:
            st.info("Nenhum andamento cadastrado com os filtros atuais.")
            return [], None

        df = pd.DataFrame(
            [
                {
                    "id": a.id,
                    "trabalho": proc_maps.label_by_id.get(
                        a.processo_id, f"[{a.processo_id}]"
                    ),
                    "data_evento": _format_dt(a.data_evento),
                    "titulo": a.titulo,
                    "descricao": a.descricao or "",
                }
                for a in andamentos
            ]
        )

        st.dataframe(
            df[["trabalho", "data_evento", "titulo", "descricao"]],
            use_container_width=True,
            hide_index=True,
            height=420,
        )

        return andamentos, df


def _section_edit_delete(
    owner_user_id: int,
    proc_maps: ProcMaps,
) -> None:
    with st.container(border=True):
        st.markdown("#### ✏️ Editar / 🗑️ Excluir")
        st.caption(
            "Selecione um andamento e ajuste os campos. O seletor é independente da lista."
        )

        ands_for_edit = _load_andamentos_for_edit_picker(owner_user_id, limit=500)
        if not ands_for_edit:
            st.info("Nenhum andamento cadastrado.")
            return

        edit_labels = [_and_label(a, proc_maps.label_by_id) for a in ands_for_edit]
        st.session_state.setdefault("and_edit_selected", edit_labels[0])

        selected_label = st.selectbox(
            "Selecione um andamento",
            options=edit_labels,
            index=(
                edit_labels.index(st.session_state.and_edit_selected)
                if st.session_state.and_edit_selected in edit_labels
                else 0
            ),
            key="and_edit_picker",
        )
        st.session_state.and_edit_selected = selected_label

        andamento_id = _parse_andamento_id_from_label(selected_label)

        with get_session() as s:
            a = AndamentosService.get(s, owner_user_id, int(andamento_id))
        if not a:
            st.error("Andamento não encontrado.")
            return

        proc_atual_lbl = proc_maps.label_by_id.get(a.processo_id, proc_maps.labels[0])

        # --- Form de edição ---
        with st.form("form_andamento_edit"):
            c1, c2, c3 = st.columns([3, 1, 1])

            proc_lbl_e = c1.selectbox(
                "Trabalho",
                proc_maps.labels,
                index=(
                    proc_maps.labels.index(proc_atual_lbl)
                    if proc_atual_lbl in proc_maps.labels
                    else 0
                ),
                key="and_edit_proc",
            )

            d_e = c2.date_input("Data", value=a.data_evento.date(), key="and_edit_date")

            usar_hora_e = c3.toggle("Usar hora", value=True, key="and_edit_use_time")
            hora_e: Optional[time] = None
            if usar_hora_e:
                hora_e = c3.time_input(
                    "Hora",
                    value=a.data_evento.time().replace(second=0, microsecond=0),
                    key="and_edit_time",
                )

            titulo_e = st.text_input(
                "Título *", value=a.titulo or "", key="and_edit_titulo"
            )
            desc_e = st.text_area(
                "Descrição", value=a.descricao or "", key="and_edit_desc"
            )

            atualizar = st.form_submit_button(
                "Salvar alterações", type="primary", use_container_width=True
            )

        if atualizar:
            if not (titulo_e or "").strip():
                st.error("Informe o **Título**.")
                return

            try:
                processo_id_e = int(proc_maps.label_to_id[proc_lbl_e])
                dt_evento_e = _combine_date_time(d_e, hora_e)

                payload = AndamentoUpdate(
                    processo_id=processo_id_e,
                    data_evento=dt_evento_e,
                    titulo=titulo_e.strip(),
                    descricao=(desc_e or "").strip() or None,
                )

                with get_session() as s:
                    AndamentosService.update(
                        s, owner_user_id, int(andamento_id), payload
                    )

                st.success("Andamento atualizado.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")

        st.divider()

        # --- Exclusão segura (fora do form) ---
        st.caption("⚠️ Exclusão irreversível")
        confirm = st.checkbox(
            "Confirmo que desejo excluir este andamento.",
            value=False,
            key=f"and_del_confirm_{andamento_id}",
        )
        if st.button(
            "🗑️ Excluir definitivamente",
            type="primary",
            disabled=not confirm,
            use_container_width=True,
            key=f"and_del_btn_{andamento_id}",
        ):
            try:
                with get_session() as s:
                    AndamentosService.delete(s, owner_user_id, int(andamento_id))
                st.success("Andamento excluído.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


# -------------------------
# Page render
# -------------------------
def render(owner_user_id: int) -> None:
    inject_global_css()

    clicked_refresh = page_header(
        "Andamentos",
        "Registro e histórico de eventos do trabalho (intimações, juntadas, despachos...).",
        right_button_label="Recarregar",
        right_button_key="and_btn_recarregar",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked_refresh:
        st.rerun()

    processos = _load_processos(owner_user_id)
    if not processos:
        st.info("Cadastre um trabalho primeiro para registrar andamentos.")
        return

    proc_maps = _build_proc_maps(processos)
    _apply_pref_processo_defaults(proc_maps)

    _section_create(owner_user_id, proc_maps)

    st.write("")

    _section_list(owner_user_id, proc_maps)

    st.write("")

    _section_edit_delete(owner_user_id, proc_maps)
