from __future__ import annotations

import html
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from db.connection import get_session
from services.processos_service import ProcessoCreate, ProcessoUpdate, ProcessosService
from ui.layout import empty_state, grid, grid_weights, is_mobile, section, spacer
from ui.page_header import HeaderAction, page_header
from ui.theme import card
from ui_state import (
    bump_data_version,
    clear_qp_keys,
    get_data_version,
    get_qp_str,
    navigate,
)

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

MENU_TRABALHOS_KEY = "Trabalhos"
MENU_PRAZOS_KEY = "Prazos"
MENU_AGENDA_KEY = "Agenda"
MENU_FIN_KEY = "Financeiro"

SECTIONS = ("Lista", "Cadastrar", "Editar")

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

K_CREATE_PASTA = "proc_create_pasta"
K_CREATE_NUMERO = "proc_create_numero"
K_CREATE_ATUACAO = "proc_create_atuacao"
K_CREATE_STATUS = "proc_create_status"
K_CREATE_CATEGORIA = "proc_create_categoria"
K_CREATE_TIPO = "proc_create_tipo_acao"
K_CREATE_COMARCA = "proc_create_comarca"
K_CREATE_VARA = "proc_create_vara"
K_CREATE_CONTRATANTE = "proc_create_contratante"
K_CREATE_OBS = "proc_create_obs"

K_EDIT_SEARCH = "proc_edit_search"

# ==================================================
# LOW-LEVEL HELPERS
# ==================================================


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _inject_processos_css() -> None:
    _render_html(
        """
        <style>
        .sp-page-hero {
            padding: 1rem 1rem 1rem 1rem;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.96));
            box-shadow: 0 10px 30px rgba(15,23,42,.04);
            margin-bottom: .95rem;
        }

        .sp-page-hero-grid {
            display: grid;
            grid-template-columns: 1.55fr 1fr;
            gap: 14px;
            align-items: center;
        }

        .sp-page-kicker {
            font-size: .74rem;
            font-weight: 900;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: rgba(15,23,42,.45);
            margin-bottom: 4px;
        }

        .sp-page-title {
            font-size: 1.54rem;
            font-weight: 900;
            line-height: 1.12;
            color: #0f172a;
        }

        .sp-page-subtitle {
            margin-top: 6px;
            color: rgba(15,23,42,.68);
            line-height: 1.48;
            font-size: .93rem;
        }

        .sp-inline-metrics {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .sp-mini-stat {
            border-radius: 14px;
            border: 1px solid rgba(15,23,42,.08);
            background: #fff;
            padding: 12px 13px;
        }

        .sp-mini-stat-label {
            font-size: .70rem;
            font-weight: 900;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: rgba(15,23,42,.45);
        }

        .sp-mini-stat-value {
            margin-top: 3px;
            font-size: 1.08rem;
            font-weight: 900;
            color: #0f172a;
        }

        .sp-mini-stat-sub {
            margin-top: 4px;
            color: rgba(15,23,42,.60);
            font-size: .80rem;
        }

        .sp-toolbar-card,
        .sp-side-panel,
        .sp-list-card,
        .sp-banner {
            border-radius: 16px;
            border: 1px solid rgba(15,23,42,.08);
            background: #fff;
            padding: 13px 14px;
            box-shadow: 0 6px 18px rgba(15,23,42,.03);
        }

        .sp-banner-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: .80rem 0 .95rem 0;
        }

        .sp-banner {
            flex: 1 1 250px;
        }

        .sp-banner-danger { border-left: 5px solid #dc2626; }
        .sp-banner-warning { border-left: 5px solid #f59e0b; }
        .sp-banner-info { border-left: 5px solid #2563eb; }
        .sp-banner-success { border-left: 5px solid #16a34a; }

        .sp-banner-title {
            font-size: .73rem;
            font-weight: 900;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: rgba(15,23,42,.45);
            margin-bottom: 4px;
        }

        .sp-banner-text {
            font-size: .90rem;
            line-height: 1.4;
            font-weight: 800;
            color: #0f172a;
        }

        .sp-kicker {
            font-size: .74rem;
            font-weight: 900;
            letter-spacing: .06em;
            text-transform: uppercase;
            color: rgba(15,23,42,.44);
            margin-bottom: 4px;
        }

        .sp-chip-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }

        .sp-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            border-radius: 999px;
            background: rgba(15,23,42,.06);
            color: rgba(15,23,42,.78);
            font-size: .79rem;
            font-weight: 750;
        }

        .sp-chip-success { background: rgba(22,163,74,.10); color: #166534; }
        .sp-chip-warning { background: rgba(245,158,11,.14); color: #92400e; }
        .sp-chip-danger  { background: rgba(220,38,38,.10); color: #991b1b; }
        .sp-chip-info    { background: rgba(37,99,235,.10); color: #1d4ed8; }
        .sp-chip-neutral { background: rgba(71,85,105,.10); color: #334155; }

        .sp-list-card {
            margin-bottom: 10px;
        }

        .sp-list-card-head {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            align-items: flex-start;
            flex-wrap: wrap;
        }

        .sp-list-title {
            font-size: .98rem;
            font-weight: 900;
            color: #0f172a;
            line-height: 1.22;
        }

        .sp-list-meta {
            margin-top: 4px;
            color: rgba(15,23,42,.65);
            font-size: .88rem;
        }

        .sp-list-body {
            margin-top: 9px;
            color: rgba(15,23,42,.82);
            line-height: 1.48;
            font-size: .92rem;
        }

        .sp-metric-line {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            padding: 7px 0;
            border-bottom: 1px dashed rgba(15,23,42,.08);
        }

        .sp-metric-line:last-child {
            border-bottom: none;
        }

        .sp-metric-label {
            color: rgba(15,23,42,.58);
            font-size: .88rem;
        }

        .sp-metric-value {
            color: #0f172a;
            font-weight: 800;
            text-align: right;
        }

        .sp-mini-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }

        .sp-mini-box {
            border: 1px solid rgba(15,23,42,.08);
            border-radius: 12px;
            padding: 10px;
            background: rgba(248,250,252,.75);
        }

        .sp-mini-box-label {
            font-size: .68rem;
            text-transform: uppercase;
            font-weight: 900;
            letter-spacing: .05em;
            color: rgba(15,23,42,.45);
        }

        .sp-mini-box-value {
            margin-top: 4px;
            font-size: .92rem;
            font-weight: 850;
            color: #0f172a;
        }

        @media (max-width: 980px) {
            .sp-page-hero-grid {
                grid-template-columns: 1fr;
            }
            .sp-inline-metrics {
                grid-template-columns: 1fr 1fr;
            }
        }

        @media (max-width: 640px) {
            .sp-inline-metrics {
                grid-template-columns: 1fr;
            }
            .sp-mini-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """
    )


