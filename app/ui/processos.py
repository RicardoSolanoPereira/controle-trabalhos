# app/ui/processos.py
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.db.connection import get_session
from services.processos_service import ProcessosService, ProcessoCreate, ProcessoUpdate

from app.ui.theme import card
from app.ui.page_header import page_header
from app.ui_state import navigate, get_qp_str, bump_data_version


ATUACAO_UI = {
    "Perícia (Juízo)": "Perito Judicial",
    "Assistência Técnica": "Assistente Técnico",
    "Particular / Outros serviços": "Trabalho Particular",
}
ATUACAO_UI_ALL = {"(Todas)": None, **ATUACAO_UI}

STATUS_VALIDOS = ("Ativo", "Concluído", "Suspenso")

CATEGORIAS_UI = [
    "Perícia",
    "Assistência Técnica",
    "Consultoria",
    "Análise documental",
    "Vistoria",
    "Topografia",
    "Avaliação imobiliária",
    "Regularização",
    "Outros",
]

ROOT_TRABALHOS = Path(os.getenv("ROOT_TRABALHOS", r"D:\TRABALHOS"))


# ==================================================
# STATE / VERSION
# ==================================================
def _data_version(owner_user_id: int) -> int:
    return int(st.session_state.get(f"data_version_{owner_user_id}", 0))


def _clear_list_state() -> None:
    for k in (
        "proc_list_status",
        "proc_list_atuacao",
        "proc_list_categoria",
        "proc_list_q",
        "proc_list_ordem",
        "proc_list_selected_id",
    ):
        st.session_state.pop(k, None)


# ==================================================
# NORMALIZAÇÃO / LABELS
# ==================================================
def _norm_tipo_trabalho(val: str | None) -> str:
    v = (val or "").strip()
    if not v:
        return "Assistente Técnico"

    v_low = v.lower()
    if v_low in ("perito", "perito judicial"):
        return "Perito Judicial"
    if v_low in ("assistente", "assistente tecnico", "assistente técnico"):
        return "Assistente Técnico"
    if v_low in (
        "particular",
        "avaliacao",
        "avaliação",
        "avaliação particular",
        "trabalho particular",
    ):
        return "Trabalho Particular"
    return v


def _atuacao_label_from_db(db_val: str | None) -> str:
    v = _norm_tipo_trabalho(db_val)
    for label, db in ATUACAO_UI.items():
        if db == v:
            return label
    return v


def _atuacao_db_from_label(label: str) -> str:
    return ATUACAO_UI.get(label, "Assistente Técnico")


def _status_badge(status: str) -> str:
    s = (status or "").strip().lower()
    if s == "ativo":
        return "🟢 Ativo"
    if s in ("concluído", "concluido"):
        return "✅ Concluído"
    if s == "suspenso":
        return "⏸ Suspenso"
    return status


def _atuacao_badge(db_val: str | None) -> str:
    v = _norm_tipo_trabalho(db_val)
    if v == "Perito Judicial":
        return "⚖️ Perícia (Juízo)"
    if v == "Assistente Técnico":
        return "🛠️ Assistência Técnica"
    if v == "Trabalho Particular":
        return "🏷️ Particular"
    return v


# ==================================================
# UX HELPERS
# ==================================================
def _guess_pasta_local(numero: str) -> str:
    n = (numero or "").strip()
    if not n:
        return ""
    safe = re.sub(r"[\\\\/]+", "-", n)
    safe = re.sub(r'[:*?"<>|]+', "", safe)
    safe = safe.strip()
    return rf"{ROOT_TRABALHOS}\{safe}"


def _toast(msg: str) -> None:
    try:
        st.toast(msg)  # type: ignore[attr-defined]
    except Exception:
        pass


