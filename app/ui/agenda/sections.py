from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from db.connection import get_session
from services.agendamentos_service import (
    AgendamentoCreate,
    AgendamentosService,
    AgendamentoUpdate,
)
from ui.theme import card, subtle_divider
from ui_state import bump_data_version

from .constants import (
    KEY_CREATE_DESC,
    KEY_CREATE_DFIM,
    KEY_CREATE_DINI,
    KEY_CREATE_HFIM,
    KEY_CREATE_HINI,
    KEY_CREATE_LOCAL,
    KEY_CREATE_PROC,
    KEY_CREATE_STATUS,
    KEY_CREATE_TIPO,
    KEY_CREATE_USE_END,
    KEY_DELETE_CONFIRM,
    KEY_EDIT_DESC,
    KEY_EDIT_DFIM,
    KEY_EDIT_DINI,
    KEY_EDIT_HFIM,
    KEY_EDIT_HINI,
    KEY_EDIT_LOCAL,
    KEY_EDIT_PICKER,
    KEY_EDIT_PROC,
    KEY_EDIT_SELECTED,
    KEY_EDIT_STATUS,
    KEY_EDIT_TIPO,
    KEY_EDIT_USE_END,
    KEY_LIST_BUSCA,
    KEY_LIST_FILTRO_PROC,
    KEY_LIST_FILTRO_STATUS,
    KEY_LIST_FILTRO_TIPO,
    KEY_LIST_LIMIT,
    KEY_LIST_ORDER,
    STATUS,
    TIPOS,
)
from .data_access import (
    cached_agendamentos_edit_picker,
    cached_agendamentos_list,
)
from .helpers import (
    ag_data_version,
    build_agendamento_label,
    combine_date_time,
    format_dt,
    is_mobile_hint,
    normalize_optional_str,
    parse_agendamento_id_from_label,
    safe_str,
    sanitize_end_dt,
)


# ==========================================================
# CSS / UI AUXILIAR
# ==========================================================


def inject_agendamento_css() -> None:
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


# ==========================================================
# HELPERS VISUAIS / OPERACIONAIS
# ==========================================================


