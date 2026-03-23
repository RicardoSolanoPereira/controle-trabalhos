from __future__ import annotations

import streamlit as st

from services.calendario_service import CalendarioService
from ui.layout import (
    PageMeta,
    form_panel,
    header_actions,
    list_panel,
    page_frame,
    section_surface,
)
from ui.prazos_components.cache import cached_prazos_list_all, cached_processos
from ui.prazos_components.constants import KEY_OWNER
from ui.prazos_components.helpers import dicts_to_dataclass, proc_label_dict
from ui.prazos_components.sections import (
    render_contexto_trabalho,
    section_tabs,
)
from ui.prazos_components.cadastro import render_cadastro
from ui.prazos_components.edicao import render_editar
from ui.prazos_components.lista import render_lista
from ui.prazos_components.state import (
    apply_pref_processo_defaults,
    apply_requested_tab,
    init_defaults,
)
from ui_state import get_data_version


def _render_header_actions() -> None:
    def _btn_recarregar() -> None:
        if st.button(
            "Recarregar",
            key="pz_btn_recarregar",
            help="Recarrega a tela e os dados",
            use_container_width=True,
        ):
            st.rerun()

    def _btn_limpar_cache() -> None:
        if st.button(
            "Limpar cache",
            key="pz_btn_clear_cache",
            type="secondary",
            help="Limpa o cache de feriados",
            use_container_width=True,
        ):
            CalendarioService.clear_cache()
            st.success("Cache de feriados limpo.")
            st.rerun()

    header_actions([_btn_recarregar, _btn_limpar_cache])


def render(owner_user_id: int) -> None:
    st.session_state[KEY_OWNER] = owner_user_id

    version = get_data_version(owner_user_id)
    processos = cached_processos(owner_user_id, version)
    all_rows = dicts_to_dataclass(cached_prazos_list_all(owner_user_id, version))

    with page_frame(
        PageMeta(
            title="Prazos",
            subtitle="Cadastro, priorização e controle operacional de prazos.",
        ),
        right_actions=_render_header_actions,
    ):
        if not processos:
            st.info("Cadastre um trabalho primeiro.")
            return

        proc_labels = [proc_label_dict(p) for p in processos]
        label_to_id = {
            proc_labels[i]: int(processos[i]["id"]) for i in range(len(processos))
        }
        proc_by_id = {int(p["id"]): p for p in processos}

        pref_id = st.session_state.get("pref_processo_id")
        pref_proc = None
        if pref_id:
            try:
                pref_proc = proc_by_id.get(int(pref_id))
            except Exception:
                pref_proc = None

        init_defaults(proc_labels)
        apply_pref_processo_defaults(proc_labels, label_to_id)
        apply_requested_tab()

        render_contexto_trabalho(pref_proc, all_rows)

        with section_surface():
            section = section_tabs("pz_active_tab")

        if section == "Cadastrar":
            with form_panel(
                "Novo prazo",
                subtitle="Escolha o modo de contagem, confira a data final e salve.",
            ):
                render_cadastro(
                    owner_user_id=owner_user_id,
                    proc_labels=proc_labels,
                    label_to_id=label_to_id,
                    proc_by_id=proc_by_id,
                )

        elif section == "Lista":
            with list_panel(
                "Lista de prazos",
                subtitle="Consulte, filtre e acompanhe os prazos cadastrados.",
            ):
                render_lista(
                    owner_user_id=owner_user_id,
                    proc_labels=proc_labels,
                    label_to_id=label_to_id,
                    version=version,
                )

        else:
            with section_surface(
                "Editar / Excluir",
                subtitle="Atualize ou remova prazos existentes com segurança.",
            ):
                render_editar(
                    owner_user_id=owner_user_id,
                    version=version,
                )