def _button(
    label: str,
    *,
    key: str,
    on_click=None,
    args: tuple | None = None,
    use_container_width: bool = True,
    type: str = "secondary",
    disabled: bool = False,
) -> bool:
    kwargs: dict[str, Any] = {
        "label": label,
        "key": key,
        "use_container_width": use_container_width,
        "type": type,
        "disabled": disabled,
    }
    if on_click is not None:
        kwargs["on_click"] = on_click
    if args is not None:
        kwargs["args"] = args
    return st.button(**kwargs)


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


def _safe_strip(value: Any) -> str:
    return _strip_html("" if value is None else str(value))


def _escape_text(value: Any) -> str:
    return html.escape(_safe_strip(value))


def _use_cards() -> bool:
    return bool(st.session_state.get("ui_mobile_cards", True) or is_mobile())


def _fmt_money_br(value: Any) -> str:
    try:
        parsed = float(value or 0)
    except Exception:
        parsed = 0.0
    return f"{parsed:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_dt_br(value: Any, with_time: bool = False) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
    return str(value)


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


def _status_chip_class(status: str | None) -> str:
    s = (status or "").strip().lower()
    if s == "ativo":
        return "sp-chip-success"
    if s in ("concluído", "concluido"):
        return "sp-chip-neutral"
    if s == "suspenso":
        return "sp-chip-warning"
    return "sp-chip-info"


def _atuacao_badge(db_val: str | None) -> str:
    v = _norm_tipo_trabalho(db_val)
    if v == "Perito Judicial":
        return "⚖️ Perícia (Juízo)"
    if v == "Assistente Técnico":
        return "🛠️ Assistência Técnica"
    if v == "Trabalho Particular":
        return "🏷️ Particular"
    return v


def _atuacao_chip_class(db_val: str | None) -> str:
    v = _norm_tipo_trabalho(db_val)
    if v == "Perito Judicial":
        return "sp-chip-info"
    if v == "Assistente Técnico":
        return "sp-chip-success"
    if v == "Trabalho Particular":
        return "sp-chip-warning"
    return "sp-chip-neutral"


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


def _clear_data_cache() -> None:
    try:
        st.cache_data.clear()
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


def _render_soft_note(title: str, body: str) -> None:
    _render_html(
        f"""
        <div class="sp-toolbar-card">
          <div style="font-weight:850; margin-bottom:4px;">{html.escape(title)}</div>
          <div style="font-size:0.93rem; color:rgba(15,23,42,.72);">{html.escape(body)}</div>
        </div>
        """
    )


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


def _results_metrics(rows: list[dict]) -> dict[str, int]:
    ativos = sum(1 for r in rows if (_safe_strip(r.get("status")).lower() == "ativo"))
    concluidos = sum(
        1 for r in rows if _safe_strip(r.get("status")).lower().startswith("concl")
    )
    suspensos = sum(
        1 for r in rows if (_safe_strip(r.get("status")).lower() == "suspenso")
    )
    com_pasta = sum(1 for r in rows if _safe_strip(r.get("pasta_local")))
    return {
        "resultado": len(rows),
        "ativos": ativos,
        "concluidos": concluidos,
        "suspensos": suspensos,
        "com_pasta": com_pasta,
    }


def _row_label(r: dict) -> str:
    ref = _strip_html(r.get("numero_processo")) or "Sem referência"
    atu = _atuacao_badge(r.get("papel"))
    cat = _strip_html(r.get("categoria_servico"))
    cli = _strip_html(r.get("contratante"))
    parts = [ref, atu]
    if cat:
        parts.append(cat)
    if cli:
        parts.append(cli)
    return " — ".join(parts)


# ==================================================
# SYNC
# ==================================================


def _sync_from_dashboard_and_qp() -> None:
    st.session_state.setdefault(K_SECTION, "Lista")
    st.session_state.setdefault(K_SECTION_SELECTOR, st.session_state[K_SECTION])

    st.session_state.setdefault(K_FILTER_ORDEM, "Mais recentes")
    st.session_state.setdefault(K_FILTER_STATUS, "(Todos)")
    st.session_state.setdefault(K_FILTER_ATUACAO, "(Todas)")
    st.session_state.setdefault(K_FILTER_CATEGORIA, "(Todas)")
    st.session_state.setdefault(K_FILTER_Q, "")
    st.session_state.setdefault(K_FILTER_SOMENTE_COM_PASTA, False)

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
        st.session_state[K_SECTION_SELECTOR] = "Lista"


# ==================================================
# CALLBACKS
# ==================================================


def _set_section(sec: str) -> None:
    if sec in SECTIONS:
        st.session_state[K_SECTION] = sec
        st.session_state[K_SECTION_SELECTOR] = sec


def _open_edit(processo_id: int) -> None:
    st.session_state[K_SELECTED_ID] = int(processo_id)
    _set_section("Editar")


def _prefill_processo_context(pid: int, ref: str, comarca: str, vara: str) -> None:
    st.session_state["pref_processo_id"] = int(pid)
    st.session_state["pref_processo_ref"] = ref
    st.session_state["pref_processo_comarca"] = comarca
    st.session_state["pref_processo_vara"] = vara


def _go_prazos(pid: int, ref: str, comarca: str, vara: str) -> None:
    _prefill_processo_context(pid, ref, comarca, vara)
    navigate(MENU_PRAZOS_KEY, state={"prazos_section": "Lista"})


def _go_agenda(pid: int, ref: str, comarca: str, vara: str) -> None:
    _prefill_processo_context(pid, ref, comarca, vara)
    navigate(MENU_AGENDA_KEY)