def _pick_folder_dialog(initialdir: str | None = None) -> str | None:
    """
    Abre seletor de pasta nativo (Windows Explorer) via tkinter.
    Funciona em localhost/Windows (não em servidor headless).
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        folder = filedialog.askdirectory(
            initialdir=initialdir or str(ROOT_TRABALHOS),
            title="Escolher pasta do trabalho",
            mustexist=False,
        )
        root.destroy()
        return str(folder) if folder else None
    except Exception:
        return None


def _is_mobile_hint() -> bool:
    return bool(st.session_state.get("ui_mobile_mode", False))


# ==================================================
# NAVEGAÇÃO INTERNA (ABA)
# ==================================================
def _request_tab(tab: str, processo_id: int | None = None) -> None:
    if processo_id is not None:
        st.session_state["proc_edit_selected_id"] = int(processo_id)
    st.session_state["proc_nav_to"] = tab


def _apply_requested_tab() -> None:
    nav = st.session_state.pop("proc_nav_to", None)
    if nav in ("Cadastrar", "Lista", "Editar / Excluir"):
        st.session_state["proc_active_tab"] = nav


def _open_edit(processo_id: int) -> None:
    _request_tab("Editar / Excluir", processo_id=processo_id)
    st.rerun()


def _sync_from_dashboard_and_qp() -> None:
    st.session_state.setdefault("proc_active_tab", "Lista")

    # vindo do dashboard
    sec = st.session_state.pop("processos_section", None)
    if sec in ("Lista", "Cadastrar", "Editar / Excluir"):
        st.session_state["proc_active_tab"] = sec

    qp_status = get_qp_str("status", "")
    qp_atuacao = get_qp_str("atuacao", "")
    qp_categoria = get_qp_str("categoria", "")
    qp_q = get_qp_str("q", "")

    has_qp = bool(qp_status or qp_atuacao or qp_categoria or qp_q)
    if not has_qp:
        return

    st.session_state["proc_active_tab"] = "Lista"

    status_options = ["(Todos)"] + list(STATUS_VALIDOS)
    st.session_state["proc_list_status"] = (
        qp_status if qp_status in status_options else "(Todos)"
    )

    atuacao_options = list(ATUACAO_UI_ALL.keys())
    st.session_state["proc_list_atuacao"] = (
        qp_atuacao if qp_atuacao in atuacao_options else "(Todas)"
    )

    categoria_options = ["(Todas)"] + CATEGORIAS_UI
    st.session_state["proc_list_categoria"] = (
        qp_categoria if qp_categoria in categoria_options else "(Todas)"
    )

    st.session_state["proc_list_q"] = qp_q
    st.session_state.setdefault("proc_list_ordem", "Mais recentes")


# ==================================================
# CACHE (SERIALIZÁVEL)
# ==================================================
def _p_to_row(p: Any) -> dict:
    return {
        "id": int(getattr(p, "id", 0) or 0),
        "numero_processo": (getattr(p, "numero_processo", "") or ""),
        "papel": (getattr(p, "papel", "") or ""),
        "categoria_servico": (getattr(p, "categoria_servico", "") or ""),
        "status": (getattr(p, "status", "") or ""),
        "contratante": (getattr(p, "contratante", "") or ""),
        "tipo_acao": (getattr(p, "tipo_acao", "") or ""),
        "comarca": (getattr(p, "comarca", "") or ""),
        "vara": (getattr(p, "vara", "") or ""),
        "pasta_local": (getattr(p, "pasta_local", "") or ""),
        "observacoes": (getattr(p, "observacoes", "") or ""),
    }


@st.cache_data(show_spinner=False, ttl=45)
def _cached_list_rows(
    owner_user_id: int,
    status: str | None,
    papel: str | None,
    categoria_servico: str | None,
    q: str | None,
    order_desc: bool,
    version: int,
) -> list[dict]:
    with get_session() as s:
        processos = ProcessosService.list(
            s,
            owner_user_id=owner_user_id,
            status=status,
            papel=papel,
            categoria_servico=categoria_servico,
            q=q,
            order_desc=order_desc,
        )
    return [_p_to_row(p) for p in (processos or [])]


@st.cache_data(show_spinner=False, ttl=45)
def _cached_get_row(owner_user_id: int, processo_id: int, version: int) -> dict | None:
    with get_session() as s:
        p = ProcessosService.get(s, owner_user_id, processo_id)
    return _p_to_row(p) if p else None


# ==================================================
# MOBILE CARD RENDER (DICT)
# ==================================================
def _render_processo_card_row(r: dict) -> None:
    pid = int(r.get("id") or 0)
    ref = (r.get("numero_processo") or "").strip()

    atu = _atuacao_badge(r.get("papel"))
    status = _status_badge(r.get("status", ""))

    cat = (r.get("categoria_servico") or "").strip()
    cli = (r.get("contratante") or "").strip()
    desc = (r.get("tipo_acao") or "").strip()
    comarca = (r.get("comarca") or "").strip()
    vara = (r.get("vara") or "").strip()
    pasta = (r.get("pasta_local") or "").strip()

    st.markdown(
        f"""
        <div class="sp-surface" style="margin-bottom:12px;">
          <div style="font-weight:900; font-size:1.02rem;">{ref}</div>
          <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
            <span class="sp-chip">{atu}</span>
            <span class="sp-chip">{status}</span>
            {f"<span class='sp-chip'>🏷️ {cat}</span>" if cat else ""}
            {f"<span class='sp-chip'>🏛️ {comarca}</span>" if comarca else "<span class='sp-chip'>⚠️ Sem comarca</span>"}
          </div>
          <div style="margin-top:8px; color: rgba(15,23,42,0.75);">
            {f"<b>Cliente:</b> {cli}<br/>" if cli else ""}
            {f"<b>Descrição:</b> {desc}<br/>" if desc else ""}
            {f"<b>Comarca:</b> {comarca} • <b>Vara:</b> {vara}<br/>" if (comarca or vara) else ""}
            {f"<b>Pasta:</b> {pasta}" if pasta else ""}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    if c1.button(
        "Editar", key=f"m_edit_{pid}", use_container_width=True, type="primary"
    ):
        _open_edit(pid)

    if c2.button("Prazos", key=f"m_pz_{pid}", use_container_width=True):
        st.session_state["pref_processo_id"] = pid
        st.session_state["pref_processo_ref"] = ref
        st.session_state["pref_processo_comarca"] = comarca
        st.session_state["pref_processo_vara"] = vara
        navigate("Prazos", state={"prazos_section": "Lista"})

    c3, c4 = st.columns(2)
    if c3.button("Agenda", key=f"m_ag_{pid}", use_container_width=True):
        st.session_state["pref_processo_id"] = pid
        st.session_state["pref_processo_ref"] = ref
        st.session_state["pref_processo_comarca"] = comarca
        st.session_state["pref_processo_vara"] = vara
        navigate("Agendamentos")

    if c4.button("Financeiro", key=f"m_fin_{pid}", use_container_width=True):
        st.session_state["pref_processo_id"] = pid
        st.session_state["pref_processo_ref"] = ref
        st.session_state["pref_processo_comarca"] = comarca
        st.session_state["pref_processo_vara"] = vara
        navigate("Financeiro", state={"financeiro_section": "Lançamentos"})

    st.write("")


