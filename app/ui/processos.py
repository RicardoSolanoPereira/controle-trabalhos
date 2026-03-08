from __future__ import annotations

import html
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from db.connection import get_session
from services.processos_service import (
    ProcessosService,
    ProcessoCreate,
    ProcessoUpdate,
)
from ui.theme import card
from ui.page_header import page_header, HeaderAction
from ui_state import navigate, get_qp_str, bump_data_version
from ui.layout import section, grid, spacer, is_mobile


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

MENU_TRABALHOS_KEY = "Processos"
MENU_PRAZOS_KEY = "Prazos"
MENU_AGENDA_KEY = "Agenda"
MENU_FIN_KEY = "Financeiro"


# ==================================================
# STATE KEYS
# ==================================================
K_SECTION = "processos_section"
K_SELECTED_ID = "processo_selected_id"

K_FILTER_STATUS = "processos_filter_status"
K_FILTER_ATUACAO = "processos_filter_atuacao"
K_FILTER_CATEGORIA = "processos_filter_categoria"
K_FILTER_Q = "processos_filter_q"
K_FILTER_ORDEM = "processos_filter_ordem"
K_FILTER_SOMENTE_COM_PASTA = "processos_filter_somente_com_pasta"

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


def _status_tone(status: str | None) -> str:
    s = (status or "").strip().lower()
    if s == "ativo":
        return "success"
    if s in ("concluído", "concluido"):
        return "neutral"
    if s == "suspenso":
        return "warning"
    return "info"


def _atuacao_badge(db_val: str | None) -> str:
    v = _norm_tipo_trabalho(db_val)
    if v == "Perito Judicial":
        return "⚖️ Perícia (Juízo)"
    if v == "Assistente Técnico":
        return "🛠️ Assistência Técnica"
    if v == "Trabalho Particular":
        return "🏷️ Particular"
    return v


def _strip_html(text: str | None) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"</div\s*>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _compact_text(v: str | None, max_len: int = 120) -> str:
    txt = _strip_html(v)
    if len(txt) <= max_len:
        return txt
    return txt[: max_len - 1].rstrip() + "…"


# ==================================================
# UX HELPERS
# ==================================================
def _guess_pasta_local(numero: str) -> str:
    n = (numero or "").strip()
    if not n:
        return ""
    safe = re.sub(r"[\\/]+", "-", n)
    safe = re.sub(r'[:*?"<>|]+', "", safe)
    safe = safe.strip()
    return rf"{ROOT_TRABALHOS}\{safe}"


def _toast(msg: str) -> None:
    try:
        st.toast(msg)  # type: ignore[attr-defined]
    except Exception:
        pass


def _pick_folder_dialog(initialdir: str | None = None) -> str | None:
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


def _open_folder(path_str: str | None) -> tuple[bool, str]:
    path = (path_str or "").strip()
    if not path:
        return False, "Pasta não informada."

    if not os.path.exists(path):
        return False, "Pasta não encontrada no caminho informado."

    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
        return True, "Pasta aberta."
    except Exception as e:
        return False, f"Não foi possível abrir a pasta: {e}"


def _copy_to_state(value: str, key: str) -> None:
    st.session_state[key] = value


def _summarize_filters() -> list[str]:
    chips: list[str] = []

    status = st.session_state.get(K_FILTER_STATUS, "(Todos)")
    atuacao = st.session_state.get(K_FILTER_ATUACAO, "(Todas)")
    categoria = st.session_state.get(K_FILTER_CATEGORIA, "(Todas)")
    q = (st.session_state.get(K_FILTER_Q, "") or "").strip()
    ordem = st.session_state.get(K_FILTER_ORDEM, "Mais recentes")
    so_pasta = bool(st.session_state.get(K_FILTER_SOMENTE_COM_PASTA, False))

    if status != "(Todos)":
        chips.append(f"Status: {status}")
    if atuacao != "(Todas)":
        chips.append(f"Atuação: {atuacao}")
    if categoria != "(Todas)":
        chips.append(f"Categoria: {categoria}")
    if q:
        chips.append(f"Busca: {q}")
    if ordem != "Mais recentes":
        chips.append(f"Ordem: {ordem}")
    if so_pasta:
        chips.append("Somente com pasta")

    return chips