def _go_fin(pid: int, ref: str, comarca: str, vara: str) -> None:
    _prefill_processo_context(pid, ref, comarca, vara)
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
    clear_qp_keys("status", "atuacao", "categoria", "q")
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
        st.session_state[K_SELECTED_ID] = int(getattr(created, "id", 0) or 0)
        _toast("📄 Processo duplicado")
        _set_section("Editar")
    except Exception as e:
        st.error(f"Erro ao duplicar: {e}")


# ==================================================
# CACHE
# ==================================================


@st.cache_data(show_spinner=False, ttl=45)
def _cached_list_rows_enriched(
    owner_user_id: int,
    status: str | None,
    papel: str | None,
    categoria_servico: str | None,
    q: str | None,
    order_desc: bool,
    version: int,
) -> list[dict]:
    _ = version
    with get_session() as s:
        return ProcessosService.list_enriched(
            s,
            owner_user_id=owner_user_id,
            status=status,
            papel=papel,
            categoria_servico=categoria_servico,
            q=q,
            order_desc=order_desc,
        )


@st.cache_data(show_spinner=False, ttl=45)
def _cached_get_row_enriched(
    owner_user_id: int, processo_id: int, version: int
) -> dict | None:
    _ = version
    with get_session() as s:
        return ProcessosService.get_enriched(s, owner_user_id, processo_id)


@st.cache_data(show_spinner=False, ttl=45)
def _cached_stats(owner_user_id: int, version: int) -> dict[str, int]:
    _ = version
    with get_session() as s:
        return ProcessosService.stats(s, owner_user_id)


# ==================================================
# RENDER HELPERS
# ==================================================


def _render_header(stats: dict[str, int]) -> None:
    _render_html(
        f"""
        <div class="sp-page-hero">
          <div class="sp-page-hero-grid">
            <div>
              <div class="sp-page-kicker">gestão de processos</div>
              <div class="sp-page-title">Processos e Trabalhos</div>
              <div class="sp-page-subtitle">
                Central para cadastro, busca, organização e operação dos seus registros técnicos,
                judiciais e particulares.
              </div>
              <div class="sp-chip-row" style="margin-top:12px;">
                <span class="sp-chip">Busca rápida</span>
                <span class="sp-chip">Ações por registro</span>
                <span class="sp-chip">Fluxo operacional</span>
              </div>
            </div>
            <div class="sp-inline-metrics">
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">total</div>
                <div class="sp-mini-stat-value">{stats.get('total', 0)}</div>
                <div class="sp-mini-stat-sub">registros</div>
              </div>
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">ativos</div>
                <div class="sp-mini-stat-value">{stats.get('ativos', 0)}</div>
                <div class="sp-mini-stat-sub">em andamento</div>
              </div>
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">concluídos</div>
                <div class="sp-mini-stat-value">{stats.get('concluidos', 0)}</div>
                <div class="sp-mini-stat-sub">finalizados</div>
              </div>
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">com pasta</div>
                <div class="sp-mini-stat-value">{stats.get('com_pasta', 0)}</div>
                <div class="sp-mini-stat-sub">vínculo local</div>
              </div>
            </div>
          </div>
        </div>
        """
    )


def _render_filter_summary() -> None:
    chips = _summarize_filters()
    if not chips:
        st.caption("Visualização geral sem filtros específicos.")
        return
    st.caption(f"Filtros aplicados: {'  •  '.join(chips)}")


def _render_priority_banners(stats: dict[str, int], rows: list[dict]) -> None:
    metrics = _results_metrics(rows)
    banners: list[tuple[str, str, str]] = []

    if stats.get("ativos", 0) > 0:
        banners.append(
            (
                "success",
                "Carteira ativa",
                f"{stats.get('ativos', 0)} processo(s) ativo(s) na base.",
            )
        )

    if metrics.get("resultado", 0) > 0:
        banners.append(
            (
                "info",
                "Resultado atual",
                f"{metrics.get('resultado', 0)} registro(s) retornado(s) com os filtros aplicados.",
            )
        )

    if stats.get("suspensos", 0) > 0:
        banners.append(
            (
                "warning",
                "Atenção de carteira",
                f"{stats.get('suspensos', 0)} processo(s) suspenso(s) aguardando retomada.",
            )
        )

    if stats.get("sem_pasta", 0) > 0:
        banners.append(
            (
                "warning",
                "Organização de arquivos",
                f"{stats.get('sem_pasta', 0)} registro(s) ainda sem pasta local vinculada.",
            )
        )

    if not banners:
        banners.append(
            ("success", "Base organizada", "Sem alertas relevantes no momento.")
        )

    _render_html("<div class='sp-banner-row'>")
    for tone, title, text in banners[:4]:
        _render_html(
            f"""
            <div class="sp-banner sp-banner-{tone}">
              <div class="sp-banner-title">{html.escape(title)}</div>
              <div class="sp-banner-text">{html.escape(text)}</div>
            </div>
            """
        )
    _render_html("</div>")


def _render_empty_list() -> None:
    empty_state(
        title="Nenhum processo encontrado",
        subtitle="Ajuste os filtros ou cadastre um novo registro.",
        icon="📁",
    )
    a, b = grid(2, columns_mobile=1)
    with a:
        _button(
            "➕ Cadastrar novo processo",
            key="proc_empty_new",
            type="primary",
            on_click=_set_section,
            args=("Cadastrar",),
        )
    with b:
        _button("🧹 Limpar filtros", key="proc_empty_clear", on_click=_clear_filters)


def _render_overview_cards(stats: dict[str, int]) -> None:
    k1, k2, k3, k4, k5 = grid(5, columns_mobile=2)
    with k1:
        card("Total", f"{stats.get('total', 0)}", "todos os processos", tone="info")
    with k2:
        card("Ativos", f"{stats.get('ativos', 0)}", "em andamento", tone="success")
    with k3:
        card(
            "Concluídos", f"{stats.get('concluidos', 0)}", "finalizados", tone="neutral"
        )
    with k4:
        card("Suspensos", f"{stats.get('suspensos', 0)}", "pausados", tone="warning")
    with k5:
        card("Com pasta", f"{stats.get('com_pasta', 0)}", "vínculo local", tone="info")


