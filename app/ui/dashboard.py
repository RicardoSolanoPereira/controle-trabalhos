from __future__ import annotations

from datetime import date, datetime, time, timedelta
from html import escape
from typing import Any, Callable, Iterable

import pandas as pd
import streamlit as st
from sqlalchemy import case, func, select

from db.connection import get_session
from db.models import Agendamento, LancamentoFinanceiro, Prazo, Processo
from services.utils import ensure_br, format_date_br, now_br
from ui.layout import content_shell, empty_state, grid, grid_weights, section, spacer
from ui.page_header import HeaderAction, page_header
from ui.theme import card
from ui_state import (
    get_data_version,
    set_current_menu,
    set_current_section,
)

ATUACAO_UI = {
    "(Todas)": None,
    "Perícia (Juízo)": "Perito Judicial",
    "Assistência Técnica": "Assistente Técnico",
    "Particular / Outros serviços": "Trabalho Particular",
}


# ==========================================================
# Base helpers
# ==========================================================


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _esc(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return escape(text) if text else fallback


def _inject_dashboard_css() -> None:
    css_key = "_sp_dashboard_css_v70"
    if st.session_state.get(css_key):
        return
    st.session_state[css_key] = True

    _render_html(
        """
        <style>
        .sp-dash-filter-surface{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:14px;
            flex-wrap:wrap;
            padding:14px 16px;
            border:1px solid rgba(15,23,42,.06);
            border-radius:20px;
            background:linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(248,250,252,.94) 100%);
            box-shadow:0 1px 2px rgba(15,23,42,.03), 0 10px 24px rgba(15,23,42,.04);
        }

        .sp-dash-filter-copy{
            display:flex;
            flex-direction:column;
            gap:4px;
        }

        .sp-dash-filter-kicker,
        .sp-dash-hero-kicker,
        .sp-dash-focus-kicker,
        .sp-dash-band-kicker{
            font-size:.72rem;
            font-weight:800;
            letter-spacing:.08em;
            text-transform:uppercase;
            color:rgba(15,23,42,.45);
        }

        .sp-dash-filter-text{
            color:rgba(15,23,42,.72);
            font-size:.90rem;
            line-height:1.45;
            max-width:62ch;
        }

        .sp-dash-hero{
            position:relative;
            overflow:hidden;
            padding:22px 24px;
            border:1px solid rgba(15,23,42,.06);
            border-radius:22px;
            background:
                radial-gradient(circle at top right, rgba(53,94,87,.10), transparent 28%),
                linear-gradient(180deg, rgba(255,255,255,.99) 0%, rgba(247,250,249,.96) 100%);
            box-shadow:
                0 1px 2px rgba(15,23,42,.03),
                0 16px 34px rgba(15,23,42,.05);
        }

        .sp-dash-hero::after{
            content:"";
            position:absolute;
            top:-36px;
            right:-16px;
            width:160px;
            height:160px;
            border-radius:999px;
            background:radial-gradient(circle, rgba(53,94,87,.10), transparent 70%);
            pointer-events:none;
        }

        .sp-dash-hero-top{
            position:relative;
            z-index:1;
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:14px;
            flex-wrap:wrap;
        }

        .sp-dash-hero-title{
            font-size:1.26rem;
            font-weight:840;
            line-height:1.18;
            color:#0f172a;
            letter-spacing:-0.02em;
            max-width:38ch;
        }

        .sp-dash-hero-copy{
            color:rgba(15,23,42,.70);
            font-size:.94rem;
            line-height:1.54;
            margin-top:7px;
            max-width:76ch;
        }

        .sp-dash-hero-meta{
            position:relative;
            z-index:1;
            display:flex;
            gap:8px;
            flex-wrap:wrap;
            margin-top:15px;
        }

        .sp-dash-command{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:12px;
            flex-wrap:wrap;
            padding:14px 16px;
            border:1px solid rgba(15,23,42,.06);
            border-radius:18px;
            background:linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(248,250,252,.95) 100%);
            box-shadow:0 1px 2px rgba(15,23,42,.03);
        }

        .sp-dash-command-title{
            font-size:1rem;
            font-weight:810;
            color:#0f172a;
            line-height:1.3;
        }

        .sp-dash-command-sub{
            font-size:.87rem;
            line-height:1.44;
            color:rgba(15,23,42,.64);
            margin-top:4px;
            max-width:72ch;
        }

        .sp-dash-band{
            padding:16px 18px;
            border:1px solid rgba(15,23,42,.07);
            border-radius:20px;
            background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(249,250,251,.96) 100%);
            box-shadow:0 1px 3px rgba(15,23,42,.03), 0 10px 22px rgba(15,23,42,.04);
        }

        .sp-dash-band-title{
            margin-top:4px;
            font-size:1.06rem;
            font-weight:820;
            line-height:1.28;
            color:#0f172a;
        }

        .sp-dash-band-copy{
            margin-top:6px;
            font-size:.90rem;
            line-height:1.48;
            color:rgba(15,23,42,.67);
            max-width:72ch;
        }

        .sp-dash-alert-strip{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:12px;
            flex-wrap:wrap;
            padding:12px 14px;
            border-radius:16px;
            border:1px solid rgba(15,23,42,.08);
            background:#fff;
            box-shadow:0 1px 2px rgba(15,23,42,.03);
        }

        .sp-dash-alert-strip-danger{
            border-left:4px solid #dc2626;
            background:linear-gradient(180deg, rgba(254,242,242,.95) 0%, rgba(255,255,255,1) 100%);
        }

        .sp-dash-alert-strip-warning{
            border-left:4px solid #f59e0b;
            background:linear-gradient(180deg, rgba(255,251,235,.95) 0%, rgba(255,255,255,1) 100%);
        }

        .sp-dash-alert-strip-info{
            border-left:4px solid #2563eb;
            background:linear-gradient(180deg, rgba(239,246,255,.95) 0%, rgba(255,255,255,1) 100%);
        }

        .sp-dash-alert-strip-success{
            border-left:4px solid #16a34a;
            background:linear-gradient(180deg, rgba(240,253,244,.95) 0%, rgba(255,255,255,1) 100%);
        }

        .sp-dash-alert-title{
            font-size:.92rem;
            font-weight:800;
            color:#0f172a;
            line-height:1.32;
        }

        .sp-dash-alert-sub{
            margin-top:4px;
            font-size:.85rem;
            line-height:1.42;
            color:rgba(15,23,42,.66);
            max-width:72ch;
        }

        .sp-dash-focus{
            padding:18px;
            border:1px solid rgba(15,23,42,.08);
            border-radius:20px;
            background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(249,250,251,.95) 100%);
            box-shadow:0 1px 3px rgba(15,23,42,.04), 0 14px 28px rgba(15,23,42,.04);
        }

        .sp-dash-focus-danger{ border-left:4px solid #dc2626; }
        .sp-dash-focus-warning{ border-left:4px solid #f59e0b; }
        .sp-dash-focus-info{ border-left:4px solid #2563eb; }
        .sp-dash-focus-success{ border-left:4px solid #16a34a; }

        .sp-dash-focus-title{
            font-size:1.05rem;
            font-weight:810;
            line-height:1.30;
            color:#0f172a;
        }

        .sp-dash-focus-copy{
            margin-top:6px;
            color:rgba(15,23,42,.70);
            line-height:1.50;
            font-size:.91rem;
        }

        .sp-dash-chip-row{
            display:flex;
            gap:8px;
            flex-wrap:wrap;
            margin-top:10px;
        }

        .sp-dash-focus-list{
            margin-top:12px;
            display:flex;
            flex-direction:column;
            gap:8px;
        }

        .sp-dash-focus-item{
            display:flex;
            gap:8px;
            align-items:flex-start;
            padding:10px 11px;
            border:1px solid rgba(15,23,42,.07);
            border-radius:13px;
            background:rgba(248,250,252,.78);
            color:#0f172a;
            font-size:.88rem;
            line-height:1.38;
        }

        .sp-dash-compact-list,
        .sp-dash-feed,
        .sp-dash-suggest-list{
            display:flex;
            flex-direction:column;
            gap:10px;
        }

        .sp-dash-compact-item,
        .sp-dash-feed-item,
        .sp-dash-suggest-item{
            border:1px solid rgba(15,23,42,.08);
            border-radius:16px;
            padding:12px 13px;
            background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(249,250,251,.96) 100%);
            box-shadow:0 1px 2px rgba(15,23,42,.03);
        }

        .sp-dash-compact-top,
        .sp-dash-feed-top{
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:10px;
        }

        .sp-dash-compact-title,
        .sp-dash-feed-title,
        .sp-dash-suggest-title{
            font-weight:790;
            color:#0f172a;
            line-height:1.32;
            font-size:.92rem;
        }

        .sp-dash-compact-sub,
        .sp-dash-feed-sub,
        .sp-dash-suggest-sub{
            margin-top:4px;
            color:rgba(15,23,42,.63);
            font-size:.84rem;
            line-height:1.40;
        }

        .sp-dash-module{
            border:1px solid rgba(15,23,42,.08);
            border-radius:20px;
            padding:15px;
            background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(249,250,251,.96) 100%);
            box-shadow:0 1px 3px rgba(15,23,42,.03), 0 10px 24px rgba(15,23,42,.035);
            height:100%;
        }

        .sp-dash-module-head{
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:10px;
            margin-bottom:10px;
        }

        .sp-dash-module-title{
            font-weight:810;
            font-size:1rem;
            line-height:1.28;
            color:#0f172a;
        }

        .sp-dash-module-copy{
            color:rgba(15,23,42,.67);
            font-size:.88rem;
            line-height:1.42;
            margin-top:3px;
        }

        .sp-dash-module-list{
            display:flex;
            flex-direction:column;
            gap:9px;
            margin-top:8px;
            margin-bottom:12px;
        }

        .sp-dash-module-row{
            padding:10px 11px;
            border:1px solid rgba(15,23,42,.07);
            border-radius:13px;
            background:rgba(248,250,252,.78);
        }

        .sp-dash-module-row-title{
            font-size:.87rem;
            font-weight:760;
            line-height:1.32;
            color:#0f172a;
        }

        .sp-dash-module-row-sub{
            font-size:.82rem;
            line-height:1.38;
            color:rgba(15,23,42,.62);
            margin-top:3px;
        }

        .sp-dash-list-card{
            border:1px solid rgba(15,23,42,.08);
            border-radius:16px;
            padding:13px 14px;
            background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(249,250,251,.96) 100%);
            box-shadow:0 1px 2px rgba(15,23,42,.03);
        }

        .sp-dash-list-card-danger{ border-left:4px solid #dc2626; }
        .sp-dash-list-card-warning{ border-left:4px solid #f59e0b; }
        .sp-dash-list-card-info{ border-left:4px solid #2563eb; }
        .sp-dash-list-card-success{ border-left:4px solid #16a34a; }

        .sp-dash-list-card-title{
            font-size:.92rem;
            font-weight:800;
            line-height:1.34;
            color:#0f172a;
        }

        .sp-dash-list-card-sub{
            margin-top:5px;
            font-size:.84rem;
            line-height:1.42;
            color:rgba(15,23,42,.66);
        }

        .sp-dashboard-action-grid .stButton > button{
            min-height:50px !important;
            font-weight:740 !important;
            white-space:normal !important;
            word-break:break-word !important;
            border-radius:14px !important;
        }

        section[data-testid="stSidebar"] .stButton > button{
            white-space:normal !important;
            word-break:break-word !important;
            height:auto !important;
            min-height:44px !important;
        }

        div[data-baseweb="tab-list"]{
            gap:.34rem;
            padding:.2rem 0 .2rem 0;
        }

        div[data-baseweb="tab"]{
            border-radius:12px !important;
            padding:.56rem .92rem !important;
            background:rgba(15,23,42,.04);
            font-weight:780 !important;
        }

        div[data-baseweb="tab-highlight"]{
            border-radius:999px !important;
        }

        [data-testid="stDataFrame"]{
            border-radius:14px;
            overflow:hidden;
        }

        @media (max-width:768px){
            .sp-dash-filter-surface,
            .sp-dash-hero,
            .sp-dash-band,
            .sp-dash-focus,
            .sp-dash-module,
            .sp-dash-alert-strip,
            .sp-dash-command,
            .sp-dash-list-card{
                border-radius:16px;
                padding:13px;
            }

            .sp-dash-hero-title{
                font-size:1.08rem;
            }
        }
        </style>
        """
    )


def _naive(dt: datetime) -> datetime:
    try:
        if getattr(dt, "tzinfo", None) is not None:
            return dt.replace(tzinfo=None)
    except Exception:
        pass
    return dt


def _fmt_money_br(value: float) -> str:
    try:
        parsed = float(value or 0)
    except Exception:
        parsed = 0.0
    return f"{parsed:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _safe_text(value: Any, fallback: str = "—") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else fallback


def _apply_tipo_filter(stmt, tipo_val: str | None):
    return stmt if not tipo_val else stmt.where(Processo.papel == tipo_val)


def _dt_bounds(hoje: date) -> tuple[datetime, datetime, datetime]:
    ate_7_dias = hoje + timedelta(days=7)
    start_today = datetime.combine(hoje, time.min)
    end_7d = datetime.combine(ate_7_dias, time.max)
    now_n = _naive(now_br())
    return start_today, end_7d, now_n


def _greeting() -> str:
    hour = now_br().hour
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"


def _today_label() -> str:
    dias = [
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    ]
    agora = now_br()
    return f"{dias[agora.weekday()]}, {agora.strftime('%d/%m/%Y')}"


# ==========================================================
# Navegação SaaS
# ==========================================================


def _sync_query_params(menu: str, section: str | None = None) -> None:
    try:
        st.query_params["menu"] = menu
        if section:
            st.query_params["section"] = section
        else:
            try:
                del st.query_params["section"]
            except Exception:
                pass
    except Exception:
        pass


def _go_to(menu: str, section: str | None = None) -> None:
    set_current_menu(menu)
    if section:
        set_current_section(menu, section)
    _sync_query_params(menu, section)


def _nav_map(menu: str, state: dict[str, Any] | None) -> str | None:
    if not state:
        return None

    mapping = {
        "Prazos": "prazos_section",
        "Trabalhos": "trabalhos_section",
        "Financeiro": "financeiro_section",
        "Agenda": "agenda_section",
        "Andamentos": "andamentos_section",
    }

    key = mapping.get(menu)
    return state.get(key) if key else None


def _render_nav_button(
    label: str,
    *,
    page: str,
    state: dict[str, Any] | None = None,
    key: str,
    type: str = "secondary",
) -> None:
    section = _nav_map(page, state)
    st.button(
        label,
        key=key,
        type=type,
        use_container_width=True,
        on_click=_go_to,
        args=(page, section),
    )


def _render_action_button(
    label: str,
    *,
    key: str,
    on_click: Callable[[], None],
    button_type: str = "secondary",
) -> None:
    st.button(
        label,
        key=key,
        type=button_type,
        use_container_width=True,
        on_click=on_click,
    )


def _render_dataframe_or_caption(
    df: pd.DataFrame,
    *,
    empty_title: str = "Nada por aqui",
    empty_subtitle: str = "Não há registros para exibir neste recorte.",
    empty_icon: str = "📭",
    height: int | None = None,
) -> None:
    if df.empty:
        empty_state(
            title=empty_title,
            subtitle=empty_subtitle,
            icon=empty_icon,
        )
        return

    dataframe_kwargs = {
        "use_container_width": True,
        "hide_index": True,
    }
    if height is not None:
        dataframe_kwargs["height"] = height

    st.dataframe(df, **dataframe_kwargs)


# ==========================================================
# Regras de prazo
# ==========================================================


def _dias_restantes(dt: Any) -> int:
    dt_br = ensure_br(dt)
    hoje = now_br().date()
    return (dt_br.date() - hoje).days


def _status_prazo(dias: int) -> str:
    if dias < 0:
        return "Atrasado"
    if dias <= 5:
        return "Urgente"
    if dias <= 10:
        return "Atenção"
    return "Em dia"


def _tone_from_prazo_status(dias: int) -> str:
    if dias < 0:
        return "danger"
    if dias <= 5:
        return "warning"
    if dias <= 10:
        return "info"
    return "success"


def _prior_badge(prioridade: str | None) -> str:
    prioridade_norm = (prioridade or "Média").strip().lower()
    if prioridade_norm.startswith("a"):
        return "Alta"
    if prioridade_norm.startswith("b"):
        return "Baixa"
    return "Média"


# ==========================================================
# Regras de agenda
# ==========================================================


def _agenda_status(hours_left: float) -> tuple[str, str]:
    if hours_left < 0:
        return "Atrasado", "danger"
    if hours_left <= 24:
        return "Urgente", "warning"
    if hours_left <= 72:
        return "Atenção", "info"
    return "Programado", "success"


def _agenda_rest_chip(hours_left: float) -> str:
    if hours_left < 0:
        return "<span class='sp-chip sp-chip-danger'>⏳ vencido</span>"

    if hours_left < 24:
        rest_txt = f"{max(0, int(round(hours_left)))}h"
    else:
        rest_txt = f"{max(0, int(round(hours_left / 24)))}d"

    return f"<span class='sp-chip'>⏳ em {rest_txt}</span>"


def _kpi_agenda_subtitle(ag_24h: int, ag_72h: int, ag_7d: int) -> str:
    if ag_7d <= 0:
        return "nenhum compromisso"
    if ag_24h > 0:
        return f"{ag_24h} em 24h • {ag_7d} em 7d"
    if ag_72h > 0:
        return f"{ag_72h} em 72h • {ag_7d} em 7d"
    return f"{ag_7d} em 7d"


def _kpi_agenda_tone(ag_24h: int, ag_72h: int, ag_7d: int) -> tuple[str, bool]:
    if ag_24h > 0:
        return "danger", True
    if ag_72h > 0:
        return "info", False
    if ag_7d > 0:
        return "success", False
    return "neutral", False


# ==========================================================
# Builders de dataframe
# ==========================================================


def _build_prazos_df(rows: Iterable[tuple]) -> pd.DataFrame:
    items: list[dict[str, Any]] = []

    for (
        _id,
        evento,
        data_limite,
        prioridade,
        numero_trabalho,
        descricao_trabalho,
    ) in rows:
        dias = int(_dias_restantes(data_limite))
        items.append(
            {
                "Trabalho": f"{_safe_text(numero_trabalho, 'Sem referência')} – {_safe_text(descricao_trabalho, 'Sem descrição')}",
                "Evento": _safe_text(evento, "Sem evento"),
                "Vencimento": format_date_br(data_limite),
                "Dias": dias,
                "Status": _status_prazo(dias),
                "Prioridade": _prior_badge(prioridade),
            }
        )

    if not items:
        return pd.DataFrame()

    return pd.DataFrame(items).sort_values(by=["Dias", "Vencimento"], ascending=True)


def _build_agenda_df(rows: Iterable[tuple]) -> pd.DataFrame:
    items: list[dict[str, str]] = []

    for _id, tipo, inicio, local, numero_trabalho, descricao_trabalho in rows:
        items.append(
            {
                "Trabalho": f"{_safe_text(numero_trabalho, 'Sem referência')} – {_safe_text(descricao_trabalho, 'Sem descrição')}",
                "Tipo": _safe_text(tipo, "Sem tipo"),
                "Início": ensure_br(inicio).strftime("%d/%m/%Y %H:%M"),
                "Local": _safe_text(local, "—"),
            }
        )

    return pd.DataFrame(items) if items else pd.DataFrame()


def _build_trabalhos_df(rows: list[tuple]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        rows,
        columns=[
            "id",
            "numero_trabalho",
            "descricao_trabalho",
            "comarca",
            "vara",
            "status",
            "tipo_trabalho",
        ],
    )

    df["descricao_trabalho"] = df["descricao_trabalho"].fillna("Sem descrição")
    df["tipo_trabalho"] = df["tipo_trabalho"].fillna("Assistente Técnico")
    df["comarca"] = df["comarca"].fillna("—")
    df["vara"] = df["vara"].fillna("—")
    df["status"] = df["status"].fillna("—")

    return df.rename(
        columns={
            "id": "ID",
            "numero_trabalho": "Referência",
            "descricao_trabalho": "Descrição",
            "comarca": "Comarca",
            "vara": "Vara",
            "status": "Status",
            "tipo_trabalho": "Atuação",
        }
    )


# ==========================================================
# Navegação específica do dashboard
# ==========================================================


def _go_prazos_lista() -> None:
    _go_to("Prazos", "Lista")


def _go_trabalhos_lista() -> None:
    _go_to("Trabalhos", "Lista")


def _go_financeiro_lancamentos() -> None:
    _go_to("Financeiro", "Lançamentos")


def _go_agenda() -> None:
    _go_to("Agenda", "Agenda")


def _go_prazos_cadastro() -> None:
    _go_to("Prazos", "Cadastro")


def _go_trabalhos_cadastro() -> None:
    _go_to("Trabalhos", "Cadastro")


# ==========================================================
# Estado visual simplificado
# ==========================================================


def _build_focus_state(kpis: dict[str, Any]) -> dict[str, Any]:
    if kpis["prazos_atrasados"] > 0:
        return {
            "tone": "danger",
            "kicker": "atenção imediata",
            "title": f"{kpis['prazos_atrasados']} prazo(s) vencido(s)",
            "copy": "Comece regularizando os itens atrasados antes de abrir novas frentes.",
            "chips": [
                f"<span class='sp-chip sp-chip-danger'>Atrasados: {kpis['prazos_atrasados']}</span>",
                f"<span class='sp-chip'>Em 7 dias: {kpis['prazos_7dias']}</span>",
            ],
            "items": [
                "Abrir a lista de pendências vencidas",
                "Tratar primeiro os itens com maior urgência",
                "Registrar a atualização logo após cada avanço",
            ],
            "primary": ("Ver prazos", _go_prazos_lista),
            "secondary": ("Novo prazo", _go_prazos_cadastro),
        }

    if kpis["ag_24h"] > 0:
        return {
            "tone": "warning",
            "kicker": "próxima ação",
            "title": f"{kpis['ag_24h']} compromisso(s) em 24h",
            "copy": "Revise horário, local, deslocamento e documentos antes do próximo compromisso.",
            "chips": [
                f"<span class='sp-chip sp-chip-warning'>Agenda 24h: {kpis['ag_24h']}</span>",
                f"<span class='sp-chip'>Agenda 7 dias: {kpis['ag_7d']}</span>",
            ],
            "items": [
                "Conferir horário e local",
                "Separar documentos e anexos",
                "Confirmar logística da visita ou audiência",
            ],
            "primary": ("Ver agenda", _go_agenda),
            "secondary": ("Ver trabalhos", _go_trabalhos_lista),
        }

    if kpis["prazos_7dias"] > 0:
        return {
            "tone": "info",
            "kicker": "janela da semana",
            "title": f"{kpis['prazos_7dias']} prazo(s) em até 7 dias",
            "copy": "Antecipar a organização desta semana reduz urgências e retrabalho.",
            "chips": [
                f"<span class='sp-chip sp-chip-info'>Em 7 dias: {kpis['prazos_7dias']}</span>",
                f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
            ],
            "items": [
                "Revisar o calendário da semana",
                "Separar as peças por trabalho",
                "Distribuir a carga antes do vencimento",
            ],
            "primary": ("Ver prazos", _go_prazos_lista),
            "secondary": ("Novo trabalho", _go_trabalhos_cadastro),
        }

    return {
        "tone": "success",
        "kicker": "painel estável",
        "title": "Sem pendências críticas agora",
        "copy": "Bom momento para atualizar cadastros, revisar trabalhos e manter a operação em dia.",
        "chips": [
            "<span class='sp-chip sp-chip-success'>Sem urgência crítica</span>",
            f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
        ],
        "items": [
            "Atualizar trabalhos em andamento",
            "Cadastrar novos prazos ou compromissos",
            "Revisar agenda e financeiro",
        ],
        "primary": ("Novo trabalho", _go_trabalhos_cadastro),
        "secondary": ("Abrir financeiro", _go_financeiro_lancamentos),
    }


# ==========================================================
# Timeline
# ==========================================================


def _build_timeline_items(
    rows_prazos_atrasados: list,
    rows_prazos_7d: list,
    rows_ag_24h: list,
    rows_ag_7d: list,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for (
        _id,
        evento,
        data_limite,
        prioridade,
        numero_trabalho,
        descricao_trabalho,
    ) in rows_prazos_atrasados:
        dias = int(_dias_restantes(data_limite))
        items.append(
            {
                "sort_dt": ensure_br(data_limite),
                "tone": "danger",
                "kind": "Prazo",
                "headline": f"{_safe_text(numero_trabalho, 'Sem referência')} – {_safe_text(evento, 'Sem evento')}",
                "meta": f"vencido há {abs(dias)} dia(s)",
                "detail": _safe_text(descricao_trabalho, "Sem descrição"),
            }
        )

    for (
        _id,
        evento,
        data_limite,
        prioridade,
        numero_trabalho,
        descricao_trabalho,
    ) in rows_prazos_7d:
        dias = int(_dias_restantes(data_limite))
        items.append(
            {
                "sort_dt": ensure_br(data_limite),
                "tone": _tone_from_prazo_status(dias),
                "kind": "Prazo",
                "headline": f"{_safe_text(numero_trabalho, 'Sem referência')} – {_safe_text(evento, 'Sem evento')}",
                "meta": f"vence em {dias} dia(s)",
                "detail": _safe_text(descricao_trabalho, "Sem descrição"),
            }
        )

    for _id, tipo, inicio, local, numero_trabalho, descricao_trabalho in rows_ag_24h:
        inicio_br = ensure_br(inicio)
        hours_left = (_naive(inicio_br) - _naive(now_br())).total_seconds() / 3600.0
        _label, tone = _agenda_status(hours_left)
        items.append(
            {
                "sort_dt": inicio_br,
                "tone": tone,
                "kind": "Agenda",
                "headline": f"{_safe_text(numero_trabalho, 'Sem referência')} – {_safe_text(tipo, 'Sem tipo')}",
                "meta": inicio_br.strftime("%d/%m %H:%M"),
                "detail": _safe_text(
                    local, _safe_text(descricao_trabalho, "Sem local")
                ),
            }
        )

    seen_agenda_keys: set[str] = set()
    for _id, *_rest in rows_ag_24h:
        seen_agenda_keys.add(f"{_id}")

    for _id, tipo, inicio, local, numero_trabalho, descricao_trabalho in rows_ag_7d:
        if f"{_id}" in seen_agenda_keys:
            continue
        inicio_br = ensure_br(inicio)
        hours_left = (_naive(inicio_br) - _naive(now_br())).total_seconds() / 3600.0
        _label, tone = _agenda_status(hours_left)
        items.append(
            {
                "sort_dt": inicio_br,
                "tone": tone,
                "kind": "Agenda",
                "headline": f"{_safe_text(numero_trabalho, 'Sem referência')} – {_safe_text(tipo, 'Sem tipo')}",
                "meta": inicio_br.strftime("%d/%m %H:%M"),
                "detail": _safe_text(
                    local, _safe_text(descricao_trabalho, "Sem local")
                ),
            }
        )

    items.sort(key=lambda x: x["sort_dt"])
    return items[:4]


# ==========================================================
# Queries cacheadas
# ==========================================================


@st.cache_data(show_spinner=False, ttl=45)
def _fetch_kpis_cached(
    owner_user_id: int,
    tipo_val: str | None,
    hoje_iso: str,
    version: int,
) -> dict[str, Any]:
    _ = version

    hoje_sp = date.fromisoformat(hoje_iso)
    start_today, end_7d, now_n = _dt_bounds(hoje_sp)

    with get_session() as s:
        stmt_total = select(func.count(Processo.id)).where(
            Processo.owner_user_id == owner_user_id
        )
        stmt_total = _apply_tipo_filter(stmt_total, tipo_val)
        total_trabalhos = int(s.execute(stmt_total).scalar_one())

        stmt_ativos = select(func.count(Processo.id)).where(
            Processo.owner_user_id == owner_user_id,
            Processo.status == "Ativo",
        )
        stmt_ativos = _apply_tipo_filter(stmt_ativos, tipo_val)
        ativos = int(s.execute(stmt_ativos).scalar_one())

        stmt_prazos_counts = (
            select(
                func.count(Prazo.id).label("abertos"),
                func.coalesce(
                    func.sum(case((Prazo.data_limite < start_today, 1), else_=0)),
                    0,
                ).label("atrasados"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (
                                    (Prazo.data_limite >= start_today)
                                    & (Prazo.data_limite <= end_7d)
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("em_7d"),
            )
            .select_from(Prazo)
            .join(Processo, Processo.id == Prazo.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Prazo.concluido.is_(False),
            )
        )
        stmt_prazos_counts = _apply_tipo_filter(stmt_prazos_counts, tipo_val)
        prazos_abertos, prazos_atrasados, prazos_7dias = s.execute(
            stmt_prazos_counts
        ).one()

        stmt_ag_7d = (
            select(func.count(Agendamento.id))
            .join(Processo, Processo.id == Agendamento.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Agendamento.status == "Agendado",
                Agendamento.inicio >= now_n,
                Agendamento.inicio <= now_n + timedelta(days=7),
            )
        )
        stmt_ag_7d = _apply_tipo_filter(stmt_ag_7d, tipo_val)
        ag_7d = int(s.execute(stmt_ag_7d).scalar_one())

        stmt_ag_24h = (
            select(func.count(Agendamento.id))
            .join(Processo, Processo.id == Agendamento.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Agendamento.status == "Agendado",
                Agendamento.inicio >= now_n,
                Agendamento.inicio <= now_n + timedelta(hours=24),
            )
        )
        stmt_ag_24h = _apply_tipo_filter(stmt_ag_24h, tipo_val)
        ag_24h = int(s.execute(stmt_ag_24h).scalar_one())

        stmt_ag_72h = (
            select(func.count(Agendamento.id))
            .join(Processo, Processo.id == Agendamento.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Agendamento.status == "Agendado",
                Agendamento.inicio >= now_n,
                Agendamento.inicio <= now_n + timedelta(hours=72),
            )
        )
        stmt_ag_72h = _apply_tipo_filter(stmt_ag_72h, tipo_val)
        ag_72h = int(s.execute(stmt_ag_72h).scalar_one())

        stmt_fin = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                LancamentoFinanceiro.tipo == "Receita",
                                LancamentoFinanceiro.valor,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("receitas"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                LancamentoFinanceiro.tipo == "Despesa",
                                LancamentoFinanceiro.valor,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("despesas"),
            )
            .select_from(LancamentoFinanceiro)
            .join(Processo, Processo.id == LancamentoFinanceiro.processo_id)
            .where(Processo.owner_user_id == owner_user_id)
        )
        stmt_fin = _apply_tipo_filter(stmt_fin, tipo_val)
        receitas, despesas = s.execute(stmt_fin).one()

    receitas = float(receitas or 0)
    despesas = float(despesas or 0)

    return {
        "hoje_sp": hoje_sp,
        "start_today": start_today,
        "end_7d": end_7d,
        "now_n": now_n,
        "total_trabalhos": total_trabalhos,
        "ativos": ativos,
        "prazos_abertos": int(prazos_abertos or 0),
        "prazos_atrasados": int(prazos_atrasados or 0),
        "prazos_7dias": int(prazos_7dias or 0),
        "ag_7d": ag_7d,
        "ag_24h": ag_24h,
        "ag_72h": ag_72h,
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
    }


@st.cache_data(show_spinner=False, ttl=45)
def _fetch_prazos_tables_cached(
    owner_user_id: int,
    tipo_val: str | None,
    start_today_iso: str,
    end_7d_iso: str,
    version: int,
) -> tuple[list, list]:
    _ = version

    start_today = datetime.fromisoformat(start_today_iso)
    end_7d = datetime.fromisoformat(end_7d_iso)

    with get_session() as s:
        stmt_base = (
            select(
                Prazo.id,
                Prazo.evento,
                Prazo.data_limite,
                Prazo.prioridade,
                Processo.numero_processo,
                Processo.tipo_acao,
            )
            .join(Processo, Processo.id == Prazo.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Prazo.concluido.is_(False),
            )
            .order_by(Prazo.data_limite.asc())
            .limit(10)
        )
        stmt_base = _apply_tipo_filter(stmt_base, tipo_val)

        rows_atrasados = s.execute(
            stmt_base.where(Prazo.data_limite < start_today)
        ).all()

        rows_7d = s.execute(
            stmt_base.where(
                Prazo.data_limite >= start_today,
                Prazo.data_limite <= end_7d,
            )
        ).all()

    return rows_atrasados, rows_7d


@st.cache_data(show_spinner=False, ttl=45)
def _fetch_agendamentos_cached(
    owner_user_id: int,
    tipo_val: str | None,
    now_n_iso: str,
    version: int,
) -> tuple[list, list]:
    _ = version

    now_n = datetime.fromisoformat(now_n_iso)

    with get_session() as s:
        stmt_base = (
            select(
                Agendamento.id,
                Agendamento.tipo,
                Agendamento.inicio,
                Agendamento.local,
                Processo.numero_processo,
                Processo.tipo_acao,
            )
            .join(Processo, Processo.id == Agendamento.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                Agendamento.status == "Agendado",
                Agendamento.inicio >= now_n,
            )
            .order_by(Agendamento.inicio.asc())
            .limit(10)
        )
        stmt_base = _apply_tipo_filter(stmt_base, tipo_val)

        rows_24h = s.execute(
            stmt_base.where(Agendamento.inicio <= now_n + timedelta(hours=24))
        ).all()

        rows_7d = s.execute(
            stmt_base.where(Agendamento.inicio <= now_n + timedelta(days=7))
        ).all()

    return rows_24h, rows_7d


@st.cache_data(show_spinner=False, ttl=60)
def _fetch_ultimos_trabalhos_cached(
    owner_user_id: int,
    tipo_val: str | None,
    version: int,
) -> list:
    _ = version

    with get_session() as s:
        stmt = (
            select(
                Processo.id,
                Processo.numero_processo,
                Processo.tipo_acao,
                Processo.comarca,
                Processo.vara,
                Processo.status,
                Processo.papel,
            )
            .where(Processo.owner_user_id == owner_user_id)
            .order_by(Processo.id.desc())
            .limit(12)
        )
        stmt = _apply_tipo_filter(stmt, tipo_val)
        return s.execute(stmt).all()


# ==========================================================
# Blocos visuais
# ==========================================================


def _header_badge(kpis: dict[str, Any]) -> tuple[str, str]:
    if kpis["prazos_atrasados"] > 0:
        return f"{kpis['prazos_atrasados']} atraso(s)", "danger"
    if kpis["ag_24h"] > 0:
        return f"{kpis['ag_24h']} em 24h", "warning"
    if kpis["prazos_7dias"] > 0:
        return f"{kpis['prazos_7dias']} na semana", "info"
    return "operação estável", "success"


def _render_header(kpis: dict[str, Any] | None = None) -> None:
    atrasados = (kpis or {}).get("prazos_atrasados", 0)
    agenda_24h = (kpis or {}).get("ag_24h", 0)
    ativos = (kpis or {}).get("ativos", 0)

    subtitle = (
        f"{_greeting()}. {_today_label()}. "
        f"{ativos} ativo(s), {atrasados} atraso(s), {agenda_24h} compromisso(s) em 24h."
    )

    badge, badge_tone = _header_badge(kpis or {})

    page_header(
        "Painel",
        subtitle,
        eyebrow="Operação",
        badge=badge,
        badge_tone=badge_tone,
        actions=[
            HeaderAction(
                "Prazos",
                key="dash_hdr_prazos",
                type="secondary",
                on_click=_go_prazos_lista,
                icon="⏳",
                emphasis="primary",
            ),
            HeaderAction(
                "Trabalhos",
                key="dash_hdr_trabalhos",
                type="secondary",
                on_click=_go_trabalhos_lista,
                icon="📁",
                emphasis="primary",
            ),
            HeaderAction(
                "Financeiro",
                key="dash_hdr_financeiro",
                type="secondary",
                on_click=_go_financeiro_lancamentos,
                icon="💰",
                emphasis="primary",
            ),
        ],
        compact=False,
        divider=False,
        bottom_spacing_rem=0.14,
    )


def _render_top_bar() -> str | None:
    with section(divider=False, compact=True):
        left, right = grid_weights((1.06, 0.94), weights_mobile=(1, 1), gap="medium")

        with left:
            atuacao_label = st.selectbox(
                "Atuação",
                list(ATUACAO_UI.keys()),
                index=0,
                key="dash_atuacao_ui",
                help="Filtra o painel pela atuação selecionada.",
            )

        with right:
            _render_html(
                """
                <div class="sp-dash-filter-surface">
                  <div class="sp-dash-filter-copy">
                    <div class="sp-dash-filter-kicker">contexto do painel</div>
                    <div class="sp-dash-filter-text">
                      Painel operacional filtrado por atuação, com foco em prioridades,
                      próximos itens e leitura rápida do dia.
                    </div>
                  </div>
                  <span class="sp-chip">tempo real</span>
                </div>
                """
            )

    return ATUACAO_UI[atuacao_label]


def _render_command_bar(kpis: dict[str, Any], atuacao_label: str) -> None:
    if kpis["prazos_atrasados"] > 0:
        title = "Prioridade máxima: regularizar pendências vencidas."
        sub = (
            f"Há {kpis['prazos_atrasados']} prazo(s) atrasado(s). "
            "Abra a fila de prazos e trate primeiro o que já venceu."
        )
        chip = f"<span class='sp-chip sp-chip-danger'>{kpis['prazos_atrasados']} atraso(s)</span>"
    elif kpis["ag_24h"] > 0:
        title = "Seu próximo compromisso já pede preparação."
        sub = (
            f"Há {kpis['ag_24h']} compromisso(s) nas próximas 24 horas. "
            "Revise local, horário, deslocamento e documentos."
        )
        chip = f"<span class='sp-chip sp-chip-warning'>{kpis['ag_24h']} em 24h</span>"
    elif kpis["prazos_7dias"] > 0:
        title = "A semana está controlada, mas já exige antecipação."
        sub = (
            f"Você tem {kpis['prazos_7dias']} prazo(s) na janela de 7 dias. "
            "Este é um bom momento para distribuir carga e evitar urgência."
        )
        chip = f"<span class='sp-chip sp-chip-info'>{kpis['prazos_7dias']} na semana</span>"
    else:
        title = "Tudo sob controle neste momento."
        sub = (
            "Sem sinais críticos agora. Aproveite para revisar cadastros, "
            "organizar próximos trabalhos e manter a base atualizada."
        )
        chip = "<span class='sp-chip sp-chip-success'>Operação estável</span>"

    with section(divider=False, compact=True):
        _render_html(
            f"""
            <div class="sp-dash-command">
              <div>
                <div class="sp-dash-command-title">{escape(title)}</div>
                <div class="sp-dash-command-sub">{escape(sub)}</div>
              </div>
              <div class="sp-dash-chip-row">
                {chip}
                <span class="sp-chip">{escape(atuacao_label)}</span>
              </div>
            </div>
            """
        )


def _render_dashboard_hero(kpis: dict[str, Any], atuacao_label: str) -> None:
    if kpis["prazos_atrasados"] > 0:
        title = "Existem pendências vencidas exigindo ação imediata."
        copy = (
            "Seu melhor próximo passo é abrir a fila de prazos e começar pelos itens "
            "já vencidos, reduzindo risco operacional e retrabalho."
        )
        chips = [
            f"<span class='sp-chip sp-chip-danger'>Atrasados: {kpis['prazos_atrasados']}</span>",
            f"<span class='sp-chip'>Prazos abertos: {kpis['prazos_abertos']}</span>",
            f"<span class='sp-chip'>Agenda 24h: {kpis['ag_24h']}</span>",
            f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
        ]
    elif kpis["ag_24h"] > 0:
        title = "Sua agenda imediata precisa de preparação."
        copy = (
            "Há compromissos próximos. Vale revisar local, horário, logística e documentos "
            "antes da próxima movimentação."
        )
        chips = [
            f"<span class='sp-chip sp-chip-warning'>Em 24h: {kpis['ag_24h']}</span>",
            f"<span class='sp-chip'>Agenda 7 dias: {kpis['ag_7d']}</span>",
            f"<span class='sp-chip'>Prazos na semana: {kpis['prazos_7dias']}</span>",
            f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
        ]
    elif kpis["prazos_7dias"] > 0:
        title = "A semana está organizada, mas já merece antecipação."
        copy = (
            "Existem vencimentos próximos. Antecipar a preparação agora reduz urgência "
            "e melhora a execução ao longo da semana."
        )
        chips = [
            f"<span class='sp-chip sp-chip-info'>Em 7 dias: {kpis['prazos_7dias']}</span>",
            f"<span class='sp-chip'>Agenda 7 dias: {kpis['ag_7d']}</span>",
            f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
            f"<span class='sp-chip'>Saldo: R$ {_fmt_money_br(kpis['saldo'])}</span>",
        ]
    else:
        title = "Operação estável e sem sinais críticos no momento."
        copy = (
            "Este é um bom momento para revisar base cadastral, atualizar registros, "
            "abrir novos trabalhos e preparar a próxima semana com calma."
        )
        chips = [
            "<span class='sp-chip sp-chip-success'>Sem urgência crítica</span>",
            f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
            f"<span class='sp-chip'>Agenda 7 dias: {kpis['ag_7d']}</span>",
            f"<span class='sp-chip'>Saldo: R$ {_fmt_money_br(kpis['saldo'])}</span>",
        ]

    with section(divider=False, compact=True):
        _render_html(
            f"""
            <div class="sp-dash-hero">
              <div class="sp-dash-hero-top">
                <div>
                  <div class="sp-dash-hero-kicker">visão executiva do dia</div>
                  <div class="sp-dash-hero-title">{escape(title)}</div>
                  <div class="sp-dash-hero-copy">{escape(copy)}</div>
                </div>
                <span class="sp-chip">{escape(atuacao_label)}</span>
              </div>
              <div class="sp-dash-hero-meta">
                {''.join(chips)}
              </div>
            </div>
            """
        )


def _build_global_alert(kpis: dict[str, Any]) -> dict[str, str]:
    if kpis["prazos_atrasados"] > 0:
        return {
            "tone": "danger",
            "title": f"{kpis['prazos_atrasados']} prazo(s) vencido(s) exigem ação imediata",
            "subtitle": "Abra a lista de prazos e trate primeiro os itens já vencidos para reduzir risco operacional.",
        }

    if kpis["ag_24h"] > 0:
        return {
            "tone": "warning",
            "title": f"{kpis['ag_24h']} compromisso(s) nas próximas 24 horas",
            "subtitle": "Revise horário, local, deslocamento e documentos antes da próxima agenda.",
        }

    if kpis["prazos_7dias"] > 0:
        return {
            "tone": "info",
            "title": f"{kpis['prazos_7dias']} prazo(s) vencem em até 7 dias",
            "subtitle": "A semana pede organização antecipada para evitar urgências desnecessárias.",
        }

    return {
        "tone": "success",
        "title": "Operação estável neste momento",
        "subtitle": "Sem sinais críticos no painel. Bom momento para atualização de cadastros e revisão geral.",
    }


def _render_global_alert_strip(kpis: dict[str, Any]) -> None:
    alert = _build_global_alert(kpis)
    tone_cls = {
        "danger": "sp-dash-alert-strip-danger",
        "warning": "sp-dash-alert-strip-warning",
        "info": "sp-dash-alert-strip-info",
        "success": "sp-dash-alert-strip-success",
    }.get(alert["tone"], "")

    with section(divider=False, compact=True):
        _render_html(
            f"""
            <div class="sp-dash-alert-strip {tone_cls}">
              <div>
                <div class="sp-dash-alert-title">{escape(alert['title'])}</div>
                <div class="sp-dash-alert-sub">{escape(alert['subtitle'])}</div>
              </div>
              <span class="sp-chip">{escape(alert['tone'])}</span>
            </div>
            """
        )


def _render_dashboard_summary(kpis: dict[str, Any], atuacao_label: str) -> None:
    with section(
        "Indicadores",
        subtitle=f"Resumo operacional • {atuacao_label}",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=2)

        with c1:
            card(
                "Trabalhos ativos",
                f"{kpis['ativos']}",
                f"{kpis['total_trabalhos']} no total",
                tone="neutral",
                emphasize=True,
            )

        with c2:
            tone_prazos = (
                "danger"
                if kpis["prazos_atrasados"] > 0
                else ("warning" if kpis["prazos_7dias"] > 0 else "success")
            )
            subtitle = (
                f"{kpis['prazos_atrasados']} atrasados • {kpis['prazos_7dias']} em 7 dias"
                if kpis["prazos_abertos"] > 0
                else "sem pendências em aberto"
            )
            card(
                "Prazos",
                f"{kpis['prazos_abertos']}",
                subtitle,
                tone=tone_prazos,
                emphasize=(kpis["prazos_atrasados"] > 0),
            )

        with c3:
            agenda_tone, agenda_emph = _kpi_agenda_tone(
                kpis["ag_24h"], kpis["ag_72h"], kpis["ag_7d"]
            )
            card(
                "Agenda próxima",
                f"{kpis['ag_7d']}",
                _kpi_agenda_subtitle(kpis["ag_24h"], kpis["ag_72h"], kpis["ag_7d"]),
                tone=agenda_tone,
                emphasize=agenda_emph,
            )

        with c4:
            saldo_tone = "success" if kpis["saldo"] >= 0 else "danger"
            card(
                "Resultado",
                f"R$ {_fmt_money_br(kpis['saldo'])}",
                f"Receitas R$ {_fmt_money_br(kpis['receitas'])} • Despesas R$ {_fmt_money_br(kpis['despesas'])}",
                tone=saldo_tone,
                emphasize=True,
            )


def _render_quick_actions() -> None:
    with section(
        "Ações rápidas",
        subtitle="Criação e acesso direto aos fluxos principais",
        divider=False,
    ):
        _render_html("<div class='sp-dashboard-action-grid'>")
        try:
            c1, c2, c3, c4 = grid(4, columns_mobile=2)

            with c1:
                _render_action_button(
                    "📁 Novo trabalho",
                    key="dash_quick_new_trabalho",
                    button_type="primary",
                    on_click=_go_trabalhos_cadastro,
                )

            with c2:
                _render_action_button(
                    "⏳ Novo prazo",
                    key="dash_quick_new_prazo",
                    on_click=_go_prazos_cadastro,
                )

            with c3:
                _render_action_button(
                    "📅 Abrir agenda",
                    key="dash_quick_agenda",
                    on_click=_go_agenda,
                )

            with c4:
                _render_action_button(
                    "💰 Abrir financeiro",
                    key="dash_quick_financeiro",
                    on_click=_go_financeiro_lancamentos,
                )
        finally:
            _render_html("</div>")


def _render_focus_panel(kpis: dict[str, Any]) -> None:
    focus = _build_focus_state(kpis)

    tone_cls = {
        "danger": "sp-dash-focus-danger",
        "warning": "sp-dash-focus-warning",
        "info": "sp-dash-focus-info",
        "success": "sp-dash-focus-success",
    }.get(focus["tone"], "")

    with section(
        "Foco do dia",
        subtitle="O melhor próximo passo para manter a operação fluindo",
        divider=False,
    ):
        _render_html(
            f"""
            <div class="sp-dash-focus {tone_cls}">
              <div class="sp-dash-focus-kicker">{escape(focus['kicker'])}</div>
              <div class="sp-dash-focus-title">{escape(focus['title'])}</div>
              <div class="sp-dash-focus-copy">{escape(focus['copy'])}</div>
              <div class="sp-dash-chip-row">{''.join(focus['chips'])}</div>
              <div class="sp-dash-focus-list">
                {''.join(f"<div class='sp-dash-focus-item'><span>•</span><span>{escape(item)}</span></div>" for item in focus['items'])}
              </div>
            </div>
            """
        )

        spacer(0.08)
        c1, c2 = grid(2, columns_mobile=1)

        primary_label, primary_callback = focus["primary"]
        secondary_label, secondary_callback = focus["secondary"]

        with c1:
            _render_action_button(
                primary_label,
                key="dash_focus_primary",
                button_type="primary",
                on_click=primary_callback,
            )

        with c2:
            _render_action_button(
                secondary_label,
                key="dash_focus_secondary",
                on_click=secondary_callback,
            )


def _render_timeline_preview(items: list[dict[str, Any]]) -> None:
    with section(
        "Próximos itens",
        subtitle="O que entra primeiro no radar",
        divider=False,
    ):
        if not items:
            empty_state(
                title="Nenhum item próximo",
                subtitle="Quando houver prazos ou compromissos, eles aparecerão aqui.",
                icon="🗓️",
            )
            return

        _render_html("<div class='sp-dash-compact-list'>")
        try:
            for item in items:
                pill_class = {
                    "danger": "sp-chip-danger",
                    "warning": "sp-chip-warning",
                    "info": "sp-chip-info",
                    "success": "sp-chip-success",
                }.get(item["tone"], "")

                _render_html(
                    f"""
                    <div class="sp-dash-compact-item">
                        <div class="sp-dash-compact-top">
                            <div>
                                <div class="sp-dash-compact-title">{_esc(item['headline'])}</div>
                                <div class="sp-dash-compact-sub">{_esc(item['detail'])}</div>
                            </div>
                            <span class="sp-chip {pill_class}">{_esc(item['kind'])}</span>
                        </div>
                        <div class="sp-dash-chip-row">
                            <span class="sp-chip {pill_class}">{_esc(item['meta'])}</span>
                        </div>
                    </div>
                    """
                )
        finally:
            _render_html("</div>")


def _render_activity_feed(items: list[dict[str, Any]]) -> None:
    with section(
        "Radar operacional",
        subtitle="Leitura rápida do que está entrando primeiro no seu campo de atenção",
        divider=False,
    ):
        if not items:
            empty_state(
                title="Nenhum movimento relevante agora",
                subtitle="Quando houver prazos ou agendas próximas, eles aparecerão aqui.",
                icon="🧭",
            )
            return

        _render_html("<div class='sp-dash-feed'>")
        try:
            for item in items:
                pill_class = {
                    "danger": "sp-chip-danger",
                    "warning": "sp-chip-warning",
                    "info": "sp-chip-info",
                    "success": "sp-chip-success",
                }.get(item["tone"], "")

                _render_html(
                    f"""
                    <div class="sp-dash-feed-item">
                        <div class="sp-dash-feed-top">
                            <div>
                                <div class="sp-dash-feed-title">{_esc(item['headline'])}</div>
                                <div class="sp-dash-feed-sub">{_esc(item['detail'])}</div>
                            </div>
                            <span class="sp-chip {pill_class}">{_esc(item['kind'])}</span>
                        </div>
                        <div class="sp-dash-chip-row">
                            <span class="sp-chip {pill_class}">{_esc(item['meta'])}</span>
                        </div>
                    </div>
                    """
                )
        finally:
            _render_html("</div>")


def _module_row_html(title: str, subtitle: str) -> str:
    return (
        f"<div class='sp-dash-module-row'>"
        f"<div class='sp-dash-module-row-title'>{title}</div>"
        f"<div class='sp-dash-module-row-sub'>{subtitle}</div>"
        f"</div>"
    )


def _render_module_preview_box(
    *,
    title: str,
    subtitle: str,
    badge: str,
    rows_html: list[str],
) -> None:
    rows_rendered = "".join(row.strip() for row in rows_html)

    _render_html(
        f"""
        <div class="sp-dash-module">
          <div class="sp-dash-module-head">
            <div>
              <div class="sp-dash-module-title">{escape(title)}</div>
              <div class="sp-dash-module-copy">{escape(subtitle)}</div>
            </div>
            <span class="sp-chip">{escape(badge)}</span>
          </div>
          <div class="sp-dash-module-list">{rows_rendered}</div>
        </div>
        """
    )


def _build_suggestions(kpis: dict[str, Any]) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []

    if kpis["prazos_atrasados"] > 0:
        suggestions.append(
            {
                "title": "Tratar prazos vencidos primeiro",
                "subtitle": "Reduz o risco operacional e limpa a fila mais crítica do painel.",
            }
        )

    if kpis["ag_24h"] > 0:
        suggestions.append(
            {
                "title": "Preparar compromissos das próximas 24h",
                "subtitle": "Conferir local, horário e anexos evita atraso ou retrabalho.",
            }
        )

    if kpis["prazos_7dias"] > 0:
        suggestions.append(
            {
                "title": "Distribuir a carga da semana",
                "subtitle": "Antecipar os próximos vencimentos ajuda a manter a operação estável.",
            }
        )

    if kpis["saldo"] < 0:
        suggestions.append(
            {
                "title": "Revisar posição financeira",
                "subtitle": "Há mais despesas do que receitas no recorte atual.",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "title": "Atualizar base cadastral",
                "subtitle": "Com o painel estável, vale revisar trabalhos, agenda e lançamentos.",
            }
        )
        suggestions.append(
            {
                "title": "Cadastrar novos itens com antecedência",
                "subtitle": "Manter dados completos melhora previsibilidade e acompanhamento.",
            }
        )

    return suggestions[:3]


def _render_smart_suggestions(kpis: dict[str, Any]) -> None:
    suggestions = _build_suggestions(kpis)

    with section(
        "Sugestões do sistema",
        subtitle="Ações recomendadas para manter previsibilidade e reduzir retrabalho",
        divider=False,
    ):
        _render_html("<div class='sp-dash-suggest-list'>")
        try:
            for item in suggestions:
                _render_html(
                    f"""
                    <div class="sp-dash-suggest-item">
                        <div class="sp-dash-suggest-title">{escape(item['title'])}</div>
                        <div class="sp-dash-suggest-sub">{escape(item['subtitle'])}</div>
                    </div>
                    """
                )
        finally:
            _render_html("</div>")


def _render_finance_strip(kpis: dict[str, Any]) -> None:
    with section(
        "Financeiro",
        subtitle="Posição consolidada do recorte atual",
        divider=False,
    ):
        left, right = grid_weights((1.0, 0.42), weights_mobile=(1, 1), gap="medium")

        with left:
            c1, c2, c3 = grid(3, columns_mobile=1)

            with c1:
                card(
                    "Receitas",
                    f"R$ {_fmt_money_br(kpis['receitas'])}",
                    "acumulado",
                    tone="success",
                )

            with c2:
                card(
                    "Despesas",
                    f"R$ {_fmt_money_br(kpis['despesas'])}",
                    "acumulado",
                    tone="danger",
                )

            with c3:
                saldo_tone = "success" if kpis["saldo"] >= 0 else "danger"
                card(
                    "Saldo atual",
                    f"R$ {_fmt_money_br(kpis['saldo'])}",
                    "posição consolidada",
                    tone=saldo_tone,
                    emphasize=True,
                )

        with right:
            _render_html(
                f"""
                <div class="sp-dash-band">
                  <div class="sp-dash-band-kicker">leitura financeira</div>
                  <div class="sp-dash-band-title">
                    {"Resultado positivo no recorte atual." if kpis["saldo"] >= 0 else "Atenção para o saldo negativo no recorte atual."}
                  </div>
                  <div class="sp-dash-band-copy">
                    {"Há folga financeira para este recorte. Ainda assim, vale acompanhar recebimentos e novos lançamentos."
                    if kpis["saldo"] >= 0 else
                    "As despesas superam as receitas neste recorte. Vale revisar lançamentos e entradas previstas."}
                  </div>
                  <div class="sp-dash-chip-row">
                    <span class="sp-chip">Receitas: R$ {_fmt_money_br(kpis['receitas'])}</span>
                    <span class="sp-chip">Despesas: R$ {_fmt_money_br(kpis['despesas'])}</span>
                  </div>
                </div>
                """
            )
            spacer(0.08)
            _render_nav_button(
                "Abrir financeiro",
                page="Financeiro",
                state={"financeiro_section": "Lançamentos"},
                key="dash_open_financeiro_strip",
                type="primary",
            )


# ==========================================================
# Tabs / previews
# ==========================================================


def _render_tab_prazos(
    owner_user_id: int,
    tipo_val: str | None,
    kpis: dict[str, Any],
    version: int,
) -> None:
    rows_atrasados, rows_7d = _fetch_prazos_tables_cached(
        owner_user_id,
        tipo_val,
        kpis["start_today"].isoformat(timespec="seconds"),
        kpis["end_7d"].isoformat(timespec="seconds"),
        version,
    )

    with section(
        "Prazos",
        subtitle="Visão rápida do que exige ação",
        divider=False,
    ):
        c1, c2 = grid(2, columns_mobile=1)

        with c1:
            rows_html: list[str] = []
            for row in rows_atrasados[:3]:
                _, evento, data_limite, _, numero_trabalho, descricao_trabalho = row
                dias = int(_dias_restantes(data_limite))
                rows_html.append(
                    _module_row_html(
                        f"{_esc(numero_trabalho, 'Sem referência')} – {_esc(descricao_trabalho, 'Sem descrição')}",
                        f"{_esc(evento, 'Sem evento')} • vencido há {abs(dias)} dia(s)",
                    )
                )

            if not rows_html:
                rows_html.append(
                    _module_row_html(
                        "Nenhum prazo atrasado",
                        "Seu painel está sem pendências vencidas neste recorte.",
                    )
                )

            _render_module_preview_box(
                title="Atrasados",
                subtitle="Trate primeiro o que já venceu",
                badge=f"{len(rows_atrasados)} item(ns)",
                rows_html=rows_html,
            )
            spacer(0.08)
            _render_nav_button(
                "Ver prazos atrasados",
                page="Prazos",
                state={"prazos_section": "Lista"},
                key="dash_prazos_preview_all_atrasados",
                type="primary",
            )

        with c2:
            rows_html = []
            for row in rows_7d[:3]:
                _, evento, data_limite, _, numero_trabalho, descricao_trabalho = row
                dias = int(_dias_restantes(data_limite))
                rows_html.append(
                    _module_row_html(
                        f"{_esc(numero_trabalho, 'Sem referência')} – {_esc(descricao_trabalho, 'Sem descrição')}",
                        f"{_esc(evento, 'Sem evento')} • vence em {dias} dia(s)",
                    )
                )

            if not rows_html:
                rows_html.append(
                    _module_row_html(
                        "Sem vencimentos próximos",
                        "Não há prazos para vencer em até 7 dias.",
                    )
                )

            _render_module_preview_box(
                title="Próximos 7 dias",
                subtitle="Organize a semana com antecedência",
                badge=f"{len(rows_7d)} item(ns)",
                rows_html=rows_html,
            )
            spacer(0.08)
            _render_nav_button(
                "Ver prazos",
                page="Prazos",
                state={"prazos_section": "Lista"},
                key="dash_prazos_preview_open",
                type="secondary",
            )

    with st.expander("Ver tabela", expanded=False):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            st.caption("Atrasados")
            _render_dataframe_or_caption(
                _build_prazos_df(rows_atrasados),
                empty_title="Sem prazos atrasados",
                empty_subtitle="Quando houver pendências vencidas, elas aparecerão aqui.",
                empty_icon="✅",
            )

        with col2:
            st.caption("Próximos 7 dias")
            _render_dataframe_or_caption(
                _build_prazos_df(rows_7d),
                empty_title="Sem vencimentos próximos",
                empty_subtitle="Nenhum prazo está previsto para vencer em até 7 dias.",
                empty_icon="📅",
            )


def _render_tab_agenda(
    owner_user_id: int,
    tipo_val: str | None,
    kpis: dict[str, Any],
    version: int,
) -> None:
    rows_24h, rows_7d = _fetch_agendamentos_cached(
        owner_user_id,
        tipo_val,
        kpis["now_n"].isoformat(timespec="seconds"),
        version,
    )

    with section(
        "Agenda",
        subtitle="Compromissos da janela operacional",
        divider=False,
    ):
        c1, c2 = grid(2, columns_mobile=1)

        with c1:
            rows_html: list[str] = []
            for row in rows_24h[:3]:
                _, tipo, inicio, local, numero_trabalho, descricao_trabalho = row
                inicio_br = ensure_br(inicio).strftime("%d/%m/%Y %H:%M")
                sub = f"{_esc(tipo, 'Sem tipo')} • {escape(inicio_br)}"
                if local:
                    sub += f" • {_esc(local)}"

                rows_html.append(
                    _module_row_html(
                        f"{_esc(numero_trabalho, 'Sem referência')} – {_esc(descricao_trabalho, 'Sem descrição')}",
                        sub,
                    )
                )

            if not rows_html:
                rows_html.append(
                    _module_row_html(
                        "Nenhum compromisso em 24h",
                        "Sua agenda imediata está livre neste momento.",
                    )
                )

            _render_module_preview_box(
                title="Próximas 24 horas",
                subtitle="Confira o que exige preparação imediata",
                badge=f"{len(rows_24h)} item(ns)",
                rows_html=rows_html,
            )
            spacer(0.08)
            _render_nav_button(
                "Ver agenda",
                page="Agenda",
                state={"agenda_section": "Agenda"},
                key="dash_agenda_preview_open_24h",
                type="primary",
            )

        with c2:
            rows_html = []
            for row in rows_7d[:3]:
                _, tipo, inicio, local, numero_trabalho, descricao_trabalho = row
                inicio_br = ensure_br(inicio).strftime("%d/%m/%Y %H:%M")
                sub = f"{_esc(tipo, 'Sem tipo')} • {escape(inicio_br)}"
                if local:
                    sub += f" • {_esc(local)}"

                rows_html.append(
                    _module_row_html(
                        f"{_esc(numero_trabalho, 'Sem referência')} – {_esc(descricao_trabalho, 'Sem descrição')}",
                        sub,
                    )
                )

            if not rows_html:
                rows_html.append(
                    _module_row_html(
                        "Sem agenda na semana",
                        "Quando houver compromissos, eles aparecerão aqui.",
                    )
                )

            _render_module_preview_box(
                title="Próximos 7 dias",
                subtitle="Planejamento da semana",
                badge=f"{len(rows_7d)} item(ns)",
                rows_html=rows_html,
            )
            spacer(0.08)
            _render_nav_button(
                "Abrir agenda",
                page="Agenda",
                state={"agenda_section": "Agenda"},
                key="dash_agenda_preview_open_7d",
                type="secondary",
            )

    with st.expander("Ver tabela", expanded=False):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            st.caption("24 horas")
            _render_dataframe_or_caption(
                _build_agenda_df(rows_24h),
                empty_title="Sem compromissos imediatos",
                empty_subtitle="Não há registros de agenda para as próximas 24 horas.",
                empty_icon="🕒",
            )

        with col2:
            st.caption("7 dias")
            _render_dataframe_or_caption(
                _build_agenda_df(rows_7d),
                empty_title="Sem compromissos nesta janela",
                empty_subtitle="Não há registros de agenda para os próximos 7 dias.",
                empty_icon="🗓️",
            )


def _render_tab_trabalhos(
    owner_user_id: int,
    tipo_val: str | None,
    version: int,
) -> None:
    rows = _fetch_ultimos_trabalhos_cached(owner_user_id, tipo_val, version)

    with section(
        "Trabalhos",
        subtitle="Últimos registros do filtro atual",
        divider=False,
    ):
        if not rows:
            empty_state(
                title="Nenhum trabalho cadastrado ainda",
                subtitle="Quando você cadastrar trabalhos para esta atuação, eles aparecerão aqui.",
                icon="📁",
            )
            return

        rows_html: list[str] = []
        for row in rows[:5]:
            _, numero_trabalho, descricao_trabalho, comarca, vara, status, papel = row
            sub = f"{_safe_text(comarca, '—')} • {_safe_text(vara, '—')} • {_safe_text(status, '—')}"
            rows_html.append(
                _module_row_html(
                    f"{_esc(numero_trabalho, 'Sem referência')} – {_esc(descricao_trabalho, 'Sem descrição')}",
                    escape(sub),
                )
            )

        _render_module_preview_box(
            title="Últimos trabalhos",
            subtitle="Acesso rápido aos registros recentes",
            badge=f"{len(rows)} item(ns)",
            rows_html=rows_html,
        )

        spacer(0.08)
        c1, c2 = grid(2, columns_mobile=1)

        with c1:
            _render_nav_button(
                "Ver trabalhos",
                page="Trabalhos",
                state={"trabalhos_section": "Lista"},
                key="dash_open_trabalhos",
                type="primary",
            )

        with c2:
            _render_nav_button(
                "Novo trabalho",
                page="Trabalhos",
                state={"trabalhos_section": "Cadastro"},
                key="dash_new_trabalhos_from_preview",
                type="secondary",
            )

    with st.expander("Ver tabela", expanded=False):
        _render_dataframe_or_caption(
            _build_trabalhos_df(rows),
            height=420,
            empty_title="Sem trabalhos para exibir",
            empty_subtitle="Não há registros neste recorte.",
            empty_icon="📁",
        )


# ==========================================================
# Render principal
# ==========================================================


def render(owner_user_id: int) -> None:
    with content_shell():
        _inject_dashboard_css()

        tipo_val = _render_top_bar()
        atuacao_label = st.session_state.get("dash_atuacao_ui", "(Todas)")

        hoje_sp = now_br().date()
        version = get_data_version(owner_user_id)

        kpis = _fetch_kpis_cached(
            owner_user_id=owner_user_id,
            tipo_val=tipo_val,
            hoje_iso=hoje_sp.isoformat(),
            version=version,
        )

        rows_prazos_atrasados, rows_prazos_7d = _fetch_prazos_tables_cached(
            owner_user_id,
            tipo_val,
            kpis["start_today"].isoformat(timespec="seconds"),
            kpis["end_7d"].isoformat(timespec="seconds"),
            version,
        )

        rows_ag_24h, rows_ag_7d = _fetch_agendamentos_cached(
            owner_user_id,
            tipo_val,
            kpis["now_n"].isoformat(timespec="seconds"),
            version,
        )

        _render_header(kpis)
        _render_dashboard_hero(kpis, atuacao_label)

        spacer(0.10)
        _render_command_bar(kpis, atuacao_label)

        spacer(0.10)
        _render_dashboard_summary(kpis, atuacao_label)

        spacer(0.12)
        _render_quick_actions()

        spacer(0.12)
        _render_global_alert_strip(kpis)

        timeline_items = _build_timeline_items(
            rows_prazos_atrasados,
            rows_prazos_7d,
            rows_ag_24h,
            rows_ag_7d,
        )

        spacer(0.14)
        left, right = grid_weights((1.05, 0.95), weights_mobile=(1, 1), gap="medium")

        with left:
            _render_focus_panel(kpis)

        with right:
            _render_activity_feed(timeline_items)

        spacer(0.14)
        left2, right2 = grid_weights((1.0, 1.0), weights_mobile=(1, 1), gap="medium")

        with left2:
            _render_timeline_preview(timeline_items)

        with right2:
            _render_smart_suggestions(kpis)

        spacer(0.14)
        _render_finance_strip(kpis)

        spacer(0.16)
        tab1, tab2, tab3 = st.tabs(
            [
                f"⏳ Prazos ({kpis['prazos_abertos']})",
                f"📅 Agenda ({kpis['ag_7d']})",
                f"📁 Trabalhos ({kpis['ativos']})",
            ]
        )

        with tab1:
            _render_tab_prazos(owner_user_id, tipo_val, kpis, version)

        with tab2:
            _render_tab_agenda(owner_user_id, tipo_val, kpis, version)

        with tab3:
            _render_tab_trabalhos(owner_user_id, tipo_val, version)
