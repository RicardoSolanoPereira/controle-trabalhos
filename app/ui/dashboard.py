from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

import pandas as pd
import streamlit as st
from sqlalchemy import case, func, select

from db.connection import get_session
from db.models import Agendamento, LancamentoFinanceiro, Prazo, Processo
from ui.layout import grid, section, spacer
from ui.page_header import HeaderAction, page_header
from ui.theme import card
from ui_state import navigate
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
    _ = owner_user_id
    return int(st.session_state.get("data_version", 0))


def _dt_bounds(hoje: date) -> tuple[datetime, datetime, datetime]:
    ate_7_dias = hoje + timedelta(days=7)
    start_today = datetime.combine(hoje, time.min)
    end_7d = datetime.combine(ate_7_dias, time.max)
    now_n = _naive(now_br())
    return start_today, end_7d, now_n


def _greeting() -> str:
    hora = now_br().hour
    if hora < 12:
        return "Bom dia"
    if hora < 18:
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


def _safe_html_text(value: Any, fallback: str = "—") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else fallback


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


def _priority_banner_data(prazos_atrasados: int, prazos_7dias: int) -> dict[str, Any]:
    if prazos_atrasados > 0:
        return {
            "tone": "danger",
            "title": "Pendências críticas exigem ação imediata",
            "left_text": f"Você tem <b>{int(prazos_atrasados)}</b> prazo(s) atrasado(s).",
            "helper": "Priorize o que está vencido antes de novos cadastros ou revisões secundárias.",
            "cta_label": "Ver atrasados",
            "cta_page": "Prazos",
            "cta_state": {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Atrasados",
            },
        }

    if prazos_7dias > 0:
        return {
            "tone": "warning",
            "title": "Há vencimentos próximos no radar",
            "left_text": f"Você tem <b>{int(prazos_7dias)}</b> prazo(s) vencendo em até 7 dias.",
            "helper": "Vale revisar documentos, agenda, visitas e pendências associadas.",
            "cta_label": "Ver próximos 7 dias",
            "cta_page": "Prazos",
            "cta_state": {
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Vencem (7 dias)",
            },
        }

    return {
        "tone": "success",
        "title": "Tudo sob controle no momento",
        "left_text": "Não há prazos críticos no painel.",
        "helper": "Bom momento para organizar agenda, financeiro e novos cadastros.",
        "cta_label": "Novo prazo",
        "cta_page": "Prazos",
        "cta_state": {"prazos_section": "Cadastro"},
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


def _make_nav_callback(page: str, state: dict[str, Any] | None = None):
    def _callback() -> None:
        navigate(page, state=state)

    return _callback


# ==========================================================
# Render utilitário
# ==========================================================


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
        on_click=_make_nav_callback(page, state),
    )