def _render_list_insights(rows: list[dict]) -> None:
    metrics = _results_metrics(rows)
    k1, k2, k3, k4, k5 = grid(5, columns_mobile=2)

    with k1:
        card("Resultado", f"{metrics['resultado']}", "nos filtros", tone="info")
    with k2:
        card(
            "Ativos",
            f"{metrics['ativos']}",
            "nesta visualização",
            tone="success" if metrics["ativos"] else "neutral",
        )
    with k3:
        card(
            "Concluídos",
            f"{metrics['concluidos']}",
            "nesta visualização",
            tone="neutral",
        )
    with k4:
        card(
            "Suspensos",
            f"{metrics['suspensos']}",
            "nesta visualização",
            tone="warning" if metrics["suspensos"] else "neutral",
        )
    with k5:
        card(
            "Com pasta",
            f"{metrics['com_pasta']}",
            "vínculo local",
            tone="info" if metrics["com_pasta"] else "neutral",
        )


def _render_selected_context(selected_row: dict | None) -> None:
    if not selected_row:
        empty_state(
            title="Nenhum processo selecionado",
            subtitle="Selecione um registro para ver os detalhes.",
            icon="🧭",
        )
        return

    ref = _escape_text(selected_row.get("numero_processo")) or "—"
    cli = _escape_text(selected_row.get("contratante")) or "—"
    desc = _escape_text(selected_row.get("tipo_acao")) or "—"
    comarca = _escape_text(selected_row.get("comarca")) or "—"
    vara = _escape_text(selected_row.get("vara")) or "—"
    pasta = _escape_text(selected_row.get("pasta_local")) or "—"
    obs = html.escape(
        _compact_text(selected_row.get("observacoes"), 240) or "Sem observações."
    )
    prox_prazo = _fmt_dt_br(selected_row.get("proximo_prazo"))
    prox_ag = _fmt_dt_br(selected_row.get("proximo_agendamento"), with_time=True)
    saldo = f"R$ {_fmt_money_br(selected_row.get('saldo', 0))}"
    prazos_abertos = int(selected_row.get("prazos_abertos", 0) or 0)
    agendamentos_futuros = int(selected_row.get("agendamentos_futuros", 0) or 0)

    categoria = _escape_text(selected_row.get("categoria_servico"))
    categoria_chip = f"<span class='sp-chip'>🏷️ {categoria}</span>" if categoria else ""

    _render_html(
        f"""
        <div class="sp-side-panel">
          <div class="sp-kicker">contexto do registro</div>
          <div style="font-weight:900; font-size:1rem; margin-bottom:8px; color:#0f172a;">{ref}</div>
          <div class="sp-chip-row" style="margin-bottom:10px;">
            <span class="sp-chip {_status_chip_class(selected_row.get('status', ''))}">{_status_badge(selected_row.get('status', ''))}</span>
            <span class="sp-chip {_atuacao_chip_class(selected_row.get('papel'))}">{_atuacao_badge(selected_row.get('papel'))}</span>
            {categoria_chip}
          </div>
          <div class="sp-metric-line"><div class="sp-metric-label">Cliente</div><div class="sp-metric-value">{cli}</div></div>
          <div class="sp-metric-line"><div class="sp-metric-label">Descrição</div><div class="sp-metric-value">{desc}</div></div>
          <div class="sp-metric-line"><div class="sp-metric-label">Comarca / Vara</div><div class="sp-metric-value">{comarca} • {vara}</div></div>
          <div class="sp-metric-line"><div class="sp-metric-label">Pasta</div><div class="sp-metric-value">{pasta}</div></div>
          <div class="sp-metric-line"><div class="sp-metric-label">Próximo prazo</div><div class="sp-metric-value">{prox_prazo}</div></div>
          <div class="sp-metric-line"><div class="sp-metric-label">Próxima agenda</div><div class="sp-metric-value">{prox_ag}</div></div>
          <div class="sp-metric-line"><div class="sp-metric-label">Saldo</div><div class="sp-metric-value">{saldo}</div></div>
          <div class="sp-chip-row">
            <span class="sp-chip">⏳ {prazos_abertos} prazo(s)</span>
            <span class="sp-chip">📅 {agendamentos_futuros} agenda(s)</span>
          </div>
          <div style="margin-top:10px; color:rgba(15,23,42,.72); font-size:.92rem; line-height:1.5;"><b>Obs.:</b> {obs}</div>
        </div>
        """
    )


def _render_operational_actions(
    pid: int, ref: str, comarca: str, vara: str, pasta: str
) -> None:
    a, b, c, d = grid(4, columns_mobile=2)
    with a:
        _button(
            "⏳ Prazos",
            key=f"proc_ops_pz_{pid}",
            type="primary",
            on_click=_go_prazos,
            args=(pid, ref, comarca, vara),
        )
    with b:
        _button(
            "📅 Agenda",
            key=f"proc_ops_ag_{pid}",
            on_click=_go_agenda,
            args=(pid, ref, comarca, vara),
        )
    with c:
        _button(
            "💰 Financeiro",
            key=f"proc_ops_fin_{pid}",
            on_click=_go_fin,
            args=(pid, ref, comarca, vara),
        )
    with d:
        if pasta.strip():
            if _button("📂 Abrir pasta", key=f"proc_ops_folder_{pid}"):
                ok, msg = _open_folder(pasta)
                if ok:
                    _toast("📂 Pasta aberta")
                else:
                    st.warning(msg)
        else:
            _button("📂 Sem pasta", key=f"proc_ops_folder_empty_{pid}", disabled=True)


