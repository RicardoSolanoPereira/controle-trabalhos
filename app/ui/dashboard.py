# app/ui/dashboard.py
from __future__ import annotations

from datetime import datetime, timedelta, time, date
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select, func, case

from app.db.connection import get_session
from app.db.models import Processo, Prazo, LancamentoFinanceiro, Agendamento
from services.utils import now_br, ensure_br, format_date_br

from app.ui_state import navigate
from app.ui.page_header import page_header
from app.ui.layout import section, grid, spacer, is_mobile
from app.ui.theme import card


ATUACAO_UI = {
    "(Todas)": None,
    "Perícia (Juízo)": "Perito Judicial",
    "Assistência Técnica": "Assistente Técnico",
    "Particular / Outros serviços": "Trabalho Particular",
}


# -------------------------
# Helpers (tempo / formatação)
# -------------------------
def _naive(dt: datetime) -> datetime:
    """Remove tzinfo caso venha timezone-aware (evita comparação com dt naive)."""
    try:
        if getattr(dt, "tzinfo", None) is not None:
            return dt.replace(tzinfo=None)
    except Exception:
        pass
    return dt


def _fmt_money_br(v: float) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0.0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(a: int, b: int) -> str:
    if b <= 0:
        return "0%"
    return f"{round((a / b) * 100)}%"


def _apply_tipo_filter(stmt, tipo_val):
    return stmt if not tipo_val else stmt.where(Processo.papel == tipo_val)


# -------------------------
# Helpers (prazos)
# -------------------------
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
    """Mapeia o status do prazo para o tone do card/surface."""
    if dias < 0:
        return "danger"
    if dias <= 5:
        return "warning"
    if dias <= 10:
        return "info"
    return "success"


def _prior_badge(p: str | None) -> str:
    p = (p or "Média").strip()
    if p.lower().startswith("a"):
        return "🔥 Alta"
    if p.lower().startswith("b"):
        return "🧊 Baixa"
    return "⚖️ Média"


# -------------------------
# Helpers (agenda) — mesmo padrão visual de prazos ✅
# -------------------------
def _agenda_status(hours_left: float) -> tuple[str, str]:
    """
    Mesmo padrão de alertas dos prazos.
    Retorna: (label, tone)
    """
    if hours_left < 0:
        return "🔴 Atrasado", "danger"

    # padrão: <=24h urgente; <=72h atenção
    if hours_left <= 24:
        return "🟠 Urgente", "warning"
    if hours_left <= 72:
        return "🟡 Atenção", "info"
    return "🟢 Ok", "success"


def _agenda_rest_chip(hours_left: float) -> str:
    """Chip de tempo restante (h/d) para agenda."""
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
    """
    KPI Agenda no padrão pedido:
    - 24h: danger (vermelho)
    - 72h: info (atenção)
    - 7d: success (ok)
    - 0: neutral
    """
    if ag_24h > 0:
        return "danger", True
    if ag_72h > 0:
        return "info", False
    if ag_7d > 0:
        return "success", False
    return "neutral", False


# -------------------------
# Helpers (datas)
# -------------------------
def _dt_bounds(hoje: date) -> tuple[datetime, datetime, datetime]:
    """Retorna: start_today, end_7d, now_naive."""
    ate7 = hoje + timedelta(days=7)
    start_today = datetime.combine(hoje, time.min)
    end_7d = datetime.combine(ate7, time.max)
    now_n = _naive(now_br())
    return start_today, end_7d, now_n


# -------------------------
# Builders de tabelas
# -------------------------
def _build_prazos_df(rows) -> pd.DataFrame:
    data = []
    for _id, evento, data_limite, prioridade, numero_processo, tipo_acao in rows:
        dias = int(_dias_restantes(data_limite))
        data.append(
            {
                "Trabalho": f"{numero_processo} – {tipo_acao or 'Sem tipo'}",
                "Evento": evento,
                "Venc.": format_date_br(data_limite),
                "Dias": dias,
                "Status": _status_prazo(dias),
                "Prior.": _prior_badge(prioridade),
            }
        )
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).sort_values(by=["Dias", "Venc."], ascending=True)


