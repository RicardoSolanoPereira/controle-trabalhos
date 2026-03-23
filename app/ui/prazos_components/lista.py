from __future__ import annotations

from datetime import timedelta

import streamlit as st

from db.connection import get_session
from services.prazos_service import PrazoUpdate, PrazosService
from services.utils import date_to_br_datetime, ensure_br, format_date_br
from ui.theme import card, subtle_divider
from ui_state import bump_data_version
from ui.prazos_components.cache import cached_prazos_list_all
from ui.prazos_components.constants import (
    KEY_FILTER_BUSCA,
    KEY_FILTER_ORIGEM,
    KEY_FILTER_PRIO,
    KEY_FILTER_PROC,
    KEY_FILTER_TIPO,
    KEY_OPEN_ORDER,
    KEY_OPEN_WINDOW,
    KEY_QUICK_CONFIRM_DELETE,
    KEY_QUICK_DELAY_DAYS,
    KEY_QUICK_SELECT,
    ORIGENS,
    PRIORIDADES,
    TIPOS_TRABALHO,
)
from ui.prazos_components.helpers import (
    apply_lista_filters,
    build_df,
    dias_restantes,
    dicts_to_dataclass,
    prazo_option_label,
    priority_rank,
    sort_operational,
    split_status_groups,
    status_label,
)
from ui.components.sections import section_card
from ui.prazos_components.sections import (
    list_tabs_selector,
    render_df,
    render_priority_queue,
    render_summary_kpis,
)

from ui.prazos_components.state import apply_requested_list_tab, request_tab


def render_filtros_lista(proc_labels: list[str]) -> tuple[str, str, str, str, str]:
    with st.container(border=True):
        section_card(
            "Filtros operacionais", "Use apenas quando precisar refinar a leitura."
        )
        subtle_divider()

        f1, f2, f3, f4 = st.columns(4)
        filtro_tipo = f1.selectbox(
            "Tipo",
            ["(Todos)"] + list(TIPOS_TRABALHO),
            index=0,
            key=KEY_FILTER_TIPO,
        )
        filtro_proc = f2.selectbox(
            "Trabalho",
            ["(Todos)"] + proc_labels,
            index=0,
            key=KEY_FILTER_PROC,
        )
        filtro_prio = f3.selectbox(
            "Prioridade",
            ["(Todas)"] + list(PRIORIDADES),
            index=0,
            key=KEY_FILTER_PRIO,
        )
        filtro_origem = f4.selectbox(
            "Origem",
            ["(Todas)"] + [o for o in ORIGENS if o],
            index=0,
            key=KEY_FILTER_ORIGEM,
        )

        busca = (
            st.text_input(
                "Buscar",
                placeholder="processo, evento, origem, referência, observações…",
                key=KEY_FILTER_BUSCA,
            )
            .strip()
            .lower()
        )

    return filtro_tipo, filtro_proc, filtro_prio, filtro_origem, busca


def render_open_controls() -> tuple[str, str]:
    with st.container(border=True):
        c1, c2 = st.columns([2, 4])
        filtro_janela = c1.selectbox(
            "Janela",
            ["Todos", "Atrasados", "Hoje", "0–7 dias", "0–15 dias", "0–30 dias"],
            index=0,
            key=KEY_OPEN_WINDOW,
        )
        ordem = c2.selectbox(
            "Ordenar",
            ["Mais urgentes primeiro", "Mais distantes primeiro"],
            index=0,
            key=KEY_OPEN_ORDER,
        )
    return filtro_janela, ordem


def filter_open_window(rows, janela: str):
    items = []
    for row in rows:
        if row.concluido:
            continue
        dias = dias_restantes(row.data_limite)

        if janela == "Atrasados" and not (dias < 0):
            continue
        if janela == "Hoje" and dias != 0:
            continue
        if janela == "0–7 dias" and not (0 <= dias <= 7):
            continue
        if janela == "0–15 dias" and not (0 <= dias <= 15):
            continue
        if janela == "0–30 dias" and not (0 <= dias <= 30):
            continue

        items.append(row)
    return items


