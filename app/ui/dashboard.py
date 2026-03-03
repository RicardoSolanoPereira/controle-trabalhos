# app/ui/dashboard.py
from __future__ import annotations

from datetime import datetime, timedelta, time, date

import pandas as pd
import streamlit as st
from sqlalchemy import select, func, case
from sqlalchemy.exc import SQLAlchemyError

from db.connection import get_session
from db.models import Processo, Prazo, LancamentoFinanceiro, Agendamento
from services.utils import now_br, ensure_br, format_date_br

from app.ui.theme import card
from app.ui_state import navigate
from app.ui.page_header import page_header

ATUACAO_UI = {
    "(Todas)": None,
    "Perícia (Juízo)": "Perito Judicial",
    "Assistência Técnica": "Assistente Técnico",
    "Particular / Outros serviços": "Trabalho Particular",
}


# -------------------------
# Helpers
# -------------------------
def _naive(dt: datetime) -> datetime:
    try:
        if getattr(dt, "tzinfo", None) is not None:
            return dt.replace(tzinfo=None)
    except Exception:
        pass
    return dt


def _dias_restantes(dt) -> int:
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


def _fmt_money_br(v: float) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0.0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _apply_tipo_filter(stmt, tipo_val):
    return stmt if not tipo_val else stmt.where(Processo.papel == tipo_val)


def _pct(a: int, b: int) -> str:
    if b <= 0:
        return "0%"
    return f"{round((a / b) * 100)}%"


def _prior_badge(p: str | None) -> str:
    p = (p or "Média").strip()
    if p.lower().startswith("a"):
        return "🔥 Alta"
    if p.lower().startswith("b"):
        return "🧊 Baixa"
    return "⚖️ Média"


def _date_range_strings(hoje: date) -> tuple[str, str]:
    ate7 = hoje + timedelta(days=7)
    return hoje.isoformat(), ate7.isoformat()


def _dt_bounds(hoje: date) -> tuple[datetime, datetime]:
    ate7 = hoje + timedelta(days=7)
    start_today = datetime.combine(hoje, time.min)
    end_7d = datetime.combine(ate7, time.max)
    return start_today, end_7d


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