# ==================================================
# SYNC
# ==================================================
def _sync_from_dashboard_and_qp() -> None:
    if "proc_active_tab" in st.session_state and K_SECTION not in st.session_state:
        st.session_state[K_SECTION] = st.session_state.get("proc_active_tab", "Lista")

    st.session_state.setdefault(K_SECTION, "Lista")
    st.session_state.setdefault(K_FILTER_ORDEM, "Mais recentes")
    st.session_state.setdefault(K_FILTER_STATUS, "(Todos)")
    st.session_state.setdefault(K_FILTER_ATUACAO, "(Todas)")
    st.session_state.setdefault(K_FILTER_CATEGORIA, "(Todas)")
    st.session_state.setdefault(K_FILTER_Q, "")
    st.session_state.setdefault(K_FILTER_SOMENTE_COM_PASTA, False)

    sec = st.session_state.pop("processos_section", None)
    if sec in ("Lista", "Cadastrar", "Editar"):
        st.session_state[K_SECTION] = sec

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
# CALLBACKS
# ==================================================
def _set_section(sec: str) -> None:
    if sec in ("Lista", "Cadastrar", "Editar"):
        st.session_state[K_SECTION] = sec
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
        K_FILTER_SOMENTE_COM_PASTA,
    ):
        st.session_state.pop(k, None)
    st.session_state.pop(K_SELECTED_ID, None)
    _set_section("Lista")


def _duplicate_processo(owner_user_id: int, processo_id: int) -> None:
    try:
        with get_session() as s:
            created = ProcessosService.duplicate(s, owner_user_id, processo_id)
        bump_data_version(owner_user_id)
        st.session_state["proc_last_created_id"] = int(getattr(created, "id", 0) or 0)
        st.session_state["proc_last_created_ref"] = (
            getattr(created, "numero_processo", "") or ""
        )
        _toast("📄 Trabalho duplicado")
        _set_section("Editar")
        st.session_state[K_SELECTED_ID] = int(getattr(created, "id", 0) or 0)
    except Exception as e:
        st.error(f"Erro ao duplicar: {e}")


# ==================================================
# CACHE
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


@st.cache_data(show_spinner=False, ttl=45)
def _cached_stats(owner_user_id: int, version: int) -> dict[str, int]:
    with get_session() as s:
        return ProcessosService.stats(s, owner_user_id)


# ==================================================
# UI FRAGMENTS
# ==================================================
def _render_filter_summary() -> None:
    chips = _summarize_filters()
    if not chips:
        st.caption("Visualização geral sem filtros específicos.")
        return

    txt = "  •  ".join(chips)
    st.caption(f"Filtros aplicados: {txt}")


def _render_empty_state() -> None:
    st.info("Nenhum trabalho encontrado com os filtros atuais.")
    a, b = st.columns(2)
    with a:
        st.button(
            "➕ Cadastrar novo trabalho",
            use_container_width=True,
            type="primary",
            key="proc_empty_new",
            on_click=_set_section,
            args=("Cadastrar",),
        )
    with b:
        st.button(
            "🧹 Limpar filtros",
            use_container_width=True,
            key="proc_empty_clear",
            on_click=_clear_filters,
        )