def render_lista_topbar() -> None:
    c1, c2 = st.columns([0.72, 0.28])

    with c1:
        st.markdown("#### Operação de prazos")
        st.caption(
            "Comece pelos itens mais críticos e depois refine a fila com os filtros."
        )

    with c2:
        if st.button(
            "➕ Novo prazo",
            key="pz_go_create_top",
            use_container_width=True,
            type="primary",
        ):
            request_tab("Cadastrar")
            st.rerun()


def quick_actions(filtered_items, owner_user_id: int) -> None:
    if not filtered_items:
        st.info("Nenhum prazo com os filtros atuais.")
        return

    options: list[str] = []
    id_by_label: dict[str, int] = {}

    ordered = sorted(
        filtered_items,
        key=lambda r: (
            r.concluido,
            dias_restantes(r.data_limite),
            priority_rank(r.prioridade),
            ensure_br(r.data_limite),
        ),
    )

    for row in ordered:
        label = prazo_option_label(row)
        options.append(label)
        id_by_label[label] = int(row.prazo_id)

    st.caption("Ações aplicadas ao prazo selecionado.")

    selected = st.selectbox("Selecione um prazo", options, key=KEY_QUICK_SELECT)
    prazo_id = id_by_label[selected]

    selected_row = next((r for r in ordered if int(r.prazo_id) == int(prazo_id)), None)
    if not selected_row:
        st.info("Prazo não encontrado.")
        return

    dias = dias_restantes(selected_row.data_limite)
    status_txt = status_label(dias, selected_row.concluido)

    meta_cols = st.columns(4)
    with meta_cols[0]:
        card("Status", status_txt, "situação atual", tone="neutral")
    with meta_cols[1]:
        card(
            "Data",
            format_date_br(selected_row.data_limite),
            "vencimento",
            tone="neutral",
        )
    with meta_cols[2]:
        card("Prioridade", selected_row.prioridade, "nível operacional", tone="neutral")
    with meta_cols[3]:
        if dias < 0:
            sub = f"{abs(dias)} dia(s) em atraso"
            tone = "danger"
        elif dias == 0:
            sub = "vence hoje"
            tone = "warning"
        else:
            sub = f"{dias} dia(s) restantes"
            tone = "info"
        card("Prazo", sub, "janela temporal", tone=tone)

    c1, c2, c3 = st.columns(3)

    if c1.button("✅ Concluir", key="pz_quick_done", use_container_width=True):
        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(concluido=True),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo concluído.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao concluir: {e}")

    if c2.button("♻️ Reabrir", key="pz_quick_reopen", use_container_width=True):
        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(concluido=False),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo reaberto.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao reabrir: {e}")

    with c3:
        st.number_input(
            "Adiar (dias)",
            min_value=1,
            max_value=365,
            step=1,
            key=KEY_QUICK_DELAY_DAYS,
        )
        if st.button("↪️ Adiar", key="pz_quick_delay", use_container_width=True):
            try:
                add_days = int(st.session_state.get(KEY_QUICK_DELAY_DAYS, 1) or 1)
                nova_data = ensure_br(selected_row.data_limite).date() + timedelta(
                    days=add_days
                )

                with get_session() as s:
                    PrazosService.update(
                        s,
                        owner_user_id,
                        int(prazo_id),
                        PrazoUpdate(data_limite=date_to_br_datetime(nova_data)),
                    )
                bump_data_version(owner_user_id)
                st.success("Prazo reagendado.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao reagendar: {e}")

    with st.expander("Zona sensível", expanded=False):
        st.caption("Exclusão definitiva do prazo selecionado.")
        confirm = st.checkbox("Confirmo a exclusão", key=KEY_QUICK_CONFIRM_DELETE)
        if st.button(
            "🗑️ Excluir prazo",
            key="pz_quick_del",
            use_container_width=True,
            disabled=not confirm,
        ):
            try:
                with get_session() as s:
                    PrazosService.delete(s, owner_user_id, int(prazo_id))
                bump_data_version(owner_user_id)
                st.warning("Prazo excluído.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


def render_lista(
    *,
    owner_user_id: int,
    proc_labels: list[str],
    label_to_id: dict[str, int],
    version: int,
) -> None:
    apply_requested_list_tab()

    all_rows = dicts_to_dataclass(cached_prazos_list_all(owner_user_id, version))

    filtered_base = apply_lista_filters(
        all_rows,
        tipo_val=None,
        processo_id_val=None,
        prioridade_val=None,
        origem_val=None,
        busca="",
    )

    abertos_base, hoje_base, atrasados_base, vencem7_base, concluidos_base = (
        split_status_groups(filtered_base)
    )

    render_lista_topbar()

    render_summary_kpis(
        abertos=len(abertos_base),
        hoje=len(hoje_base),
        atrasados=len(atrasados_base),
        vencem7=len(vencem7_base),
        concluidos=len(concluidos_base),
    )

    with st.container(border=True):
        render_priority_queue(filtered_base)

    filtro_tipo, filtro_proc, filtro_prio, filtro_origem, busca = render_filtros_lista(
        proc_labels
    )

    tipo_val = None if filtro_tipo == "(Todos)" else filtro_tipo
    processo_id_val = (
        None if filtro_proc == "(Todos)" else int(label_to_id[filtro_proc])
    )
    prioridade_val = None if filtro_prio == "(Todas)" else filtro_prio
    origem_val = None if filtro_origem == "(Todas)" else filtro_origem

    filtered = apply_lista_filters(
        all_rows,
        tipo_val=tipo_val,
        processo_id_val=processo_id_val,
        prioridade_val=prioridade_val,
        origem_val=origem_val,
        busca=busca,
    )

    abertos, hoje, atrasados, vencem7, concluidos = split_status_groups(filtered)

    with st.container(border=True):
        section_card(
            "⚡ Ações rápidas", "Resolva operações frequentes sem sair da fila."
        )
        quick_actions(filtered, owner_user_id)

    subtle_divider()
    chosen_view = list_tabs_selector()

    if chosen_view == "Atrasados":
        items = sorted(
            atrasados,
            key=lambda r: (
                dias_restantes(r.data_limite),
                priority_rank(r.prioridade),
                ensure_br(r.data_limite),
            ),
        )
        df = build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo atrasado com os filtros atuais.")
            return

        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[True, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=380,
        )
        return

    if chosen_view == "Hoje":
        items = sorted(
            hoje,
            key=lambda r: (
                priority_rank(r.prioridade),
                ensure_br(r.data_limite),
                -int(r.prazo_id),
            ),
        )
        df = build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo vencendo hoje com os filtros atuais.")
            return

        df = df.sort_values(by=["_sort_dt"], ascending=[True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "prioridade",
                "origem",
                "status",
            ],
            height=340,
        )
        return

    if chosen_view == "Vencem (7 dias)":
        items = sorted(
            vencem7,
            key=lambda r: (
                dias_restantes(r.data_limite),
                priority_rank(r.prioridade),
                ensure_br(r.data_limite),
            ),
        )
        df = build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo vencendo em até 7 dias com os filtros atuais.")
            return

        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[True, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=380,
        )
        return

    if chosen_view == "Abertos":
        filtro_janela, ordem = render_open_controls()
        items = filter_open_window(filtered, filtro_janela)

        reverse_days = ordem == "Mais distantes primeiro"
        items = sort_operational(items, reverse_days=reverse_days)

        df = build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo aberto com os filtros atuais.")
            return

        asc = ordem == "Mais urgentes primeiro"
        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[asc, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=460,
        )
        return

    items = sorted(concluidos, key=lambda r: ensure_br(r.data_limite), reverse=True)
    df = build_df(items, include_status=False)
    if df is None:
        st.info("Nenhum prazo concluído com os filtros atuais.")
        return

    df = df.sort_values(by=["_sort_dt"], ascending=False).drop(
        columns=["_sort_dt"], errors="ignore"
    )
    render_df(
        df,
        ["prazo_id", "processo", "evento", "data_limite", "prioridade", "origem"],
        height=380,
    )