def _render_prazo_cards(rows: list, title: str, empty_msg: str) -> None:
    """
    Mobile-friendly: cards (sem tabela).
    rows: (Prazo.id, evento, data_limite, prioridade, Processo.numero_processo, Processo.tipo_acao)
    """
    with st.container(border=True):
        st.subheader(title)
        if not rows:
            st.caption(empty_msg)
            return

        for _id, evento, data_limite, prioridade, numero_processo, tipo_acao in rows:
            dias = int(_dias_restantes(data_limite))
            status = _status_prazo(dias)
            prior = _prior_badge(prioridade)

            st.markdown(
                f"""
                <div class="sp-surface" style="margin-bottom:10px;">
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
    """
    rows: (Agendamento.id, tipo, inicio, local, numero_processo, tipo_acao)
    """
    with st.container(border=True):
        st.subheader(title)
        if not rows:
            st.caption(empty_msg)
            return

        for _id, tipo, inicio, local, numero_processo, tipo_acao in rows:
            inicio_br = ensure_br(inicio).strftime("%d/%m/%Y %H:%M")
            st.markdown(
                f"""
                <div class="sp-surface" style="margin-bottom:10px;">
                  <div style="font-weight:850; font-size:0.98rem;">
                    {numero_processo} – {tipo_acao or "Sem tipo"}
                  </div>
                  <div style="margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;">
                    <span class="sp-chip">📌 {tipo}</span>
                    <span class="sp-chip">🕒 {inicio_br}</span>
                    {f"<span class='sp-chip'>📍 {local}</span>" if local else ""}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.button(
            "Abrir agenda",
            use_container_width=True,
            type="primary",
            key=f"btn_open_{title}_agenda",
        ):
            navigate("Agendamentos")


def _alert_tone(prazos_atrasados: int, prazos_7dias: int) -> str:
    if prazos_atrasados > 0:
        return "danger"
    if prazos_7dias > 0:
        return "warning"
    return "success"


# -------------------------
# Queries (cacheadas)
# -------------------------
@st.cache_data(show_spinner=False, ttl=45)
def _fetch_kpis_cached(owner_user_id: int, tipo_val: str | None, hoje_iso: str) -> dict:
    hoje_sp = date.fromisoformat(hoje_iso)
    start_today, end_7d = _dt_bounds(hoje_sp)
    now = now_br()
    now_n = _naive(now)

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
                                (Prazo.data_limite >= start_today)
                                & (Prazo.data_limite <= end_7d),
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
                Prazo.concluido == False,  # noqa
            )
        )
        stmt_prazos_counts = _apply_tipo_filter(stmt_prazos_counts, tipo_val)
        prazos_abertos, prazos_atrasados, prazos_7dias = s.execute(
            stmt_prazos_counts
        ).one()

        prazos_abertos = int(prazos_abertos or 0)
        prazos_atrasados = int(prazos_atrasados or 0)
        prazos_7dias = int(prazos_7dias or 0)

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

        stmt_receitas = (
            select(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0))
            .join(Processo, Processo.id == LancamentoFinanceiro.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                LancamentoFinanceiro.tipo == "Receita",
            )
        )
        stmt_despesas = (
            select(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0))
            .join(Processo, Processo.id == LancamentoFinanceiro.processo_id)
            .where(
                Processo.owner_user_id == owner_user_id,
                LancamentoFinanceiro.tipo == "Despesa",
            )
        )
        stmt_receitas = _apply_tipo_filter(stmt_receitas, tipo_val)
        stmt_despesas = _apply_tipo_filter(stmt_despesas, tipo_val)

        receitas = float(s.execute(stmt_receitas).scalar_one() or 0)
        despesas = float(s.execute(stmt_despesas).scalar_one() or 0)

    saldo = receitas - despesas

    return {
        "now": now,
        "now_n": now_n,
        "hoje_sp": hoje_sp,
        "start_today": start_today,
        "end_7d": end_7d,
        "total_proc": total_proc,
        "ativos": ativos,
        "prazos_abertos": prazos_abertos,
        "prazos_atrasados": prazos_atrasados,
        "prazos_7dias": prazos_7dias,
        "ag_7d": ag_7d,
        "receitas": receitas,
        "despesas": despesas,
        "saldo": saldo,
    }


@st.cache_data(show_spinner=False, ttl=45)
def _fetch_prazos_tables_cached(
    owner_user_id: int, tipo_val: str | None, start_today_iso: str, end_7d_iso: str
) -> tuple[list, list]:
    start_today = datetime.fromisoformat(start_today_iso)
    end_7d = datetime.fromisoformat(end_7d_iso)

    with get_session() as s:
        stmt_atrasados = (
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
                Prazo.concluido == False,  # noqa
                Prazo.data_limite < start_today,
            )
            .order_by(Prazo.data_limite.asc())
            .limit(10)
        )
        stmt_atrasados = _apply_tipo_filter(stmt_atrasados, tipo_val)
        rows_atrasados = s.execute(stmt_atrasados).all()

        stmt_7d = (
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
                Prazo.concluido == False,  # noqa
                Prazo.data_limite >= start_today,
                Prazo.data_limite <= end_7d,
            )
            .order_by(Prazo.data_limite.asc())
            .limit(10)
        )
        stmt_7d = _apply_tipo_filter(stmt_7d, tipo_val)
        rows_7d = s.execute(stmt_7d).all()

    return rows_atrasados, rows_7d


@st.cache_data(show_spinner=False, ttl=45)
def _fetch_agendamentos_cached(
    owner_user_id: int, tipo_val: str | None, now_n_iso: str
) -> tuple[list, list]:
    now_n = datetime.fromisoformat(now_n_iso)

    with get_session() as s:
        stmt_24h = (
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
                Agendamento.inicio <= now_n + timedelta(hours=24),
            )
            .order_by(Agendamento.inicio.asc())
            .limit(10)
        )
        stmt_24h = _apply_tipo_filter(stmt_24h, tipo_val)
        rows_24h = s.execute(stmt_24h).all()

        stmt_7d = (
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
                Agendamento.inicio <= now_n + timedelta(days=7),
            )
            .order_by(Agendamento.inicio.asc())
            .limit(10)
        )
        stmt_7d = _apply_tipo_filter(stmt_7d, tipo_val)
        rows_7d = s.execute(stmt_7d).all()

    return rows_24h, rows_7d


