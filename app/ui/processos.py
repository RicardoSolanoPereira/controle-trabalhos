# app/ui/processos.py
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.db.connection import get_session
from app.services.processos_service import (
    ProcessosService,
    ProcessoCreate,
    ProcessoUpdate,
)
from app.ui.theme import card
from app.ui.page_header import page_header, HeaderAction
from app.ui_state import navigate, get_qp_str, bump_data_version
from app.ui.layout import section, grid, spacer, is_mobile


# ==================================================
# CONSTANTS / UI MAPS
# ==================================================
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

# menu keys atuais do seu main.py (mantidos)
MENU_TRABALHOS_KEY = "Processos"  # label do menu/aba
MENU_PRAZOS_KEY = "Prazos"
MENU_AGENDA_KEY = (
    "Agenda"  # ⚠️ se no main.py estiver "Agendamentos", troque aqui para igual
)
MENU_FIN_KEY = "Financeiro"


# ==================================================
# STATE KEYS
# ==================================================
K_SECTION = "processos_section"  # "Lista" | "Cadastrar" | "Editar"
K_SELECTED_ID = "processo_selected_id"

K_FILTER_STATUS = "processos_filter_status"
K_FILTER_ATUACAO = "processos_filter_atuacao"
K_FILTER_CATEGORIA = "processos_filter_categoria"
K_FILTER_Q = "processos_filter_q"
K_FILTER_ORDEM = "processos_filter_ordem"

# Widget key do selector de seção (segmented/radio)
K_SECTION_SELECTOR = "processos_section_selector"


# ==================================================
# VERSION
# ==================================================
def _data_version(owner_user_id: int) -> int:
    return int(st.session_state.get(f"data_version_{owner_user_id}", 0))


# ==================================================
# MOBILE MODE
# ==================================================
def _use_cards() -> bool:
    return bool(st.session_state.get("ui_mobile_cards", True) or is_mobile())


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
        "trabalho particular",
        "avaliação particular",
        "avaliacao",
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
    return status or "—"


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
    Seletor de pasta nativo (tkinter).
    Funciona em localhost/Windows. Em servidor headless, falha e retorna None.
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


# ==================================================
# SYNC: dashboard + query params + compat antigo
# ==================================================
def _sync_from_dashboard_and_qp() -> None:
    # compat com versões antigas do seu app
    if "proc_active_tab" in st.session_state and K_SECTION not in st.session_state:
        st.session_state[K_SECTION] = st.session_state.get("proc_active_tab", "Lista")

    st.session_state.setdefault(K_SECTION, "Lista")
    st.session_state.setdefault(K_FILTER_ORDEM, "Mais recentes")
    st.session_state.setdefault(K_FILTER_STATUS, "(Todos)")
    st.session_state.setdefault(K_FILTER_ATUACAO, "(Todas)")
    st.session_state.setdefault(K_FILTER_CATEGORIA, "(Todas)")
    st.session_state.setdefault(K_FILTER_Q, "")

    # vindo do dashboard
    sec = st.session_state.pop("processos_section", None)
    if sec in ("Lista", "Cadastrar", "Editar"):
        st.session_state[K_SECTION] = sec

    # query params
    qp_status = get_qp_str("status", "")
    qp_atuacao = get_qp_str("atuacao", "")
    qp_categoria = get_qp_str("categoria", "")
    qp_q = get_qp_str("q", "")

    if qp_status:
        status_options = ["(Todos)"] + list(STATUS_VALIDOS)
        st.session_state[K_FILTER_STATUS] = (
            qp_status if qp_status in status_options else "(Todos)"
        )

    if qp_atuacao:
        atuacao_options = list(ATUACAO_UI_ALL.keys())
        st.session_state[K_FILTER_ATUACAO] = (
            qp_atuacao if qp_atuacao in atuacao_options else "(Todas)"
        )

    if qp_categoria:
        categoria_options = ["(Todas)"] + CATEGORIAS_UI
        st.session_state[K_FILTER_CATEGORIA] = (
            qp_categoria if qp_categoria in categoria_options else "(Todas)"
        )

    if qp_q:
        st.session_state[K_FILTER_Q] = qp_q
        st.session_state[K_SECTION] = "Lista"