def _render_next_steps_panel(row: dict) -> None:
    status = _safe_strip(row.get("status"))
    pasta = _safe_strip(row.get("pasta_local"))
    obs = _safe_strip(row.get("observacoes"))
    contratante = _safe_strip(row.get("contratante"))
    prazos_abertos = int(row.get("prazos_abertos", 0) or 0)
    agendamentos_futuros = int(row.get("agendamentos_futuros", 0) or 0)

    items: list[str] = []

    if status.lower() == "ativo":
        if prazos_abertos == 0:
            items.append(
                "Cadastre os prazos principais deste processo para evitar perda de controle."
            )
        else:
            items.append(
                "Revise os prazos em aberto e confirme a prioridade do próximo vencimento."
            )

        if agendamentos_futuros == 0:
            items.append(
                "Confira se já há vistoria, reunião ou diligência que precise entrar em agenda."
            )
        else:
            items.append(
                "Valide local, horário e documentação dos compromissos futuros."
            )
    elif status.lower() == "suspenso":
        items.append(
            "Mantenha o histórico organizado e registre retomadas quando houver novidade."
        )
    else:
        items.append(
            "Confira se financeiro, observações e documentação final estão consolidados."
        )

    if not pasta:
        items.append(
            "Vincule a pasta local para acesso rápido aos arquivos do processo."
        )
    if not contratante:
        items.append(
            "Complete a identificação do cliente/contratante para melhorar a busca."
        )
    if not obs:
        items.append("Adicione observações resumidas para contexto futuro.")

    items = items[:4]
    if not items:
        items = ["Registro consistente. O processo está bem estruturado nesta etapa."]

    for idx, item in enumerate(items, start=1):
        _render_html(
            f"""
            <div class="sp-toolbar-card" style="margin-bottom:10px;">
              <div class="sp-kicker">próximo passo {idx}</div>
              <div style="color:rgba(15,23,42,.86); line-height:1.5; text-align:left;">
                {html.escape(item)}
              </div>
            </div>
            """
        )


def _render_processo_card_row(owner_user_id: int, r: dict) -> None:
    pid = int(r.get("id") or 0)
    ref = html.escape(_compact_text(r.get("numero_processo"), 90))

    atu = _atuacao_badge(r.get("papel"))
    status = _status_badge(r.get("status", ""))
    cat = html.escape(_compact_text(r.get("categoria_servico"), 40))
    cli = html.escape(_compact_text(r.get("contratante"), 80))
    desc = html.escape(_compact_text(r.get("tipo_acao"), 180))
    comarca = _compact_text(r.get("comarca"), 40)
    vara = _compact_text(r.get("vara"), 40)
    pasta = _strip_html(r.get("pasta_local"))
    obs = html.escape(_compact_text(r.get("observacoes"), 160))

    prazos_abertos = int(r.get("prazos_abertos", 0) or 0)
    proximo_prazo = _fmt_dt_br(r.get("proximo_prazo"))
    agendamentos_futuros = int(r.get("agendamentos_futuros", 0) or 0)
    proximo_ag = _fmt_dt_br(r.get("proximo_agendamento"), with_time=True)
    saldo = f"R$ {_fmt_money_br(r.get('saldo', 0))}"

    meta_line = html.escape(" • ".join([x for x in [cli, comarca, vara] if x]))
    categoria_chip = f"<span class='sp-chip'>🏷️ {cat}</span>" if cat else ""

    descricao_line = (
        f"<div class='sp-list-body'><b>Descrição:</b> {desc}</div>" if desc else ""
    )
    obs_line = (
        f"<div class='sp-list-body' style='margin-top:6px; color:rgba(15,23,42,.70);'><b>Obs.:</b> {obs}</div>"
        if obs
        else ""
    )

    pasta_chip = (
        "<span class='sp-chip sp-chip-success'>📂 Pasta vinculada</span>"
        if pasta
        else "<span class='sp-chip sp-chip-neutral'>📂 Sem pasta</span>"
    )

    _render_html(
        f"""
        <div class="sp-list-card">
          <div class="sp-list-card-head">
            <div style="min-width:0;">
              <div class="sp-list-title">{ref or "Sem referência"}</div>
              <div class="sp-list-meta">{meta_line or "Sem metadados principais"}</div>
            </div>
            <div class="sp-chip-row" style="margin-top:0; justify-content:flex-end;">
              <span class="sp-chip {_status_chip_class(r.get('status', ''))}">{status}</span>
              <span class="sp-chip {_atuacao_chip_class(r.get('papel'))}">{atu}</span>
              {categoria_chip}
            </div>
          </div>
          {descricao_line}
          {obs_line}
          <div class="sp-chip-row">
            {pasta_chip}
          </div>
          <div class="sp-mini-grid">
            <div class="sp-mini-box">
                <div class="sp-mini-box-label">prazos</div>
                <div class="sp-mini-box-value">{prazos_abertos} aberto(s)</div>
            </div>
            <div class="sp-mini-box">
                <div class="sp-mini-box-label">próximo prazo</div>
                <div class="sp-mini-box-value">{html.escape(proximo_prazo)}</div>
            </div>
            <div class="sp-mini-box">
                <div class="sp-mini-box-label">saldo</div>
                <div class="sp-mini-box-value">{html.escape(saldo)}</div>
            </div>
            <div class="sp-mini-box">
                <div class="sp-mini-box-label">agenda</div>
                <div class="sp-mini-box-value">{agendamentos_futuros} futuro(s)</div>
            </div>
            <div class="sp-mini-box">
                <div class="sp-mini-box-label">próx. agendamento</div>
                <div class="sp-mini-box-value">{html.escape(proximo_ag)}</div>
            </div>
            <div class="sp-mini-box">
                <div class="sp-mini-box-label">cliente</div>
                <div class="sp-mini-box-value">{html.escape(_compact_text(r.get("contratante"), 40) or "—")}</div>
            </div>
          </div>
        </div>
        """
    )

    a, b, c = grid(3, columns_mobile=1)
    with a:
        _button(
            "Abrir processo",
            key=f"m_open_{pid}",
            type="primary",
            on_click=_open_edit,
            args=(pid,),
        )
    with b:
        _button(
            "Prazos",
            key=f"m_pz_{pid}",
            on_click=_go_prazos,
            args=(pid, _strip_html(r.get("numero_processo")), comarca, vara),
        )
    with c:
        _button(
            "Financeiro",
            key=f"m_fin_{pid}",
            on_click=_go_fin,
            args=(pid, _strip_html(r.get("numero_processo")), comarca, vara),
        )

    with st.expander("Mais ações"):
        d, e, f = grid(3, columns_mobile=1)
        with d:
            _button(
                "Agenda",
                key=f"m_ag_{pid}",
                on_click=_go_agenda,
                args=(pid, _strip_html(r.get("numero_processo")), comarca, vara),
            )
        with e:
            _button(
                "Duplicar",
                key=f"m_dup_{pid}",
                on_click=_duplicate_processo,
                args=(owner_user_id, pid),
            )
        with f:
            if pasta:
                if _button("Abrir pasta", key=f"m_open_folder_{pid}"):
                    ok, msg = _open_folder(pasta)
                    if ok:
                        _toast("📂 Pasta aberta")
                    else:
                        st.warning(msg)
            else:
                _button("Sem pasta", key=f"m_no_folder_{pid}", disabled=True)

    spacer(0.16)


