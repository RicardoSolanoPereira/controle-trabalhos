from __future__ import annotations

import streamlit as st

from db.connection import get_session
from services.processos_service import ProcessoCreate, ProcessosService
from ui.layout import grid, section, spacer
from ui.processos.constants import (
    ATUACAO_UI_PROCESSOS,
    CATEGORIAS_UI,
    K_CREATE_ATUACAO,
    K_CREATE_CATEGORIA,
    K_CREATE_COMARCA,
    K_CREATE_CONTRATANTE,
    K_CREATE_NUMERO,
    K_CREATE_OBS,
    K_CREATE_PASTA,
    K_CREATE_STATUS,
    K_CREATE_TIPO,
    K_CREATE_VARA,
    K_SELECTED_ID,
    ROOT_TRABALHOS,
    SECTION_PAINEL,
    STATUS_VALIDOS,
)
from ui_state import bump_data_version


def render_cadastro(
    owner_user_id: int,
    *,
    button,
    soft_note,
    pick_folder_dialog,
    go_new,
    open_edit,
    go_prazos,
    duplicate_processo,
    set_section,
    toast,
    clear_data_cache,
    guess_pasta_local,
    atuacao_db_from_label,
) -> None:
    if st.session_state.get("proc_last_created_id"):
        last_id = int(st.session_state["proc_last_created_id"])
        last_ref = st.session_state.get("proc_last_created_ref", "")

        with section(
            "✅ Trabalho cadastrado",
            subtitle="Escolha o próximo passo para continuar o fluxo.",
            divider=False,
        ):
            a, b, c, d = grid(4, columns_mobile=1)
            with a:
                button(
                    "Abrir trabalho",
                    key="proc_post_edit",
                    type="primary",
                    on_click=open_edit,
                    args=(last_id,),
                )
            with b:
                button(
                    "Prazos",
                    key="proc_post_prazos",
                    on_click=go_prazos,
                    args=(last_id, last_ref, "", ""),
                )
            with c:
                button(
                    "Duplicar",
                    key="proc_post_dup",
                    on_click=duplicate_processo,
                    args=(owner_user_id, last_id),
                )
            with d:
                button("Cadastrar outro", key="proc_post_new", on_click=go_new)

    with section(
        "Novo trabalho",
        subtitle="Cadastre o essencial primeiro. Depois complemente com prazos, agenda, financeiro e notas.",
        divider=False,
    ):
        soft_note(
            "Fluxo recomendado",
            "Primeiro registre referência, atuação, categoria e cliente. Depois refine pasta, observações e os módulos operacionais.",
        )

        spacer(0.10)
        st.session_state.setdefault(K_CREATE_PASTA, "")

        a, b = grid(2, columns_mobile=1)
        with a:
            if button("📁 Escolher pasta…", key="proc_create_pick_folder"):
                chosen = pick_folder_dialog(initialdir=str(ROOT_TRABALHOS))
                if chosen:
                    st.session_state[K_CREATE_PASTA] = chosen
                    st.rerun()
                else:
                    st.info(
                        "Seleção de pasta indisponível em ambiente headless ou operação cancelada."
                    )
        with b:
            st.caption(
                "Se estiver no Windows local, já vincule a pasta do trabalho desde o cadastro."
            )

        suggest_folder = False
        submitted = False

        with st.form("form_trabalho_create", clear_on_submit=False):
            c1, c2, c3 = grid(3, columns_mobile=1)
            with c1:
                numero = st.text_input(
                    "Número / Código *",
                    placeholder="0000000-00.0000.0.00.0000 ou AP-2026-001",
                    key=K_CREATE_NUMERO,
                )
            with c2:
                atuacao_label = st.selectbox(
                    "Atuação *",
                    list(ATUACAO_UI_PROCESSOS.keys()),
                    index=1,
                    key=K_CREATE_ATUACAO,
                )
            with c3:
                status = st.selectbox(
                    "Status", list(STATUS_VALIDOS), index=0, key=K_CREATE_STATUS
                )

            c4, c5 = grid(2, columns_mobile=1)
            with c4:
                categoria = st.selectbox(
                    "Categoria / Serviço",
                    CATEGORIAS_UI,
                    index=0,
                    key=K_CREATE_CATEGORIA,
                )
            with c5:
                tipo_acao = st.text_input(
                    "Descrição / Tipo",
                    placeholder="Ex.: Ação possessória / Avaliação / Vistoria...",
                    key=K_CREATE_TIPO,
                )

            c6, c7, c8 = grid(3, columns_mobile=1)
            with c6:
                comarca = st.text_input("Comarca", key=K_CREATE_COMARCA)
            with c7:
                vara = st.text_input("Vara", key=K_CREATE_VARA)
            with c8:
                contratante = st.text_input(
                    "Contratante / Cliente", key=K_CREATE_CONTRATANTE
                )

            pasta = st.text_input(
                "Pasta local (opcional)",
                placeholder=str(ROOT_TRABALHOS / "AP-2026-001"),
                key=K_CREATE_PASTA,
            )

            aux1, aux2 = grid(2, columns_mobile=1)
            with aux1:
                suggest_folder = st.form_submit_button(
                    "Sugerir pasta (auto)", type="secondary", use_container_width=True
                )
            with aux2:
                spacer(0.01)

            obs = st.text_area("Observações", key=K_CREATE_OBS, height=120)

            submit_col1, submit_col2 = grid(2, columns_mobile=1)
            with submit_col1:
                submitted = st.form_submit_button(
                    "Salvar trabalho", type="primary", use_container_width=True
                )
            with submit_col2:
                spacer(0.01)

        if suggest_folder:
            st.session_state[K_CREATE_PASTA] = guess_pasta_local(
                st.session_state.get(K_CREATE_NUMERO, "")
            )
            st.rerun()

        if submitted:
            numero_v = (numero or "").strip()
            if not numero_v:
                st.error("Informe o Número / Código.")
                return

            papel_db = atuacao_db_from_label(atuacao_label)
            try:
                with get_session() as s:
                    created = ProcessosService.create(
                        s,
                        owner_user_id=owner_user_id,
                        payload=ProcessoCreate(
                            numero_processo=numero_v,
                            comarca=(comarca or "").strip(),
                            vara=(vara or "").strip(),
                            tipo_acao=(tipo_acao or "").strip(),
                            contratante=(contratante or "").strip(),
                            papel=papel_db,
                            status=status,
                            pasta_local=(pasta or "").strip(),
                            categoria_servico=(categoria or "").strip(),
                            observacoes=(obs or "").strip(),
                        ),
                    )

                bump_data_version(owner_user_id)
                clear_data_cache()
                created_id = int(getattr(created, "id", 0) or 0)
                st.session_state["proc_last_created_id"] = created_id
                st.session_state["proc_last_created_ref"] = numero_v
                st.session_state[K_SELECTED_ID] = created_id
                toast("✅ Trabalho cadastrado")
                set_section(SECTION_PAINEL)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")