# ==================================================
# CALLBACKS (IMPORTANTÍSSIMO)
# - callbacks rodam antes da renderização do widget na próxima execução
# - evita "cannot be modified after widget is instantiated"
# ==================================================
def _set_section(sec: str) -> None:
    if sec in ("Lista", "Cadastrar", "Editar"):
        st.session_state[K_SECTION] = sec
        # setar selector aqui é seguro porque é callback
        st.session_state[K_SECTION_SELECTOR] = sec


def _open_edit(processo_id: int) -> None:
    st.session_state[K_SELECTED_ID] = int(processo_id)
    _set_section("Editar")


def _go_prazos(pid: int, ref: str, comarca: str, vara: str) -> None:
    st.session_state["pref_processo_id"] = int(pid)
    st.session_state["pref_processo_ref"] = ref
    st.session_state["pref_processo_comarca"] = comarca
    st.session_state["pref_processo_vara"] = vara
    navigate(MENU_PRAZOS_KEY, state={"prazos_section": "Lista"})


def _go_agenda(pid: int, ref: str, comarca: str, vara: str) -> None:
    st.session_state["pref_processo_id"] = int(pid)
    st.session_state["pref_processo_ref"] = ref
    st.session_state["pref_processo_comarca"] = comarca
    st.session_state["pref_processo_vara"] = vara
    navigate(MENU_AGENDA_KEY)


def _go_fin(pid: int, ref: str, comarca: str, vara: str) -> None:
    st.session_state["pref_processo_id"] = int(pid)
    st.session_state["pref_processo_ref"] = ref
    st.session_state["pref_processo_comarca"] = comarca
    st.session_state["pref_processo_vara"] = vara
    navigate(MENU_FIN_KEY, state={"financeiro_section": "Lançamentos"})