@st.cache_data(show_spinner=False, ttl=60)
def _fetch_ultimos_processos_cached(owner_user_id: int, tipo_val: str | None) -> list:
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

    # Filtro Atuação (compacto)
    with st.container(border=True):
        c1, c2 = st.columns([0.42, 0.58], vertical_alignment="center")
        with c1:
            atuacao_label = st.selectbox(
                "Atuação",
                list(ATUACAO_UI.keys()),
                index=0,
                key="dash_atuacao_ui",
            )
        with c2:
            st.caption("Filtra indicadores e listas conforme sua atuação.")
    tipo_val = ATUACAO_UI[atuacao_label]

    hoje_sp = now_br().date()
    hoje_iso, _ = _date_range_strings(hoje_sp)
    k = _fetch_kpis_cached(owner_user_id, tipo_val, hoje_iso)

    # ------------------------------------------------------------
    # 1) ALERTA (Prioridades)
    # ------------------------------------------------------------
    tone = _alert_tone(k["prazos_atrasados"], k["prazos_7dias"])

    with st.container(border=True):
        # Dá “cara de alerta” (borda esquerda) usando sua classe sp-tone-*
        st.markdown(
            f"""
            <div class="sp-card sp-tone-{tone}" style="margin-bottom:6px;">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
                <div>
                  <div style="font-weight:900;font-size:1.05rem;">Prioridades de hoje</div>
                  <div class="sp-muted" style="margin-top:4px;">
                    {atuacao_label}
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        left, right = st.columns([0.72, 0.28], vertical_alignment="center")

        if k["prazos_atrasados"] > 0:
            with left:
                st.markdown(f"**🔴 {int(k['prazos_atrasados'])} prazo(s) atrasado(s)**")
            with right:
                if st.button(
                    "Abrir atrasados", use_container_width=True, type="primary"
                ):
                    navigate(
                        "Prazos",
                        state={
                            "prazos_section": "Lista",
                            "pz_nav_to": "Lista",
                            "pz_list_nav_to": "Atrasados",
                        },
                    )

        elif k["prazos_7dias"] > 0:
            with left:
                st.markdown(f"**🟠 {int(k['prazos_7dias'])} prazo(s) em até 7 dias**")
            with right:
                if st.button("Ver 7 dias", use_container_width=True, type="primary"):
                    navigate(
                        "Prazos",
                        state={
                            "prazos_section": "Lista",
                            "pz_nav_to": "Lista",
                            "pz_list_nav_to": "Vencem (7 dias)",
                        },
                    )
        else:
            with left:
                st.markdown("**🟢 Nenhum prazo crítico**")
            with right:
                if st.button(
                    "Cadastrar prazo", use_container_width=True, type="primary"
                ):
                    navigate("Prazos", state={"prazos_section": "Cadastro"})

    st.write("")

    # ------------------------------------------------------------
    # 2) RESUMO (separado: Operacional / Financeiro)
    # ------------------------------------------------------------
    pct_atraso = _pct(k["prazos_atrasados"], k["prazos_abertos"])
    pct_7d = _pct(k["prazos_7dias"], k["prazos_abertos"])

    # -------------------
    # Operacional
    # -------------------
    with st.container(border=True):
        st.subheader("Resumo operacional")

        # Ordem mobile-first: Prazos → Ativos → Trabalhos → Agenda
        # (Usar 2 colunas é ok no desktop; no mobile vira mais estreito, mas ainda funcional)
        r1c1, r1c2 = st.columns(2)
        with r1c1:
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
            if st.button("Ver prazos", use_container_width=True, key="go_prazos"):
                navigate(
                    "Prazos",
                    state={
                        "prazos_section": "Lista",
                        "pz_nav_to": "Lista",
                        "pz_list_nav_to": "Abertos",
                    },
                )

        with r1c2:
            card("Ativos", f"{k['ativos']}", "em andamento", tone="neutral")
            if st.button("Ver ativos", use_container_width=True, key="go_proc_ativos"):
                navigate(
                    "Processos",
                    qp={"status": "Ativo"},
                    state={"processos_section": "Lista"},
                )

        r2c1, r2c2 = st.columns(2)
        with r2c1:
            card("Trabalhos", f"{k['total_proc']}", "cadastrados", tone="info")
            if st.button("Ver todos", use_container_width=True, key="go_proc"):
                navigate("Processos", state={"processos_section": "Lista"})

        with r2c2:
            card("Agenda (7 dias)", f"{k['ag_7d']}", "agendados", tone="info")
            if st.button("Ver agenda", use_container_width=True, key="go_agenda"):
                navigate("Agendamentos")

    st.write("")

    # -------------------
    # Financeiro
    # -------------------
    with st.container(border=True):
        st.subheader("Resumo financeiro")

        f1, f2 = st.columns(2)
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

        card(
            "Saldo (R$)",
            _fmt_money_br(k["saldo"]),
            "receitas - despesas",
            tone=("success" if k["saldo"] >= 0 else "danger"),
            emphasize=True,
        )

        if st.button(
            "Abrir financeiro", use_container_width=True, type="primary", key="go_fin"
        ):
            navigate("Financeiro", state={"financeiro_section": "Lançamentos"})

    st.divider()

    # ------------------------------------------------------------
    # 3) Listas Analíticas
    # ------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(["⏳ Prazos", "📅 Agenda", "🗂️ Trabalhos"])

    with tab1:
        rows_atrasados, rows_7d = _fetch_prazos_tables_cached(
            owner_user_id,
            tipo_val,
            k["start_today"].isoformat(timespec="seconds"),
            k["end_7d"].isoformat(timespec="seconds"),
        )

        _render_prazo_cards(
            rows_atrasados, "Prazos atrasados", "✅ Sem prazos atrasados."
        )
        _render_prazo_cards(
            rows_7d, "Vencem em até 7 dias", "✅ Sem prazos vencendo em até 7 dias."
        )

        with st.expander("Ver em tabela", expanded=False):
            colA, colB = st.columns(2, vertical_alignment="top")

            with colA:
                st.caption("Atrasados (Top 10)")
                if rows_atrasados:
                    df = _build_prazos_df(rows_atrasados)
                    st.dataframe(
                        df, use_container_width=True, hide_index=True, height=320
                    )
                else:
                    st.caption("—")

            with colB:
                st.caption("7 dias (Top 10)")
                if rows_7d:
                    df = _build_prazos_df(rows_7d)
                    st.dataframe(
                        df, use_container_width=True, hide_index=True, height=320
                    )
                else:
                    st.caption("—")

    with tab2:
        rows_24h, rows_ag_7d = _fetch_agendamentos_cached(
            owner_user_id, tipo_val, k["now_n"].isoformat(timespec="seconds")
        )

        _render_agenda_cards(
            rows_24h, "Próximas 24 horas", "✅ Sem agendamentos nas próximas 24 horas."
        )
        _render_agenda_cards(
            rows_ag_7d, "Próximos 7 dias", "✅ Sem agendamentos nos próximos 7 dias."
        )

        with st.expander("Ver em tabela", expanded=False):
            col1, col2 = st.columns(2, vertical_alignment="top")
            with col1:
                st.caption("24 horas (Top 10)")
                if rows_24h:
                    dfa = _build_agenda_df(rows_24h)
                    st.dataframe(
                        dfa, use_container_width=True, hide_index=True, height=320
                    )
                else:
                    st.caption("—")
            with col2:
                st.caption("7 dias (Top 10)")
                if rows_ag_7d:
                    dfa = _build_agenda_df(rows_ag_7d)
                    st.dataframe(
                        dfa, use_container_width=True, hide_index=True, height=320
                    )
                else:
                    st.caption("—")

    with tab3:
        procs = _fetch_ultimos_processos_cached(owner_user_id, tipo_val)

        with st.container(border=True):
            st.subheader("Últimos trabalhos")
            st.caption("Registros mais recentes cadastrados (respeita a atuação)")

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