def _build_table_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
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
                "Pasta": "Sim" if _strip_html(r.get("pasta_local")) else "Não",
                "Prazos": int(r.get("prazos_abertos", 0) or 0),
                "Agenda": int(r.get("agendamentos_futuros", 0) or 0),
                "Saldo": f"R$ {_fmt_money_br(r.get('saldo', 0))}",
            }
            for r in rows
        ]
    )


# ==================================================
# ENTRY
# ==================================================


def render(owner_user_id: int):
    _sync_from_dashboard_and_qp()
    _inject_processos_css()

    version = get_data_version(owner_user_id)
    stats = _cached_stats(owner_user_id, version)

    _render_header(stats)

    page_header(
        "",
        "",
        actions=[
            HeaderAction("➕ Novo", key="tb_new", type="primary", disabled=False),
            HeaderAction(
                "🧹 Limpar", key="tb_clear", type="secondary", on_click=_clear_filters
            ),
            HeaderAction("↻ Recarregar", key="tb_reload", type="secondary"),
        ],
        divider=False,
        compact=True,
    )

    if st.session_state.pop("tb_new", False):
        st.session_state[K_SECTION] = "Cadastrar"
        st.session_state[K_SECTION_SELECTOR] = "Cadastrar"

    if st.session_state.pop("tb_reload", False):
        _clear_data_cache()
        _toast("↻ Dados recarregados")

    options = list(SECTIONS)
    label_vis = "collapsed" if _use_cards() else "visible"

    with section(
        "Modo da tela",
        subtitle="Escolha entre lista, cadastro e painel do processo",
        divider=False,
        compact=True,
    ):
        if hasattr(st, "segmented_control"):
            sec = st.segmented_control(
                "Seção",
                options=options,
                key=K_SECTION_SELECTOR,
                label_visibility=label_vis,
            )
        else:
            sec = st.radio(
                "Seção",
                options=options,
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
        _render_lista(owner_user_id, stats, version)


# ==================================================
# CADASTRAR
# ==================================================


def _render_cadastrar(owner_user_id: int) -> None:
    if st.session_state.get("proc_last_created_id"):
        last_id = int(st.session_state["proc_last_created_id"])
        last_ref = st.session_state.get("proc_last_created_ref", "")

        with section(
            "✅ Processo cadastrado",
            subtitle="Escolha o próximo passo para continuar o fluxo.",
            divider=False,
        ):
            a, b, c, d = grid(4, columns_mobile=1)
            with a:
                _button(
                    "Abrir processo",
                    key="proc_post_edit",
                    type="primary",
                    on_click=_open_edit,
                    args=(last_id,),
                )
            with b:
                _button(
                    "Prazos",
                    key="proc_post_prazos",
                    on_click=_go_prazos,
                    args=(last_id, last_ref, "", ""),
                )
            with c:
                _button(
                    "Duplicar",
                    key="proc_post_dup",
                    on_click=_duplicate_processo,
                    args=(owner_user_id, last_id),
                )
            with d:
                if _button("Cadastrar outro", key="proc_post_new"):
                    st.session_state.pop("proc_last_created_id", None)
                    st.session_state.pop("proc_last_created_ref", None)
                    st.rerun()

    with section(
        "Novo processo",
        subtitle="Cadastre primeiro o essencial. Depois complemente com prazos, agenda, financeiro e notas.",
        divider=False,
    ):
        _render_soft_note(
            "Fluxo recomendado",
            "Primeiro registre número/código, atuação, categoria e cliente. Depois refine pasta, observações e demais vínculos do processo.",
        )

        spacer(0.10)
        st.session_state.setdefault(K_CREATE_PASTA, "")

        a, b = grid(2, columns_mobile=1)
        with a:
            if _button("📁 Escolher pasta…", key="proc_create_pick_folder"):
                chosen = _pick_folder_dialog(initialdir=str(ROOT_TRABALHOS))
                if chosen:
                    st.session_state[K_CREATE_PASTA] = chosen
                    st.rerun()
                else:
                    st.info(
                        "Seleção de pasta indisponível em servidor/headless ou operação cancelada."
                    )
        with b:
            st.caption(
                "Dica: se estiver no Windows local, você pode vincular a pasta do processo desde já."
            )

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
                    "Atuação *", list(ATUACAO_UI.keys()), index=1, key=K_CREATE_ATUACAO
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
                    "Salvar processo", type="primary", use_container_width=True
                )
            with submit_col2:
                spacer(0.01)

        if suggest_folder:
            st.session_state[K_CREATE_PASTA] = _guess_pasta_local(
                st.session_state.get(K_CREATE_NUMERO, "")
            )
            st.rerun()

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
                _toast("✅ Processo cadastrado")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")


# ==================================================
# LISTA
# ==================================================