def _build_agenda_df(rows) -> pd.DataFrame:
    data = []
    for _id, tipo, inicio, local, numero_processo, tipo_acao in rows:
        data.append(
            {
                "Trabalho": f"{numero_processo} – {tipo_acao or 'Sem tipo'}",
                "Tipo": tipo,
                "Início": ensure_br(inicio).strftime("%d/%m/%Y %H:%M"),
                "Local": local or "",
            }
        )
    return pd.DataFrame(data) if data else pd.DataFrame()


# -------------------------
# Cards (listas)
# -------------------------
def _render_prazo_cards(rows: list, title: str, empty_msg: str) -> None:
    """Cards (mobile-friendly) com mesmo tom do status."""
    with section(title, subtitle="Top 10 (resumo)", divider=False):
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

        st.button(
            "Abrir lista completa",
            use_container_width=True,
            key=f"btn_open_{title}_prazos",
            type="primary",
            on_click=lambda: navigate(
                "Prazos",
                state={"prazos_section": "Lista", "pz_nav_to": "Lista"},
            ),
        )


def _render_agenda_cards(rows: list, title: str, empty_msg: str) -> None:
    """Cards (mobile-friendly) com alerta no mesmo estilo de prazos."""
    with section(title, subtitle="Top 10 (resumo)", divider=False):
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
                    {f"<span class='sp-chip'>📍 {local}</span>" if local else ""}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.button(
            "Abrir agenda",
            use_container_width=True,
            type="primary",
            key=f"btn_open_{title}_agenda",
            on_click=lambda: navigate("Agendamentos"),
        )


# -------------------------
# Tom do banner de prioridades (prazos)
# -------------------------
def _alert_tone(prazos_atrasados: int, prazos_7dias: int) -> str:
    if prazos_atrasados > 0:
        return "danger"
    if prazos_7dias > 0:
        return "warning"
    return "success"


def _cache_buster(owner_user_id: int) -> int:
    return int(st.session_state.get(f"data_version_{owner_user_id}", 0))


# -------------------------
# Queries (cacheadas)
# -------------------------
@st.cache_data(show_spinner=False, ttl=45)
def _fetch_kpis_cached(
    owner_user_id: int, tipo_val: str | None, hoje_iso: str, version: int
) -> dict:
    hoje_sp = date.fromisoformat(hoje_iso)
    start_today, end_7d, now_n = _dt_bounds(hoje_sp)

    with get_session() as s:
        # Processos
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

        # Prazos (contagens)
        stmt_prazos_counts = (
            select(
                func.count(Prazo.id).label("abertos"),
                func.coalesce(
                    func.sum(case((Prazo.data_limite < start_today, 1), else_=0)), 0
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
        prazos_abertos = int(prazos_abertos or 0)
        prazos_atrasados = int(prazos_atrasados or 0)
        prazos_7dias = int(prazos_7dias or 0)

        # Agenda (contagens) — para KPI com alerta igual prazos ✅
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

        # Financeiro
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

    saldo = receitas - despesas

    return {
        "hoje_sp": hoje_sp,
        "start_today": start_today,
        "end_7d": end_7d,
        "now_n": now_n,
        "total_proc": total_proc,
        "ativos": ativos,
        "prazos_abertos": prazos_abertos,
        "prazos_atrasados": prazos_atrasados,
        "prazos_7dias": prazos_7dias,
        "ag_7d": ag_7d,
        "ag_24h": ag_24h,
        "ag_72h": ag_72h,
        "receitas": receitas,
        "despesas": despesas,
        "saldo": saldo,
    }


@st.cache_data(show_spinner=False, ttl=45)
def _fetch_prazos_tables_cached(
    owner_user_id: int,
    tipo_val: str | None,
    start_today_iso: str,
    end_7d_iso: str,
    version: int,
) -> tuple[list, list]:
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
                Prazo.data_limite >= start_today, Prazo.data_limite <= end_7d
            )
        ).all()

    return rows_atrasados, rows_7d


@st.cache_data(show_spinner=False, ttl=45)
def _fetch_agendamentos_cached(
    owner_user_id: int, tipo_val: str | None, now_n_iso: str, version: int
) -> tuple[list, list]:
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
    owner_user_id: int, tipo_val: str | None, version: int
) -> list:
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