def _render_info_strip(k: dict[str, Any], atuacao_label: str) -> None:
    st.markdown(
        f"""
        <div class="sp-surface" style="padding:14px 16px;">
          <div style="display:flex; flex-wrap:wrap; justify-content:space-between; gap:12px; align-items:flex-start;">
            <div>
              <div style="font-weight:900; font-size:1.02rem;">{_greeting()}</div>
              <div class="sp-muted" style="margin-top:2px;">
                {_today_label()} • atuação: <b>{atuacao_label}</b>
              </div>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
              <span class="sp-chip">⏳ {k["prazos_atrasados"]} atrasado(s)</span>
              <span class="sp-chip">📅 {k["ag_24h"]} em 24h</span>
              <span class="sp-chip">💰 saldo R$ {_fmt_money_br(k["saldo"])}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_priority_banner(k: dict[str, Any]) -> None:
    banner = _priority_banner_data(k["prazos_atrasados"], k["prazos_7dias"])

    left, right = grid(2, columns_mobile=1)

    with left:
        st.markdown(
            f"""
            <div class="sp-card sp-tone-{banner['tone']}" style="padding:18px;">
              <div style="font-size:1.04rem; font-weight:900;">{banner['title']}</div>
              <div style="margin-top:8px;">{banner['left_text']}</div>
              <div class="sp-muted" style="margin-top:6px;">{banner['helper']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        with section("Próxima ação", subtitle="Atalho recomendado", divider=False):
            _render_nav_button(
                banner["cta_label"],
                page=banner["cta_page"],
                state=banner["cta_state"],
                key="dash_priority_cta",
                type="primary",
            )
            spacer(0.10)
            _render_nav_button(
                "Abrir prazos",
                page="Prazos",
                state={"prazos_section": "Lista"},
                key="dash_priority_open_prazos",
                type="secondary",
            )


def _render_kpi_section(k: dict[str, Any]) -> None:
    pct_atraso = _pct(k["prazos_atrasados"], k["prazos_abertos"])
    pct_7d = _pct(k["prazos_7dias"], k["prazos_abertos"])

    with section("Visão geral", subtitle="Resumo operacional do painel", divider=False):
        c1, c2, c3, c4 = grid(4, columns_mobile=1)

        with c1:
            card(
                "Trabalhos ativos",
                f"{k['ativos']}",
                f"{k['total_proc']} cadastrados",
                tone="neutral",
            )

        with c2:
            tone_pz = (
                "danger"
                if k["prazos_atrasados"] > 0
                else ("warning" if k["prazos_7dias"] > 0 else "success")
            )
            card(
                "Prazos",
                f"{k['prazos_abertos']}",
                f"{pct_atraso} atrasados • {pct_7d} em 7d",
                tone=tone_pz,
                emphasize=(k["prazos_atrasados"] > 0),
            )

        with c3:
            ag_tone, ag_emph = _kpi_agenda_tone(k["ag_24h"], k["ag_72h"], k["ag_7d"])
            card(
                "Agenda",
                f"{k['ag_7d']}",
                _kpi_agenda_subtitle(k["ag_24h"], k["ag_72h"], k["ag_7d"]),
                tone=ag_tone,
                emphasize=ag_emph,
            )

        with c4:
            card(
                "Saldo",
                f"R$ {_fmt_money_br(k['saldo'])}",
                "receitas - despesas",
                tone=("success" if k["saldo"] >= 0 else "danger"),
                emphasize=True,
            )


def _render_quick_actions() -> None:
    with section(
        "Ações rápidas",
        subtitle="Atalhos para tarefas frequentes",
        divider=False,
    ):
        c1, c2, c3, c4 = grid(4, columns_mobile=1)

        with c1:
            st.button(
                "⏳ Novo prazo",
                key="dash_quick_new_prazo",
                type="primary",
                use_container_width=True,
                on_click=_go_prazos_cadastro,
            )

        with c2:
            st.button(
                "📁 Novo trabalho",
                key="dash_quick_new_trabalho",
                use_container_width=True,
                on_click=_go_trabalhos_cadastro,
            )

        with c3:
            st.button(
                "📅 Ver agenda",
                key="dash_quick_agenda",
                use_container_width=True,
                on_click=_go_agenda,
            )

        with c4:
            st.button(
                "💰 Lançamentos",
                key="dash_quick_financeiro",
                use_container_width=True,
                on_click=_go_financeiro_lancamentos,
            )


def _summary_surface(title: str, value: Any, subtitle: str, tone: str) -> None:
    value_txt = _safe_html_text(value, "0")
    title_txt = _safe_html_text(title)
    subtitle_txt = _safe_html_text(subtitle)

    st.markdown(
        f"""
        <div class="sp-surface sp-tone-{tone}">
          <div style="font-weight:900;">{title_txt}</div>
          <div style="font-size:1.8rem; font-weight:900; margin-top:6px;">{value_txt}</div>
          <div class="sp-muted" style="margin-top:4px;">{subtitle_txt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_operational_summary(k: dict[str, Any]) -> None:
    with section(
        "Radar do dia",
        subtitle="O que merece atenção imediata",
        divider=False,
    ):
        c1, c2, c3 = grid(3, columns_mobile=1)

        with c1:
            _summary_surface(
                "Prazos atrasados",
                k["prazos_atrasados"],
                "precisam de ação imediata",
                "danger" if k["prazos_atrasados"] > 0 else "success",
            )

        with c2:
            _summary_surface(
                "Próximos 7 dias",
                k["prazos_7dias"],
                "vencimentos no curto prazo",
                "warning" if k["prazos_7dias"] > 0 else "success",
            )

        with c3:
            agenda_tone = (
                "danger"
                if k["ag_24h"] > 0
                else ("info" if k["ag_72h"] > 0 else "success")
            )
            texto = (
                f"{k['ag_24h']} em 24h"
                if k["ag_24h"] > 0
                else (f"{k['ag_72h']} em 72h" if k["ag_72h"] > 0 else "sem urgência")
            )
            _summary_surface("Agenda próxima", k["ag_7d"], texto, agenda_tone)


def _render_finance_section(k: dict[str, Any]) -> None:
    with section(
        "Financeiro",
        subtitle="Receitas, despesas e posição acumulada",
        divider=False,
    ):
        col1, col2, col3 = grid(3, columns_mobile=1)

        with col1:
            card(
                "Receitas",
                f"R$ {_fmt_money_br(k['receitas'])}",
                "acumulado",
                tone="success",
            )

        with col2:
            card(
                "Despesas",
                f"R$ {_fmt_money_br(k['despesas'])}",
                "acumulado",
                tone="danger",
            )

        with col3:
            card(
                "Saldo",
                f"R$ {_fmt_money_br(k['saldo'])}",
                "posição atual",
                tone=("success" if k["saldo"] >= 0 else "danger"),
                emphasize=True,
            )

        spacer(0.16)

        c1, c2 = grid(2, columns_mobile=1)
        with c1:
            st.button(
                "Abrir financeiro",
                key="go_fin_open",
                type="primary",
                use_container_width=True,
                on_click=_go_financeiro_lancamentos,
            )
        with c2:
            st.button(
                "Ver trabalhos",
                key="go_fin_jobs",
                type="secondary",
                use_container_width=True,
                on_click=_go_trabalhos_lista,
            )


def _render_prazo_cards(rows: list, empty_msg: str) -> None:
    if not rows:
        st.caption(empty_msg)
        return

    for _id, evento, data_limite, prioridade, numero_processo, tipo_acao in rows:
        dias = int(_dias_restantes(data_limite))
        status = _status_prazo(dias)
        prior = _prior_badge(prioridade)
        tone = _tone_from_prazo_status(dias)

        numero_processo_txt = _safe_html_text(numero_processo, "Sem referência")
        tipo_acao_txt = _safe_html_text(tipo_acao, "Sem tipo")
        evento_txt = _safe_html_text(evento, "Sem evento")

        st.markdown(
            f"""
            <div class="sp-surface sp-tone-{tone}" style="margin-bottom:10px;">
              <div style="font-weight:850; font-size:0.98rem;">
                {numero_processo_txt} – {tipo_acao_txt}
              </div>
              <div style="margin-top:6px; color:rgba(15,23,42,0.75);">
                <b>Evento:</b> {evento_txt}
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

        numero_processo_txt = _safe_html_text(numero_processo, "Sem referência")
        tipo_acao_txt = _safe_html_text(tipo_acao, "Sem tipo")
        tipo_txt = _safe_html_text(tipo, "Sem tipo")

        local_chip = (
            f"<span class='sp-chip'>📍 {_safe_html_text(local, 'Local não informado')}</span>"
            if local
            else ""
        )

        st.markdown(
            f"""
            <div class="sp-surface sp-tone-{tone}" style="margin-bottom:10px;">
              <div style="font-weight:850; font-size:0.98rem;">
                {numero_processo_txt} – {tipo_acao_txt}
              </div>
              <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
                <span class="sp-chip">📌 {tipo_txt}</span>
                <span class="sp-chip">🕒 {inicio_br_txt}</span>
                {rest_chip}
                <span class="sp-chip">{alert_label}</span>
                {local_chip}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
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
# Header / filtros
# ==========================================================


def _render_header_actions() -> None:
    page_header(
        "Painel de Controle",
        "Visão geral dos trabalhos, prazos, agenda e financeiro",
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
                key="dash_hdr_fin",
                type="secondary",
                on_click=_go_financeiro_lancamentos,
            ),
        ],
        compact=False,
        divider=True,
    )


def _render_filters() -> str | None:
    with section(
        "Filtros", subtitle="Refine o painel por tipo de atuação", divider=False
    ):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            atuacao_label = st.selectbox(
                "Atuação",
                list(ATUACAO_UI.keys()),
                index=0,
                key="dash_atuacao_ui",
            )

        with col2:
            st.caption(
                "Use “(Todas)” para visão geral ou selecione uma atuação para focar o painel."
            )

    return ATUACAO_UI[atuacao_label]


# ==========================================================
# Tabs
# ==========================================================


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

    with section("Atrasados", subtitle="Top 10 com maior urgência", divider=False):
        _render_prazo_cards(rows_atrasados, "✅ Sem prazos atrasados.")
        spacer(0.10)
        _render_nav_button(
            "Abrir lista completa",
            page="Prazos",
            state={"prazos_section": "Lista"},
            key="dash_open_prazos_all",
            type="primary",
        )

    spacer(0.20)

    with section(
        "Vencem em até 7 dias",
        subtitle="Top 10 no curto prazo",
        divider=False,
    ):
        _render_prazo_cards(rows_7d, "✅ Sem prazos vencendo em até 7 dias.")

    with st.expander("Ver em tabela", expanded=False):
        col1, col2 = grid(2, columns_mobile=1)

        with col1:
            st.caption("Atrasados")
            _render_dataframe_or_caption(_build_prazos_df(rows_atrasados))

        with col2:
            st.caption("Próximos 7 dias")
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

    with section(
        "Próximas 24 horas",
        subtitle="Compromissos mais imediatos",
        divider=False,
    ):
        _render_agenda_cards(rows_24h, "✅ Sem agendamentos nas próximas 24 horas.")
        spacer(0.10)
        _render_nav_button(
            "Abrir agenda",
            page="Agenda",
            key="dash_open_agenda",
            type="primary",
        )

    spacer(0.20)

    with section("Próximos 7 dias", subtitle="Planejamento da semana", divider=False):
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
        subtitle="Registros mais recentes conforme o filtro de atuação",
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

        spacer(0.10)
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

    spacer(0.10)
    _render_info_strip(k, atuacao_label)

    spacer(0.18)
    _render_priority_banner(k)

    spacer(0.22)
    _render_kpi_section(k)

    spacer(0.22)
    _render_operational_summary(k)

    spacer(0.22)
    _render_quick_actions()

    spacer(0.22)
    _render_finance_section(k)

    spacer(0.26)
    tab1, tab2, tab3 = st.tabs(["⏳ Prazos", "📅 Agenda", "🗂️ Trabalhos"])

    with tab1:
        _render_tab_prazos(owner_user_id, tipo_val, k, version)

    with tab2:
        _render_tab_agenda(owner_user_id, tipo_val, k, version)

    with tab3:
        _render_tab_trabalhos(owner_user_id, tipo_val, version)
