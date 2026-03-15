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
# Base UI helpers
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
        .block-container {
            padding-top: 0.90rem;
            padding-bottom: 2rem;
        }

        /* -------------------------------------------------- */
        /* Layout base                                        */
        /* -------------------------------------------------- */
        .sp-panel {
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: rgba(255,255,255,0.96);
            border-radius: 18px;
            box-shadow: 0 8px 28px rgba(15, 23, 42, 0.04);
        }

        .sp-panel-soft {
            border: 1px solid rgba(15, 23, 42, 0.07);
            background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,250,252,.98));
            border-radius: 18px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.035);
        }

        .sp-muted {
            color: rgba(15,23,42,.62);
        }

        .sp-caption {
            font-size: .75rem;
            font-weight: 800;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: rgba(15,23,42,.42);
        }

        /* -------------------------------------------------- */
        /* Hero                                               */
        /* -------------------------------------------------- */
        .sp-page-hero {
            padding: 1rem 1rem 0.95rem 1rem;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(247,250,252,0.96));
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.85rem;
        }

        .sp-page-hero-grid {
            display: grid;
            grid-template-columns: 1.45fr .95fr;
            gap: 14px;
            align-items: start;
        }

        .sp-page-kicker {
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: rgba(15,23,42,.45);
            margin-bottom: 4px;
        }

        .sp-page-title {
            font-size: 1.55rem;
            font-weight: 900;
            line-height: 1.10;
            color: #0f172a;
        }

        .sp-page-subtitle {
            margin-top: 7px;
            color: rgba(15,23,42,.68);
            line-height: 1.48;
            font-size: .93rem;
            max-width: 780px;
        }

        .sp-chip-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
        }

        .sp-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            border-radius: 999px;
            background: rgba(15,23,42,.06);
            color: rgba(15,23,42,.80);
            font-size: .79rem;
            font-weight: 750;
            line-height: 1;
        }

        .sp-chip-danger { background: rgba(220,38,38,.10); color: #991b1b; }
        .sp-chip-warning { background: rgba(245,158,11,.13); color: #92400e; }
        .sp-chip-info { background: rgba(37,99,235,.10); color: #1d4ed8; }
        .sp-chip-success { background: rgba(22,163,74,.10); color: #166534; }
        .sp-chip-neutral { background: rgba(15,23,42,.06); color: rgba(15,23,42,.78); }

        .sp-inline-metrics {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .sp-mini-stat {
            min-height: 88px;
            border-radius: 16px;
            border: 1px solid rgba(15,23,42,.08);
            background: #ffffff;
            padding: 12px 13px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .sp-mini-stat-label {
            font-size: .70rem;
            font-weight: 900;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: rgba(15,23,42,.45);
        }

        .sp-mini-stat-value {
            font-size: 1.18rem;
            font-weight: 900;
            color: #0f172a;
            margin-top: 3px;
            line-height: 1.1;
        }

        .sp-mini-stat-sub {
            margin-top: 5px;
            color: rgba(15,23,42,.60);
            font-size: .80rem;
            line-height: 1.25;
        }

        /* -------------------------------------------------- */
        /* Banner / summary                                   */
        /* -------------------------------------------------- */
        .sp-banner-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: .65rem 0 .95rem 0;
        }

        .sp-banner {
            border-radius: 16px;
            padding: 12px 13px;
            border: 1px solid rgba(15,23,42,.08);
            background: #fff;
            box-shadow: 0 6px 18px rgba(15,23,42,.04);
        }

        .sp-banner-danger { border-left: 5px solid #dc2626; }
        .sp-banner-warning { border-left: 5px solid #f59e0b; }
        .sp-banner-info { border-left: 5px solid #2563eb; }
        .sp-banner-success { border-left: 5px solid #16a34a; }

        .sp-banner-title {
            font-size: .72rem;
            font-weight: 900;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: rgba(15,23,42,.45);
            margin-bottom: 4px;
        }

        .sp-banner-text {
            font-size: .90rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.35;
        }

        /* -------------------------------------------------- */
        /* Surface section                                    */
        /* -------------------------------------------------- */
        .sp-surface {
            border-radius: 18px;
            border: 1px solid rgba(15,23,42,.08);
            background: rgba(255,255,255,.97);
            padding: 14px;
            box-shadow: 0 8px 24px rgba(15,23,42,.04);
        }

        .sp-surface-title {
            margin-bottom: 8px;
            font-size: .78rem;
            font-weight: 900;
            letter-spacing: .06em;
            text-transform: uppercase;
            color: rgba(15,23,42,.42);
        }

        .sp-focus-title {
            font-size: 1.08rem;
            font-weight: 900;
            line-height: 1.22;
            color: #0f172a;
        }

        .sp-focus-copy {
            margin-top: 8px;
            color: rgba(15,23,42,.74);
            line-height: 1.52;
            font-size: .92rem;
        }

        /* -------------------------------------------------- */
        /* List cards                                          */
        /* -------------------------------------------------- */
        .sp-list-card {
            border: 1px solid rgba(15,23,42,.08);
            border-radius: 16px;
            padding: 12px 13px;
            background: #fff;
            box-shadow: 0 4px 14px rgba(15,23,42,.03);
            margin-bottom: 10px;
        }

        .sp-list-card-danger { border-left: 4px solid #dc2626; }
        .sp-list-card-warning { border-left: 4px solid #f59e0b; }
        .sp-list-card-info { border-left: 4px solid #2563eb; }
        .sp-list-card-success { border-left: 4px solid #16a34a; }

        .sp-list-card-head {
            display: flex;
            align-items: start;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 8px;
        }

        .sp-list-card-title {
            font-weight: 850;
            color: #0f172a;
            line-height: 1.30;
            font-size: .95rem;
        }

        .sp-list-card-sub {
            color: rgba(15,23,42,.64);
            font-size: .86rem;
            line-height: 1.40;
            margin-top: 4px;
        }

        /* -------------------------------------------------- */
        /* Quick strip                                         */
        /* -------------------------------------------------- */
        .sp-quick-strip {
            border: 1px dashed rgba(15,23,42,.12);
            background: rgba(248,250,252,.75);
            border-radius: 16px;
            padding: 10px 12px;
        }

        .sp-quick-strip-title {
            font-size: .73rem;
            font-weight: 900;
            letter-spacing: .05em;
            text-transform: uppercase;
            color: rgba(15,23,42,.42);
            margin-bottom: 4px;
        }

        .sp-quick-strip-copy {
            color: rgba(15,23,42,.72);
            font-size: .88rem;
            line-height: 1.42;
        }

        /* -------------------------------------------------- */
        /* Streamlit adjustments                               */
        /* -------------------------------------------------- */
        div[data-baseweb="tab-list"] {
            gap: .35rem;
        }

        div[data-baseweb="tab"] {
            border-radius: 12px !important;
            padding: .55rem .90rem !important;
            background: rgba(15,23,42,.04);
            font-weight: 800 !important;
        }

        div[data-baseweb="tab-highlight"] {
            border-radius: 999px !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
        }

        /* -------------------------------------------------- */
        /* Responsive                                          */
        /* -------------------------------------------------- */
        @media (max-width: 980px) {
            .sp-page-hero-grid {
                grid-template-columns: 1fr;
            }

            .sp-inline-metrics {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .sp-banner-row {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 640px) {
            .sp-inline-metrics {
                grid-template-columns: 1fr;
            }

            .sp-page-title {
                font-size: 1.35rem;
            }

            .sp-list-card-title {
                font-size: .92rem;
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
# Navegação rápida
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
# Render helpers de cards/listas
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
        "danger": "sp-list-card-danger",
        "warning": "sp-list-card-warning",
        "info": "sp-list-card-info",
        "success": "sp-list-card-success",
    }.get(tone, "")

    body_html = "".join(
        f"<div class='sp-list-card-sub'>{line}</div>" for line in body_lines if line
    )
    chips_html = "".join(chips)

    _render_html(
        f"""
        <div class="sp-list-card {tone_cls}">
          <div class="sp-list-card-head">
            <div>
              <div class="sp-list-card-title">{title}</div>
              {body_html}
            </div>
          </div>
          <div class="sp-chip-row">{chips_html}</div>
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
# Timeline / radar / banners
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


def _render_priority_banners(
    kpis: dict[str, Any],
    rows_prazos_atrasados: list,
    rows_ag_24h: list,
    rows_prazos_7d: list,
) -> None:
    banners: list[str] = []

    if kpis["prazos_atrasados"] > 0:
        primeiro = rows_prazos_atrasados[0] if rows_prazos_atrasados else None
        ref = (
            _safe_text(primeiro[4], "Sem referência") if primeiro else "Sem referência"
        )
        text = f"{kpis['prazos_atrasados']} prazo(s) atrasado(s). Priorize {ref}."
        banners.append(
            f"<div class='sp-banner sp-banner-danger'><div class='sp-banner-title'>Urgência crítica</div><div class='sp-banner-text'>{escape(text)}</div></div>"
        )

    if kpis["ag_24h"] > 0:
        primeiro = rows_ag_24h[0] if rows_ag_24h else None
        horario = (
            ensure_br(primeiro[2]).strftime("%d/%m %H:%M")
            if primeiro
            else "sem horário"
        )
        ref = (
            _safe_text(primeiro[4], "Sem referência") if primeiro else "Sem referência"
        )
        text = f"{kpis['ag_24h']} compromisso(s) em 24h. Próximo: {ref} às {horario}."
        banners.append(
            f"<div class='sp-banner sp-banner-warning'><div class='sp-banner-title'>Agenda imediata</div><div class='sp-banner-text'>{escape(text)}</div></div>"
        )

    if kpis["prazos_7dias"] > 0 and kpis["prazos_atrasados"] == 0:
        primeiro = rows_prazos_7d[0] if rows_prazos_7d else None
        venc = format_date_br(primeiro[2]) if primeiro else "sem data"
        ref = (
            _safe_text(primeiro[4], "Sem referência") if primeiro else "Sem referência"
        )
        text = f"{kpis['prazos_7dias']} prazo(s) na semana. Próximo: {ref} em {venc}."
        banners.append(
            f"<div class='sp-banner sp-banner-info'><div class='sp-banner-title'>Planejamento da semana</div><div class='sp-banner-text'>{escape(text)}</div></div>"
        )

    if not banners:
        banners.append(
            "<div class='sp-banner sp-banner-success'><div class='sp-banner-title'>Situação estável</div><div class='sp-banner-text'>Sem pendências críticas no momento. Bom momento para atualizar processos, organizar documentos e registrar novos itens.</div></div>"
        )

    _render_html(f"<div class='sp-banner-row'>{''.join(banners)}</div>")


def _render_timeline_preview(items: list[dict[str, Any]]) -> None:
    with section(
        "Linha do tempo operacional",
        subtitle="Próximos passos em ordem cronológica",
        divider=False,
    ):
        if not items:
            empty_state(
                title="Nenhum evento próximo",
                subtitle="Quando houver prazos ou compromissos no radar, eles aparecerão aqui.",
                icon="🗓️",
            )
            return

        for item in items:
            tone = item["tone"]
            pill_class = {
                "danger": "sp-chip-danger",
                "warning": "sp-chip-warning",
                "info": "sp-chip-info",
                "success": "sp-chip-success",
            }.get(tone, "")
            _render_html(
                f"""
                <div class="sp-list-card">
                    <div class="sp-list-card-head">
                        <div>
                            <div class="sp-list-card-title">{_esc(item['headline'])}</div>
                            <div class="sp-list-card-sub">{_esc(item['detail'])}</div>
                        </div>
                        <span class="sp-chip {pill_class}">{_esc(item['kind'])}</span>
                    </div>
                    <div class="sp-chip-row">
                        <span class="sp-chip {pill_class}">{_esc(item['meta'])}</span>
                    </div>
                </div>
                """
            )


def _render_radar_panel(
    *,
    kpis: dict[str, Any],
) -> None:
    with section(
        "Radar do dia",
        subtitle="O que merece sua atenção primeiro",
        divider=False,
    ):
        if kpis["prazos_atrasados"] > 0:
            title = "Prioridade máxima: regularizar prazos vencidos"
            tone = "danger"
            lines = [
                f"Você possui <b>{kpis['prazos_atrasados']}</b> prazo(s) atrasado(s).",
                "Comece pelos itens vencidos antes de abrir novas frentes administrativas.",
            ]
            cta_label = "Abrir prazos atrasados"
            cta_page = "Prazos"
            cta_state = {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Atrasados",
            }
        elif kpis["ag_24h"] > 0:
            title = "Atenção operacional nas próximas 24 horas"
            tone = "warning"
            lines = [
                f"Há <b>{kpis['ag_24h']}</b> compromisso(s) muito próximo(s).",
                "Vale revisar deslocamento, documentos, endereço e horário antes do início.",
            ]
            cta_label = "Abrir agenda"
            cta_page = "Agenda"
            cta_state = None
        elif kpis["prazos_7dias"] > 0:
            title = "Organize a semana com antecedência"
            tone = "info"
            lines = [
                f"Há <b>{kpis['prazos_7dias']}</b> prazo(s) vencendo em até 7 dias.",
                "Bom momento para separar peças, documentos e prioridades por trabalho.",
            ]
            cta_label = "Ver próximos prazos"
            cta_page = "Prazos"
            cta_state = {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Vencem (7 dias)",
            }
        else:
            title = "Painel sob controle no momento"
            tone = "success"
            lines = [
                "Não há pendências críticas neste recorte.",
                "Você pode usar este momento para cadastrar, revisar ou atualizar trabalhos.",
            ]
            cta_label = "Novo trabalho"
            cta_page = "Trabalhos"
            cta_state = {"trabalhos_section": "Cadastro"}

        badge_class = {
            "danger": "sp-chip-danger",
            "warning": "sp-chip-warning",
            "info": "sp-chip-info",
            "success": "sp-chip-success",
        }.get(tone, "sp-chip-neutral")

        _render_html(
            f"""
            <div class="sp-surface">
              <div class="sp-surface-title">foco do momento</div>
              <div class="sp-focus-title">{title}</div>
              <div class="sp-focus-copy">
                {'<br>'.join(lines)}
              </div>
              <div class="sp-chip-row" style="margin-top:12px;">
                <span class="sp-chip {badge_class}">Prazos atrasados: {kpis['prazos_atrasados']}</span>
                <span class="sp-chip">Prazos em 7 dias: {kpis['prazos_7dias']}</span>
                <span class="sp-chip">Agenda em 24h: {kpis['ag_24h']}</span>
                <span class="sp-chip">Agenda em 7 dias: {kpis['ag_7d']}</span>
              </div>
            </div>
            """
        )

        spacer(0.10)
        _render_nav_button(
            cta_label,
            page=cta_page,
            state=cta_state,
            key="dash_radar_cta",
            type="primary",
        )


def _render_quick_context_strip(kpis: dict[str, Any], atuacao_label: str) -> None:
    saldo_txt = f"R$ {_fmt_money_br(kpis['saldo'])}"
    tone_cls = "sp-chip-success" if kpis["saldo"] >= 0 else "sp-chip-danger"

    _render_html(
        f"""
        <div class="sp-quick-strip">
            <div class="sp-quick-strip-title">leitura executiva</div>
            <div class="sp-quick-strip-copy">
                Atuação atual: <b>{escape(atuacao_label)}</b> •
                {kpis['ativos']} processo(s) ativo(s) •
                {kpis['prazos_abertos']} prazo(s) em aberto •
                {kpis['ag_7d']} compromisso(s) em 7 dias •
                <span class="sp-chip {tone_cls}" style="vertical-align:middle;">Saldo {escape(saldo_txt)}</span>
            </div>
        </div>
        """
    )


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
    saldo = (kpis or {}).get("saldo", 0.0)

    saldo_sub = "posição consolidada"
    agenda_sub = "compromissos próximos" if agenda_24h > 0 else "sem urgência imediata"
    atraso_sub = "prioridade máxima" if atrasados > 0 else "nenhum vencido"
    ativos_sub = "em andamento"

    _render_html(
        f"""
        <div class="sp-page-hero">
          <div class="sp-page-hero-grid">
            <div>
              <div class="sp-page-kicker">gestão técnica</div>
              <div class="sp-page-title">Painel de Controle</div>
              <div class="sp-page-subtitle">
                Visão consolidada dos seus processos, prazos, agenda e posição financeira,
                com foco no que exige ação imediata e no que precisa ser planejado para os próximos dias.
              </div>
              <div class="sp-chip-row">
                <span class="sp-chip">{escape(_greeting())}</span>
                <span class="sp-chip">{escape(_today_label())}</span>
                <span class="sp-chip">Painel executivo</span>
              </div>
            </div>
            <div class="sp-inline-metrics">
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">processos ativos</div>
                <div class="sp-mini-stat-value">{ativos}</div>
                <div class="sp-mini-stat-sub">{escape(ativos_sub)}</div>
              </div>
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">prazos atrasados</div>
                <div class="sp-mini-stat-value">{atrasados}</div>
                <div class="sp-mini-stat-sub">{escape(atraso_sub)}</div>
              </div>
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">agenda 24h</div>
                <div class="sp-mini-stat-value">{agenda_24h}</div>
                <div class="sp-mini-stat-sub">{escape(agenda_sub)}</div>
              </div>
              <div class="sp-mini-stat">
                <div class="sp-mini-stat-label">saldo atual</div>
                <div class="sp-mini-stat-value">R$ {_fmt_money_br(saldo)}</div>
                <div class="sp-mini-stat-sub">{escape(saldo_sub)}</div>
              </div>
            </div>
          </div>
        </div>
        """
    )

    page_header(
        "",
        "",
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
        compact=True,
        divider=False,
    )


def _render_top_bar() -> str | None:
    with section(
        "Visão atual",
        subtitle="Escolha a atuação para filtrar o painel",
        divider=False,
        compact=True,
    ):
        left, right = grid_weights((1.0, 1.0), weights_mobile=(1, 1), gap="medium")

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
                <div class="sp-surface" style="min-height:58px; display:flex; align-items:center; justify-content:space-between; gap:10px;">
                  <div>
                    <div class="sp-surface-title" style="margin-bottom:3px;">modo do painel</div>
                    <div style="color:rgba(15,23,42,0.74); font-weight:700;">Filtro aplicado somente à atuação selecionada</div>
                  </div>
                  <div class="sp-chip">Atualizado em tempo real</div>
                </div>
                """
            )

    return ATUACAO_UI[atuacao_label]


def _render_dashboard_summary(kpis: dict[str, Any], atuacao_label: str) -> None:
    with section(
        "Indicadores principais",
        subtitle=f"Leitura rápida do painel • atuação: {atuacao_label}",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=2)

        with c1:
            card(
                "Processos ativos",
                f"{kpis['ativos']}",
                f"{kpis['total_proc']} cadastrados no total",
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
                "Prazos críticos",
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
                "Agenda da semana",
                f"{kpis['ag_7d']}",
                _kpi_agenda_subtitle(kpis["ag_24h"], kpis["ag_72h"], kpis["ag_7d"]),
                tone=agenda_tone,
                emphasize=agenda_emph,
            )

        with c4:
            card(
                "Saldo atual",
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
        "Ações rápidas", subtitle="Atalhos operacionais do dia", divider=False
    ):
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


def _render_finance_summary(kpis: dict[str, Any]) -> None:
    with section(
        "Financeiro",
        subtitle="Resumo rápido da posição atual",
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
        "Prazos atrasados", subtitle="Top 10 com maior urgência", divider=False
    ):
        _render_prazo_cards(
            rows_atrasados,
            "Nenhum prazo atrasado no momento",
            "Ótimo sinal. Seu painel não possui pendências vencidas neste recorte.",
        )
        spacer(0.08)
        _render_nav_button(
            "Abrir lista completa",
            page="Prazos",
            state={"prazos_section": "Lista"},
            key="dash_open_prazos_all",
            type="primary",
        )

    spacer(0.18)

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

    spacer(0.18)

    with section("Próximos 7 dias", subtitle="Planejamento da semana", divider=False):
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
        subtitle="Registros mais recentes conforme o filtro de atuação",
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
    st.set_page_config(layout="wide")

    with content_shell(max_width="1500px"):
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

        _render_header(kpis)

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

        _render_priority_banners(
            kpis,
            rows_prazos_atrasados,
            rows_ag_24h,
            rows_prazos_7d,
        )

        _render_quick_context_strip(kpis, atuacao_label)

        spacer(0.14)
        _render_dashboard_summary(kpis, atuacao_label)

        spacer(0.16)
        _render_quick_actions()

        spacer(0.18)
        left, right = grid_weights((1.1, 0.9), weights_mobile=(1, 1), gap="medium")

        with left:
            _render_radar_panel(kpis=kpis)

        with right:
            timeline_items = _build_timeline_items(
                rows_prazos_atrasados,
                rows_prazos_7d,
                rows_ag_24h,
                rows_ag_7d,
            )
            _render_timeline_preview(timeline_items)

        spacer(0.18)
        _render_finance_summary(kpis)

        spacer(0.22)
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
