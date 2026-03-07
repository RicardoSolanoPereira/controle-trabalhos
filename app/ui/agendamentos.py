# app/ui/agendamentos.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.agendamentos_service import (
    AgendamentosService,
    AgendamentoCreate,
    AgendamentoUpdate,
    TIPOS_VALIDOS,
    STATUS_VALIDOS,
)
from ui.theme import inject_global_css, card
from ui.page_header import page_header


# -------------------------
# Helpers
# -------------------------
@dataclass(frozen=True)
class ProcMaps:
    labels: List[str]
    label_to_id: Dict[str, int]
    label_by_id: Dict[int, str]


def _is_mobile_hint() -> bool:
    """
    Streamlit não expõe viewport real.
    Heurística controlada por toggle (útil para testes no celular).
    """
    return bool(st.session_state.get("ui_mobile_mode", False))


def _proc_label(p: Processo) -> str:
    tipo = (p.tipo_acao or "").strip()
    papel = (p.papel or "").strip()
    base = f"[{p.id}] {p.numero_processo}"
    if tipo:
        base += f" – {tipo}"
    if papel:
        base += f"  •  {papel}"
    return base


def _combine_date_time(d: date, t) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, 0)


def _sanitize_end_dt(inicio: datetime, fim: datetime) -> Optional[datetime]:
    if fim == inicio:
        return None
    if fim < inicio:
        raise ValueError("A data/hora de fim não pode ser anterior ao início.")
    return fim


def _format_dt(dt: Optional[datetime]) -> str:
    return dt.strftime("%d/%m/%Y %H:%M") if dt else ""


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
    labels: List[str] = []
    label_to_id: Dict[str, int] = {}
    label_by_id: Dict[int, str] = {}

    for p in processos:
        lbl = _proc_label(p)
        labels.append(lbl)
        label_to_id[lbl] = int(p.id)
        label_by_id[int(p.id)] = lbl

    return ProcMaps(labels=labels, label_to_id=label_to_id, label_by_id=label_by_id)


def _load_agendamentos_for_list(
    owner_user_id: int,
    *,
    processo_id: Optional[int],
    tipo: Optional[str],
    status: Optional[str],
    q: Optional[str],
    order: str,
    limit: int,
):
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


def _load_agendamentos_for_edit_picker(owner_user_id: int, limit: int = 500):
    """
    O seletor de edição não depende dos filtros da lista.
    Evita o bug: “tenho 2 cadastrados mas no editar só aparece 1”.
    """
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


def _build_agendamento_label(a, proc_label_by_id: Dict[int, str]) -> str:
    proc_lbl = proc_label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    return f"[#{a.id}] {_format_dt(a.inicio)} — {a.tipo} — {a.status} — {proc_lbl}"


def _parse_agendamento_id_from_label(label: str) -> int:
    head = label.split("]")[0]  # "[#123"
    return int(head.replace("[#", "").strip())


