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
from ui_state import get_data_version, navigate

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
    _render_html(
        """
        <style>
        .sp-dash-filter-note{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:10px;
            flex-wrap:wrap;
            padding:12px 14px;
            border:1px solid rgba(15,23,42,.08);
            border-radius:16px;
            background:linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(248,250,252,.92) 100%);
            box-shadow:0 1px 2px rgba(15,23,42,.03);
        }

        .sp-dash-filter-note-copy{
            color:rgba(15,23,42,.68);
            font-size:.89rem;
            line-height:1.42;
        }

        .sp-dash-panel{
            padding:15px;
            border:1px solid rgba(15,23,42,.08);
            border-radius:16px;
            background:#fff;
            box-shadow:0 1px 3px rgba(15,23,42,.04);
        }

        .sp-dash-panel-title{
            font-size:1rem;
            font-weight:810;
            line-height:1.28;
            color:#0f172a;
        }

        .sp-dash-panel-copy{
            margin-top:7px;
            color:rgba(15,23,42,.70);
            line-height:1.46;
            font-size:.90rem;
        }

        .sp-dash-panel-list{
            margin-top:11px;
            display:flex;
            flex-direction:column;
            gap:8px;
        }

        .sp-dash-panel-item{
            padding:9px 10px;
            border:1px solid rgba(15,23,42,.07);
            border-radius:12px;
            background:rgba(248,250,252,.72);
            color:#0f172a;
            font-size:.86rem;
            line-height:1.35;
        }

        .sp-dash-chip-row{
            display:flex;
            gap:8px;
            flex-wrap:wrap;
            margin-top:10px;
        }

        .sp-dash-note-card{
            border:1px solid rgba(15,23,42,.08);
            border-radius:15px;
            padding:11px 12px;
            background:#fff;
            box-shadow:0 1px 3px rgba(15,23,42,.03);
            margin-bottom:10px;
        }

        .sp-dash-note-card-danger{ border-left:3px solid #dc2626; }
        .sp-dash-note-card-warning{ border-left:3px solid #f59e0b; }
        .sp-dash-note-card-info{ border-left:3px solid #2563eb; }
        .sp-dash-note-card-success{ border-left:3px solid #16a34a; }

        .sp-dash-note-kicker{
            font-size:.71rem;
            font-weight:800;
            letter-spacing:.05em;
            text-transform:uppercase;
            color:rgba(15,23,42,.43);
            margin-bottom:4px;
        }

        .sp-dash-note-title{
            font-size:.93rem;
            font-weight:810;
            color:#0f172a;
            line-height:1.34;
        }

        .sp-dash-note-copy{
            margin-top:5px;
            color:rgba(15,23,42,.68);
            font-size:.87rem;
            line-height:1.42;
        }

        .sp-dash-list-card{
            border:1px solid rgba(15,23,42,.08);
            border-radius:15px;
            padding:11px 12px;
            background:#fff;
            box-shadow:0 1px 3px rgba(15,23,42,.03);
            margin-bottom:10px;
        }

        .sp-dash-list-card-danger{ border-left:3px solid #dc2626; }
        .sp-dash-list-card-warning{ border-left:3px solid #f59e0b; }
        .sp-dash-list-card-info{ border-left:3px solid #2563eb; }
        .sp-dash-list-card-success{ border-left:3px solid #16a34a; }

        .sp-dash-list-card-title{
            font-weight:800;
            color:#0f172a;
            line-height:1.32;
            font-size:.93rem;
        }

        .sp-dash-list-card-sub{
            color:rgba(15,23,42,.62);
            font-size:.85rem;
            line-height:1.40;
            margin-top:4px;
        }

        .sp-dash-timeline-item{
            border:1px solid rgba(15,23,42,.08);
            border-radius:14px;
            padding:10px 11px;
            background:#fff;
            margin-bottom:10px;
        }

        .sp-dash-timeline-head{
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:10px;
        }

        .sp-dash-timeline-title{
            font-weight:790;
            color:#0f172a;
            line-height:1.32;
            font-size:.92rem;
        }

        .sp-dash-timeline-sub{
            margin-top:4px;
            color:rgba(15,23,42,.64);
            font-size:.84rem;
            line-height:1.40;
        }

        .sp-dashboard-action-grid .stButton > button{
            min-height:46px !important;
            font-weight:720 !important;
        }

        div[data-baseweb="tab-list"]{
            gap:.30rem;
        }

        div[data-baseweb="tab"]{
            border-radius:12px !important;
            padding:.52rem .86rem !important;
            background:rgba(15,23,42,.04);
            font-weight:770 !important;
        }

        div[data-baseweb="tab-highlight"]{
            border-radius:999px !important;
        }

        [data-testid="stDataFrame"]{
            border-radius:14px;
            overflow:hidden;
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


def _make_nav_callback(page: str, state: dict[str, Any] | None = None):
    def _callback() -> None:
        navigate(page, state=state)

    return _callback


def _render_nav_button(
    label: str,
    *,
    page: str,
    state: dict[str, Any] | None = None,
    key: str,
    type: str = "secondary",
) -> None:
    st.button(
        label,
        key=key,
        type=type,
        use_container_width=True,
        on_click=_make_nav_callback(page, state),
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
        return "nenhum compromisso próximo"
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

    for _id, evento, data_limite, prioridade, numero_processo, tipo_acao in rows:
        dias = int(_dias_restantes(data_limite))
        items.append(
            {
                "Trabalho": f"{_safe_text(numero_processo, 'Sem referência')} – {_safe_text(tipo_acao, 'Sem tipo')}",
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

    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows:
        items.append(
            {
                "Trabalho": f"{_safe_text(numero_processo, 'Sem referência')} – {_safe_text(tipo_acao, 'Sem tipo')}",
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
            "numero_processo",
            "tipo_acao",
            "comarca",
            "vara",
            "status",
            "tipo_trabalho",
        ],
    )

    df["tipo_acao"] = df["tipo_acao"].fillna("Sem tipo")
    df["tipo_trabalho"] = df["tipo_trabalho"].fillna("Assistente Técnico")
    df["comarca"] = df["comarca"].fillna("—")
    df["vara"] = df["vara"].fillna("—")
    df["status"] = df["status"].fillna("—")

    return df.rename(
        columns={
            "id": "ID",
            "numero_processo": "Referência",
            "tipo_acao": "Descrição",
            "comarca": "Comarca",
            "vara": "Vara",
            "status": "Status",
            "tipo_trabalho": "Atuação",
        }
    )


# ==========================================================
# Navegação
# ==========================================================


def _go_prazos_lista() -> None:
    navigate("Prazos", state={"prazos_section": "Lista"})


def _go_trabalhos_lista() -> None:
    navigate("Trabalhos", state={"trabalhos_section": "Lista"})


def _go_financeiro_lancamentos() -> None:
    navigate("Financeiro", state={"financeiro_section": "Lançamentos"})


def _go_agenda() -> None:
    navigate("Agenda")


def _go_prazos_cadastro() -> None:
    navigate("Prazos", state={"prazos_section": "Cadastro"})


def _go_trabalhos_cadastro() -> None:
    navigate("Trabalhos", state={"trabalhos_section": "Cadastro"})


# ==========================================================
# Estado visual
# ==========================================================


def _build_today_state(kpis: dict[str, Any]) -> dict[str, Any]:
    if kpis["prazos_atrasados"] > 0:
        return {
            "title": "Comece pelos prazos vencidos",
            "copy": "Regularize os itens atrasados antes de abrir novas frentes.",
            "items": [
                "Abrir a lista de atrasados",
                "Tratar os itens mais urgentes",
                "Registrar cada atualização",
            ],
            "primary": ("Abrir prazos", _go_prazos_lista),
            "secondary": ("Novo prazo", _go_prazos_cadastro),
        }

    if kpis["ag_24h"] > 0:
        return {
            "title": "Prepare a agenda imediata",
            "copy": "Confirme horários, local, deslocamento e documentos.",
            "items": [
                "Revisar agenda de 24h",
                "Separar documentos",
                "Confirmar logística",
            ],
            "primary": ("Abrir agenda", _go_agenda),
            "secondary": ("Abrir processos", _go_trabalhos_lista),
        }

    if kpis["prazos_7dias"] > 0:
        return {
            "title": "Organize a semana com antecedência",
            "copy": "Há vencimentos próximos. Antecipar agora evita urgência depois.",
            "items": [
                "Revisar próximos 7 dias",
                "Separar peças por trabalho",
                "Distribuir a carga da semana",
            ],
            "primary": ("Ver próximos prazos", _go_prazos_lista),
            "secondary": ("Novo processo", _go_trabalhos_cadastro),
        }

    return {
        "title": "Painel sob controle",
        "copy": "Sem urgências críticas neste momento. Aproveite para atualizar a operação.",
        "items": [
            "Atualizar processos ativos",
            "Cadastrar pendências novas",
            "Revisar financeiro e agenda",
        ],
        "primary": ("Novo processo", _go_trabalhos_cadastro),
        "secondary": ("Abrir financeiro", _go_financeiro_lancamentos),
    }


def _build_notifications(kpis: dict[str, Any]) -> list[dict[str, Any]]:
    notifications: list[dict[str, Any]] = []

    if kpis["prazos_atrasados"] > 0:
        notifications.append(
            {
                "tone": "danger",
                "kicker": "atenção imediata",
                "title": f"{kpis['prazos_atrasados']} prazo(s) vencido(s)",
                "copy": "Trate primeiro os itens já atrasados.",
                "primary": ("Abrir prazos", _go_prazos_lista),
            }
        )

    if kpis["ag_24h"] > 0:
        notifications.append(
            {
                "tone": "warning",
                "kicker": "agenda imediata",
                "title": f"{kpis['ag_24h']} compromisso(s) em 24h",
                "copy": "Revise horário, local e documentos.",
                "primary": ("Abrir agenda", _go_agenda),
            }
        )

    if kpis["prazos_7dias"] > 0:
        notifications.append(
            {
                "tone": "info",
                "kicker": "janela da semana",
                "title": f"{kpis['prazos_7dias']} prazo(s) em até 7 dias",
                "copy": "Organize agora para reduzir urgência depois.",
                "primary": ("Ver próximos prazos", _go_prazos_lista),
            }
        )

    if kpis["saldo"] < 0:
        notifications.append(
            {
                "tone": "warning",
                "kicker": "financeiro",
                "title": "Saldo atual negativo",
                "copy": "Vale revisar lançamentos e recebimentos previstos.",
                "primary": ("Abrir financeiro", _go_financeiro_lancamentos),
            }
        )

    if not notifications:
        notifications.append(
            {
                "tone": "success",
                "kicker": "situação estável",
                "title": "Nenhuma pendência crítica",
                "copy": "Bom momento para atualizar processos e cadastros.",
                "primary": ("Novo processo", _go_trabalhos_cadastro),
            }
        )

    return notifications[:4]


# ==========================================================
# Render helpers de listas
# ==========================================================


def _render_surface_list_item(
    *,
    tone: str,
    title: str,
    body_lines: list[str] | None = None,
    chips: list[str] | None = None,
) -> None:
    body_lines = body_lines or []
    chips = chips or []

    tone_cls = {
        "danger": "sp-dash-list-card-danger",
        "warning": "sp-dash-list-card-warning",
        "info": "sp-dash-list-card-info",
        "success": "sp-dash-list-card-success",
    }.get(tone, "")

    body_html = "".join(
        f"<div class='sp-dash-list-card-sub'>{line}</div>"
        for line in body_lines
        if line
    )
    chips_html = "".join(chips)

    _render_html(
        f"""
        <div class="sp-dash-list-card {tone_cls}">
          <div class="sp-dash-list-card-title">{title}</div>
          {body_html}
          <div class="sp-dash-chip-row">{chips_html}</div>
        </div>
        """
    )


def _render_prazo_cards(rows: list, empty_title: str, empty_subtitle: str) -> None:
    if not rows:
        empty_state(
            title=empty_title,
            subtitle=empty_subtitle,
            icon="✅",
        )
        return

    for _id, evento, data_limite, prioridade, numero_processo, tipo_acao in rows:
        dias = int(_dias_restantes(data_limite))
        status = _status_prazo(dias)
        tone = _tone_from_prazo_status(dias)
        prior = _prior_badge(prioridade)

        title = (
            f"{_esc(numero_processo, 'Sem referência')} – "
            f"{_esc(tipo_acao, 'Sem tipo')}"
        )

        chip_tone = {
            "danger": "sp-chip-danger",
            "warning": "sp-chip-warning",
            "info": "sp-chip-info",
            "success": "sp-chip-success",
        }.get(tone, "sp-chip-neutral")

        _render_surface_list_item(
            tone=tone,
            title=title,
            body_lines=[f"<b>Evento:</b> {_esc(evento, 'Sem evento')}"],
            chips=[
                f"<span class='sp-chip'>📅 {escape(format_date_br(data_limite))}</span>",
                f"<span class='sp-chip {chip_tone}'>⏳ {dias} dia(s)</span>",
                f"<span class='sp-chip'>{escape(status)}</span>",
                f"<span class='sp-chip'>⚖️ {escape(prior)}</span>",
            ],
        )


def _render_agenda_cards(rows: list, empty_title: str, empty_subtitle: str) -> None:
    if not rows:
        empty_state(
            title=empty_title,
            subtitle=empty_subtitle,
            icon="📭",
        )
        return

    now_n = _naive(now_br())

    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows:
        inicio_br = ensure_br(inicio)
        inicio_n = _naive(inicio_br)
        inicio_br_txt = inicio_br.strftime("%d/%m/%Y %H:%M")

        hours_left = (inicio_n - now_n).total_seconds() / 3600.0
        alert_label, tone = _agenda_status(hours_left)

        title = (
            f"{_esc(numero_processo, 'Sem referência')} – "
            f"{_esc(tipo_acao, 'Sem tipo')}"
        )

        chips = [
            f"<span class='sp-chip'>📌 {_esc(tipo, 'Sem tipo')}</span>",
            f"<span class='sp-chip'>🕒 {escape(inicio_br_txt)}</span>",
            _agenda_rest_chip(hours_left),
            f"<span class='sp-chip'>{escape(alert_label)}</span>",
        ]

        if local:
            chips.append(
                f"<span class='sp-chip'>📍 {_esc(local, 'Local não informado')}</span>"
            )

        _render_surface_list_item(
            tone=tone,
            title=title,
            chips=chips,
        )


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
        numero_processo,
        tipo_acao,
    ) in rows_prazos_atrasados:
        dias = int(_dias_restantes(data_limite))
        items.append(
            {
                "sort_dt": ensure_br(data_limite),
                "tone": "danger",
                "kind": "Prazo",
                "headline": f"{_safe_text(numero_processo, 'Sem referência')} – {_safe_text(evento, 'Sem evento')}",
                "meta": f"vencido há {abs(dias)} dia(s)",
                "detail": _safe_text(tipo_acao, "Sem tipo"),
            }
        )

    for (
        _id,
        evento,
        data_limite,
        prioridade,
        numero_processo,
        tipo_acao,
    ) in rows_prazos_7d:
        dias = int(_dias_restantes(data_limite))
        items.append(
            {
                "sort_dt": ensure_br(data_limite),
                "tone": _tone_from_prazo_status(dias),
                "kind": "Prazo",
                "headline": f"{_safe_text(numero_processo, 'Sem referência')} – {_safe_text(evento, 'Sem evento')}",
                "meta": f"vence em {dias} dia(s)",
                "detail": _safe_text(tipo_acao, "Sem tipo"),
            }
        )

    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows_ag_24h:
        inicio_br = ensure_br(inicio)
        hours_left = (_naive(inicio_br) - _naive(now_br())).total_seconds() / 3600.0
        _label, tone = _agenda_status(hours_left)
        items.append(
            {
                "sort_dt": inicio_br,
                "tone": tone,
                "kind": "Agenda",
                "headline": f"{_safe_text(numero_processo, 'Sem referência')} – {_safe_text(tipo, 'Sem tipo')}",
                "meta": inicio_br.strftime("%d/%m %H:%M"),
                "detail": _safe_text(local, _safe_text(tipo_acao, "Sem local")),
            }
        )

    seen_agenda_keys: set[str] = set()
    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows_ag_24h:
        seen_agenda_keys.add(f"{_id}")

    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows_ag_7d:
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
                "headline": f"{_safe_text(numero_processo, 'Sem referência')} – {_safe_text(tipo, 'Sem tipo')}",
                "meta": inicio_br.strftime("%d/%m %H:%M"),
                "detail": _safe_text(local, _safe_text(tipo_acao, "Sem local")),
            }
        )

    items.sort(key=lambda x: x["sort_dt"])
    return items[:8]


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
        total_proc = int(s.execute(stmt_total).scalar_one())

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
        "total_proc": total_proc,
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
def _fetch_ultimos_processos_cached(
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


def _render_header(kpis: dict[str, Any] | None = None) -> None:
    atrasados = (kpis or {}).get("prazos_atrasados", 0)
    agenda_24h = (kpis or {}).get("ag_24h", 0)
    ativos = (kpis or {}).get("ativos", 0)

    subtitle = (
        f"{_greeting()}. {_today_label()}. "
        f"{ativos} ativo(s), {atrasados} atraso(s), {agenda_24h} compromisso(s) em 24h."
    )

    page_header(
        "Painel",
        subtitle,
        actions=[
            HeaderAction(
                "Prazos",
                key="dash_hdr_prazos",
                type="secondary",
                on_click=_go_prazos_lista,
            ),
            HeaderAction(
                "Trabalhos",
                key="dash_hdr_trabalhos",
                type="secondary",
                on_click=_go_trabalhos_lista,
            ),
            HeaderAction(
                "Financeiro",
                key="dash_hdr_financeiro",
                type="secondary",
                on_click=_go_financeiro_lancamentos,
            ),
        ],
        compact=False,
        divider=False,
        bottom_spacing_rem=0.16,
    )


def _render_top_bar() -> str | None:
    with section(
        "Visão atual",
        subtitle="Filtre o painel por atuação",
        divider=False,
        compact=True,
    ):
        left, right = grid_weights((1.06, 0.94), weights_mobile=(1, 1), gap="medium")

        with left:
            atuacao_label = st.selectbox(
                "Atuação",
                list(ATUACAO_UI.keys()),
                index=0,
                key="dash_atuacao_ui",
            )

        with right:
            _render_html(
                """
                <div class="sp-dash-filter-note">
                  <div class="sp-dash-filter-note-copy">
                    O painel se ajusta automaticamente conforme a atuação selecionada.
                  </div>
                  <span class="sp-chip">tempo real</span>
                </div>
                """
            )

    return ATUACAO_UI[atuacao_label]


def _render_dashboard_summary(kpis: dict[str, Any], atuacao_label: str) -> None:
    with section(
        "Indicadores principais",
        subtitle=f"Leitura rápida • {atuacao_label}",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=2)

        with c1:
            card(
                "Processos ativos",
                f"{kpis['ativos']}",
                f"{kpis['total_proc']} cadastrados",
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
                else "nenhum prazo em aberto"
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
                "Agenda",
                f"{kpis['ag_7d']}",
                _kpi_agenda_subtitle(kpis["ag_24h"], kpis["ag_72h"], kpis["ag_7d"]),
                tone=agenda_tone,
                emphasize=agenda_emph,
            )

        with c4:
            card(
                "Saldo",
                f"R$ {_fmt_money_br(kpis['saldo'])}",
                (
                    f"Receitas R$ {_fmt_money_br(kpis['receitas'])} • "
                    f"Despesas R$ {_fmt_money_br(kpis['despesas'])}"
                ),
                tone=("success" if kpis["saldo"] >= 0 else "danger"),
                emphasize=True,
            )


def _render_quick_actions() -> None:
    with section(
        "Ações rápidas",
        subtitle="Atalhos do dia",
        divider=False,
    ):
        _render_html('<div class="sp-dashboard-action-grid">')
        try:
            c1, c2, c3, c4 = grid(4, columns_mobile=2)

            with c1:
                _render_action_button(
                    "📁 Novo processo",
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
                    "📅 Nova vistoria",
                    key="dash_quick_agenda",
                    on_click=_go_agenda,
                )

            with c4:
                _render_action_button(
                    "💰 Registrar financeiro",
                    key="dash_quick_financeiro",
                    on_click=_go_financeiro_lancamentos,
                )
        finally:
            _render_html("</div>")


def _render_radar_panel(kpis: dict[str, Any]) -> None:
    with section(
        "Radar do dia",
        subtitle="O que merece atenção primeiro",
        divider=False,
    ):
        if kpis["prazos_atrasados"] > 0:
            title = "Prioridade: regularizar prazos vencidos"
            copy = "Existem pendências atrasadas que devem ser tratadas antes das demais frentes."
            cta_label = "Abrir prazos atrasados"
            cta_page = "Prazos"
            cta_state = {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Atrasados",
            }
            chips = [
                f"<span class='sp-chip sp-chip-danger'>Atrasados: {kpis['prazos_atrasados']}</span>",
                f"<span class='sp-chip'>Em 7 dias: {kpis['prazos_7dias']}</span>",
            ]
        elif kpis["ag_24h"] > 0:
            title = "Prioridade: preparar agenda imediata"
            copy = "Há compromisso próximo. Vale revisar local, documentos e horários."
            cta_label = "Abrir agenda"
            cta_page = "Agenda"
            cta_state = None
            chips = [
                f"<span class='sp-chip sp-chip-warning'>Agenda 24h: {kpis['ag_24h']}</span>",
                f"<span class='sp-chip'>Agenda 7 dias: {kpis['ag_7d']}</span>",
            ]
        elif kpis["prazos_7dias"] > 0:
            title = "Prioridade: organizar a próxima semana"
            copy = (
                "Existem vencimentos próximos. Antecipar agora reduz urgência depois."
            )
            cta_label = "Ver próximos prazos"
            cta_page = "Prazos"
            cta_state = {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Vencem (7 dias)",
            }
            chips = [
                f"<span class='sp-chip sp-chip-info'>Em 7 dias: {kpis['prazos_7dias']}</span>",
                f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
            ]
        else:
            title = "Painel estável"
            copy = "Sem urgências críticas neste recorte. Bom momento para atualizar a operação."
            cta_label = "Novo processo"
            cta_page = "Trabalhos"
            cta_state = {"trabalhos_section": "Cadastro"}
            chips = [
                f"<span class='sp-chip sp-chip-success'>Sem urgência crítica</span>",
                f"<span class='sp-chip'>Ativos: {kpis['ativos']}</span>",
            ]

        _render_html(
            f"""
            <div class="sp-dash-panel">
              <div class="sp-dash-panel-title">{escape(title)}</div>
              <div class="sp-dash-panel-copy">{escape(copy)}</div>
              <div class="sp-dash-chip-row">{''.join(chips)}</div>
            </div>
            """
        )

        spacer(0.08)
        _render_nav_button(
            cta_label,
            page=cta_page,
            state=cta_state,
            key="dash_radar_cta",
            type="primary",
        )


def _render_today_panel(kpis: dict[str, Any]) -> None:
    today = _build_today_state(kpis)

    with section(
        "Hoje",
        subtitle="Plano rápido para começar bem o dia",
        divider=False,
    ):
        _render_html(
            f"""
            <div class="sp-dash-panel">
              <div class="sp-dash-panel-title">{escape(today['title'])}</div>
              <div class="sp-dash-panel-copy">{escape(today['copy'])}</div>
              <div class="sp-dash-panel-list">
                {''.join(f"<div class='sp-dash-panel-item'>• {escape(item)}</div>" for item in today["items"])}
              </div>
            </div>
            """
        )

        spacer(0.08)
        c1, c2 = grid(2, columns_mobile=1)

        primary_label, primary_callback = today["primary"]
        secondary_label, secondary_callback = today["secondary"]

        with c1:
            _render_action_button(
                primary_label,
                key="dash_today_primary",
                button_type="primary",
                on_click=primary_callback,
            )

        with c2:
            _render_action_button(
                secondary_label,
                key="dash_today_secondary",
                on_click=secondary_callback,
            )


def _render_notifications_center(kpis: dict[str, Any]) -> None:
    with section(
        "Notificações",
        subtitle="Leitura rápida das pendências e sinais do painel",
        divider=False,
    ):
        notifications = _build_notifications(kpis)

        for idx, item in enumerate(notifications):
            tone_cls = {
                "danger": "sp-dash-note-card-danger",
                "warning": "sp-dash-note-card-warning",
                "info": "sp-dash-note-card-info",
                "success": "sp-dash-note-card-success",
            }.get(item["tone"], "")

            _render_html(
                f"""
                <div class="sp-dash-note-card {tone_cls}">
                    <div class="sp-dash-note-kicker">{escape(item['kicker'])}</div>
                    <div class="sp-dash-note-title">{escape(item['title'])}</div>
                    <div class="sp-dash-note-copy">{escape(item['copy'])}</div>
                </div>
                """
            )

            label, callback = item["primary"]
            st.button(
                label,
                key=f"dash_notification_action_{idx}",
                use_container_width=True,
                on_click=callback,
            )


def _render_timeline_preview(items: list[dict[str, Any]]) -> None:
    with section(
        "Próximos passos",
        subtitle="Linha do tempo operacional",
        divider=False,
    ):
        if not items:
            empty_state(
                title="Nenhum evento próximo",
                subtitle="Quando houver prazos ou compromissos, eles aparecerão aqui.",
                icon="🗓️",
            )
            return

        for item in items:
            pill_class = {
                "danger": "sp-chip-danger",
                "warning": "sp-chip-warning",
                "info": "sp-chip-info",
                "success": "sp-chip-success",
            }.get(item["tone"], "")

            _render_html(
                f"""
                <div class="sp-dash-timeline-item">
                    <div class="sp-dash-timeline-head">
                        <div>
                            <div class="sp-dash-timeline-title">{_esc(item['headline'])}</div>
                            <div class="sp-dash-timeline-sub">{_esc(item['detail'])}</div>
                        </div>
                        <span class="sp-chip {pill_class}">{_esc(item['kind'])}</span>
                    </div>
                    <div class="sp-dash-chip-row">
                        <span class="sp-chip {pill_class}">{_esc(item['meta'])}</span>
                    </div>
                </div>
                """
            )


def _render_finance_summary(kpis: dict[str, Any]) -> None:
    with section(
        "Financeiro",
        subtitle="Resumo da posição atual",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=2)

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
                "Saldo",
                f"R$ {_fmt_money_br(kpis['saldo'])}",
                "posição atual",
                tone=saldo_tone,
                emphasize=True,
            )

        with c4:
            _render_nav_button(
                "Abrir financeiro",
                page="Financeiro",
                state={"financeiro_section": "Lançamentos"},
                key="dash_open_financeiro_compact",
                type="primary",
            )


# ==========================================================
# Tabs
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
        "Prazos atrasados",
        subtitle="Top 10 com maior urgência",
        divider=False,
    ):
        _render_prazo_cards(
            rows_atrasados,
            "Nenhum prazo atrasado no momento",
            "Seu painel não possui pendências vencidas neste recorte.",
        )
        spacer(0.08)
        _render_nav_button(
            "Abrir lista completa",
            page="Prazos",
            state={"prazos_section": "Lista"},
            key="dash_open_prazos_all",
            type="primary",
        )

    spacer(0.14)

    with section(
        "Prazos em até 7 dias",
        subtitle="Itens que exigem organização no curto prazo",
        divider=False,
    ):
        _render_prazo_cards(
            rows_7d,
            "Sem vencimentos na próxima janela",
            "Não há prazos previstos para vencer em até 7 dias.",
        )

    with st.expander("Ver em tabela", expanded=False):
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
        "Próximas 24 horas",
        subtitle="Compromissos com prioridade operacional",
        divider=False,
    ):
        _render_agenda_cards(
            rows_24h,
            "Nenhum agendamento nas próximas 24 horas",
            "Sua agenda imediata está livre neste momento.",
        )
        spacer(0.08)
        _render_nav_button(
            "Abrir agenda",
            page="Agenda",
            key="dash_open_agenda",
            type="primary",
        )

    spacer(0.14)

    with section(
        "Próximos 7 dias",
        subtitle="Planejamento da semana",
        divider=False,
    ):
        _render_agenda_cards(
            rows_7d,
            "Nenhum agendamento nos próximos 7 dias",
            "Quando houver compromissos programados, eles aparecerão aqui.",
        )

    with st.expander("Ver em tabela", expanded=False):
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
    rows = _fetch_ultimos_processos_cached(owner_user_id, tipo_val, version)

    with section(
        "Últimos processos",
        subtitle="Registros mais recentes conforme o filtro atual",
        divider=False,
    ):
        if not rows:
            empty_state(
                title="Nenhum processo cadastrado ainda",
                subtitle="Quando você cadastrar processos para esta atuação, eles aparecerão aqui.",
                icon="📁",
            )
            return

        _render_dataframe_or_caption(
            _build_trabalhos_df(rows),
            height=420,
            empty_title="Sem processos para exibir",
            empty_subtitle="Não há registros neste recorte.",
            empty_icon="📁",
        )

        spacer(0.08)
        _render_nav_button(
            "Abrir processos",
            page="Trabalhos",
            state={"trabalhos_section": "Lista"},
            key="dash_open_trabalhos",
            type="primary",
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
        _render_dashboard_summary(kpis, atuacao_label)

        spacer(0.14)
        _render_quick_actions()

        spacer(0.16)
        left, right = grid_weights((1.02, 0.98), weights_mobile=(1, 1), gap="medium")

        with left:
            _render_radar_panel(kpis)
            spacer(0.14)
            _render_today_panel(kpis)

        with right:
            _render_notifications_center(kpis)
            spacer(0.14)
            timeline_items = _build_timeline_items(
                rows_prazos_atrasados,
                rows_prazos_7d,
                rows_ag_24h,
                rows_ag_7d,
            )
            _render_timeline_preview(timeline_items)

        spacer(0.16)
        _render_finance_summary(kpis)

        spacer(0.18)
        tab1, tab2, tab3 = st.tabs(
            [
                f"⏳ Prazos ({kpis['prazos_atrasados']})",
                f"📅 Agenda ({kpis['ag_7d']})",
                f"🗂️ Processos ({kpis['ativos']})",
            ]
        )

        with tab1:
            _render_tab_prazos(owner_user_id, tipo_val, kpis, version)

        with tab2:
            _render_tab_agenda(owner_user_id, tipo_val, kpis, version)

        with tab3:
            _render_tab_trabalhos(owner_user_id, tipo_val, version)