# -------------------------
# Render
# -------------------------
def render(owner_user_id: int):
    page_header("Painel de Controle", "Alertas, prazos, agenda e financeiro")

    with section(
        "Filtros",
        subtitle="A atuação filtra indicadores e listas.",
        divider=False,
    ):
        fc1, fc2 = grid(2, columns_mobile=1)
        with fc1:
            atuacao_label = st.selectbox(
                "Atuação",
                list(ATUACAO_UI.keys()),
                index=0,
                key="dash_atuacao_ui",
            )
        with fc2:
            st.caption("Dica: use “(Todas)” para visão geral.")

    tipo_val = ATUACAO_UI[atuacao_label]

    hoje_sp = now_br().date()
    version = _cache_buster(owner_user_id)
    k = _fetch_kpis_cached(owner_user_id, tipo_val, hoje_sp.isoformat(), version)

    spacer(0.4)

    # 1) PRIORIDADES (prazos)
    tone = _alert_tone(k["prazos_atrasados"], k["prazos_7dias"])

    if k["prazos_atrasados"] > 0:
        cta_label = "Abrir atrasados"
        cta_action = lambda: navigate(
            "Prazos",
            state={
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Atrasados",
            },
        )
        left_text = f"**🔴 {int(k['prazos_atrasados'])} prazo(s) atrasado(s)**"
    elif k["prazos_7dias"] > 0:
        cta_label = "Ver 7 dias"
        cta_action = lambda: navigate(
            "Prazos",
            state={
                "prazos_section": "Lista",
                "pz_nav_to": "Lista",
                "pz_list_nav_to": "Vencem (7 dias)",
            },
        )
        left_text = f"**🟠 {int(k['prazos_7dias'])} prazo(s) em até 7 dias**"
    else:
        cta_label = "Cadastrar prazo"
        cta_action = lambda: navigate("Prazos", state={"prazos_section": "Cadastro"})
        left_text = "**🟢 Nenhum prazo crítico**"

    def _prio_actions():
        st.button(
            cta_label,
            use_container_width=True,
            type="primary",
            on_click=cta_action,
            key="dash_cta",
        )

    with section(
        "Prioridades de hoje",
        subtitle=atuacao_label,
        divider=False,
        header_actions=_prio_actions,
    ):
        st.markdown(
            f"""
            <div class="sp-card sp-tone-{tone}" style="margin-bottom:10px;">
              <div style="font-weight:900;font-size:1.05rem;">Status de prazos</div>
              <div class="sp-muted" style="margin-top:4px;">Acompanhe o que precisa de ação imediata.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(left_text)

        # Mobile: reforça CTA abaixo (melhor toque)
        if is_mobile():
            spacer(0.25)
            st.button(
                cta_label,
                use_container_width=True,
                type="primary",
                on_click=cta_action,
                key="dash_cta_mobile_dup",
            )

    spacer(0.6)

    # 2) RESUMO
    pct_atraso = _pct(k["prazos_atrasados"], k["prazos_abertos"])
    pct_7d = _pct(k["prazos_7dias"], k["prazos_abertos"])

    with section(
        "Resumo operacional",
        subtitle="Visão rápida do que está rodando.",
        divider=False,
    ):
        c1, c2 = grid(2, columns_mobile=1)
        with c1:
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
            st.button(
                "Ver prazos",
                use_container_width=True,
                key="go_prazos",
                on_click=lambda: navigate(
                    "Prazos",
                    state={
                        "prazos_section": "Lista",
                        "pz_nav_to": "Lista",
                        "pz_list_nav_to": "Abertos",
                    },
                ),
            )

        with c2:
            card("Ativos", f"{k['ativos']}", "em andamento", tone="neutral")
            st.button(
                "Ver ativos",
                use_container_width=True,
                key="go_proc_ativos",
                on_click=lambda: navigate(
                    "Processos",
                    qp={"status": "Ativo"},
                    state={"processos_section": "Lista"},
                ),
            )

        spacer(0.25)

        c3, c4 = grid(2, columns_mobile=1)
        with c3:
            card("Trabalhos", f"{k['total_proc']}", "cadastrados", tone="info")
            st.button(
                "Ver todos",
                use_container_width=True,
                key="go_proc",
                on_click=lambda: navigate(
                    "Processos", state={"processos_section": "Lista"}
                ),
            )

        with c4:
            ag_tone, ag_emph = _kpi_agenda_tone(k["ag_24h"], k["ag_72h"], k["ag_7d"])
            card(
                "Agenda (7 dias)",
                f"{k['ag_7d']}",
                _kpi_agenda_subtitle(k["ag_24h"], k["ag_72h"], k["ag_7d"]),
                tone=ag_tone,
                emphasize=ag_emph,
            )
            st.button(
                "Ver agenda",
                use_container_width=True,
                key="go_agenda",
                on_click=lambda: navigate("Agendamentos"),
            )

    spacer(0.6)

    # 3) FINANCEIRO
    with section(
        "Resumo financeiro",
        subtitle="Receitas, despesas e saldo acumulado.",
        divider=False,
    ):
        f1, f2 = grid(2, columns_mobile=1)
        with f1:
            card(
                "Receitas (R$)",
                _fmt_money_br(k["receitas"]),
                "acumulado",
                tone="success",
            )
        with f2:
            card(
                "Despesas (R$)",
                _fmt_money_br(k["despesas"]),
                "acumulado",
                tone="danger",
            )

        spacer(0.25)

        card(
            "Saldo (R$)",
            _fmt_money_br(k["saldo"]),
            "receitas - despesas",
            tone=("success" if k["saldo"] >= 0 else "danger"),
            emphasize=True,
        )

        st.button(
            "Abrir financeiro",
            use_container_width=True,
            type="primary",
            key="go_fin",
            on_click=lambda: navigate(
                "Financeiro", state={"financeiro_section": "Lançamentos"}
            ),
        )

    spacer(0.6)

    # 4) LISTAS ANALÍTICAS
    tab1, tab2, tab3 = st.tabs(["⏳ Prazos", "📅 Agenda", "🗂️ Trabalhos"])

    with tab1:
        rows_atrasados, rows_7d = _fetch_prazos_tables_cached(
            owner_user_id,
            tipo_val,
            k["start_today"].isoformat(timespec="seconds"),
            k["end_7d"].isoformat(timespec="seconds"),
            version,
        )

        _render_prazo_cards(
            rows_atrasados, "Prazos atrasados", "✅ Sem prazos atrasados."
        )
        spacer(0.25)
        _render_prazo_cards(
            rows_7d, "Vencem em até 7 dias", "✅ Sem prazos vencendo em até 7 dias."
        )

        with st.expander("Ver em tabela", expanded=False):
            colA, colB = grid(2, columns_mobile=1)
            with colA:
                st.caption("Atrasados (Top 10)")
                if rows_atrasados:
                    df = _build_prazos_df(rows_atrasados)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.caption("—")

            with colB:
                st.caption("7 dias (Top 10)")
                if rows_7d:
                    df = _build_prazos_df(rows_7d)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.caption("—")

    with tab2:
        rows_24h, rows_ag_7d = _fetch_agendamentos_cached(
            owner_user_id,
            tipo_val,
            k["now_n"].isoformat(timespec="seconds"),
            version,
        )

        _render_agenda_cards(
            rows_24h, "Próximas 24 horas", "✅ Sem agendamentos nas próximas 24 horas."
        )
        spacer(0.25)
        _render_agenda_cards(
            rows_ag_7d, "Próximos 7 dias", "✅ Sem agendamentos nos próximos 7 dias."
        )

        with st.expander("Ver em tabela", expanded=False):
            col1, col2 = grid(2, columns_mobile=1)
            with col1:
                st.caption("24 horas (Top 10)")
                if rows_24h:
                    dfa = _build_agenda_df(rows_24h)
                    st.dataframe(dfa, use_container_width=True, hide_index=True)
                else:
                    st.caption("—")
            with col2:
                st.caption("7 dias (Top 10)")
                if rows_ag_7d:
                    dfa = _build_agenda_df(rows_ag_7d)
                    st.dataframe(dfa, use_container_width=True, hide_index=True)
                else:
                    st.caption("—")

    with tab3:
        procs = _fetch_ultimos_processos_cached(owner_user_id, tipo_val, version)

        with section(
            "Últimos trabalhos",
            subtitle="Registros mais recentes cadastrados (respeita a atuação)",
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
