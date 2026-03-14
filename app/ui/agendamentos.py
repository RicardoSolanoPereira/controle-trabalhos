from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.agendamentos_service import (
    STATUS_VALIDOS,
    TIPOS_VALIDOS,
    AgendamentoCreate,
    AgendamentosService,
    AgendamentoUpdate,
)
from ui.page_header import page_header
from ui.theme import card, inject_global_css, subtle_divider
from ui_state import bump_data_version, get_data_version


# ==========================================================
# CONSTANTES
# ==========================================================

KEY_MOBILE_MODE = "ui_mobile_mode"

KEY_CREATE_PROC = "ag_create_proc"
KEY_CREATE_TIPO = "ag_create_tipo"
KEY_CREATE_STATUS = "ag_create_status"
KEY_CREATE_DINI = "ag_create_dini"
KEY_CREATE_HINI = "ag_create_hini"
KEY_CREATE_USE_END = "ag_create_use_end"
KEY_CREATE_DFIM = "ag_create_dfim"
KEY_CREATE_HFIM = "ag_create_hfim"
KEY_CREATE_LOCAL = "ag_create_local"
KEY_CREATE_DESC = "ag_create_desc"

KEY_LIST_FILTRO_PROC = "ag_list_filtro_proc"
KEY_LIST_FILTRO_TIPO = "ag_list_filtro_tipo"
KEY_LIST_FILTRO_STATUS = "ag_list_filtro_status"
KEY_LIST_LIMIT = "ag_list_limit"
KEY_LIST_ORDER = "ag_list_order"
KEY_LIST_BUSCA = "ag_list_busca"

KEY_EDIT_SELECTED = "ag_edit_selected"
KEY_EDIT_PICKER = "ag_edit_picker"
KEY_EDIT_PROC = "ag_edit_proc"
KEY_EDIT_TIPO = "ag_edit_tipo"
KEY_EDIT_STATUS = "ag_edit_status"
KEY_EDIT_DINI = "ag_edit_dini"
KEY_EDIT_HINI = "ag_edit_hini"
KEY_EDIT_USE_END = "ag_edit_use_end"
KEY_EDIT_DFIM = "ag_edit_dfim"
KEY_EDIT_HFIM = "ag_edit_hfim"
KEY_EDIT_LOCAL = "ag_edit_local"
KEY_EDIT_DESC = "ag_edit_desc"

KEY_DELETE_CONFIRM = "ag_del_confirm"

TIPOS = list(TIPOS_VALIDOS)
STATUS = list(STATUS_VALIDOS)


# ==========================================================
# DTO AUXILIAR
# ==========================================================


@dataclass(frozen=True)
class ProcMaps:
    labels: List[str]
    label_to_id: Dict[str, int]
    label_by_id: Dict[int, str]


# ==========================================================
# HELPERS BÁSICOS
# ==========================================================


def _is_mobile_hint() -> bool:
    return bool(st.session_state.get(KEY_MOBILE_MODE, False))


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_optional_str(value: str | None) -> str | None:
    text = _safe_str(value)
    return text or None


def _format_dt(dt: Optional[datetime]) -> str:
    return dt.strftime("%d/%m/%Y %H:%M") if dt else ""


def _combine_date_time(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, 0)


def _sanitize_end_dt(
    inicio: datetime,
    use_end: bool,
    d_fim: date,
    h_fim: time,
) -> Optional[datetime]:
    if not use_end:
        return None

    fim = _combine_date_time(d_fim, h_fim)

    if fim == inicio:
        return None
    if fim < inicio:
        raise ValueError("A data/hora de fim não pode ser anterior ao início.")

    return fim


def _ag_data_version(owner_user_id: int) -> int:
    return get_data_version(owner_user_id)


def _proc_label(p: Processo) -> str:
    tipo = _safe_str(getattr(p, "tipo_acao", None))
    papel = _safe_str(getattr(p, "papel", None))
    numero = _safe_str(getattr(p, "numero_processo", None))

    base = f"[{p.id}] {numero}"
    if tipo:
        base += f" – {tipo}"
    if papel:
        base += f"  •  {papel}"
    return base


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