def _apply_pref_processo_defaults(proc_maps: ProcMaps) -> None:
    """
    Integra com Trabalhos/Prazos:
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

    st.session_state.setdefault("ag_create_proc", pref_label)
    st.session_state.setdefault("ag_list_filtro_proc", pref_label)


def _render_agendamento_card(a, proc_label_by_id: Dict[int, str]) -> None:
    proc_lbl = proc_label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    local = (a.local or "").strip()
    desc = (a.descricao or "").strip()

    st.markdown(
        f"""
        <div class="sp-surface" style="margin-bottom:10px;">
          <div style="font-weight:850; font-size:0.98rem;">
            {proc_lbl}
          </div>
          <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
            <span class="sp-chip">📌 {a.tipo}</span>
            <span class="sp-chip">🧾 {a.status}</span>
            <span class="sp-chip">🕒 {_format_dt(a.inicio)}</span>
            {f"<span class='sp-chip'>⏱️ {_format_dt(a.fim)}</span>" if a.fim else ""}
            {f"<span class='sp-chip'>📍 {local}</span>" if local else ""}
          </div>
          {f"<div style='margin-top:8px; color: rgba(15,23,42,0.75);'><b>Descrição:</b> {desc}</div>" if desc else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------
# Page
# -------------------------
def render(owner_user_id: int):
    inject_global_css()

    clicked_refresh = page_header(
        "Agendamentos",
        "Cadastro, filtros e controle de compromissos.",
        right_button_label="Recarregar",
        right_button_key="ag_btn_recarregar",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked_refresh:
        st.rerun()

    # Toggle de testes (mesmo padrão da aba Trabalhos)
    with st.sidebar.expander("📱 Ajustes (UI)", expanded=False):
        st.checkbox("Modo mobile (cards)", value=False, key="ui_mobile_mode")

    processos = _load_processos(owner_user_id)
    if not processos:
        st.info("Cadastre um trabalho primeiro para criar agendamentos.")
        return

    proc_maps = _build_proc_maps(processos)
    _apply_pref_processo_defaults(proc_maps)

    TIPOS = list(TIPOS_VALIDOS)
    STATUS = list(STATUS_VALIDOS)

    # =========================================================
    # CRIAR
    # =========================================================
    with st.container(border=True):
        st.markdown("#### ➕ Novo agendamento")
        st.caption("Crie um compromisso vinculado a um trabalho.")

        with st.form("form_agendamento_create", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            proc_lbl = c1.selectbox(
                "Trabalho *", proc_maps.labels, key="ag_create_proc"
            )
            tipo = c2.selectbox("Tipo *", TIPOS, key="ag_create_tipo")
            status = c3.selectbox("Status *", STATUS, index=0, key="ag_create_status")

            c4, c5 = st.columns(2)
            d_ini = c4.date_input(
                "Data início *", value=date.today(), key="ag_create_dini"
            )
            h_ini = c5.time_input(
                "Hora início *",
                value=datetime.now().replace(second=0, microsecond=0).time(),
                key="ag_create_hini",
            )

            c6, c7 = st.columns(2)
            d_fim = c6.date_input(
                "Data fim (opcional)", value=d_ini, key="ag_create_dfim"
            )
            h_fim = c7.time_input(
                "Hora fim (opcional)",
                value=datetime.now().replace(second=0, microsecond=0).time(),
                key="ag_create_hfim",
            )

            local = st.text_input("Local", key="ag_create_local")
            descricao = st.text_area("Descrição", key="ag_create_desc")

            submitted = st.form_submit_button(
                "Salvar agendamento", type="primary", use_container_width=True
            )

        if submitted:
            try:
                processo_id = int(proc_maps.label_to_id[proc_lbl])
                inicio = _combine_date_time(d_ini, h_ini)
                fim = _combine_date_time(d_fim, h_fim)
                fim_val = _sanitize_end_dt(inicio, fim)

                with get_session() as s:
                    AgendamentosService.create(
                        s,
                        owner_user_id=owner_user_id,
                        payload=AgendamentoCreate(
                            processo_id=processo_id,
                            tipo=tipo,
                            inicio=inicio,
                            fim=fim_val,
                            local=local,
                            descricao=descricao,
                            status=status,
                        ),
                    )

                st.success("Agendamento criado.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao criar agendamento: {e}")

    st.write("")

    # =========================================================
    # LISTA (filtros)
    # =========================================================
    with st.container(border=True):
        st.markdown("#### 📋 Lista")
        st.caption("Filtre e visualize rapidamente.")

        if _is_mobile_hint():
            filtro_proc = st.selectbox(
                "Trabalho",
                ["(Todos)"] + proc_maps.labels,
                index=0,
                key="ag_list_filtro_proc",
            )
            filtro_tipo = st.selectbox(
                "Tipo",
                ["(Todos)"] + TIPOS,
                index=0,
                key="ag_list_filtro_tipo",
            )
            filtro_status = st.selectbox(
                "Status",
                ["(Todos)"] + STATUS,
                index=0,
                key="ag_list_filtro_status",
            )
            filtro_limit = st.selectbox(
                "Limite", [100, 200, 300, 500], index=1, key="ag_list_limit"
            )

            order = st.radio(
                "Ordem", ["Próximos", "Recentes"], horizontal=True, key="ag_list_order"
            )
            filtro_q = st.text_input(
                "Buscar (local/descrição)", value="", key="ag_list_busca"
            )
        else:
            cF1, cF2, cF3, cF4 = st.columns([3, 2, 2, 1])
            filtro_proc = cF1.selectbox(
                "Trabalho",
                ["(Todos)"] + proc_maps.labels,
                index=0,
                key="ag_list_filtro_proc",
            )
            filtro_tipo = cF2.selectbox(
                "Tipo",
                ["(Todos)"] + TIPOS,
                index=0,
                key="ag_list_filtro_tipo",
            )
            filtro_status = cF3.selectbox(
                "Status",
                ["(Todos)"] + STATUS,
                index=0,
                key="ag_list_filtro_status",
            )
            filtro_limit = cF4.selectbox(
                "Limite", [100, 200, 300, 500], index=1, key="ag_list_limit"
            )

            cO1, cO2 = st.columns([1, 3])
            order = cO1.radio(
                "Ordem", ["Próximos", "Recentes"], horizontal=True, key="ag_list_order"
            )
            filtro_q = cO2.text_input(
                "Buscar (local/descrição)", value="", key="ag_list_busca"
            )

        order_val = "asc" if order == "Próximos" else "desc"

        processo_id = None
        if filtro_proc != "(Todos)":
            processo_id = int(proc_maps.label_to_id[filtro_proc])

        tipo_val = None if filtro_tipo == "(Todos)" else filtro_tipo
        status_val = None if filtro_status == "(Todos)" else filtro_status
        q_val = (filtro_q or "").strip() or None

        ags = _load_agendamentos_for_list(
            owner_user_id,
            processo_id=processo_id,
            tipo=tipo_val,
            status=status_val,
            q=q_val,
            order=order_val,
            limit=int(filtro_limit),
        )

        # KPIs rápidos (padrão painel)
        total = len(ags or [])
        agendados = sum(
            1 for a in (ags or []) if (a.status or "").lower() == "agendado"
        )
        realizados = sum(
            1 for a in (ags or []) if (a.status or "").lower() == "realizado"
        )
        cancelados = sum(
            1 for a in (ags or []) if (a.status or "").lower() == "cancelado"
        )

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            card("Total", f"{total}", "nos filtros", tone="info")
        with k2:
            card(
                "Agendados",
                f"{agendados}",
                "ativos",
                tone="success" if agendados else "neutral",
            )
        with k3:
            card("Realizados", f"{realizados}", "concluídos", tone="neutral")
        with k4:
            card(
                "Cancelados",
                f"{cancelados}",
                "baixados",
                tone="warning" if cancelados else "neutral",
            )

        st.write("")

        if not ags:
            st.info("Nenhum agendamento encontrado com os filtros atuais.")
        else:
            # Mobile-first: cards | Desktop: tabela
            if _is_mobile_hint():
                for a in ags[:50]:
                    _render_agendamento_card(a, proc_maps.label_by_id)
                if len(ags) > 50:
                    st.caption(f"Mostrando 50 de {len(ags)}. Use filtros para reduzir.")
            else:
                df = pd.DataFrame(
                    [
                        {
                            "id": a.id,
                            "trabalho": proc_maps.label_by_id.get(
                                a.processo_id, f"[{a.processo_id}]"
                            ),
                            "status": a.status,
                            "tipo": a.tipo,
                            "início": _format_dt(a.inicio),
                            "fim": _format_dt(a.fim),
                            "local": a.local or "",
                            "descrição": a.descricao or "",
                        }
                        for a in ags
                    ]
                )
                st.dataframe(df, use_container_width=True, hide_index=True, height=420)

    st.write("")

    # =========================================================
    # EDITAR / EXCLUIR (seletor independente)
    # =========================================================
    with st.container(border=True):
        st.markdown("#### ✏️ Editar / 🗑️ Excluir")
        st.caption(
            "Selecione um agendamento e ajuste os campos. O seletor não depende dos filtros acima."
        )

        ags_for_edit = _load_agendamentos_for_edit_picker(owner_user_id, limit=500)
        if not ags_for_edit:
            st.info("Nenhum agendamento cadastrado.")
            return

        edit_labels = [
            _build_agendamento_label(a, proc_maps.label_by_id) for a in ags_for_edit
        ]
        st.session_state.setdefault("ag_edit_selected", edit_labels[0])

        selected_label = st.selectbox(
            "Selecione um agendamento",
            options=edit_labels,
            index=(
                edit_labels.index(st.session_state.ag_edit_selected)
                if st.session_state.ag_edit_selected in edit_labels
                else 0
            ),
            key="ag_edit_picker",
        )
        st.session_state.ag_edit_selected = selected_label
        agendamento_id = _parse_agendamento_id_from_label(selected_label)

        # buscar agendamento
        with get_session() as s:
            a = AgendamentosService.get(s, owner_user_id, int(agendamento_id))
        if not a:
            st.error("Agendamento não encontrado.")
            return

        # Ações rápidas (fora do form)
        st.caption("⚡ Ações rápidas (no agendamento selecionado)")
        cA, cB, cC, cD = st.columns([1, 1, 1, 1.6], vertical_alignment="center")

        if cA.button(
            "✅ Realizado", key="ag_quick_realizado", use_container_width=True
        ):
            try:
                with get_session() as s:
                    AgendamentosService.set_status(
                        s, owner_user_id, int(agendamento_id), "Realizado"
                    )
                st.success("Agendamento marcado como Realizado.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if cB.button("⛔ Cancelar", key="ag_quick_cancelar", use_container_width=True):
            try:
                with get_session() as s:
                    AgendamentosService.set_status(
                        s, owner_user_id, int(agendamento_id), "Cancelado"
                    )
                st.warning("Agendamento cancelado.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if cC.button("🔁 Reativar", key="ag_quick_reativar", use_container_width=True):
            try:
                with get_session() as s:
                    AgendamentosService.set_status(
                        s, owner_user_id, int(agendamento_id), "Agendado"
                    )
                st.success("Agendamento reativado (Agendado).")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        with cD:
            confirm_del = st.checkbox(
                "Confirmar exclusão", value=False, key="ag_del_confirm"
            )
            if st.button(
                "🗑️ Excluir definitivamente",
                key="ag_quick_delete",
                use_container_width=True,
                disabled=not confirm_del,
            ):
                try:
                    with get_session() as s:
                        AgendamentosService.delete(
                            s, owner_user_id, int(agendamento_id)
                        )
                    st.warning("Agendamento excluído.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

        st.divider()

        proc_atual_lbl = proc_maps.label_by_id.get(a.processo_id, proc_maps.labels[0])

        # Form edição (somente salvar aqui)
        with st.form("form_agendamento_edit"):
            c1, c2, c3 = st.columns([3, 1, 1])
            proc_lbl_e = c1.selectbox(
                "Trabalho",
                proc_maps.labels,
                index=(
                    proc_maps.labels.index(proc_atual_lbl)
                    if proc_atual_lbl in proc_maps.labels
                    else 0
                ),
                key="ag_edit_proc",
            )
            tipo_e = c2.selectbox(
                "Tipo",
                TIPOS,
                index=TIPOS.index(a.tipo) if a.tipo in TIPOS else 0,
                key="ag_edit_tipo",
            )
            status_e = c3.selectbox(
                "Status",
                STATUS,
                index=STATUS.index(a.status) if a.status in STATUS else 0,
                key="ag_edit_status",
            )

            c4, c5 = st.columns(2)
            d_ini_e = c4.date_input(
                "Data início", value=a.inicio.date(), key="ag_edit_dini"
            )
            h_ini_e = c5.time_input(
                "Hora início",
                value=a.inicio.time().replace(second=0, microsecond=0),
                key="ag_edit_hini",
            )

            fim_dt = a.fim
            d_fim_default = fim_dt.date() if fim_dt else a.inicio.date()
            h_fim_default = (
                fim_dt.time().replace(second=0, microsecond=0)
                if fim_dt
                else a.inicio.time().replace(second=0, microsecond=0)
            )

            c6, c7 = st.columns(2)
            d_fim_e = c6.date_input("Data fim", value=d_fim_default, key="ag_edit_dfim")
            h_fim_e = c7.time_input("Hora fim", value=h_fim_default, key="ag_edit_hfim")

            local_e = st.text_input("Local", value=a.local or "", key="ag_edit_local")
            desc_e = st.text_area(
                "Descrição", value=a.descricao or "", key="ag_edit_desc"
            )

            atualizar = st.form_submit_button(
                "Salvar alterações", type="primary", use_container_width=True
            )

        if atualizar:
            try:
                processo_id_e = int(proc_maps.label_to_id[proc_lbl_e])
                inicio_e = _combine_date_time(d_ini_e, h_ini_e)
                fim_e = _combine_date_time(d_fim_e, h_fim_e)
                fim_val = _sanitize_end_dt(inicio_e, fim_e)

                with get_session() as s:
                    AgendamentosService.update(
                        s,
                        owner_user_id,
                        int(agendamento_id),
                        AgendamentoUpdate(
                            processo_id=processo_id_e,
                            tipo=tipo_e,
                            status=status_e,
                            inicio=inicio_e,
                            fim=fim_val,
                            local=local_e,
                            descricao=desc_e,
                        ),
                    )

                st.success("Agendamento atualizado.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")
