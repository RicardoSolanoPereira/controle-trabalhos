from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

import pandas as pd
import streamlit as st
from sqlalchemy import case, func, select

from app.db.connection import get_session
from app.db.models import Agendamento, LancamentoFinanceiro, Prazo, Processo
from app.ui.layout import grid, section, spacer
from app.ui.page_header import HeaderAction, page_header
from app.ui.theme import card
from app.ui_state import navigate
from services.utils import ensure_br, format_date_br, now_br

ATUACAO_UI = {
    "(Todas)": None,
    "Perícia (Juízo)": "Perito Judicial",
    "Assistência Técnica": "Assistente Técnico",
    "Particular / Outros serviços": "Trabalho Particular",
}


# ==========================================================
# Helpers gerais
# ==========================================================


def _naive(dt: datetime) -> datetime:
    """Remove tzinfo caso venha timezone-aware."""
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


def _pct(part: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{round((part / total) * 100)}%"


def _apply_tipo_filter(stmt, tipo_val: str | None):
    return stmt if not tipo_val else stmt.where(Processo.papel == tipo_val)


def _cache_buster(owner_user_id: int) -> int:
    """
    Usa a versão global de dados da sessão.
    Mantido por compatibilidade com o mecanismo atual.
    """
    _ = owner_user_id
    return int(st.session_state.get("data_version", 0))


def _dt_bounds(hoje: date) -> tuple[datetime, datetime, datetime]:
    ate_7_dias = hoje + timedelta(days=7)
    start_today = datetime.combine(hoje, time.min)
    end_7d = datetime.combine(ate_7_dias, time.max)
    now_n = _naive(now_br())
    return start_today, end_7d, now_n


# ==========================================================
# Helpers de prazo
# ==========================================================


def _dias_restantes(dt: Any) -> int:
    dt_br = ensure_br(dt)
    hoje = now_br().date()
    return (dt_br.date() - hoje).days


def _status_prazo(dias: int) -> str:
    if dias < 0:
        return "🔴 Atrasado"
    if dias <= 5:
        return "🟠 Urgente"
    if dias <= 10:
        return "🟡 Atenção"
    return "🟢 Ok"


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
        return "🔥 Alta"
    if prioridade_norm.startswith("b"):
        return "🧊 Baixa"
    return "⚖️ Média"


def _alert_tone(prazos_atrasados: int, prazos_7dias: int) -> str:
    if prazos_atrasados > 0:
        return "danger"
    if prazos_7dias > 0:
        return "warning"
    return "success"


def _priority_banner_data(prazos_atrasados: int, prazos_7dias: int) -> dict[str, Any]:
    if prazos_atrasados > 0:
        return {
            "tone": "danger",
            "cta_label": "Ver atrasados",
            "cta_state": {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Atrasados",
            },
            "left_text": f"🔴 **{int(prazos_atrasados)} prazo(s) atrasado(s)**",
        }

    if prazos_7dias > 0:
        return {
            "tone": "warning",
            "cta_label": "Ver 7 dias",
            "cta_state": {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Vencem (7 dias)",
            },
            "left_text": f"🟠 **{int(prazos_7dias)} prazo(s) em até 7 dias**",
        }

    return {
        "tone": "success",
        "cta_label": "Novo prazo",
        "cta_state": {"prazos_section": "Cadastro"},
        "left_text": "🟢 **Nenhum prazo crítico**",
    }


# ==========================================================
# Helpers de agenda
# ==========================================================


def _agenda_status(hours_left: float) -> tuple[str, str]:
    if hours_left < 0:
        return "🔴 Atrasado", "danger"
    if hours_left <= 24:
        return "🟠 Urgente", "warning"
    if hours_left <= 72:
        return "🟡 Atenção", "info"
    return "🟢 Ok", "success"


def _agenda_rest_chip(hours_left: float) -> str:
    if hours_left < 0:
        return "<span class='sp-chip'>⏳ —</span>"

    if hours_left < 24:
        rest_txt = f"{max(0, int(round(hours_left)))}h"
    else:
        rest_txt = f"{max(0, int(round(hours_left / 24)))}d"

    return f"<span class='sp-chip'>⏳ {rest_txt}</span>"


def _kpi_agenda_subtitle(ag_24h: int, ag_72h: int, ag_7d: int) -> str:
    if ag_7d <= 0:
        return "nenhum agendado"
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
                "Trabalho": f"{numero_processo} – {tipo_acao or 'Sem tipo'}",
                "Evento": evento,
                "Venc.": format_date_br(data_limite),
                "Dias": dias,
                "Status": _status_prazo(dias),
                "Prior.": _prior_badge(prioridade),
            }
        )

    if not items:
        return pd.DataFrame()

    return pd.DataFrame(items).sort_values(by=["Dias", "Venc."], ascending=True)