def _build_agendamento_label(a, proc_label_by_id: Dict[int, str]) -> str:
    proc_lbl = proc_label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    return f"[#{a.id}] {_format_dt(a.inicio)} — {a.tipo} — {a.status} — {proc_lbl}"


def _parse_agendamento_id_from_label(label: str) -> int:
    head = label.split("]")[0]
    return int(head.replace("[#", "").strip())


def _apply_pref_processo_defaults(proc_maps: ProcMaps) -> None:
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

    st.session_state.setdefault(KEY_CREATE_PROC, pref_label)
    st.session_state.setdefault(KEY_LIST_FILTRO_PROC, pref_label)


# ==========================================================
# CSS / UI AUXILIAR
# ==========================================================


def _inject_agendamento_css() -> None:
    st.markdown(
        """
        <style>
        .ag-chip{
            display:inline-block;
            padding:6px 10px;
            border-radius:999px;
            background:rgba(17,25,40,0.06);
            font-size:12px;
            font-weight:600;
            margin-right:6px;
            margin-bottom:6px;
        }
        .ag-card{
            border:1px solid rgba(49,51,63,0.12);
            border-radius:14px;
            padding:14px 16px;
            margin-bottom:10px;
            background:#fff;
        }
        .ag-title{
            font-weight:850;
            font-size:0.98rem;
        }
        .ag-muted{
            color: rgba(15,23,42,0.72);
            font-size: 0.92rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_agendamento_card(a, proc_label_by_id: Dict[int, str]) -> None:
    proc_lbl = proc_label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    local = _safe_str(a.local)
    desc = _safe_str(a.descricao)

    st.markdown(
        f"""
        <div class="ag-card">
          <div class="ag-title">{proc_lbl}</div>
          <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
            <span class="ag-chip">📌 {a.tipo}</span>
            <span class="ag-chip">🧾 {a.status}</span>
            <span class="ag-chip">🕒 {_format_dt(a.inicio)}</span>
            {f"<span class='ag-chip'>⏱️ {_format_dt(a.fim)}</span>" if a.fim else ""}
            {f"<span class='ag-chip'>📍 {local}</span>" if local else ""}
          </div>
          {f"<div style='margin-top:8px;' class='ag-muted'><b>Descrição:</b> {desc}</div>" if desc else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# LEITURA / CACHE
# ==========================================================


@st.cache_data(show_spinner=False, ttl=45)
def _cached_processos(owner_user_id: int, version: int) -> list[Processo]:
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
def _cached_agendamentos_list(
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
def _cached_agendamentos_edit_picker(
    owner_user_id: int, version: int, limit: int = 500
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


# ==========================================================
# KPI / TABELA
# ==========================================================


def _render_kpis(ags: list) -> None:
    total = len(ags or [])
    agendados = sum(1 for a in (ags or []) if _safe_str(a.status).lower() == "agendado")
    realizados = sum(
        1 for a in (ags or []) if _safe_str(a.status).lower() == "realizado"
    )
    cancelados = sum(
        1 for a in (ags or []) if _safe_str(a.status).lower() == "cancelado"
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


def _render_desktop_table(ags: list, proc_maps: ProcMaps) -> None:
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


def _render_mobile_cards(ags: list, proc_maps: ProcMaps) -> None:
    for a in ags[:50]:
        _render_agendamento_card(a, proc_maps.label_by_id)

    if len(ags) > 50:
        st.caption(f"Mostrando 50 de {len(ags)}. Use filtros para reduzir.")


# ==========================================================
# BLOCOS
# ==========================================================


def _render_create_block(owner_user_id: int, proc_maps: ProcMaps) -> None:
    with st.container(border=True):
        st.markdown("#### ➕ Novo agendamento")
        st.caption("Crie um compromisso vinculado a um trabalho.")
        subtle_divider()

        with st.form("form_agendamento_create", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            proc_lbl = c1.selectbox("Trabalho *", proc_maps.labels, key=KEY_CREATE_PROC)
            tipo = c2.selectbox("Tipo *", TIPOS, key=KEY_CREATE_TIPO)
            status = c3.selectbox("Status *", STATUS, index=0, key=KEY_CREATE_STATUS)

            c4, c5 = st.columns(2)
            d_ini = c4.date_input(
                "Data início *", value=date.today(), key=KEY_CREATE_DINI
            )
            h_ini = c5.time_input(
                "Hora início *",
                value=datetime.now().replace(second=0, microsecond=0).time(),
                key=KEY_CREATE_HINI,
            )

            use_end = st.checkbox(
                "Informar data/hora de fim",
                value=False,
                key=KEY_CREATE_USE_END,
            )

            c6, c7 = st.columns(2)
            d_fim = c6.date_input(
                "Data fim",
                value=d_ini,
                key=KEY_CREATE_DFIM,
                disabled=not use_end,
            )
            h_fim = c7.time_input(
                "Hora fim",
                value=datetime.now().replace(second=0, microsecond=0).time(),
                key=KEY_CREATE_HFIM,
                disabled=not use_end,
            )

            local = st.text_input("Local", key=KEY_CREATE_LOCAL)
            descricao = st.text_area("Descrição", key=KEY_CREATE_DESC)

            submitted = st.form_submit_button(
                "Salvar agendamento",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            try:
                processo_id = int(proc_maps.label_to_id[proc_lbl])
                inicio = _combine_date_time(d_ini, h_ini)
                fim_val = _sanitize_end_dt(inicio, use_end, d_fim, h_fim)

                with get_session() as s:
                    AgendamentosService.create(
                        s,
                        owner_user_id=owner_user_id,
                        payload=AgendamentoCreate(
                            processo_id=processo_id,
                            tipo=tipo,
                            inicio=inicio,
                            fim=fim_val,
                            local=_normalize_optional_str(local),
                            descricao=_normalize_optional_str(descricao),
                            status=status,
                        ),
                    )

                bump_data_version(owner_user_id)
                st.success("Agendamento criado.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao criar agendamento: {e}")


def _render_list_block(owner_user_id: int, proc_maps: ProcMaps) -> None:
    with st.container(border=True):
        st.markdown("#### 📋 Lista")
        st.caption("Filtre e visualize rapidamente.")
        subtle_divider()

        if _is_mobile_hint():
            filtro_proc = st.selectbox(
                "Trabalho",
                ["(Todos)"] + proc_maps.labels,
                index=0,
                key=KEY_LIST_FILTRO_PROC,
            )
            filtro_tipo = st.selectbox(
                "Tipo",
                ["(Todos)"] + TIPOS,
                index=0,
                key=KEY_LIST_FILTRO_TIPO,
            )
            filtro_status = st.selectbox(
                "Status",
                ["(Todos)"] + STATUS,
                index=0,
                key=KEY_LIST_FILTRO_STATUS,
            )
            filtro_limit = st.selectbox(
                "Limite",
                [100, 200, 300, 500],
                index=1,
                key=KEY_LIST_LIMIT,
            )

            order = st.radio(
                "Ordem",
                ["Próximos", "Recentes"],
                horizontal=True,
                key=KEY_LIST_ORDER,
            )
            filtro_q = st.text_input(
                "Buscar (local/descrição)",
                value="",
                key=KEY_LIST_BUSCA,
            )
        else:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            filtro_proc = c1.selectbox(
                "Trabalho",
                ["(Todos)"] + proc_maps.labels,
                index=0,
                key=KEY_LIST_FILTRO_PROC,
            )
            filtro_tipo = c2.selectbox(
                "Tipo",
                ["(Todos)"] + TIPOS,
                index=0,
                key=KEY_LIST_FILTRO_TIPO,
            )
            filtro_status = c3.selectbox(
                "Status",
                ["(Todos)"] + STATUS,
                index=0,
                key=KEY_LIST_FILTRO_STATUS,
            )
            filtro_limit = c4.selectbox(
                "Limite",
                [100, 200, 300, 500],
                index=1,
                key=KEY_LIST_LIMIT,
            )

            c5, c6 = st.columns([1, 3])
            order = c5.radio(
                "Ordem",
                ["Próximos", "Recentes"],
                horizontal=True,
                key=KEY_LIST_ORDER,
            )
            filtro_q = c6.text_input(
                "Buscar (local/descrição)",
                value="",
                key=KEY_LIST_BUSCA,
            )

        order_val = "asc" if order == "Próximos" else "desc"
        processo_id = (
            None
            if filtro_proc == "(Todos)"
            else int(proc_maps.label_to_id[filtro_proc])
        )
        tipo_val = None if filtro_tipo == "(Todos)" else filtro_tipo
        status_val = None if filtro_status == "(Todos)" else filtro_status
        q_val = _normalize_optional_str(filtro_q)

        version = _ag_data_version(owner_user_id)
        ags = _cached_agendamentos_list(
            owner_user_id,
            version,
            processo_id,
            tipo_val,
            status_val,
            q_val,
            order_val,
            int(filtro_limit),
        )

        _render_kpis(ags)
        st.write("")

        if not ags:
            st.info("Nenhum agendamento encontrado com os filtros atuais.")
            return

        if _is_mobile_hint():
            _render_mobile_cards(ags, proc_maps)
        else:
            _render_desktop_table(ags, proc_maps)


def _render_edit_block(owner_user_id: int, proc_maps: ProcMaps) -> None:
    with st.container(border=True):
        st.markdown("#### ✏️ Editar / 🗑️ Excluir")
        st.caption("Selecione um agendamento e ajuste os campos necessários.")
        subtle_divider()

        version = _ag_data_version(owner_user_id)
        ags_for_edit = _cached_agendamentos_edit_picker(
            owner_user_id, version, limit=500
        )

        if not ags_for_edit:
            st.info("Nenhum agendamento cadastrado.")
            return

        edit_labels = [
            _build_agendamento_label(a, proc_maps.label_by_id) for a in ags_for_edit
        ]

        st.session_state.setdefault(KEY_EDIT_SELECTED, edit_labels[0])

        selected_label = st.selectbox(
            "Selecione um agendamento",
            options=edit_labels,
            index=(
                edit_labels.index(st.session_state[KEY_EDIT_SELECTED])
                if st.session_state.get(KEY_EDIT_SELECTED) in edit_labels
                else 0
            ),
            key=KEY_EDIT_PICKER,
        )

        st.session_state[KEY_EDIT_SELECTED] = selected_label
        agendamento_id = _parse_agendamento_id_from_label(selected_label)

        with get_session() as s:
            a = AgendamentosService.get(s, owner_user_id, int(agendamento_id))

        if not a:
            st.error("Agendamento não encontrado.")
            return

        st.caption("⚡ Ações rápidas")
        cA, cB, cC, cD = st.columns([1, 1, 1, 1.7], vertical_alignment="center")

        if cA.button(
            "✅ Realizado", key="ag_quick_realizado", use_container_width=True
        ):
            try:
                with get_session() as s:
                    AgendamentosService.set_status(
                        s,
                        owner_user_id,
                        int(agendamento_id),
                        "Realizado",
                    )
                bump_data_version(owner_user_id)
                st.success("Agendamento marcado como Realizado.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if cB.button("⛔ Cancelar", key="ag_quick_cancelar", use_container_width=True):
            try:
                with get_session() as s:
                    AgendamentosService.set_status(
                        s,
                        owner_user_id,
                        int(agendamento_id),
                        "Cancelado",
                    )
                bump_data_version(owner_user_id)
                st.warning("Agendamento cancelado.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if cC.button("🔁 Reativar", key="ag_quick_reativar", use_container_width=True):
            try:
                with get_session() as s:
                    AgendamentosService.set_status(
                        s,
                        owner_user_id,
                        int(agendamento_id),
                        "Agendado",
                    )
                bump_data_version(owner_user_id)
                st.success("Agendamento reativado.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        with cD:
            confirm_del = st.checkbox(
                "Confirmar exclusão",
                value=False,
                key=KEY_DELETE_CONFIRM,
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
                    bump_data_version(owner_user_id)
                    st.warning("Agendamento excluído.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

        st.divider()

        proc_atual_lbl = proc_maps.label_by_id.get(a.processo_id, proc_maps.labels[0])

        fim_dt = a.fim
        inicio_dt = a.inicio
        use_end_default = fim_dt is not None
        d_fim_default = fim_dt.date() if fim_dt else inicio_dt.date()
        h_fim_default = (
            fim_dt.time().replace(second=0, microsecond=0)
            if fim_dt
            else inicio_dt.time().replace(second=0, microsecond=0)
        )

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
                key=KEY_EDIT_PROC,
            )
            tipo_e = c2.selectbox(
                "Tipo",
                TIPOS,
                index=TIPOS.index(a.tipo) if a.tipo in TIPOS else 0,
                key=KEY_EDIT_TIPO,
            )
            status_e = c3.selectbox(
                "Status",
                STATUS,
                index=STATUS.index(a.status) if a.status in STATUS else 0,
                key=KEY_EDIT_STATUS,
            )

            c4, c5 = st.columns(2)
            d_ini_e = c4.date_input(
                "Data início",
                value=inicio_dt.date(),
                key=KEY_EDIT_DINI,
            )
            h_ini_e = c5.time_input(
                "Hora início",
                value=inicio_dt.time().replace(second=0, microsecond=0),
                key=KEY_EDIT_HINI,
            )

            use_end_e = st.checkbox(
                "Informar data/hora de fim",
                value=use_end_default,
                key=KEY_EDIT_USE_END,
            )

            c6, c7 = st.columns(2)
            d_fim_e = c6.date_input(
                "Data fim",
                value=d_fim_default,
                key=KEY_EDIT_DFIM,
                disabled=not use_end_e,
            )
            h_fim_e = c7.time_input(
                "Hora fim",
                value=h_fim_default,
                key=KEY_EDIT_HFIM,
                disabled=not use_end_e,
            )

            local_e = st.text_input("Local", value=a.local or "", key=KEY_EDIT_LOCAL)
            desc_e = st.text_area(
                "Descrição", value=a.descricao or "", key=KEY_EDIT_DESC
            )

            atualizar = st.form_submit_button(
                "Salvar alterações",
                type="primary",
                use_container_width=True,
            )

        if atualizar:
            try:
                processo_id_e = int(proc_maps.label_to_id[proc_lbl_e])
                inicio_e = _combine_date_time(d_ini_e, h_ini_e)
                fim_val = _sanitize_end_dt(inicio_e, use_end_e, d_fim_e, h_fim_e)

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
                            local=_normalize_optional_str(local_e),
                            descricao=_normalize_optional_str(desc_e),
                        ),
                    )

                bump_data_version(owner_user_id)
                st.success("Agendamento atualizado.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")


# ==========================================================
# RENDER PRINCIPAL
# ==========================================================


def render(owner_user_id: int) -> None:
    inject_global_css()
    _inject_agendamento_css()

    clicked_refresh = page_header(
        "Agendamentos",
        "Cadastro, filtros e controle de compromissos.",
        right_button_label="Recarregar",
        right_button_key="ag_btn_recarregar",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked_refresh:
        st.rerun()

    with st.sidebar.expander("📱 Ajustes (UI)", expanded=False):
        st.checkbox("Modo mobile (cards)", value=False, key=KEY_MOBILE_MODE)

    version = _ag_data_version(owner_user_id)
    processos = _cached_processos(owner_user_id, version)

    if not processos:
        st.info("Cadastre um trabalho primeiro para criar agendamentos.")
        return

    proc_maps = _build_proc_maps(processos)
    _apply_pref_processo_defaults(proc_maps)

    _render_create_block(owner_user_id, proc_maps)
    st.write("")
    _render_list_block(owner_user_id, proc_maps)
    st.write("")
    _render_edit_block(owner_user_id, proc_maps)