# ==================================================
# SEGMENTED / RADIO (DESKTOP)
# ==================================================
def _segmented_or_radio(options: list[str], key: str) -> str:
    if hasattr(st, "segmented_control"):
        return st.segmented_control(
            "Seção",
            options=options,
            key=key,
            label_visibility="collapsed",
        )
    return st.radio(
        "Seção", options, key=key, horizontal=True, label_visibility="collapsed"
    )


# ==================================================
# RENDER (ENTRY)
# ==================================================
def render(owner_user_id: int):
    st.markdown(
        """
        <style>
          .sec-title { font-weight: 850; font-size: 1.05rem; margin: 0.1rem 0 0.35rem 0; }
          .sec-cap { color: rgba(15,23,42,0.62); font-size: 0.90rem; margin-top: -0.25rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    clicked = page_header(
        "Trabalhos",
        "Cadastro e gestão de atividades técnicas (judicial e particular).",
        right_button_label="Recarregar",
        right_button_key="processos_btn_recarregar_top",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked:
        st.rerun()

    _sync_from_dashboard_and_qp()
    _apply_requested_tab()
    st.session_state.setdefault("proc_active_tab", "Lista")

    with st.sidebar.expander("📱 Ajustes (UI)", expanded=False):
        st.checkbox(
            "Modo mobile (cards)", value=_is_mobile_hint(), key="ui_mobile_mode"
        )

    options = ["Cadastrar", "Lista", "Editar / Excluir"]

    if _is_mobile_hint():
        t1, t2, t3 = st.tabs(options)
        with t1:
            st.session_state["proc_active_tab"] = "Cadastrar"
            _render_cadastrar(owner_user_id)
        with t2:
            st.session_state["proc_active_tab"] = "Lista"
            _render_lista(owner_user_id)
        with t3:
            st.session_state["proc_active_tab"] = "Editar / Excluir"
            _render_editar(owner_user_id)
        return

    section_name = _segmented_or_radio(options, key="proc_active_tab")
    if section_name == "Cadastrar":
        _render_cadastrar(owner_user_id)
    elif section_name == "Lista":
        _render_lista(owner_user_id)
    else:
        _render_editar(owner_user_id)


# ==================================================
# CADASTRAR
# ==================================================
def _render_cadastrar(owner_user_id: int) -> None:
    if st.session_state.get("proc_last_created_id"):
        last_id = int(st.session_state["proc_last_created_id"])
        last_ref = st.session_state.get("proc_last_created_ref", "")

        with st.container(border=True):
            st.markdown("### ✅ Trabalho cadastrado")
            st.caption("Próximo passo: prazos, agenda ou financeiro deste trabalho.")

            c1, c2 = st.columns(2)
            if c1.button(
                "Editar", use_container_width=True, type="primary", key="proc_post_edit"
            ):
                _open_edit(last_id)

            if c2.button(
                "Cadastrar outro", use_container_width=True, key="proc_post_new"
            ):
                st.session_state.pop("proc_last_created_id", None)
                st.session_state.pop("proc_last_created_ref", None)
                for k in (
                    "proc_create_numero",
                    "proc_create_atuacao",
                    "proc_create_status",
                    "proc_create_categoria",
                    "proc_create_tipo_acao",
                    "proc_create_comarca",
                    "proc_create_vara",
                    "proc_create_contratante",
                    "proc_create_pasta",
                    "proc_create_obs",
                ):
                    st.session_state.pop(k, None)
                st.rerun()

            c3, c4, c5 = st.columns(3)
            if c3.button("Prazos", use_container_width=True, key="proc_post_prazos"):
                st.session_state["pref_processo_id"] = last_id
                st.session_state["pref_processo_ref"] = last_ref
                # Se já tivermos no estado, ótimo; senão mantém vazio (UI da tela seguinte avisa)
                st.session_state.setdefault("pref_processo_comarca", "")
                st.session_state.setdefault("pref_processo_vara", "")
                navigate("Prazos", state={"prazos_section": "Cadastro"})
            if c4.button("Agenda", use_container_width=True, key="proc_post_agenda"):
                st.session_state["pref_processo_id"] = last_id
                st.session_state["pref_processo_ref"] = last_ref
                st.session_state.setdefault("pref_processo_comarca", "")
                st.session_state.setdefault("pref_processo_vara", "")
                navigate("Agendamentos")
            if c5.button("Financeiro", use_container_width=True, key="proc_post_fin"):
                st.session_state["pref_processo_id"] = last_id
                st.session_state["pref_processo_ref"] = last_ref
                st.session_state.setdefault("pref_processo_comarca", "")
                st.session_state.setdefault("pref_processo_vara", "")
                navigate("Financeiro", state={"financeiro_section": "Lançamentos"})

    with st.container(border=True):
        st.markdown(
            "<div class='sec-title'>Novo trabalho</div>", unsafe_allow_html=True
        )
        st.markdown(
            "<div class='sec-cap'>Cadastre o essencial primeiro; detalhes você completa depois.</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        st.session_state.setdefault("proc_create_pasta", "")

        a, b = st.columns([1.2, 3.8], vertical_alignment="center")
        if a.button("📁 Escolher pasta…", key="proc_create_pick_folder"):
            chosen = _pick_folder_dialog(initialdir=str(ROOT_TRABALHOS))
            if chosen:
                st.session_state["proc_create_pasta"] = chosen
                st.rerun()
            else:
                st.warning(
                    "Não foi possível abrir o Explorer (ou nenhuma pasta foi escolhida)."
                )
        b.caption("Dica: escolha a pasta no Windows Explorer (localhost).")

        if st.button(
            "Sugerir pasta (auto)", use_container_width=True, key="proc_suggest_folder"
        ):
            st.session_state["proc_create_pasta"] = _guess_pasta_local(
                st.session_state.get("proc_create_numero", "")
            )
            st.rerun()

        with st.form("form_trabalho_create", clear_on_submit=False):
            with st.container(border=True):
                st.markdown("**1) Essencial**")
                st.caption("O mínimo para começar a operar (obrigatórios).")

                c1, c2, c3 = st.columns(3)
                numero = c1.text_input(
                    "Número do processo / Código interno *",
                    placeholder="0000000-00.0000.0.00.0000 ou AP-2026-001",
                    key="proc_create_numero",
                )
                atuacao_label = c2.selectbox(
                    "Atuação *",
                    list(ATUACAO_UI.keys()),
                    index=1,
                    key="proc_create_atuacao",
                )
                status = c3.selectbox(
                    "Status", list(STATUS_VALIDOS), index=0, key="proc_create_status"
                )

            with st.container(border=True):
                st.markdown("**2) Classificação**")
                st.caption("Ajuda a filtrar e organizar na lista.")

                c4, c5 = st.columns([1.2, 1.8])
                categoria = c4.selectbox(
                    "Categoria / Serviço",
                    CATEGORIAS_UI,
                    index=0,
                    key="proc_create_categoria",
                )
                tipo_acao = c5.text_input(
                    "Descrição / Tipo",
                    placeholder="Ex.: Ação possessória / Avaliação / Vistoria...",
                    key="proc_create_tipo_acao",
                )

            with st.container(border=True):
                st.markdown("**3) Complementos**")
                st.caption("Preencha quando quiser (não bloqueia o uso).")

                c6, c7, c8 = st.columns(3)
                comarca = c6.text_input(
                    "Comarca",
                    key="proc_create_comarca",
                    help="Impacta cálculo de prazos (CPC/TJSP) e feriados municipais.",
                )
                vara = c7.text_input("Vara", key="proc_create_vara")
                contratante = c8.text_input(
                    "Contratante / Cliente", key="proc_create_contratante"
                )

                # Aviso UX (não bloqueia): comarca é essencial p/ cálculo de prazos
                if (status == "Ativo") and not (comarca or "").strip():
                    st.warning(
                        "Comarca não informada. Isso pode afetar o cálculo de prazos (CPC/TJSP) e feriados municipais.",
                        icon="⚠️",
                    )

                pasta = st.text_input(
                    "Pasta local (opcional)",
                    placeholder=rf"{ROOT_TRABALHOS}\AP-2026-001",
                    key="proc_create_pasta",
                )
                obs = st.text_area("Observações", key="proc_create_obs", height=120)

            submitted = st.form_submit_button("Salvar", type="primary")

        if submitted:
            papel_db = _atuacao_db_from_label(atuacao_label)

            if not (numero or "").strip():
                st.error("Informe o Número do processo / Código interno.")
            else:
                try:
                    with get_session() as s:
                        created = ProcessosService.create(
                            s,
                            owner_user_id=owner_user_id,
                            payload=ProcessoCreate(
                                numero_processo=numero.strip(),
                                comarca=(comarca or "").strip(),
                                vara=(vara or "").strip(),
                                tipo_acao=(tipo_acao or "").strip(),
                                contratante=(contratante or "").strip(),
                                papel=papel_db,
                                status=status,
                                pasta_local=(pasta or "").strip(),
                                categoria_servico=categoria,
                                observacoes=(obs or "").strip(),
                            ),
                        )

                    bump_data_version(owner_user_id)

                    st.session_state["proc_last_created_id"] = int(
                        getattr(created, "id", 0) or 0
                    )
                    st.session_state["proc_last_created_ref"] = numero.strip()

                    # ✅ guarda contexto para telas seguintes (UX)
                    st.session_state["pref_processo_comarca"] = (comarca or "").strip()
                    st.session_state["pref_processo_vara"] = (vara or "").strip()

                    _toast("✅ Trabalho cadastrado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")

    with st.expander("Ferramentas (manutenção)", expanded=False):
        st.caption("Utilidades para padronização e migração de dados antigos.")

        cA, cB = st.columns([0.55, 0.45])
        remove_prefix = cA.checkbox(
            "Remover prefixo [Categoria: ...] das observações após migrar",
            value=True,
            key="proc_backfill_remove_prefix",
        )
        only_if_empty = cB.checkbox(
            "Migrar apenas quando categoria_servico estiver vazia",
            value=True,
            key="proc_backfill_only_if_empty",
        )

        if st.button(
            "Backfill categoria (observações → categoria_servico)",
            type="secondary",
            key="proc_backfill_btn",
        ):
            try:
                with get_session() as s:
                    changed = ProcessosService.backfill_categoria_from_observacoes(
                        s,
                        owner_user_id=owner_user_id,
                        remove_prefix=remove_prefix,
                        only_if_empty=only_if_empty,
                    )
                bump_data_version(owner_user_id)
                st.success(f"Backfill concluído. Registros atualizados: {changed}")
                st.rerun()
            except Exception as e:
                st.error(f"Erro no backfill: {e}")


# ==================================================
# LISTA
# ==================================================
def _render_lista(owner_user_id: int) -> None:
    with st.container(border=True):
        st.markdown("<div class='sec-title'>Lista</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='sec-cap'>Filtre rápido. Use as ações para operar.</div>",
            unsafe_allow_html=True,
        )

        if _is_mobile_hint():
            status_options = ["(Todos)"] + list(STATUS_VALIDOS)
            filtro_status = st.selectbox(
                "Status", status_options, key="proc_list_status"
            )

            atuacao_options = list(ATUACAO_UI_ALL.keys())
            filtro_atuacao = st.selectbox(
                "Atuação", atuacao_options, key="proc_list_atuacao"
            )

            categoria_options = ["(Todas)"] + CATEGORIAS_UI
            filtro_categoria = st.selectbox(
                "Categoria", categoria_options, key="proc_list_categoria"
            )

            ordem = st.selectbox(
                "Ordenar", ["Mais recentes", "Mais antigos"], key="proc_list_ordem"
            )

            filtro_q = st.text_input(
                "Buscar",
                placeholder="nº/código, comarca, vara, cliente, descrição, observações…",
                key="proc_list_q",
            )

            if st.button(
                "Limpar filtros", use_container_width=True, key="proc_list_clear_btn"
            ):
                _clear_list_state()
                navigate(
                    "Processos", clear_qp=True, state={"processos_section": "Lista"}
                )
                return
        else:
            c1, c2, c3, c4 = st.columns([1.1, 1.4, 1.4, 1.1])
            status_options = ["(Todos)"] + list(STATUS_VALIDOS)
            filtro_status = c1.selectbox(
                "Status", status_options, key="proc_list_status"
            )

            atuacao_options = list(ATUACAO_UI_ALL.keys())
            filtro_atuacao = c2.selectbox(
                "Atuação", atuacao_options, key="proc_list_atuacao"
            )

            categoria_options = ["(Todas)"] + CATEGORIAS_UI
            filtro_categoria = c3.selectbox(
                "Categoria", categoria_options, key="proc_list_categoria"
            )

            ordem = c4.selectbox(
                "Ordenar", ["Mais recentes", "Mais antigos"], key="proc_list_ordem"
            )

            c5, c6 = st.columns([3.0, 1.0])
            filtro_q = c5.text_input(
                "Buscar",
                placeholder="nº/código, comarca, vara, cliente, descrição, observações…",
                key="proc_list_q",
            )
            if c6.button(
                "Limpar filtros", use_container_width=True, key="proc_list_clear_btn"
            ):
                _clear_list_state()
                navigate(
                    "Processos", clear_qp=True, state={"processos_section": "Lista"}
                )
                return

    status_val = None if filtro_status == "(Todos)" else filtro_status
    papel_val = ATUACAO_UI_ALL.get(filtro_atuacao)
    categoria_val = None if filtro_categoria == "(Todas)" else filtro_categoria
    order_desc = ordem == "Mais recentes"

    version = _data_version(owner_user_id)
    rows = _cached_list_rows(
        owner_user_id,
        status_val,
        papel_val,
        categoria_val,
        (filtro_q or None),
        order_desc,
        version,
    )

    if not rows:
        st.info("Nenhum trabalho encontrado com os filtros atuais.")
        return

    total = len(rows)
    ativos = sum(1 for r in rows if (r.get("status", "") or "").lower() == "ativo")
    concl = sum(
        1 for r in rows if (r.get("status", "") or "").lower().startswith("concl")
    )
    susp = sum(1 for r in rows if (r.get("status", "") or "").lower() == "suspenso")

    k1, k2 = st.columns(2)
    with k1:
        card("Trabalhos", f"{total}", "nos filtros", tone="info")
    with k2:
        card(
            "Ativos",
            f"{ativos}",
            "em andamento",
            tone="success" if ativos else "neutral",
        )

    k3, k4 = st.columns(2)
    with k3:
        card("Concluídos", f"{concl}", "finalizados", tone="neutral")
    with k4:
        card("Suspensos", f"{susp}", "pausados", tone="warning" if susp else "neutral")

    if _is_mobile_hint():
        for r in rows[:50]:
            _render_processo_card_row(r)
        if len(rows) > 50:
            st.caption(
                f"Mostrando 50 de {len(rows)} (mobile). Use filtros para reduzir."
            )
        return

    df = pd.DataFrame(
        [
            {
                "ID": int(r["id"]),
                "Referência": r.get("numero_processo", ""),
                "Atuação": _atuacao_badge(r.get("papel")),
                "Categoria": r.get("categoria_servico", ""),
                "Status": _status_badge(r.get("status", "")),
                "Cliente": r.get("contratante", ""),
                "Descrição": r.get("tipo_acao", ""),
                "Comarca": r.get("comarca", ""),
                "Vara": r.get("vara", ""),
                "Pasta": r.get("pasta_local", ""),
            }
            for r in rows
        ]
    )

    with st.container(border=True):
        st.caption(f"Total: **{len(df)}**")
        st.dataframe(
            df[
                [
                    "Referência",
                    "Atuação",
                    "Categoria",
                    "Status",
                    "Cliente",
                    "Descrição",
                    "Comarca",
                    "Vara",
                    "Pasta",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            height=520,
        )

    with st.container(border=True):
        st.markdown("**Ações rápidas**")

        id_to_label = {int(r["id"]): r.get("numero_processo", "") for r in rows}
        ids = list(id_to_label.keys())
        default_id = st.session_state.get("proc_list_selected_id", ids[0])
        if default_id not in ids:
            default_id = ids[0]

        cA, cB, cC, cD, cE = st.columns(
            [2.2, 0.9, 0.9, 0.9, 1.1], vertical_alignment="center"
        )
        selected_id = cA.selectbox(
            "Selecionar trabalho",
            options=ids,
            format_func=lambda x: f"[{x}] {id_to_label.get(int(x), '')}",
            index=ids.index(default_id),
            key="proc_list_selected_id",
        )
        selected_ref = id_to_label.get(int(selected_id), "")

        # ✅ guarda comarca/vara do selecionado para UX nas telas seguintes
        selected_row = next(
            (r for r in rows if int(r.get("id", 0)) == int(selected_id)), None
        )
        st.session_state["pref_processo_comarca"] = (
            (selected_row.get("comarca") or "").strip() if selected_row else ""
        )
        st.session_state["pref_processo_vara"] = (
            (selected_row.get("vara") or "").strip() if selected_row else ""
        )

        if cB.button(
            "Editar",
            use_container_width=True,
            key="proc_list_action_edit",
            type="primary",
        ):
            _open_edit(int(selected_id))

        if cC.button("Prazos", use_container_width=True, key="proc_list_action_prazos"):
            st.session_state["pref_processo_id"] = int(selected_id)
            st.session_state["pref_processo_ref"] = selected_ref
            navigate("Prazos", state={"prazos_section": "Lista"})

        if cD.button("Agenda", use_container_width=True, key="proc_list_action_agenda"):
            st.session_state["pref_processo_id"] = int(selected_id)
            st.session_state["pref_processo_ref"] = selected_ref
            navigate("Agendamentos")

        if cE.button(
            "Financeiro", use_container_width=True, key="proc_list_action_fin"
        ):
            st.session_state["pref_processo_id"] = int(selected_id)
            st.session_state["pref_processo_ref"] = selected_ref
            navigate("Financeiro", state={"financeiro_section": "Lançamentos"})


# ==================================================
# EDITAR / EXCLUIR
# ==================================================
def _render_editar(owner_user_id: int) -> None:
    with st.container(border=True):
        st.markdown(
            "<div class='sec-title'>Editar / Excluir</div>", unsafe_allow_html=True
        )
        st.markdown(
            "<div class='sec-cap'>Selecione um trabalho e ajuste os campos necessários.</div>",
            unsafe_allow_html=True,
        )

        busca_editar = st.text_input(
            "Buscar (nº/código, cliente, descrição...)",
            placeholder="Ex.: 0001246, Barequeçaba, avaliação, ...",
            key="proc_edit_search",
        )

        with get_session() as s:
            processos_all = ProcessosService.list(
                s,
                owner_user_id=owner_user_id,
                status=None,
                papel=None,
                categoria_servico=None,
                q=(busca_editar or None),
                order_desc=True,
                limit=None,
            )

        if not processos_all:
            st.info("Nenhum trabalho encontrado.")
            return

        pre_selected_id = st.session_state.get("proc_edit_selected_id", None)

        id_to_label: dict[int, str] = {}
        for pr in processos_all:
            ref = pr.numero_processo
            cli = (pr.contratante or "").strip()
            atu = _atuacao_badge(pr.papel)
            cat = (pr.categoria_servico or "").strip()
            label = (
                f"{ref} — {atu}"
                + (f" — {cat}" if cat else "")
                + (f" — {cli}" if cli else "")
            )
            id_to_label[int(pr.id)] = label

        ids = list(id_to_label.keys())
        default_id = int(pre_selected_id) if pre_selected_id in ids else ids[0]

        selected_id = st.selectbox(
            "Selecione",
            options=ids,
            format_func=lambda x: f"[{x}] {id_to_label.get(int(x), '')}",
            index=ids.index(default_id),
            key="proc_edit_selected_id",
        )

        version = _data_version(owner_user_id)
        p = _cached_get_row(owner_user_id, int(selected_id), version)
        if not p:
            st.error("Trabalho não encontrado.")
            return

        papel_atual = _norm_tipo_trabalho(p.get("papel"))
        atuacao_atual_label = _atuacao_label_from_db(papel_atual)

    with st.container(border=True):
        pasta_key = f"proc_edit_pasta_{selected_id}"
        st.session_state.setdefault(pasta_key, p.get("pasta_local", "") or "")

        cA, cB, cC = st.columns([1.2, 1.6, 2.2], vertical_alignment="center")

        if cA.button("📁 Escolher pasta…", key=f"proc_edit_pick_folder_{selected_id}"):
            chosen = _pick_folder_dialog(initialdir=str(ROOT_TRABALHOS))
            if chosen:
                st.session_state[pasta_key] = chosen
                st.rerun()
            else:
                st.warning(
                    "Não foi possível abrir o Explorer (ou nenhuma pasta foi escolhida)."
                )

        confirm = cB.checkbox(
            "Confirmar exclusão", value=False, key=f"proc_del_confirm_{selected_id}"
        )
        if cC.button(
            "🗑️ Excluir definitivamente",
            key=f"proc_delete_direct_{selected_id}",
            disabled=not confirm,
        ):
            try:
                with get_session() as s:
                    ProcessosService.delete(s, owner_user_id, int(selected_id))
                bump_data_version(owner_user_id)
                st.success("Trabalho excluído.")
                st.session_state.pop("proc_edit_selected_id", None)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")

        st.caption("⚠️ Exclusão remove o registro do banco. Use com cuidado.")

    with st.form(f"form_trabalho_edit_{selected_id}"):
        c1, c2, c3 = st.columns(3)
        numero_e = c1.text_input(
            "Número / Código interno *",
            value=p.get("numero_processo", "") or "",
            key=f"proc_edit_numero_{selected_id}",
        )
        comarca_e = c2.text_input(
            "Comarca",
            value=p.get("comarca", "") or "",
            key=f"proc_edit_comarca_{selected_id}",
            help="Impacta cálculo de prazos (CPC/TJSP) e feriados municipais.",
        )
        vara_e = c3.text_input(
            "Vara", value=p.get("vara", "") or "", key=f"proc_edit_vara_{selected_id}"
        )

        c4, c5, c6 = st.columns(3)
        tipo_acao_e = c4.text_input(
            "Descrição / Tipo",
            value=p.get("tipo_acao", "") or "",
            key=f"proc_edit_tipo_acao_{selected_id}",
        )
        contratante_e = c5.text_input(
            "Contratante / Cliente",
            value=p.get("contratante", "") or "",
            key=f"proc_edit_contratante_{selected_id}",
        )
        atuacao_label_e = c6.selectbox(
            "Atuação",
            list(ATUACAO_UI.keys()),
            index=(
                list(ATUACAO_UI.keys()).index(atuacao_atual_label)
                if atuacao_atual_label in ATUACAO_UI
                else 1
            ),
            key=f"proc_edit_atuacao_{selected_id}",
        )
        papel_db_e = _atuacao_db_from_label(atuacao_label_e)

        c7, c8, c9 = st.columns(3)
        cat_atual = p.get("categoria_servico", "")
        categoria_e = c7.selectbox(
            "Categoria / Serviço",
            CATEGORIAS_UI,
            index=(CATEGORIAS_UI.index(cat_atual) if cat_atual in CATEGORIAS_UI else 0),
            key=f"proc_edit_categoria_{selected_id}",
        )

        status_atual = p.get("status", "Ativo") or "Ativo"
        status_e = c8.selectbox(
            "Status",
            list(STATUS_VALIDOS),
            index=(
                list(STATUS_VALIDOS).index(status_atual)
                if status_atual in STATUS_VALIDOS
                else 0
            ),
            key=f"proc_edit_status_{selected_id}",
        )

        # Aviso UX (não bloqueia): comarca é essencial p/ cálculo de prazos
        if (status_e == "Ativo") and not (comarca_e or "").strip():
            st.warning(
                "Comarca não informada. Isso pode afetar o cálculo de prazos (CPC/TJSP) e feriados municipais.",
                icon="⚠️",
            )

        pasta_e = c9.text_input("Pasta local", key=pasta_key)

        obs_e = st.text_area(
            "Observações",
            value=p.get("observacoes", "") or "",
            key=f"proc_edit_obs_{selected_id}",
            height=120,
        )

        atualizar = st.form_submit_button("Salvar alterações", type="primary")

    if atualizar:
        if not (numero_e or "").strip():
            st.error("Número / Código interno não pode ficar vazio.")
        else:
            try:
                with get_session() as s:
                    ProcessosService.update(
                        s,
                        owner_user_id,
                        int(selected_id),
                        ProcessoUpdate(
                            numero_processo=(numero_e or "").strip(),
                            comarca=(comarca_e or "").strip(),
                            vara=(vara_e or "").strip(),
                            tipo_acao=(tipo_acao_e or "").strip(),
                            contratante=(contratante_e or "").strip(),
                            papel=papel_db_e,
                            status=status_e,
                            pasta_local=(pasta_e or "").strip(),
                            categoria_servico=categoria_e,
                            observacoes=(obs_e or "").strip(),
                        ),
                    )
                bump_data_version(owner_user_id)

                # ✅ mantém contexto atualizado para telas seguintes (UX)
                st.session_state["pref_processo_comarca"] = (comarca_e or "").strip()
                st.session_state["pref_processo_vara"] = (vara_e or "").strip()

                _toast("✅ Trabalho atualizado")
                st.success("Trabalho atualizado.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")