def _build_agenda_df(rows: Iterable[tuple]) -> pd.DataFrame:
    items: list[dict[str, str]] = []

    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows:
        items.append(
            {
                "Trabalho": f"{numero_processo} – {tipo_acao or 'Sem tipo'}",
                "Tipo": tipo,
                "Início": ensure_br(inicio).strftime("%d/%m/%Y %H:%M"),
                "Local": local or "",
            }
        )

    return pd.DataFrame(items) if items else pd.DataFrame()


# ==========================================================
# Render de cards/listas
# ==========================================================


def _render_prazo_cards(rows: list, empty_msg: str) -> None:
    if not rows:
        st.caption(empty_msg)
        return

    for _id, evento, data_limite, prioridade, numero_processo, tipo_acao in rows:
        dias = int(_dias_restantes(data_limite))
        status = _status_prazo(dias)
        prior = _prior_badge(prioridade)
        tone = _tone_from_prazo_status(dias)

        st.markdown(
            f"""
            <div class="sp-surface sp-tone-{tone}" style="margin-bottom:10px;">
              <div style="font-weight:850; font-size:0.98rem;">
                {numero_processo} – {tipo_acao or "Sem tipo"}
              </div>
              <div style="margin-top:6px; color: rgba(15,23,42,0.75);">
                <b>Evento:</b> {evento}
              </div>
              <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
                <span class="sp-chip">📅 {format_date_br(data_limite)}</span>
                <span class="sp-chip">⏳ {dias} dia(s)</span>
                <span class="sp-chip">{status}</span>
                <span class="sp-chip">{prior}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_agenda_cards(rows: list, empty_msg: str) -> None:
    if not rows:
        st.caption(empty_msg)
        return

    now_n = _naive(now_br())

    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows:
        inicio_n = _naive(ensure_br(inicio))
        inicio_br_txt = ensure_br(inicio).strftime("%d/%m/%Y %H:%M")

        hours_left = (inicio_n - now_n).total_seconds() / 3600.0
        alert_label, tone = _agenda_status(hours_left)
        rest_chip = _agenda_rest_chip(hours_left)

        local_chip = f"<span class='sp-chip'>📍 {local}</span>" if local else ""

        st.markdown(
            f"""
            <div class="sp-surface sp-tone-{tone}" style="margin-bottom:10px;">
              <div style="font-weight:850; font-size:0.98rem;">
                {numero_processo} – {tipo_acao or "Sem tipo"}
              </div>
              <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
                <span class="sp-chip">📌 {tipo}</span>
                <span class="sp-chip">🕒 {inicio_br_txt}</span>
                {rest_chip}
                <span class="sp-chip">{alert_label}</span>
                {local_chip}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_dataframe_or_caption(df: pd.DataFrame, empty_text: str = "—") -> None:
    if df.empty:
        st.caption(empty_text)
        return

    st.dataframe(df, use_container_width=True, hide_index=True)


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
        use_container_width=True,
        key=key,
        type=type,
        on_click=lambda: navigate(page, state=state),
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
                                (LancamentoFinanceiro.tipo == "Receita"),
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
                                (LancamentoFinanceiro.tipo == "Despesa"),
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
# Blocos de render
# ==========================================================


def _render_header_actions() -> None:
    actions = [
        HeaderAction("⏳ Prazos", key="dash_hdr_prazos", type="secondary"),
        HeaderAction("📁 Trabalhos", key="dash_hdr_trabalhos", type="secondary"),
        HeaderAction("💰 Financeiro", key="dash_hdr_fin", type="secondary"),
    ]
    page_header(
        "Painel de Controle",
        "Alertas, prazos, agenda e financeiro",
        actions=actions,
        compact=False,
        divider=True,
    )

    if st.session_state.get("dash_hdr_prazos"):
        navigate("Prazos", state={"prazos_section": "Lista"})

    if st.session_state.get("dash_hdr_trabalhos"):
        navigate("Trabalhos", state={"trabalhos_section": "Lista"})

    if st.session_state.get("dash_hdr_fin"):
        navigate("Financeiro", state={"financeiro_section": "Lançamentos"})


def _render_filters() -> str | None:
    with section(None, divider=False):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            atuacao_label = st.selectbox(
                "Atuação",
                list(ATUACAO_UI.keys()),
                index=0,
                key="dash_atuacao_ui",
            )

        with col2:
            st.caption("Dica: use “(Todas)” para visão geral.")

    return ATUACAO_UI[atuacao_label]


def _render_priority_section(k: dict[str, Any], atuacao_label: str) -> None:
    banner = _priority_banner_data(k["prazos_atrasados"], k["prazos_7dias"])

    def _actions():
        _render_nav_button(
            banner["cta_label"],
            page="Prazos",
            state=banner["cta_state"],
            key="dash_cta",
            type="primary",
        )

    with section(
        "Prioridades",
        subtitle=atuacao_label,
        divider=False,
        header_actions=_actions,
    ):
        st.markdown(
            f"""
            <div class="sp-card sp-tone-{banner['tone']}">
              <div style="font-weight:900;font-size:1.02rem;">Status de prazos</div>
              <div class="sp-muted" style="margin-top:4px;">O que precisa de ação agora.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        spacer(0.15)
        st.markdown(banner["left_text"])


def _render_kpi_section(k: dict[str, Any]) -> None:
    pct_atraso = _pct(k["prazos_atrasados"], k["prazos_abertos"])
    pct_7d = _pct(k["prazos_7dias"], k["prazos_abertos"])

    with section("Resumo", subtitle="Visão rápida do operacional", divider=False):
        row1_col1, row1_col2 = grid(2, columns_mobile=1)

        with row1_col1:
            tone_pz = (
                "danger"
                if k["prazos_atrasados"] > 0
                else ("warning" if k["prazos_7dias"] > 0 else "success")
            )
            card(
                "Prazos abertos",
                f"{k['prazos_abertos']}",
                f"{pct_atraso} atrasados • {pct_7d} em 7d",
                tone=tone_pz,
                emphasize=(k["prazos_atrasados"] > 0),
            )

        with row1_col2:
            card("Ativos", f"{k['ativos']}", "em andamento", tone="neutral")

        spacer(0.15)

        row2_col1, row2_col2 = grid(2, columns_mobile=1)

        with row2_col1:
            card("Trabalhos", f"{k['total_proc']}", "cadastrados", tone="info")

        with row2_col2:
            ag_tone, ag_emph = _kpi_agenda_tone(k["ag_24h"], k["ag_72h"], k["ag_7d"])
            card(
                "Agenda (7 dias)",
                f"{k['ag_7d']}",
                _kpi_agenda_subtitle(k["ag_24h"], k["ag_72h"], k["ag_7d"]),
                tone=ag_tone,
                emphasize=ag_emph,
            )

        spacer(0.25)

        cta1, cta2, cta3 = grid(3, columns_mobile=1)

        with cta1:
            _render_nav_button(
                "⏳ Ver prazos",
                page="Prazos",
                state={"prazos_section": "Lista"},
                key="go_prazos",
            )

        with cta2:
            _render_nav_button(
                "📁 Ver trabalhos",
                page="Trabalhos",
                state={"trabalhos_section": "Lista"},
                key="go_trabalhos",
            )

        with cta3:
            _render_nav_button(
                "📅 Ver agenda",
                page="Agenda",
                key="go_agenda",
            )


def _render_finance_section(k: dict[str, Any]) -> None:
    with section("Financeiro", subtitle="Receitas, despesas e saldo", divider=False):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            card(
                "Receitas (R$)",
                _fmt_money_br(k["receitas"]),
                "acumulado",
                tone="success",
            )

        with col2:
            card(
                "Despesas (R$)",
                _fmt_money_br(k["despesas"]),
                "acumulado",
                tone="danger",
            )

        spacer(0.15)

        card(
            "Saldo (R$)",
            _fmt_money_br(k["saldo"]),
            "receitas - despesas",
            tone=("success" if k["saldo"] >= 0 else "danger"),
            emphasize=True,
        )

        _render_nav_button(
            "Abrir financeiro",
            page="Financeiro",
            state={"financeiro_section": "Lançamentos"},
            key="go_fin",
            type="primary",
        )


def _render_tab_prazos(
    owner_user_id: int,
    tipo_val: str | None,
    k: dict[str, Any],
    version: int,
) -> None:
    rows_atrasados, rows_7d = _fetch_prazos_tables_cached(
        owner_user_id,
        tipo_val,
        k["start_today"].isoformat(timespec="seconds"),
        k["end_7d"].isoformat(timespec="seconds"),
        version,
    )

    with section("Atrasados (Top 10)", subtitle=None, divider=False):
        _render_prazo_cards(rows_atrasados, "✅ Sem prazos atrasados.")
        _render_nav_button(
            "Abrir lista completa",
            page="Prazos",
            state={"prazos_section": "Lista"},
            key="dash_open_prazos_all",
            type="primary",
        )

    spacer(0.25)

    with section("Vencem em até 7 dias (Top 10)", subtitle=None, divider=False):
        _render_prazo_cards(rows_7d, "✅ Sem prazos vencendo em até 7 dias.")

    with st.expander("Ver em tabela", expanded=False):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            st.caption("Atrasados")
            _render_dataframe_or_caption(_build_prazos_df(rows_atrasados))

        with col2:
            st.caption("7 dias")
            _render_dataframe_or_caption(_build_prazos_df(rows_7d))


def _render_tab_agenda(
    owner_user_id: int,
    tipo_val: str | None,
    k: dict[str, Any],
    version: int,
) -> None:
    rows_24h, rows_ag_7d = _fetch_agendamentos_cached(
        owner_user_id,
        tipo_val,
        k["now_n"].isoformat(timespec="seconds"),
        version,
    )

    with section("Próximas 24 horas (Top 10)", divider=False):
        _render_agenda_cards(rows_24h, "✅ Sem agendamentos nas próximas 24 horas.")
        _render_nav_button(
            "Abrir agenda",
            page="Agenda",
            key="dash_open_agenda",
            type="primary",
        )

    spacer(0.25)

    with section("Próximos 7 dias (Top 10)", divider=False):
        _render_agenda_cards(rows_ag_7d, "✅ Sem agendamentos nos próximos 7 dias.")

    with st.expander("Ver em tabela", expanded=False):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            st.caption("24 horas")
            _render_dataframe_or_caption(_build_agenda_df(rows_24h))

        with col2:
            st.caption("7 dias")
            _render_dataframe_or_caption(_build_agenda_df(rows_ag_7d))


def _render_tab_trabalhos(
    owner_user_id: int,
    tipo_val: str | None,
    version: int,
) -> None:
    procs = _fetch_ultimos_processos_cached(owner_user_id, tipo_val, version)

    with section(
        "Últimos trabalhos",
        subtitle="Registros mais recentes (respeita a atuação)",
        divider=False,
    ):
        if not procs:
            st.caption("Nenhum trabalho cadastrado ainda para esta atuação.")
            return

        dfp = pd.DataFrame(
            procs,
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

        dfp["tipo_acao"] = dfp["tipo_acao"].fillna("Sem tipo")
        dfp["tipo_trabalho"] = dfp["tipo_trabalho"].fillna("Assistente Técnico")

        dfp = dfp.rename(
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

        st.dataframe(dfp, use_container_width=True, hide_index=True, height=420)

        _render_nav_button(
            "Abrir trabalhos",
            page="Trabalhos",
            state={"trabalhos_section": "Lista"},
            key="dash_open_trabalhos",
            type="primary",
        )


# ==========================================================
# Render principal
# ==========================================================


def render(owner_user_id: int) -> None:
    _render_header_actions()

    tipo_val = _render_filters()
    atuacao_label = st.session_state.get("dash_atuacao_ui", "(Todas)")

    hoje_sp = now_br().date()
    version = _cache_buster(owner_user_id)

    k = _fetch_kpis_cached(
        owner_user_id=owner_user_id,
        tipo_val=tipo_val,
        hoje_iso=hoje_sp.isoformat(),
        version=version,
    )

    spacer(0.25)
    _render_priority_section(k, atuacao_label)

    spacer(0.45)
    _render_kpi_section(k)

    spacer(0.45)
    _render_finance_section(k)

    spacer(0.45)
    tab1, tab2, tab3 = st.tabs(["⏳ Prazos", "📅 Agenda", "🗂️ Trabalhos"])

    with tab1:
        _render_tab_prazos(owner_user_id, tipo_val, k, version)

    with tab2:
        _render_tab_agenda(owner_user_id, tipo_val, k, version)

    with tab3:
        _render_tab_trabalhos(owner_user_id, tipo_val, version)