def _render_lista(owner_user_id: int, stats: dict[str, int], version: int) -> None:
    with section(
        "Central de processos",
        subtitle="Filtre, localize e opere rapidamente sobre os registros cadastrados.",
        divider=False,
    ):
        cta1, cta2, cta3 = grid(3, columns_mobile=1)
        with cta1:
            _button(
                "➕ Novo processo",
                key="proc_list_new",
                type="primary",
                on_click=_set_section,
                args=("Cadastrar",),
            )
        with cta2:
            _button("🧹 Limpar filtros", key="proc_list_clear", on_click=_clear_filters)
        with cta3:
            if _button("↻ Recarregar", key="proc_list_reload"):
                _clear_data_cache()
                _toast("↻ Dados recarregados")

        spacer(0.10)
        _render_overview_cards(stats)

        spacer(0.12)

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
            st.checkbox("Somente com pasta local", key=K_FILTER_SOMENTE_COM_PASTA)

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

    rows = _cached_list_rows_enriched(
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

    _render_priority_banners(stats, rows)

    if not rows:
        _render_empty_list()
        return

    _render_list_insights(rows)
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

    df = _build_table_df(rows)

    with section(
        "Tabela principal", subtitle=f"Total exibido: {len(df)}", divider=False
    ):
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
                    "Prazos",
                    "Agenda",
                    "Saldo",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            height=540,
        )

    with section(
        "Ações rápidas por processo",
        subtitle="Selecione um registro para abrir o painel ou navegar para áreas relacionadas.",
        divider=False,
    ):
        id_to_row = {int(r["id"]): r for r in rows}
        id_to_label = {int(r["id"]): _row_label(r) for r in rows}
        ids = list(id_to_label.keys())

        default_id = st.session_state.get(K_SELECTED_ID, ids[0])
        if default_id not in ids:
            default_id = ids[0]

        cA, cB = grid_weights((1.15, 1.0), weights_mobile=(1, 1), gap="medium")

        with cA:
            selected_id = st.selectbox(
                "Selecionar",
                options=ids,
                format_func=lambda x: f"[{x}] {id_to_label.get(int(x), '')}",
                index=ids.index(default_id),
                key=K_SELECTED_ID,
            )

            selected_row = id_to_row.get(int(selected_id))
            selected_ref = _strip_html((selected_row or {}).get("numero_processo"))
            comarca = _strip_html((selected_row or {}).get("comarca"))
            vara = _strip_html((selected_row or {}).get("vara"))

            a1, a2, a3 = grid(3, columns_mobile=1)
            with a1:
                _button(
                    "Abrir processo",
                    key="proc_act_edit",
                    type="primary",
                    on_click=_open_edit,
                    args=(int(selected_id),),
                )
            with a2:
                _button(
                    "Prazos",
                    key="proc_act_pz",
                    on_click=_go_prazos,
                    args=(int(selected_id), selected_ref, comarca, vara),
                )
            with a3:
                _button(
                    "Duplicar",
                    key="proc_act_dup",
                    on_click=_duplicate_processo,
                    args=(owner_user_id, int(selected_id)),
                )

            a4, a5 = grid(2, columns_mobile=1)
            with a4:
                _button(
                    "Agenda",
                    key="proc_act_ag",
                    on_click=_go_agenda,
                    args=(int(selected_id), selected_ref, comarca, vara),
                )
            with a5:
                _button(
                    "Financeiro",
                    key="proc_act_fin",
                    on_click=_go_fin,
                    args=(int(selected_id), selected_ref, comarca, vara),
                )

        with cB:
            _render_selected_context(id_to_row.get(int(selected_id)))


# ==================================================
# EDITAR / PAINEL DO PROCESSO
# ==================================================