# ==================================================
# CARD
# ==================================================
def _render_processo_card_row(owner_user_id: int, r: dict) -> None:
    pid = int(r.get("id") or 0)
    ref = _compact_text(r.get("numero_processo"), 80)

    atu = _atuacao_badge(r.get("papel"))
    status = _status_badge(r.get("status", ""))
    cat = _compact_text(r.get("categoria_servico"), 40)
    cli = _compact_text(r.get("contratante"), 80)
    desc = _compact_text(r.get("tipo_acao"), 180)
    comarca = _compact_text(r.get("comarca"), 40)
    vara = _compact_text(r.get("vara"), 40)
    pasta = _strip_html(r.get("pasta_local"))
    obs = _compact_text(r.get("observacoes"), 180)

    meta_line = " • ".join([x for x in [cli, comarca, vara] if x])

    st.markdown(
        f"""
        <div class="sp-surface" style="margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start; flex-wrap:wrap;">
            <div style="min-width:0;">
              <div style="font-weight:900; font-size:1.03rem; line-height:1.2;">{ref or "Sem referência"}</div>
              <div style="margin-top:4px; color:rgba(15,23,42,0.68); font-size:0.92rem;">{meta_line or "Sem metadados principais"}</div>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end;">
              <span class="sp-chip">{status}</span>
              <span class="sp-chip">{atu}</span>
              {f"<span class='sp-chip'>🏷️ {cat}</span>" if cat else ""}
            </div>
          </div>

          {f"<div style='margin-top:10px; color: rgba(15,23,42,0.82);'><b>Descrição:</b> {desc}</div>" if desc else ""}
          {f"<div style='margin-top:6px; color: rgba(15,23,42,0.72);'><b>Obs.:</b> {obs}</div>" if obs else ""}
          {f"<div style='margin-top:6px; color: rgba(15,23,42,0.65);'><b>Pasta:</b> {_compact_text(pasta, 110)}</div>" if pasta else ""}
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

    with st.expander("Mais ações"):
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

        e, f = st.columns(2)
        e.button(
            "Duplicar",
            key=f"m_dup_{pid}",
            use_container_width=True,
            on_click=_duplicate_processo,
            args=(owner_user_id, pid),
        )

        if pasta:
            if f.button(
                "Abrir pasta",
                key=f"m_open_folder_{pid}",
                use_container_width=True,
            ):
                ok, msg = _open_folder(pasta)
                if ok:
                    _toast("📂 Pasta aberta")
                else:
                    st.warning(msg)
        else:
            f.button(
                "Sem pasta",
                key=f"m_no_folder_{pid}",
                use_container_width=True,
                disabled=True,
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
        "Cadastro e gestão de atividades técnicas, judiciais e particulares.",
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
            subtitle="Próximas ações recomendadas para o novo trabalho.",
            divider=False,
        ):
            a, b, c, d = grid(4, columns_mobile=1)
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
                st.button(
                    "Duplicar",
                    use_container_width=True,
                    key="proc_post_dup",
                    on_click=_duplicate_processo,
                    args=(owner_user_id, last_id),
                )
            with d:
                if st.button(
                    "Cadastrar outro", use_container_width=True, key="proc_post_new"
                ):
                    st.session_state.pop("proc_last_created_id", None)
                    st.session_state.pop("proc_last_created_ref", None)
                    st.rerun()

    with section(
        "Novo trabalho",
        subtitle="Cadastre o essencial primeiro. Os demais detalhes podem ser ajustados depois.",
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
                        "Seleção de pasta indisponível em servidor/headless ou operação cancelada."
                    )
        with tip_col:
            st.caption(
                "Dica: em localhost/Windows você pode selecionar a pasta local diretamente."
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
                    "Status",
                    list(STATUS_VALIDOS),
                    index=0,
                    key="proc_create_status",
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
                    "Contratante / Cliente",
                    key="proc_create_contratante",
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
    version = _data_version(owner_user_id)
    stats = _cached_stats(owner_user_id, version)

    with section(
        "Lista", subtitle="Filtre, localize e opere rapidamente.", divider=False
    ):
        cta1, cta2, cta3 = grid(3, columns_mobile=1)
        with cta1:
            st.button(
                "➕ Novo trabalho",
                use_container_width=True,
                type="primary",
                key="proc_list_new",
                on_click=_set_section,
                args=("Cadastrar",),
            )
        with cta2:
            st.button(
                "🧹 Limpar filtros",
                use_container_width=True,
                on_click=_clear_filters,
                key="proc_list_clear",
            )
        with cta3:
            st.button(
                "↻ Recarregar",
                use_container_width=True,
                key="proc_list_reload",
                on_click=st.rerun,
            )

        spacer(0.10)

        k1, k2, k3, k4 = grid(4, columns_mobile=2)
        with k1:
            card("Total", f"{stats.get('total', 0)}", "todos os trabalhos", tone="info")
        with k2:
            card("Ativos", f"{stats.get('ativos', 0)}", "em andamento", tone="success")
        with k3:
            card(
                "Concluídos",
                f"{stats.get('concluidos', 0)}",
                "finalizados",
                tone="neutral",
            )
        with k4:
            card(
                "Suspensos", f"{stats.get('suspensos', 0)}", "pausados", tone="warning"
            )

        spacer(0.10)

        status_options = ["(Todos)"] + list(STATUS_VALIDOS)
        atuacao_options = list(ATUACAO_UI_ALL.keys())
        categoria_options = ["(Todas)"] + CATEGORIAS_UI

        c1, c2, c3, c4 = grid(4, columns_mobile=1)
        with c1:
            st.selectbox("Status", status_options, key=K_FILTER_STATUS)
        with c2:
            st.selectbox("Atuação", atuacao_options, key=K_FILTER_ATUACAO)
        with c3:
            st.selectbox("Categoria", categoria_options, key=K_FILTER_CATEGORIA)
        with c4:
            st.selectbox(
                "Ordenar", ["Mais recentes", "Mais antigos"], key=K_FILTER_ORDEM
            )

        c5, c6 = grid(2, columns_mobile=1)
        with c5:
            st.text_input(
                "Buscar",
                placeholder="nº/código, comarca, vara, cliente, descrição, observações…",
                key=K_FILTER_Q,
            )
        with c6:
            st.checkbox(
                "Somente com pasta local",
                key=K_FILTER_SOMENTE_COM_PASTA,
            )

        _render_filter_summary()

    filtro_status = st.session_state.get(K_FILTER_STATUS, "(Todos)")
    filtro_atuacao = st.session_state.get(K_FILTER_ATUACAO, "(Todas)")
    filtro_categoria = st.session_state.get(K_FILTER_CATEGORIA, "(Todas)")
    ordem = st.session_state.get(K_FILTER_ORDEM, "Mais recentes")
    filtro_q = st.session_state.get(K_FILTER_Q, "")
    somente_com_pasta = bool(st.session_state.get(K_FILTER_SOMENTE_COM_PASTA, False))

    status_val = None if filtro_status == "(Todos)" else filtro_status
    papel_val = ATUACAO_UI_ALL.get(filtro_atuacao)
    categoria_val = None if filtro_categoria == "(Todas)" else filtro_categoria
    order_desc = ordem == "Mais recentes"

    rows = _cached_list_rows(
        owner_user_id,
        status_val,
        papel_val,
        categoria_val,
        (filtro_q or None),
        order_desc,
        version,
    )

    if somente_com_pasta:
        rows = [r for r in rows if (r.get("pasta_local") or "").strip()]

    if not rows:
        _render_empty_state()
        return

    total_resultado = len(rows)
    ativos = sum(1 for r in rows if (r.get("status", "") or "").lower() == "ativo")
    concl = sum(
        1 for r in rows if (r.get("status", "") or "").lower().startswith("concl")
    )
    susp = sum(1 for r in rows if (r.get("status", "") or "").lower() == "suspenso")

    k1, k2, k3, k4 = grid(4, columns_mobile=2)
    with k1:
        card("Resultado", f"{total_resultado}", "nos filtros", tone="info")
    with k2:
        card(
            "Ativos",
            f"{ativos}",
            "nesta visualização",
            tone="success" if ativos else "neutral",
        )
    with k3:
        card("Concluídos", f"{concl}", "nesta visualização", tone="neutral")
    with k4:
        card(
            "Suspensos",
            f"{susp}",
            "nesta visualização",
            tone="warning" if susp else "neutral",
        )

    spacer(0.15)

    if _use_cards():
        limit = 50
        for r in rows[:limit]:
            _render_processo_card_row(owner_user_id, r)
        if len(rows) > limit:
            st.caption(
                f"Mostrando {limit} de {len(rows)} resultados. Use filtros para reduzir a lista."
            )
        return

    df = pd.DataFrame(
        [
            {
                "ID": int(r["id"]),
                "Referência": _strip_html(r.get("numero_processo")),
                "Atuação": _atuacao_badge(r.get("papel")),
                "Categoria": _strip_html(r.get("categoria_servico")),
                "Status": _status_badge(r.get("status", "")),
                "Cliente": _strip_html(r.get("contratante")),
                "Descrição": _strip_html(r.get("tipo_acao")),
                "Comarca": _strip_html(r.get("comarca")),
                "Vara": _strip_html(r.get("vara")),
                "Pasta": _strip_html(r.get("pasta_local")),
            }
            for r in rows
        ]
    )

    with section("Tabela", subtitle=f"Total exibido: {len(df)}", divider=False):
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
        id_to_label = {
            int(r["id"]): _strip_html(r.get("numero_processo")) for r in rows
        }
        ids = list(id_to_label.keys())

        default_id = st.session_state.get(K_SELECTED_ID, ids[0])
        if default_id not in ids:
            default_id = ids[0]

        cA, cB, cC, cD, cE, cF = grid(6, columns_mobile=1)
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

        comarca = _strip_html((selected_row or {}).get("comarca"))
        vara = _strip_html((selected_row or {}).get("vara"))

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
        with cF:
            st.button(
                "Duplicar",
                use_container_width=True,
                key="proc_act_dup",
                on_click=_duplicate_processo,
                args=(owner_user_id, int(selected_id)),
            )


# ==================================================
# EDITAR
# ==================================================
def _render_editar(owner_user_id: int) -> None:
    with section(
        "Editar",
        subtitle="Localize o trabalho e ajuste os dados principais.",
        divider=False,
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
            ref = _strip_html(pr.numero_processo)
            cli = _strip_html(pr.contratante)
            atu = _atuacao_badge(pr.papel)
            cat = _strip_html(pr.categoria_servico)
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
    status_atual = p.get("status", "Ativo") or "Ativo"

    with section(
        "Resumo atual",
        subtitle="Leitura rápida do registro selecionado.",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=2)
        with c1:
            card(
                "Referência",
                _strip_html(p.get("numero_processo")) or "—",
                "identificação",
                tone="info",
            )
        with c2:
            card(
                "Status",
                _status_badge(status_atual),
                "situação",
                tone=_status_tone(status_atual),
            )
        with c3:
            card(
                "Atuação",
                _atuacao_badge(p.get("papel")),
                "classificação",
                tone="neutral",
            )
        with c4:
            card(
                "Categoria",
                _strip_html(p.get("categoria_servico")) or "—",
                "serviço",
                tone="neutral",
            )

    with section(
        "Ações", subtitle="Pasta local, duplicação e exclusão.", divider=False
    ):
        pasta_key = f"proc_edit_pasta_{selected_id}"
        st.session_state.setdefault(pasta_key, p.get("pasta_local", "") or "")

        a, b, c, d = grid(4, columns_mobile=1)
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
            st.button(
                "📄 Duplicar",
                use_container_width=True,
                key=f"proc_duplicate_{selected_id}",
                on_click=_duplicate_processo,
                args=(owner_user_id, int(selected_id)),
            )

        with c:
            current_pasta = st.session_state.get(pasta_key, "") or ""
            if st.button(
                "📂 Abrir pasta",
                use_container_width=True,
                key=f"proc_open_folder_{selected_id}",
                disabled=not bool(current_pasta.strip()),
            ):
                ok, msg = _open_folder(current_pasta)
                if ok:
                    _toast("📂 Pasta aberta")
                else:
                    st.warning(msg)

        with d:
            confirm = st.checkbox(
                "Confirmar exclusão",
                value=False,
                key=f"proc_del_confirm_{selected_id}",
            )
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

        st.caption("⚠️ A exclusão remove definitivamente o registro do banco.")

    with st.form(f"form_trabalho_edit_{selected_id}"):
        c1, c2, c3 = grid(3, columns_mobile=1)
        with c1:
            numero_e = st.text_input(
                "Número / Código *",
                value=_strip_html(p.get("numero_processo")) or "",
                key=f"proc_edit_num_{selected_id}",
            )
        with c2:
            comarca_e = st.text_input(
                "Comarca",
                value=_strip_html(p.get("comarca")) or "",
                key=f"proc_edit_comarca_{selected_id}",
            )
        with c3:
            vara_e = st.text_input(
                "Vara",
                value=_strip_html(p.get("vara")) or "",
                key=f"proc_edit_vara_{selected_id}",
            )

        c4, c5, c6 = grid(3, columns_mobile=1)
        with c4:
            tipo_acao_e = st.text_input(
                "Descrição / Tipo",
                value=_strip_html(p.get("tipo_acao")) or "",
                key=f"proc_edit_tipo_{selected_id}",
            )
        with c5:
            contratante_e = st.text_input(
                "Contratante / Cliente",
                value=_strip_html(p.get("contratante")) or "",
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
            cat_atual = _strip_html(p.get("categoria_servico"))
            categoria_e = st.selectbox(
                "Categoria / Serviço",
                CATEGORIAS_UI,
                index=(
                    CATEGORIAS_UI.index(cat_atual) if cat_atual in CATEGORIAS_UI else 0
                ),
                key=f"proc_edit_cat_{selected_id}",
            )
        with c8:
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
            value=_strip_html(p.get("observacoes")) or "",
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
