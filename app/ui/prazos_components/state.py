from __future__ import annotations

import streamlit as st

from ui.prazos_components.constants import (
    KEY_ACTIVE_TAB,
    KEY_C_AUDIT,
    KEY_C_BASE,
    KEY_C_DATA_LIM,
    KEY_C_DIAS,
    KEY_C_LOCAL,
    KEY_C_MODE,
    KEY_C_PROC,
    KEY_C_USAR_TJSP,
    KEY_FILTER_ORIGEM,
    KEY_FILTER_PRIO,
    KEY_FILTER_PROC,
    KEY_LIST_ACTIVE,
    KEY_LIST_NAV_TO,
    KEY_LIST_SELECTOR,
    KEY_NAV_TO,
)
from services.utils import now_br


def request_tab(tab: str) -> None:
    st.session_state[KEY_NAV_TO] = tab


def apply_requested_tab() -> None:
    nav = st.session_state.pop(KEY_NAV_TO, None)
    if nav in ("Cadastrar", "Lista", "Editar / Excluir"):
        st.session_state[KEY_ACTIVE_TAB] = nav
    st.session_state.setdefault(KEY_ACTIVE_TAB, "Cadastrar")


def request_list_tab(tab: str) -> None:
    st.session_state[KEY_LIST_NAV_TO] = tab


def apply_requested_list_tab() -> None:
    nav = st.session_state.pop(KEY_LIST_NAV_TO, None)
    if nav in ("Abertos", "Hoje", "Atrasados", "Vencem (7 dias)", "Concluídos"):
        st.session_state[KEY_LIST_ACTIVE] = nav
        st.session_state[KEY_LIST_SELECTOR] = nav

    st.session_state.setdefault(KEY_LIST_ACTIVE, "Abertos")
    st.session_state.setdefault(KEY_LIST_SELECTOR, "Abertos")


def apply_pref_processo_defaults(
    proc_labels: list[str],
    label_to_id: dict[str, int],
) -> None:
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return

    try:
        pref_id = int(pref_id)
    except Exception:
        return

    chosen_label = None
    for label, pid in label_to_id.items():
        if int(pid) == pref_id:
            chosen_label = label
            break

    if not chosen_label:
        return

    st.session_state.setdefault(KEY_C_PROC, chosen_label)
    st.session_state.setdefault(KEY_FILTER_PROC, chosen_label)


def init_defaults(proc_labels: list[str]) -> None:
    hoje_sp = now_br().date()
    st.session_state.setdefault(KEY_C_MODE, "Manual")
    st.session_state.setdefault(KEY_C_DATA_LIM, hoje_sp)
    st.session_state.setdefault(KEY_C_AUDIT, "")
    st.session_state.setdefault(KEY_C_BASE, hoje_sp)
    st.session_state.setdefault(KEY_C_DIAS, 15)
    st.session_state.setdefault(KEY_C_USAR_TJSP, True)
    st.session_state.setdefault(KEY_C_LOCAL, True)
    st.session_state.setdefault(KEY_C_PROC, proc_labels[0] if proc_labels else "")
    st.session_state.setdefault(KEY_FILTER_PRIO, "(Todas)")
    st.session_state.setdefault(KEY_FILTER_ORIGEM, "(Todas)")
    st.session_state.setdefault(KEY_LIST_SELECTOR, "Abertos")
