from __future__ import annotations

import streamlit as st

from ui.page_header import page_header
from ui.theme import inject_global_css

from .constants import KEY_MOBILE_MODE
from .data_access import cached_processos
from .helpers import ag_data_version, apply_pref_processo_defaults, build_proc_maps
from .sections import (
    inject_agendamento_css,
    render_create_block,
    render_edit_block,
    render_list_block,
)


def render(owner_user_id: int) -> None:
    inject_global_css()
    inject_agendamento_css()

    clicked_refresh = page_header(
        "Agenda",
        "Visualize, cadastre e acompanhe compromissos dos seus trabalhos.",
        right_button_label="Recarregar",
        right_button_key="ag_btn_recarregar",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked_refresh:
        st.rerun()

    with st.sidebar.expander("📱 Ajustes (UI)", expanded=False):
        st.checkbox("Modo mobile (cards)", value=False, key=KEY_MOBILE_MODE)

    version = ag_data_version(owner_user_id)
    processos = cached_processos(owner_user_id, version)

    if not processos:
        st.info("Cadastre um trabalho primeiro para criar compromissos na agenda.")
        return

    proc_maps = build_proc_maps(processos)
    apply_pref_processo_defaults(proc_maps)

    render_list_block(owner_user_id, proc_maps)
    st.write("")

    render_create_block(owner_user_id, proc_maps)
    st.write("")

    render_edit_block(owner_user_id, proc_maps)