def _truncate(text: str, limit: int = 80) -> str:
    text = safe_str(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _is_agendado(a) -> bool:
    return safe_str(a.status).lower() == "agendado"


def _is_cancelado(a) -> bool:
    return safe_str(a.status).lower() == "cancelado"


def _is_realizado(a) -> bool:
    return safe_str(a.status).lower() == "realizado"


def _format_day_label(dt) -> str:
    return dt.strftime("%d/%m/%Y")


def _status_label(status: str) -> str:
    s = safe_str(status).lower()
    if s == "agendado":
        return "Agendado"
    if s == "realizado":
        return "Realizado"
    if s == "cancelado":
        return "Cancelado"
    return safe_str(status)


def _tipo_label(tipo: str) -> str:
    return safe_str(tipo).title()


def _periodo_label(a) -> str:
    inicio = format_dt(a.inicio)
    fim = format_dt(a.fim)

    if not a.fim:
        return inicio

    if a.inicio.date() == a.fim.date():
        return f"{a.inicio.strftime('%d/%m/%Y %H:%M')} → {a.fim.strftime('%H:%M')}"
    return f"{inicio} → {fim}"


# ==========================================================
# COMPONENTES VISUAIS
# ==========================================================


def render_agendamento_card(a, proc_label_by_id: dict[int, str]) -> None:
    proc_lbl = proc_label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    local = safe_str(a.local)
    desc = safe_str(a.descricao)

    st.markdown(
        f"""
        <div class="ag-card">
          <div class="ag-title">{proc_lbl}</div>
          <div style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;">
            <span class="ag-chip">📌 {a.tipo}</span>
            <span class="ag-chip">🧾 {a.status}</span>
            <span class="ag-chip">🕒 {format_dt(a.inicio)}</span>
            {f"<span class='ag-chip'>⏱️ {format_dt(a.fim)}</span>" if a.fim else ""}
            {f"<span class='ag-chip'>📍 {local}</span>" if local else ""}
          </div>
          {f"<div style='margin-top:8px;' class='ag-muted'><b>Descrição:</b> {desc}</div>" if desc else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_compact_item(a, proc_maps) -> None:
    proc_lbl = proc_maps.label_by_id.get(a.processo_id, f"[{a.processo_id}]")
    horario = a.inicio.strftime("%H:%M")
    local = safe_str(a.local)

    extra = f" • {local}" if local else ""
    st.markdown(
        f"""
        <div class="ag-card" style="padding:10px 12px; margin-bottom:8px;">
          <div style="font-weight:700;">{horario} • {safe_str(a.tipo).title()}</div>
          <div class="ag-muted">{proc_lbl}{extra}</div>
          {f"<div class='ag-muted' style='margin-top:4px;'>{_truncate(a.descricao, 90)}</div>" if safe_str(a.descricao) else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(ags: list) -> None:
    total = len(ags or [])
    agendados = sum(1 for a in (ags or []) if _is_agendado(a))
    realizados = sum(1 for a in (ags or []) if _is_realizado(a))
    cancelados = sum(1 for a in (ags or []) if _is_cancelado(a))

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


def render_agenda_highlights(ags: list, proc_maps) -> None:
    now = datetime.now()
    today = now.date()
    next_7 = today.fromordinal(today.toordinal() + 7)

    hoje = [a for a in ags if _is_agendado(a) and a.inicio.date() == today]
    proximos_7 = [
        a for a in ags if _is_agendado(a) and today < a.inicio.date() <= next_7
    ]
    vencidos = [a for a in ags if _is_agendado(a) and a.inicio < now]
    cancelados = [a for a in ags if _is_cancelado(a)]

    st.markdown("##### Visão rápida")

    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            st.markdown("**Hoje**")
            if not hoje:
                st.caption("Nenhum compromisso agendado para hoje.")
            else:
                for a in hoje[:4]:
                    _render_compact_item(a, proc_maps)
                if len(hoje) > 4:
                    st.caption(f"+ {len(hoje) - 4} compromisso(s) de hoje.")

    with c2:
        with st.container(border=True):
            st.markdown("**Próximos 7 dias**")
            if not proximos_7:
                st.caption("Nenhum compromisso agendado nos próximos 7 dias.")
            else:
                for a in proximos_7[:4]:
                    dia = _format_day_label(a.inicio)
                    st.markdown(f"**{dia}**")
                    _render_compact_item(a, proc_maps)
                if len(proximos_7) > 4:
                    st.caption(f"+ {len(proximos_7) - 4} compromisso(s) no período.")

    c3, c4 = st.columns(2)

    with c3:
        with st.container(border=True):
            st.markdown("**Vencidos**")
            if not vencidos:
                st.caption("Nenhum compromisso vencido em aberto.")
            else:
                for a in vencidos[:4]:
                    _render_compact_item(a, proc_maps)
                if len(vencidos) > 4:
                    st.caption(f"+ {len(vencidos) - 4} compromisso(s) vencido(s).")

    with c4:
        with st.container(border=True):
            st.markdown("**Cancelados**")
            if not cancelados:
                st.caption("Nenhum compromisso cancelado nos filtros atuais.")
            else:
                for a in cancelados[:4]:
                    _render_compact_item(a, proc_maps)
                if len(cancelados) > 4:
                    st.caption(f"+ {len(cancelados) - 4} compromisso(s) cancelado(s).")


def render_desktop_table(ags: list, proc_maps) -> None:
    rows = []
    for a in ags:
        rows.append(
            {
                "ID": a.id,
                "Trabalho": proc_maps.label_by_id.get(
                    a.processo_id, f"[{a.processo_id}]"
                ),
                "Status": _status_label(a.status),
                "Tipo": _tipo_label(a.tipo),
                "Período": _periodo_label(a),
                "Local": _truncate(a.local or "", 40),
                "Descrição": _truncate(a.descricao or "", 80),
            }
        )

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=440,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Trabalho": st.column_config.TextColumn("Trabalho", width="large"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
            "Período": st.column_config.TextColumn("Período", width="medium"),
            "Local": st.column_config.TextColumn("Local", width="medium"),
            "Descrição": st.column_config.TextColumn("Descrição", width="large"),
        },
    )


def render_mobile_cards(ags: list, proc_maps) -> None:
    for a in ags[:50]:
        render_agendamento_card(a, proc_maps.label_by_id)

    if len(ags) > 50:
        st.caption(f"Mostrando 50 de {len(ags)}. Use filtros para reduzir.")


# ==========================================================
# BLOCOS
# ==========================================================


def render_create_block(owner_user_id: int, proc_maps) -> None:
    with st.container(border=True):
        st.markdown("#### ➕ Novo compromisso")
        st.caption("Cadastre rapidamente um compromisso vinculado a um trabalho.")
        subtle_divider()

        with st.form("form_agendamento_create", clear_on_submit=True):

            # Linha 1
            c1, c2, c3 = st.columns([3, 1.5, 1.5])
            proc_lbl = c1.selectbox(
                "Trabalho *",
                proc_maps.labels,
                key=KEY_CREATE_PROC,
            )
            tipo = c2.selectbox(
                "Tipo *",
                TIPOS,
                key=KEY_CREATE_TIPO,
            )
            status = c3.selectbox(
                "Status",
                STATUS,
                index=0,
                key=KEY_CREATE_STATUS,
            )

            # Linha 2 - início
            c4, c5 = st.columns(2)
            d_ini = c4.date_input(
                "Data",
                value=date.today(),
                key=KEY_CREATE_DINI,
            )
            h_ini = c5.time_input(
                "Hora",
                value=datetime.now().replace(second=0, microsecond=0).time(),
                key=KEY_CREATE_HINI,
            )

            # Sugestão automática de fim (+1h)
            inicio_temp = combine_date_time(d_ini, h_ini)
            fim_sugerido = inicio_temp.replace(hour=min(inicio_temp.hour + 1, 23))

            use_end = st.checkbox(
                "Definir horário de término",
                value=False,
                key=KEY_CREATE_USE_END,
            )

            # Linha 3 - fim
            c6, c7 = st.columns(2)
            d_fim = c6.date_input(
                "Data fim",
                value=d_ini,
                key=KEY_CREATE_DFIM,
                disabled=not use_end,
            )
            h_fim = c7.time_input(
                "Hora fim",
                value=fim_sugerido.time(),
                key=KEY_CREATE_HFIM,
                disabled=not use_end,
            )

            # Linha 4
            local = st.text_input(
                "Local (opcional)",
                key=KEY_CREATE_LOCAL,
                placeholder="Ex: Fórum, Cliente, Online...",
            )

            descricao = st.text_area(
                "Descrição (opcional)",
                key=KEY_CREATE_DESC,
                placeholder="Detalhes do compromisso...",
                height=80,
            )

            # Botão
            submitted = st.form_submit_button(
                "Salvar compromisso",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            try:
                processo_id = int(proc_maps.label_to_id[proc_lbl])
                inicio = combine_date_time(d_ini, h_ini)
                fim_val = sanitize_end_dt(inicio, use_end, d_fim, h_fim)

                with get_session() as s:
                    AgendamentosService.create(
                        s,
                        owner_user_id=owner_user_id,
                        payload=AgendamentoCreate(
                            processo_id=processo_id,
                            tipo=tipo,
                            inicio=inicio,
                            fim=fim_val,
                            local=normalize_optional_str(local),
                            descricao=normalize_optional_str(descricao),
                            status=status,
                        ),
                    )

                bump_data_version(owner_user_id)
                st.success("Compromisso criado com sucesso.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao criar compromisso: {e}")


def render_list_block(owner_user_id: int, proc_maps) -> None:
    with st.container(border=True):
        st.markdown("#### 🗓️ Agenda")
        st.caption("Visualize, filtre e acompanhe os compromissos.")
        subtle_divider()

        if is_mobile_hint():
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
                "Buscar por local ou descrição",
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
                "Buscar por local ou descrição",
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
        q_val = normalize_optional_str(filtro_q)

        version = ag_data_version(owner_user_id)
        ags = cached_agendamentos_list(
            owner_user_id,
            version,
            processo_id,
            tipo_val,
            status_val,
            q_val,
            order_val,
            int(filtro_limit),
        )

        render_kpis(ags)
        st.write("")

        if not ags:
            st.info("Nenhum compromisso encontrado com os filtros atuais.")
            return

        render_agenda_highlights(ags, proc_maps)
        st.write("")

        if is_mobile_hint():
            render_mobile_cards(ags, proc_maps)
        else:
            render_desktop_table(ags, proc_maps)


def render_edit_block(owner_user_id: int, proc_maps) -> None:
    with st.container(border=True):
        st.markdown("#### ⚙️ Gerenciar compromisso")
        st.caption("Edite dados, altere status ou exclua o compromisso selecionado.")
        subtle_divider()

        version = ag_data_version(owner_user_id)
        ags_for_edit = cached_agendamentos_edit_picker(
            owner_user_id,
            version,
            limit=500,
        )

        if not ags_for_edit:
            st.info("Nenhum compromisso cadastrado.")
            return

        edit_labels = [
            build_agendamento_label(a, proc_maps.label_by_id) for a in ags_for_edit
        ]

        st.session_state.setdefault(KEY_EDIT_SELECTED, edit_labels[0])

        selected_label = st.selectbox(
            "Selecione um compromisso",
            options=edit_labels,
            index=(
                edit_labels.index(st.session_state[KEY_EDIT_SELECTED])
                if st.session_state.get(KEY_EDIT_SELECTED) in edit_labels
                else 0
            ),
            key=KEY_EDIT_PICKER,
        )

        st.session_state[KEY_EDIT_SELECTED] = selected_label
        agendamento_id = parse_agendamento_id_from_label(selected_label)

        with get_session() as s:
            a = AgendamentosService.get(s, owner_user_id, int(agendamento_id))

        if not a:
            st.error("Compromisso não encontrado.")
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
                st.success("Compromisso marcado como Realizado.")
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
                st.warning("Compromisso cancelado.")
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
                st.success("Compromisso reativado.")
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
                            s,
                            owner_user_id,
                            int(agendamento_id),
                        )
                    bump_data_version(owner_user_id)
                    st.warning("Compromisso excluído.")
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
                inicio_e = combine_date_time(d_ini_e, h_ini_e)
                fim_val = sanitize_end_dt(inicio_e, use_end_e, d_fim_e, h_fim_e)

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
                            local=normalize_optional_str(local_e),
                            descricao=normalize_optional_str(desc_e),
                        ),
                    )

                bump_data_version(owner_user_id)
                st.success("Compromisso atualizado.")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")