def _clear_filters() -> None:
    for k in (
        K_FILTER_STATUS,
        K_FILTER_ATUACAO,
        K_FILTER_CATEGORIA,
        K_FILTER_Q,
        K_FILTER_ORDEM,
    ):
        st.session_state.pop(k, None)
    st.session_state.pop(K_SELECTED_ID, None)
    _set_section("Lista")


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
# MOBILE CARD
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

    comarca_chip = (
        f"<span class='sp-chip'>🏛️ {comarca}</span>"
        if comarca
        else "<span class='sp-chip'>⚠️ Sem comarca</span>"
    )

    st.markdown(
        f"""
        <div class="sp-surface" style="margin-bottom:12px;">
          <div style="font-weight:900; font-size:1.02rem;">{ref}</div>
          <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
            <span class="sp-chip">{atu}</span>
            <span class="sp-chip">{status}</span>
            {f"<span class='sp-chip'>🏷️ {cat}</span>" if cat else ""}
            {comarca_chip}
          </div>
          <div style="margin-top:8px; color: rgba(15,23,42,0.75); line-height:1.35;">
            {f"<b>Cliente:</b> {cli}<br/>" if cli else ""}
            {f"<b>Descrição:</b> {desc}<br/>" if desc else ""}
            {f"<b>Comarca:</b> {comarca} • <b>Vara:</b> {vara}<br/>" if (comarca or vara) else ""}
            {f"<b>Pasta:</b> {pasta}" if pasta else ""}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b = st.columns(2)
    a.button(
        "Editar",
        key=f"m_edit_{pid}",
        use_container_width=True,
        type="primary",
        on_click=_open_edit,
        args=(pid,),
    )

    b.button(
        "Prazos",
        key=f"m_pz_{pid}",
        use_container_width=True,
        on_click=_go_prazos,
        args=(pid, ref, comarca, vara),
    )

    c, d = st.columns(2)
    c.button(
        "Agenda",
        key=f"m_ag_{pid}",
        use_container_width=True,
        on_click=_go_agenda,
        args=(pid, ref, comarca, vara),
    )

    d.button(
        "Financeiro",
        key=f"m_fin_{pid}",
        use_container_width=True,
        on_click=_go_fin,
        args=(pid, ref, comarca, vara),
    )

    spacer(0.2)


# ==================================================
# ENTRY
# ==================================================
def render(owner_user_id: int):
    _sync_from_dashboard_and_qp()

    actions = [
        HeaderAction("➕ Novo", key="tb_new", type="primary"),
        HeaderAction("🧹 Limpar", key="tb_clear", type="secondary"),
        HeaderAction("↻ Recarregar", key="tb_reload", type="secondary"),
    ]
    page_header(
        "Trabalhos",
        "Cadastro e gestão de atividades técnicas (judicial e particular).",
        actions=actions,
        divider=True,
    )

    if st.session_state.get("tb_reload"):
        st.rerun()

    if st.session_state.get("tb_clear"):
        _clear_filters()
        navigate(
            MENU_TRABALHOS_KEY, clear_qp=True, state={"processos_section": "Lista"}
        )
        return

    if st.session_state.get("tb_new"):
        _set_section("Cadastrar")

    options = ["Lista", "Cadastrar", "Editar"]

    # ✅ IMPORTANTÍSSIMO: evitar warning default + session_state
    label_vis = "collapsed" if _use_cards() else "visible"

    if hasattr(st, "segmented_control"):
        if K_SECTION_SELECTOR in st.session_state:
            sec = st.segmented_control(
                "Seção",
                options=options,
                key=K_SECTION_SELECTOR,
                label_visibility=label_vis,
            )
        else:
            sec = st.segmented_control(
                "Seção",
                options=options,
                default=st.session_state.get(K_SECTION, "Lista"),
                key=K_SECTION_SELECTOR,
                label_visibility=label_vis,
            )
    else:
        if K_SECTION_SELECTOR in st.session_state:
            sec = st.radio(
                "Seção",
                options=options,
                horizontal=True,
                key=K_SECTION_SELECTOR,
                label_visibility=label_vis,
            )
        else:
            sec = st.radio(
                "Seção",
                options=options,
                index=options.index(st.session_state.get(K_SECTION, "Lista")),
                horizontal=True,
                key=K_SECTION_SELECTOR,
                label_visibility=label_vis,
            )

    # Source of truth: selector -> K_SECTION
    st.session_state[K_SECTION] = sec

    if sec == "Cadastrar":
        _render_cadastrar(owner_user_id)
    elif sec == "Editar":
        _render_editar(owner_user_id)
    else:
        _render_lista(owner_user_id)


# ==================================================
# CADASTRAR
# ==================================================
def _render_cadastrar(owner_user_id: int) -> None:
    if st.session_state.get("proc_last_created_id"):
        last_id = int(st.session_state["proc_last_created_id"])
        last_ref = st.session_state.get("proc_last_created_ref", "")

        with section(
            "✅ Cadastrado",
            subtitle="Próximo passo: operar este trabalho.",
            divider=False,
        ):
            a, b, c = grid(3, columns_mobile=1)
            with a:
                st.button(
                    "Editar",
                    use_container_width=True,
                    type="primary",
                    key="proc_post_edit",
                    on_click=_open_edit,
                    args=(last_id,),
                )
            with b:
                st.button(
                    "Prazos",
                    use_container_width=True,
                    key="proc_post_prazos",
                    on_click=_go_prazos,
                    args=(last_id, last_ref, "", ""),
                )
            with c:
                if st.button(
                    "Cadastrar outro", use_container_width=True, key="proc_post_new"
                ):
                    st.session_state.pop("proc_last_created_id", None)
                    st.session_state.pop("proc_last_created_ref", None)
                    st.rerun()

    with section(
        "Novo trabalho",
        subtitle="Cadastre o essencial primeiro; complete depois.",
        divider=False,
    ):
        st.session_state.setdefault("proc_create_pasta", "")

        pick_col, tip_col = grid(2, columns_mobile=1)
        with pick_col:
            if st.button(
                "📁 Escolher pasta…",
                use_container_width=True,
                key="proc_create_pick_folder",
            ):
                chosen = _pick_folder_dialog(initialdir=str(ROOT_TRABALHOS))
                if chosen:
                    st.session_state["proc_create_pasta"] = chosen
                    st.rerun()
                else:
                    st.info(
                        "Seleção de pasta indisponível (servidor/headless) ou cancelada."
                    )
        with tip_col:
            st.caption(
                "Dica: funciona em localhost/Windows. Em servidor, use o campo ‘Pasta local’."
            )

        with st.form("form_trabalho_create", clear_on_submit=False):
            c1, c2, c3 = grid(3, columns_mobile=1)
            with c1:
                numero = st.text_input(
                    "Número / Código *",
                    placeholder="0000000-00.0000.0.00.0000 ou AP-2026-001",
                    key="proc_create_numero",
                )
            with c2:
                atuacao_label = st.selectbox(
                    "Atuação *",
                    list(ATUACAO_UI.keys()),
                    index=1,
                    key="proc_create_atuacao",
                )
            with c3:
                status = st.selectbox(
                    "Status", list(STATUS_VALIDOS), index=0, key="proc_create_status"
                )

            c4, c5 = grid(2, columns_mobile=1)
            with c4:
                categoria = st.selectbox(
                    "Categoria / Serviço",
                    CATEGORIAS_UI,
                    index=0,
                    key="proc_create_categoria",
                )
            with c5:
                tipo_acao = st.text_input(
                    "Descrição / Tipo",
                    placeholder="Ex.: Ação possessória / Avaliação / Vistoria...",
                    key="proc_create_tipo_acao",
                )

            c6, c7, c8 = grid(3, columns_mobile=1)
            with c6:
                comarca = st.text_input("Comarca", key="proc_create_comarca")
            with c7:
                vara = st.text_input("Vara", key="proc_create_vara")
            with c8:
                contratante = st.text_input(
                    "Contratante / Cliente", key="proc_create_contratante"
                )

            pasta = st.text_input(
                "Pasta local (opcional)",
                placeholder=str(ROOT_TRABALHOS / "AP-2026-001"),
                key="proc_create_pasta",
            )

            if st.form_submit_button("Sugerir pasta (auto)", type="secondary"):
                st.session_state["proc_create_pasta"] = _guess_pasta_local(
                    st.session_state.get("proc_create_numero", "")
                )
                st.rerun()

            obs = st.text_area("Observações", key="proc_create_obs", height=120)
            submitted = st.form_submit_button("Salvar", type="primary")

        if submitted:
            if not (numero or "").strip():
                st.error("Informe o Número / Código.")
                return

            papel_db = _atuacao_db_from_label(atuacao_label)
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
                _toast("✅ Trabalho cadastrado")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")


# ==================================================
# LISTA
# ==================================================
def _render_lista(owner_user_id: int) -> None:
    with section("Lista", subtitle="Filtre e abra rapidamente.", divider=False):
        if _use_cards():
            status_options = ["(Todos)"] + list(STATUS_VALIDOS)
            st.selectbox("Status", status_options, key=K_FILTER_STATUS)

            atuacao_options = list(ATUACAO_UI_ALL.keys())
            st.selectbox("Atuação", atuacao_options, key=K_FILTER_ATUACAO)

            categoria_options = ["(Todas)"] + CATEGORIAS_UI
            st.selectbox("Categoria", categoria_options, key=K_FILTER_CATEGORIA)

            st.selectbox(
                "Ordenar", ["Mais recentes", "Mais antigos"], key=K_FILTER_ORDEM
            )

            st.text_input(
                "Buscar",
                placeholder="nº/código, comarca, vara, cliente, descrição, observações…",
                key=K_FILTER_Q,
            )
        else:
            c1, c2, c3, c4 = grid(4, columns_mobile=1)
            status_options = ["(Todos)"] + list(STATUS_VALIDOS)
            with c1:
                st.selectbox("Status", status_options, key=K_FILTER_STATUS)

            atuacao_options = list(ATUACAO_UI_ALL.keys())
            with c2:
                st.selectbox("Atuação", atuacao_options, key=K_FILTER_ATUACAO)

            categoria_options = ["(Todas)"] + CATEGORIAS_UI
            with c3:
                st.selectbox("Categoria", categoria_options, key=K_FILTER_CATEGORIA)

            with c4:
                st.selectbox(
                    "Ordenar", ["Mais recentes", "Mais antigos"], key=K_FILTER_ORDEM
                )

            st.text_input(
                "Buscar",
                placeholder="nº/código, comarca, vara, cliente, descrição, observações…",
                key=K_FILTER_Q,
            )

        spacer(0.15)

        a1, a2, a3 = grid(3, columns_mobile=1)
        with a1:
            st.button(
                "➕ Novo trabalho",
                use_container_width=True,
                type="primary",
                key="proc_list_new",
                on_click=_set_section,
                args=("Cadastrar",),
            )
        with a2:
            st.button(
                "🧹 Limpar filtros",
                use_container_width=True,
                on_click=_clear_filters,
                key="proc_list_clear",
            )
        with a3:
            st.button(
                "↻ Recarregar",
                use_container_width=True,
                key="proc_list_reload",
                on_click=st.rerun,
            )

    filtro_status = st.session_state.get(K_FILTER_STATUS, "(Todos)")
    filtro_atuacao = st.session_state.get(K_FILTER_ATUACAO, "(Todas)")
    filtro_categoria = st.session_state.get(K_FILTER_CATEGORIA, "(Todas)")
    ordem = st.session_state.get(K_FILTER_ORDEM, "Mais recentes")
    filtro_q = st.session_state.get(K_FILTER_Q, "")

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

    k1, k2, k3, k4 = grid(4, columns_mobile=2)
    with k1:
        card("Trabalhos", f"{total}", "nos filtros", tone="info")
    with k2:
        card(
            "Ativos",
            f"{ativos}",
            "em andamento",
            tone="success" if ativos else "neutral",
        )
    with k3:
        card("Concluídos", f"{concl}", "finalizados", tone="neutral")
    with k4:
        card("Suspensos", f"{susp}", "pausados", tone="warning" if susp else "neutral")

    spacer(0.2)

    if _use_cards():
        limit = 50
        for r in rows[:limit]:
            _render_processo_card_row(r)
        if len(rows) > limit:
            st.caption(f"Mostrando {limit} de {len(rows)}. Use filtros para reduzir.")
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

    with section("Tabela", subtitle=f"Total: {len(df)}", divider=False):
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

    with section(
        "Ações rápidas", subtitle="Selecione um trabalho para operar.", divider=False
    ):
        id_to_label = {int(r["id"]): r.get("numero_processo", "") for r in rows}
        ids = list(id_to_label.keys())

        default_id = st.session_state.get(K_SELECTED_ID, ids[0])
        if default_id not in ids:
            default_id = ids[0]

        cA, cB, cC, cD, cE = grid(5, columns_mobile=1)
        with cA:
            selected_id = st.selectbox(
                "Selecionar",
                options=ids,
                format_func=lambda x: f"[{x}] {id_to_label.get(int(x), '')}",
                index=ids.index(default_id),
                key=K_SELECTED_ID,
            )

        selected_row = next(
            (r for r in rows if int(r.get("id", 0)) == int(selected_id)), None
        )
        selected_ref = id_to_label.get(int(selected_id), "")

        comarca = ((selected_row or {}).get("comarca") or "").strip()
        vara = ((selected_row or {}).get("vara") or "").strip()

        with cB:
            st.button(
                "Editar",
                use_container_width=True,
                type="primary",
                key="proc_act_edit",
                on_click=_open_edit,
                args=(int(selected_id),),
            )
        with cC:
            st.button(
                "Prazos",
                use_container_width=True,
                key="proc_act_pz",
                on_click=_go_prazos,
                args=(int(selected_id), selected_ref, comarca, vara),
            )
        with cD:
            st.button(
                "Agenda",
                use_container_width=True,
                key="proc_act_ag",
                on_click=_go_agenda,
                args=(int(selected_id), selected_ref, comarca, vara),
            )
        with cE:
            st.button(
                "Financeiro",
                use_container_width=True,
                key="proc_act_fin",
                on_click=_go_fin,
                args=(int(selected_id), selected_ref, comarca, vara),
            )


# ==================================================
# EDITAR
# ==================================================
def _render_editar(owner_user_id: int) -> None:
    with section(
        "Editar", subtitle="Busque e edite o trabalho selecionado.", divider=False
    ):
        busca = st.text_input(
            "Buscar",
            placeholder="nº/código, cliente, descrição...",
            key="proc_edit_search",
        )

        with get_session() as s:
            processos_all = ProcessosService.list(
                s,
                owner_user_id=owner_user_id,
                status=None,
                papel=None,
                categoria_servico=None,
                q=(busca or None),
                order_desc=True,
                limit=None,
            )

        if not processos_all:
            st.info("Nenhum trabalho encontrado.")
            return

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
        pre = st.session_state.get(K_SELECTED_ID, ids[0])
        if pre not in ids:
            pre = ids[0]

        selected_id = st.selectbox(
            "Selecione",
            options=ids,
            format_func=lambda x: f"[{x}] {id_to_label.get(int(x), '')}",
            index=ids.index(pre),
            key=K_SELECTED_ID,
        )

    version = _data_version(owner_user_id)
    p = _cached_get_row(owner_user_id, int(selected_id), version)
    if not p:
        st.error("Trabalho não encontrado.")
        return

    papel_atual = _norm_tipo_trabalho(p.get("papel"))
    atuacao_atual_label = _atuacao_label_from_db(papel_atual)

    with section("Ações", subtitle="Pasta / exclusão", divider=False):
        pasta_key = f"proc_edit_pasta_{selected_id}"
        st.session_state.setdefault(pasta_key, p.get("pasta_local", "") or "")

        a, b, c = grid(3, columns_mobile=1)
        with a:
            if st.button(
                "📁 Escolher pasta…",
                use_container_width=True,
                key=f"proc_edit_pick_folder_{selected_id}",
            ):
                chosen = _pick_folder_dialog(initialdir=str(ROOT_TRABALHOS))
                if chosen:
                    st.session_state[pasta_key] = chosen
                    st.rerun()
        with b:
            confirm = st.checkbox(
                "Confirmar exclusão", value=False, key=f"proc_del_confirm_{selected_id}"
            )
        with c:
            if st.button(
                "🗑️ Excluir",
                use_container_width=True,
                disabled=not bool(confirm),
                key=f"proc_delete_{selected_id}",
            ):
                try:
                    with get_session() as s:
                        ProcessosService.delete(s, owner_user_id, int(selected_id))
                    bump_data_version(owner_user_id)
                    st.session_state.pop(K_SELECTED_ID, None)
                    _toast("🗑️ Trabalho excluído")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

        st.caption("⚠️ Exclusão remove o registro do banco. Use com cuidado.")

    with st.form(f"form_trabalho_edit_{selected_id}"):
        c1, c2, c3 = grid(3, columns_mobile=1)
        with c1:
            numero_e = st.text_input(
                "Número / Código *",
                value=p.get("numero_processo", "") or "",
                key=f"proc_edit_num_{selected_id}",
            )
        with c2:
            comarca_e = st.text_input(
                "Comarca",
                value=p.get("comarca", "") or "",
                key=f"proc_edit_comarca_{selected_id}",
            )
        with c3:
            vara_e = st.text_input(
                "Vara",
                value=p.get("vara", "") or "",
                key=f"proc_edit_vara_{selected_id}",
            )

        c4, c5, c6 = grid(3, columns_mobile=1)
        with c4:
            tipo_acao_e = st.text_input(
                "Descrição / Tipo",
                value=p.get("tipo_acao", "") or "",
                key=f"proc_edit_tipo_{selected_id}",
            )
        with c5:
            contratante_e = st.text_input(
                "Contratante / Cliente",
                value=p.get("contratante", "") or "",
                key=f"proc_edit_cli_{selected_id}",
            )
        with c6:
            atuacao_label_e = st.selectbox(
                "Atuação",
                list(ATUACAO_UI.keys()),
                index=(
                    list(ATUACAO_UI.keys()).index(atuacao_atual_label)
                    if atuacao_atual_label in ATUACAO_UI
                    else 1
                ),
                key=f"proc_edit_atu_{selected_id}",
            )
        papel_db_e = _atuacao_db_from_label(atuacao_label_e)

        c7, c8, c9 = grid(3, columns_mobile=1)
        with c7:
            cat_atual = p.get("categoria_servico", "")
            categoria_e = st.selectbox(
                "Categoria / Serviço",
                CATEGORIAS_UI,
                index=(
                    CATEGORIAS_UI.index(cat_atual) if cat_atual in CATEGORIAS_UI else 0
                ),
                key=f"proc_edit_cat_{selected_id}",
            )
        with c8:
            status_atual = p.get("status", "Ativo") or "Ativo"
            status_e = st.selectbox(
                "Status",
                list(STATUS_VALIDOS),
                index=(
                    list(STATUS_VALIDOS).index(status_atual)
                    if status_atual in STATUS_VALIDOS
                    else 0
                ),
                key=f"proc_edit_status_{selected_id}",
            )
        with c9:
            pasta_e = st.text_input("Pasta local", key=pasta_key)

        obs_e = st.text_area(
            "Observações",
            value=p.get("observacoes", "") or "",
            key=f"proc_edit_obs_{selected_id}",
            height=120,
        )

        atualizar = st.form_submit_button("Salvar alterações", type="primary")

    if atualizar:
        if not (numero_e or "").strip():
            st.error("Número / Código não pode ficar vazio.")
            return

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
            _toast("✅ Trabalho atualizado")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao atualizar: {e}")