def _render_editar(owner_user_id: int) -> None:
    with section(
        "Abrir processo",
        subtitle="Localize o registro para visualizar contexto, ações e edição.",
        divider=False,
    ):
        busca = st.text_input(
            "Buscar", placeholder="nº/código, cliente, descrição...", key=K_EDIT_SEARCH
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
            empty_state(
                title="Nenhum processo encontrado",
                subtitle="Não há registros compatíveis com a busca informada.",
                icon="🔎",
            )
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

    version = get_data_version(owner_user_id)
    p = _cached_get_row_enriched(owner_user_id, int(selected_id), version)
    if not p:
        st.error("Processo não encontrado.")
        return

    papel_atual = _norm_tipo_trabalho(p.get("papel"))
    atuacao_atual_label = _atuacao_label_from_db(papel_atual)
    status_atual = p.get("status", "Ativo") or "Ativo"

    ref = _escape_text(p.get("numero_processo")) or "Sem referência"
    categoria = _escape_text(p.get("categoria_servico")) or "—"
    contratante = _escape_text(p.get("contratante")) or "—"
    descricao = _escape_text(p.get("tipo_acao")) or "—"
    comarca = _escape_text(p.get("comarca")) or "—"
    vara = _escape_text(p.get("vara")) or "—"
    pasta = _strip_html(p.get("pasta_local")) or ""
    pasta_html = html.escape(pasta) if pasta else "Não vinculada"
    obs = html.escape(_compact_text(p.get("observacoes"), 280) or "Sem observações.")
    saldo = f"R$ {_fmt_money_br(p.get('saldo', 0))}"
    receitas = f"R$ {_fmt_money_br(p.get('receitas', 0))}"
    despesas = f"R$ {_fmt_money_br(p.get('despesas', 0))}"
    proximo_prazo = _fmt_dt_br(p.get("proximo_prazo"))
    proximo_agendamento = _fmt_dt_br(p.get("proximo_agendamento"), with_time=True)
    prazos_abertos = int(p.get("prazos_abertos", 0) or 0)
    agendamentos_futuros = int(p.get("agendamentos_futuros", 0) or 0)

    with section(
        "Painel do processo",
        subtitle="Visão consolidada do registro selecionado",
        divider=False,
    ):
        _render_html(
            f"""
            <div class="sp-side-panel">
              <div style="display:flex; justify-content:space-between; gap:14px; align-items:flex-start; flex-wrap:wrap;">
                <div style="min-width:0;">
                  <div style="font-size:1.16rem; font-weight:900; line-height:1.2; color:#0f172a;">{ref}</div>
                  <div style="margin-top:6px; color:rgba(15,23,42,.72);">{descricao}</div>
                </div>
                <div class="sp-chip-row" style="margin-top:0; justify-content:flex-end;">
                  <span class="sp-chip {_status_chip_class(status_atual)}">{_status_badge(status_atual)}</span>
                  <span class="sp-chip {_atuacao_chip_class(p.get('papel'))}">{_atuacao_badge(p.get('papel'))}</span>
                  <span class="sp-chip">🏷️ {categoria}</span>
                </div>
              </div>
            </div>
            """
        )

    with section(
        "Ações operacionais",
        subtitle="Atalhos mais usados para seguir o fluxo do processo",
        divider=False,
    ):
        _render_operational_actions(
            int(selected_id),
            _strip_html(p.get("numero_processo")) or "",
            _strip_html(p.get("comarca")) or "",
            _strip_html(p.get("vara")) or "",
            pasta,
        )

    with section(
        "Resumo do registro",
        subtitle="Leitura rápida dos dados principais",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=2)
        with c1:
            card(
                "Status",
                _status_badge(status_atual),
                "situação",
                tone=_status_tone(status_atual),
            )
        with c2:
            card(
                "Atuação",
                _atuacao_badge(p.get("papel")),
                "classificação",
                tone="neutral",
            )
        with c3:
            card(
                "Categoria",
                _strip_html(p.get("categoria_servico")) or "—",
                "serviço",
                tone="neutral",
            )
        with c4:
            card(
                "Cliente",
                _strip_html(p.get("contratante")) or "—",
                "contratante",
                tone="info",
            )

    with section(
        "Operação vinculada",
        subtitle="Indicadores já conectados a este processo",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=2)
        with c1:
            card(
                "Prazos abertos",
                f"{prazos_abertos}",
                f"próximo: {proximo_prazo}",
                tone="warning" if prazos_abertos else "neutral",
            )
        with c2:
            card(
                "Agenda futura",
                f"{agendamentos_futuros}",
                f"próximo: {proximo_agendamento}",
                tone="info" if agendamentos_futuros else "neutral",
            )
        with c3:
            card("Receitas", receitas, "acumulado", tone="success")
        with c4:
            card(
                "Saldo",
                saldo,
                f"despesas: {despesas}",
                tone="success" if (p.get("saldo", 0) or 0) >= 0 else "danger",
            )

    left, right = grid_weights((1.12, 1.0), weights_mobile=(1, 1), gap="medium")

    with left:
        with section(
            "Contexto do processo",
            subtitle="Informações úteis para entendimento rápido do registro",
            divider=False,
        ):
            _render_html(
                f"""
                <div class="sp-side-panel">
                  <div class="sp-metric-line"><div class="sp-metric-label">Descrição</div><div class="sp-metric-value">{descricao}</div></div>
                  <div class="sp-metric-line"><div class="sp-metric-label">Comarca / Vara</div><div class="sp-metric-value">{comarca} • {vara}</div></div>
                  <div class="sp-metric-line"><div class="sp-metric-label">Cliente</div><div class="sp-metric-value">{contratante}</div></div>
                  <div class="sp-metric-line"><div class="sp-metric-label">Pasta local</div><div class="sp-metric-value">{pasta_html}</div></div>
                  <div class="sp-metric-line"><div class="sp-metric-label">Próximo prazo</div><div class="sp-metric-value">{proximo_prazo}</div></div>
                  <div class="sp-metric-line"><div class="sp-metric-label">Próxima agenda</div><div class="sp-metric-value">{proximo_agendamento}</div></div>
                </div>
                """
            )

        spacer(0.12)

        with section(
            "Observações",
            subtitle="Resumo útil para retomada rápida do caso",
            divider=False,
        ):
            _render_html(
                f"""
                <div class="sp-side-panel">
                  <div style="color:rgba(15,23,42,.76); line-height:1.55;">
                    {obs}
                  </div>
                </div>
                """
            )

    with right:
        with section(
            "Próximos passos recomendados",
            subtitle="Sugestões operacionais com base no estado atual do registro",
            divider=False,
        ):
            _render_next_steps_panel(p)

        spacer(0.12)

        with section(
            "Ações administrativas",
            subtitle="Operações menos frequentes para este registro",
            divider=False,
        ):
            a, b = grid(2, columns_mobile=1)
            with a:
                _button(
                    "📄 Duplicar",
                    key=f"proc_duplicate_{selected_id}",
                    on_click=_duplicate_processo,
                    args=(owner_user_id, int(selected_id)),
                )
            with b:
                pasta_key = f"proc_edit_pasta_{selected_id}"
                st.session_state.setdefault(pasta_key, p.get("pasta_local", "") or "")
                current_pasta = st.session_state.get(pasta_key, "") or ""
                if _button(
                    "📂 Abrir pasta",
                    key=f"proc_open_folder_{selected_id}",
                    disabled=not bool(current_pasta.strip()),
                ):
                    ok, msg = _open_folder(current_pasta)
                    if ok:
                        _toast("📂 Pasta aberta")
                    else:
                        st.warning(msg)

    with section(
        "Editar dados do processo",
        subtitle="Ajuste os campos principais do registro abaixo",
        divider=False,
    ):
        pasta_key = f"proc_edit_pasta_{selected_id}"
        st.session_state.setdefault(pasta_key, p.get("pasta_local", "") or "")

        a, b = grid(2, columns_mobile=1)
        with a:
            if _button(
                "📁 Escolher pasta…", key=f"proc_edit_pick_folder_{selected_id}"
            ):
                chosen = _pick_folder_dialog(initialdir=str(ROOT_TRABALHOS))
                if chosen:
                    st.session_state[pasta_key] = chosen
                    st.rerun()
        with b:
            st.caption(
                "Use este formulário para manter o cadastro principal atualizado."
            )

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
                        CATEGORIAS_UI.index(cat_atual)
                        if cat_atual in CATEGORIAS_UI
                        else 0
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
                height=140,
            )

            atualizar = st.form_submit_button(
                "Salvar alterações", type="primary", use_container_width=True
            )

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
                _toast("✅ Processo atualizado")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")

    with section(
        "Zona de exclusão",
        subtitle="Use apenas quando tiver certeza de que deseja remover o registro.",
        divider=False,
    ):
        a, b = grid(2, columns_mobile=1)
        with a:
            confirm = st.checkbox(
                "Confirmar exclusão", value=False, key=f"proc_del_confirm_{selected_id}"
            )
        with b:
            if _button(
                "🗑️ Excluir processo",
                key=f"proc_delete_{selected_id}",
                disabled=not bool(confirm),
            ):
                try:
                    with get_session() as s:
                        ProcessosService.delete(s, owner_user_id, int(selected_id))
                    bump_data_version(owner_user_id)
                    st.session_state.pop(K_SELECTED_ID, None)
                    _toast("🗑️ Processo excluído")
                    _set_section("Lista")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

        st.caption("A exclusão remove definitivamente o registro do banco.")
