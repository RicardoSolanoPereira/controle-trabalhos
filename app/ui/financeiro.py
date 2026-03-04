# app/ui/financeiro.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.financeiro_service import (
    FinanceiroService,
    LancamentoCreate,
    LancamentoUpdate,
)

from app.ui.theme import inject_global_css, card, subtle_divider
from app.ui.page_header import page_header


# ============================================================
# Constantes / UI
# ============================================================
RECEITA_STATUS_VALIDOS = ("Recebido", "A receber", "Cancelado")

# Despesa sem vínculo com trabalho (ex.: impressão CV, prospecção, visita, etc.)
SEM_VINCULO_LABEL = "— (Sem vínculo / Despesa geral)"


# ============================================================
# Helpers
# ============================================================
@dataclass(frozen=True)
class ProcMaps:
    labels: List[str]
    label_to_id: Dict[str, Optional[int]]
    label_by_id: Dict[int, str]


def _proc_label(p: Processo) -> str:
    tipo = (p.tipo_acao or "").strip()
    papel = (p.papel or "").strip()
    base = f"[{p.id}] {p.numero_processo}"
    if tipo:
        base += f" – {tipo}"
    if papel:
        base += f"  •  {papel}"
    return base


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _dt_ini_from_date(d: Optional[date]) -> Optional[datetime]:
    if not d:
        return None
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def _dt_fim_from_date(d: Optional[date]) -> Optional[datetime]:
    if not d:
        return None
    return datetime(d.year, d.month, d.day, 23, 59, 59)


def _status_receita(obj) -> str:
    """
    Tolerante com versões antigas do DB/model:
    - se não existir atributo, assume Recebido.
    """
    v = getattr(obj, "status_recebimento", None)
    v = (v or "").strip()
    return v or "Recebido"


def _safe_trabalho_label(
    processo_id: Optional[int], proc_label_by_id: Dict[int, str]
) -> str:
    if processo_id is None:
        return SEM_VINCULO_LABEL
    try:
        return proc_label_by_id.get(int(processo_id), f"[{processo_id}]")
    except Exception:
        return f"[{processo_id}]"


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _make_create_payload(**kwargs):
    """
    Compatível com versões antigas do LancamentoCreate:
    - se o payload não aceitar 'status_recebimento', tenta sem.
    """
    try:
        return LancamentoCreate(**kwargs)
    except TypeError:
        kwargs.pop("status_recebimento", None)
        return LancamentoCreate(**kwargs)


def _make_update_payload(**kwargs):
    try:
        return LancamentoUpdate(**kwargs)
    except TypeError:
        kwargs.pop("status_recebimento", None)
        return LancamentoUpdate(**kwargs)


# ============================================================
# Data version (cache-buster simples)
# ============================================================
def _data_version(owner_user_id: int) -> int:
    return int(st.session_state.get(f"data_version_{owner_user_id}", 0))


def _bump_version(owner_user_id: int) -> None:
    st.session_state[f"data_version_{owner_user_id}"] = _data_version(owner_user_id) + 1


# ============================================================
# Cache / Loads
# ============================================================
@st.cache_data(show_spinner=False, ttl=45)
def _load_processos(owner_user_id: int, version: int) -> List[Processo]:
    with get_session() as s:
        return (
            s.execute(
                select(Processo)
                .where(Processo.owner_user_id == owner_user_id)
                .order_by(Processo.id.desc())
            )
            .scalars()
            .all()
        )


def _build_proc_maps(processos: List[Processo]) -> ProcMaps:
    labels: List[str] = []
    label_to_id: Dict[str, Optional[int]] = {}
    label_by_id: Dict[int, str] = {}

    for p in processos:
        lbl = _proc_label(p)
        labels.append(lbl)
        label_to_id[lbl] = int(p.id)
        label_by_id[int(p.id)] = lbl

    return ProcMaps(labels=labels, label_to_id=label_to_id, label_by_id=label_by_id)


def _apply_pref_processo_defaults(proc_maps: ProcMaps) -> None:
    """
    Integra com Trabalhos/Prazos/Agenda:
    - se vier st.session_state["pref_processo_id"], pré-seleciona no filtro e no cadastro.
    Não sobrescreve escolhas do usuário.
    """
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return
    try:
        pref_id_int = int(pref_id)
    except Exception:
        return

    pref_label = proc_maps.label_by_id.get(pref_id_int)
    if not pref_label:
        return

    st.session_state.setdefault("fin_visao_proc", pref_label)
    # não seta as keys do form (que mudam por tipo), só o filtro global


def _section_tabs(key: str) -> str:
    options = ["Lançamentos", "Resumo", "Categorias", "Mensal"]
    if hasattr(st, "segmented_control"):
        return st.segmented_control(
            "Seção", options, key=key, label_visibility="collapsed"
        )
    return st.radio(
        "Seção", options, horizontal=True, key=key, label_visibility="collapsed"
    )


# ============================================================
# Filtros
# ============================================================
def _section_filters(
    proc_maps: ProcMaps,
) -> Tuple[Optional[int], Optional[datetime], Optional[datetime], Optional[str]]:
    with st.container(border=True):
        st.markdown("#### 🔎 Filtros")
        st.caption(
            "Filtre por trabalho e período. Se não preencher datas, mostra tudo."
        )
        subtle_divider()

        c1, c2, c3 = st.columns([3, 1, 1])

        proc_sel = c1.selectbox(
            "Trabalho",
            ["(Todos)", SEM_VINCULO_LABEL] + proc_maps.labels,
            index=0,
            key="fin_visao_proc",
        )

        # Datas opcionais (sem value=None no widget)
        st.session_state.setdefault("fin_dt_ini", None)
        st.session_state.setdefault("fin_dt_fim", None)

        dt_ini_d = c2.date_input(
            "De", value=st.session_state.fin_dt_ini or date.today(), key="fin_dt_ini_ui"
        )
        usar_ini = c2.checkbox(
            "Usar", value=bool(st.session_state.fin_dt_ini), key="fin_use_ini"
        )

        dt_fim_d = c3.date_input(
            "Até",
            value=st.session_state.fin_dt_fim or date.today(),
            key="fin_dt_fim_ui",
        )
        usar_fim = c3.checkbox(
            "Usar", value=bool(st.session_state.fin_dt_fim), key="fin_use_fim"
        )

        st.session_state.fin_dt_ini = dt_ini_d if usar_ini else None
        st.session_state.fin_dt_fim = dt_fim_d if usar_fim else None

        processo_id_visao: Optional[int] = None
        trabalho_scope: Optional[str] = None  # None=Todos | "sem_vinculo" | "vinculado"

        if proc_sel == "(Todos)":
            processo_id_visao = None
            trabalho_scope = None
        elif proc_sel == SEM_VINCULO_LABEL:
            processo_id_visao = None
            trabalho_scope = "sem_vinculo"
        else:
            processo_id_visao = int(proc_maps.label_to_id[proc_sel] or 0)
            trabalho_scope = "vinculado"

        dt_ini = _dt_ini_from_date(st.session_state.fin_dt_ini)
        dt_fim = _dt_fim_from_date(st.session_state.fin_dt_fim)

        if dt_ini and dt_fim and dt_ini > dt_fim:
            st.error("Período inválido: **'De'** não pode ser maior que **'Até'**.")
            dt_ini, dt_fim = None, None

        cA, cB = st.columns([1, 3])
        if cA.button("Limpar datas", use_container_width=True, key="fin_clear_dates"):
            st.session_state.fin_dt_ini = None
            st.session_state.fin_dt_fim = None
            st.session_state.fin_use_ini = False
            st.session_state.fin_use_fim = False
            st.rerun()
        cB.caption("Dica: marque **Usar** para ativar o filtro por data.")

    return processo_id_visao, dt_ini, dt_fim, trabalho_scope


# ============================================================
# Listagem / métricas
# ============================================================
def _list_rows(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
    tipo_val: Optional[str],
    q: Optional[str],
    limit: int,
):
    with get_session() as s:
        return FinanceiroService.list(
            s,
            owner_user_id=owner_user_id,
            processo_id=processo_id_visao,
            tipo=tipo_val,
            q=q,
            dt_ini=dt_ini,
            dt_fim=dt_fim,
            limit=limit,
        )


def _load_lancamentos_for_edit_picker(owner_user_id: int, limit: int = 500):
    with get_session() as s:
        return FinanceiroService.list(
            s,
            owner_user_id=owner_user_id,
            processo_id=None,
            tipo=None,
            q=None,
            dt_ini=None,
            dt_fim=None,
            limit=limit,
        )


def _calc_breakdown(
    rows, *, trabalho_scope: Optional[str]
) -> Tuple[float, float, float]:
    """
    (recebidas, a_receber, despesas)
    - Cancelado em receita não entra
    - trabalho_scope: None | "sem_vinculo" | "vinculado"
    """
    recebidas = 0.0
    a_receber = 0.0
    despesas = 0.0

    for x in rows or []:
        pid = getattr(x, "processo_id", None)

        if trabalho_scope == "sem_vinculo" and pid is not None:
            continue
        if trabalho_scope == "vinculado" and pid is None:
            continue

        tipo = (x.tipo or "").lower().strip()
        v = float(x.valor or 0.0)

        if tipo == "despesa":
            despesas += v
            continue

        if tipo == "receita":
            stt = _status_receita(x)
            if stt == "A receber":
                a_receber += v
            elif stt == "Recebido" or not stt:
                recebidas += v
            else:
                # Cancelado/outros
                pass

    return recebidas, a_receber, despesas


def _rows_to_df(
    rows, proc_label_by_id: Dict[int, str], *, trabalho_scope: Optional[str]
) -> pd.DataFrame:
    data = []
    for l in rows or []:
        pid = getattr(l, "processo_id", None)

        if trabalho_scope == "sem_vinculo" and pid is not None:
            continue
        if trabalho_scope == "vinculado" and pid is None:
            continue

        tipo = (l.tipo or "").strip()
        status_rec = _status_receita(l) if tipo.lower() == "receita" else ""

        data.append(
            {
                "id": l.id,
                "trabalho": _safe_trabalho_label(pid, proc_label_by_id),
                "data": l.data_lancamento.strftime("%d/%m/%Y"),
                "tipo": tipo,
                "situação": status_rec,
                "categoria": l.categoria or "",
                "descricao": l.descricao or "",
                "valor": float(l.valor),
            }
        )
    return pd.DataFrame(data)


# ============================================================
# Totais
# ============================================================
def _section_totals(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
    *,
    trabalho_scope: Optional[str],
) -> None:
    # Totais do backend (compat)
    with get_session() as s:
        tot = FinanceiroService.totals(
            s,
            owner_user_id=owner_user_id,
            processo_id=processo_id_visao,
            dt_ini=dt_ini,
            dt_fim=dt_fim,
        )

    # Probe para calcular A receber e saldo caixa (funciona mesmo se backend não tiver)
    rows_probe = _list_rows(
        owner_user_id=owner_user_id,
        processo_id_visao=processo_id_visao,
        dt_ini=dt_ini,
        dt_fim=dt_fim,
        tipo_val=None,
        q=None,
        limit=5000,
    )
    recebidas, a_receber, despesas_lista = _calc_breakdown(
        rows_probe, trabalho_scope=trabalho_scope
    )
    saldo_caixa = recebidas - despesas_lista

    with st.container(border=True):
        st.markdown("#### 📌 Totais (com filtros)")
        subtle_divider()

        k1, k2 = st.columns(2)
        with k1:
            card(
                "Recebido",
                _brl(recebidas),
                "caixa",
                tone="success" if recebidas else "neutral",
            )
        with k2:
            card(
                "A receber",
                _brl(a_receber),
                "previsto",
                tone="warning" if a_receber else "neutral",
            )

        k3, k4 = st.columns(2)
        with k3:
            card(
                "Despesas",
                _brl(float(tot.get("despesas", 0.0))),
                "no período",
                tone="warning",
            )
        with k4:
            card("Saldo (caixa)", _brl(saldo_caixa), "recebido - despesas", tone="info")


# ============================================================
# Criar lançamento (Despesas sem vínculo + keys distintas)
# ============================================================
def _section_create(owner_user_id: int, proc_maps: ProcMaps) -> None:
    with st.container(border=True):
        st.markdown("#### ➕ Novo lançamento")
        st.caption("Registre receita/despesa. Despesas podem ser gerais (sem vínculo).")
        subtle_divider()

        with st.form("form_fin_create", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

            tipo = c2.selectbox("Tipo *", ["Receita", "Despesa"], key="fin_create_tipo")
            d = c3.date_input("Data *", value=date.today(), key="fin_create_data")

            # IMPORTANTE: keys diferentes para o widget "Trabalho" conforme tipo
            if tipo == "Despesa":
                proc_options = [SEM_VINCULO_LABEL] + proc_maps.labels
                proc_lbl = c1.selectbox(
                    "Trabalho", proc_options, key="fin_create_proc_desp"
                )
                c4.caption(" ")
                status_rec = None
            else:
                proc_lbl = c1.selectbox(
                    "Trabalho *", proc_maps.labels, key="fin_create_proc_rec"
                )
                status_rec = c4.selectbox(
                    "Situação",
                    list(RECEITA_STATUS_VALIDOS),
                    index=0,
                    key="fin_create_status_receb",
                )

            c5, c6 = st.columns([2, 1])
            categoria = c5.text_input(
                "Categoria",
                placeholder="Honorários / Custas / Impressão / Prospecção...",
                key="fin_create_cat",
            )
            valor = c6.number_input(
                "Valor (R$) *",
                min_value=0.0,
                step=50.0,
                value=0.0,
                key="fin_create_valor",
            )

            descricao = st.text_area("Descrição", key="fin_create_desc")

            submitted = st.form_submit_button(
                "Salvar lançamento", type="primary", use_container_width=True
            )

        if not submitted:
            return

        if float(valor) <= 0:
            st.error("Informe um **valor maior que zero**.")
            return

        try:
            # Despesa sem vínculo => processo_id None
            if tipo == "Despesa" and proc_lbl == SEM_VINCULO_LABEL:
                processo_id: Optional[int] = None
            else:
                # Receita sempre vinculada; Despesa vinculada também
                processo_id = int(proc_maps.label_to_id.get(proc_lbl) or 0)

            dt = datetime(d.year, d.month, d.day, 12, 0, 0)

            payload = _make_create_payload(
                processo_id=processo_id,
                data_lancamento=dt,
                tipo=tipo,
                categoria=(categoria or "").strip() or None,
                descricao=(descricao or "").strip() or None,
                valor=float(valor),
                status_recebimento=(status_rec if tipo == "Receita" else None),
            )

            with get_session() as s:
                FinanceiroService.create(
                    s, owner_user_id=owner_user_id, payload=payload
                )

            _bump_version(owner_user_id)
            st.success("Lançamento criado.")
            st.rerun()

        except Exception as e:
            st.error(
                f"Erro ao criar lançamento: {e}\n\n"
                f"Se você selecionou **{SEM_VINCULO_LABEL}**, confirme no backend se "
                f"`processo_id` aceita **None** (FK nullable) e se o service suporta isso."
            )


# ============================================================
# Lançamentos + Editar/Excluir
# ============================================================
def _section_lancamentos(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
    proc_maps: ProcMaps,
    *,
    trabalho_scope: Optional[str],
):
    with st.container(border=True):
        st.markdown("#### 📋 Lançamentos")
        st.caption(
            "Lista por filtros atuais. Edição abaixo é independente dos filtros."
        )
        subtle_divider()

        c1, c2, c3 = st.columns([2, 3, 1])
        filtro_tipo = c1.selectbox(
            "Tipo", ["(Todos)", "Receita", "Despesa"], index=0, key="fin_list_tipo"
        )
        filtro_q = c2.text_input(
            "Buscar (categoria/descrição)", value="", key="fin_list_q"
        )
        filtro_limit = c3.selectbox(
            "Limite", [100, 200, 300, 500], index=1, key="fin_list_limit"
        )

        tipo_val = None if filtro_tipo == "(Todos)" else filtro_tipo

        rows = _list_rows(
            owner_user_id=owner_user_id,
            processo_id_visao=processo_id_visao,
            dt_ini=dt_ini,
            dt_fim=dt_fim,
            tipo_val=tipo_val,
            q=(filtro_q or "").strip() or None,
            limit=int(filtro_limit),
        )

        recebidas, a_receber, despesas = _calc_breakdown(
            rows, trabalho_scope=trabalho_scope
        )
        total = len(rows or [])

        k1, k2 = st.columns(2)
        with k1:
            card("Qtd", f"{total}", "itens", tone="info")
        with k2:
            card(
                "Recebido",
                _brl(recebidas),
                "na lista",
                tone="success" if recebidas else "neutral",
            )

        k3, k4 = st.columns(2)
        with k3:
            card(
                "A receber",
                _brl(a_receber),
                "previsto",
                tone="warning" if a_receber else "neutral",
            )
        with k4:
            card(
                "Despesas",
                _brl(despesas),
                "na lista",
                tone="warning" if despesas else "neutral",
            )

        st.write("")
        if not rows:
            st.info("Nenhum lançamento cadastrado para os filtros atuais.")
        else:
            df = _rows_to_df(rows, proc_maps.label_by_id, trabalho_scope=trabalho_scope)
            df_display = df.copy()
            df_display["valor"] = df_display["valor"].apply(_brl)

            cols = ["trabalho", "data", "tipo", "categoria", "descricao", "valor"]
            if "situação" in df_display.columns:
                cols = [
                    "trabalho",
                    "data",
                    "tipo",
                    "situação",
                    "categoria",
                    "descricao",
                    "valor",
                ]

            st.dataframe(
                df_display[cols], use_container_width=True, hide_index=True, height=420
            )

            st.write("")
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Baixar CSV (filtros atuais)",
                data=csv,
                file_name="financeiro_export.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # -------------------------
    # Editar / Excluir (independente)
    # -------------------------
    with st.container(border=True):
        st.markdown("#### ✏️ Editar / 🗑️ Excluir")
        st.caption("Selecione qualquer lançamento (não depende dos filtros acima).")
        subtle_divider()

        all_for_edit = _load_lancamentos_for_edit_picker(owner_user_id, limit=500)
        if not all_for_edit:
            st.info("Nenhum lançamento cadastrado.")
            return

        def _lanc_label(l) -> str:
            trab = _safe_trabalho_label(
                getattr(l, "processo_id", None), proc_maps.label_by_id
            )
            dt_ = l.data_lancamento.strftime("%d/%m/%Y")
            tipo_ = (l.tipo or "").strip()
            cat_ = (l.categoria or "").strip()
            val_ = _brl(float(l.valor))
            extra = f" | {_status_receita(l)}" if tipo_.lower() == "receita" else ""
            return f"[#{l.id}] {dt_} | {tipo_}{extra} | {val_} | {trab} | {cat_}"

        def _parse_id(label: str) -> int:
            head = label.split("]")[0]
            return int(head.replace("[#", "").strip())

        labels = [_lanc_label(l) for l in all_for_edit]
        st.session_state.setdefault("fin_edit_selected", labels[0])

        selected_label = st.selectbox(
            "Selecione um lançamento",
            options=labels,
            index=(
                labels.index(st.session_state.fin_edit_selected)
                if st.session_state.fin_edit_selected in labels
                else 0
            ),
            key="fin_edit_picker",
        )
        st.session_state.fin_edit_selected = selected_label
        lanc_id = _parse_id(selected_label)

        with get_session() as s:
            l = FinanceiroService.get(s, owner_user_id, int(lanc_id))
        if not l:
            st.error("Lançamento não encontrado.")
            return

        tipo_atual = (l.tipo or "").strip()
        pid_atual = getattr(l, "processo_id", None)
        proc_atual_lbl = _safe_trabalho_label(pid_atual, proc_maps.label_by_id)

        with st.form("form_fin_edit"):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

            tipo_e = c2.selectbox(
                "Tipo",
                ["Receita", "Despesa"],
                index=0 if tipo_atual == "Receita" else 1,
                key="fin_edit_tipo",
            )
            d_e = c3.date_input(
                "Data", value=l.data_lancamento.date(), key="fin_edit_data"
            )

            if tipo_e == "Despesa":
                proc_options = [SEM_VINCULO_LABEL] + proc_maps.labels
                idx = (
                    proc_options.index(proc_atual_lbl)
                    if proc_atual_lbl in proc_options
                    else 0
                )
                proc_lbl_e = c1.selectbox(
                    "Trabalho", proc_options, index=idx, key="fin_edit_proc_desp"
                )
                c4.caption(" ")
                status_rec_e = None
            else:
                idx = (
                    proc_maps.labels.index(proc_atual_lbl)
                    if proc_atual_lbl in proc_maps.labels
                    else 0
                )
                proc_lbl_e = c1.selectbox(
                    "Trabalho *", proc_maps.labels, index=idx, key="fin_edit_proc_rec"
                )
                status_rec_e = c4.selectbox(
                    "Situação",
                    list(RECEITA_STATUS_VALIDOS),
                    index=(
                        list(RECEITA_STATUS_VALIDOS).index(_status_receita(l))
                        if _status_receita(l) in RECEITA_STATUS_VALIDOS
                        else 0
                    ),
                    key="fin_edit_status_receb",
                )

            c5, c6 = st.columns([2, 1])
            cat_e = c5.text_input(
                "Categoria", value=l.categoria or "", key="fin_edit_cat"
            )
            valor_e = c6.number_input(
                "Valor (R$) *",
                min_value=0.0,
                step=50.0,
                value=float(l.valor),
                key="fin_edit_valor",
            )
            desc_e = st.text_area(
                "Descrição", value=l.descricao or "", key="fin_edit_desc"
            )

            atualizar = st.form_submit_button(
                "Salvar alterações", type="primary", use_container_width=True
            )

        if atualizar:
            if float(valor_e) <= 0:
                st.error("Informe um **valor maior que zero**.")
                return
            try:
                if tipo_e == "Despesa" and proc_lbl_e == SEM_VINCULO_LABEL:
                    processo_id_e: Optional[int] = None
                else:
                    processo_id_e = int(proc_maps.label_to_id.get(proc_lbl_e) or 0)

                dt_e = datetime(d_e.year, d_e.month, d_e.day, 12, 0, 0)

                payload = _make_update_payload(
                    processo_id=processo_id_e,
                    data_lancamento=dt_e,
                    tipo=tipo_e,
                    categoria=(cat_e or "").strip() or None,
                    descricao=(desc_e or "").strip() or None,
                    valor=float(valor_e),
                    status_recebimento=(status_rec_e if tipo_e == "Receita" else None),
                )

                with get_session() as s:
                    FinanceiroService.update(s, owner_user_id, int(lanc_id), payload)

                _bump_version(owner_user_id)
                st.success("Lançamento atualizado.")
                st.rerun()
            except Exception as e:
                st.error(
                    f"Erro ao atualizar: {e}\n\n"
                    f"Se você selecionou **{SEM_VINCULO_LABEL}**, confirme no backend se "
                    f"`processo_id` aceita **None** (FK nullable) e se o service suporta isso."
                )

        st.divider()

        st.caption("⚠️ Exclusão irreversível")
        confirm = st.checkbox(
            "Confirmo que desejo excluir este lançamento.",
            value=False,
            key=f"fin_del_confirm_{lanc_id}",
        )
        if st.button(
            "🗑️ Excluir definitivamente",
            type="primary",
            disabled=not confirm,
            use_container_width=True,
            key=f"fin_del_btn_{lanc_id}",
        ):
            try:
                with get_session() as s:
                    FinanceiroService.delete(s, owner_user_id, int(lanc_id))
                _bump_version(owner_user_id)
                st.success("Lançamento excluído.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


# ============================================================
# Resumos
# ============================================================
def _section_resumo_por_processo(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
    proc_maps: ProcMaps,
):
    with st.container(border=True):
        st.markdown("#### 📊 Resumo por trabalho")
        subtle_divider()

        if processo_id_visao:
            st.info(
                "Selecione **(Todos)** no filtro de Trabalho para ver o resumo por trabalho."
            )
            return

        with get_session() as s:
            resumo = FinanceiroService.resumo_por_processo(
                s, owner_user_id=owner_user_id, dt_ini=dt_ini, dt_fim=dt_fim
            )

        if not resumo:
            st.info("Sem dados para os filtros atuais.")
            return

        df = pd.DataFrame(
            [
                {
                    "trabalho": proc_maps.label_by_id.get(
                        x["processo_id"], f"[{x['processo_id']}]"
                    ),
                    "receitas": _brl(float(x.get("receitas", 0.0))),
                    "despesas": _brl(float(x.get("despesas", 0.0))),
                    "saldo": _brl(float(x.get("saldo", 0.0))),
                }
                for x in resumo
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)


def _section_resumo_por_categoria(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
):
    with st.container(border=True):
        st.markdown("#### 🏷️ Resumo por categoria")
        subtle_divider()

        with get_session() as s:
            cats = FinanceiroService.resumo_por_categoria(
                s,
                owner_user_id=owner_user_id,
                processo_id=processo_id_visao,
                dt_ini=dt_ini,
                dt_fim=dt_fim,
            )

        if not cats:
            st.info("Sem dados para os filtros atuais.")
            return

        df = pd.DataFrame(
            [
                {
                    "categoria": x["categoria"],
                    "tipo": x["tipo"],
                    "total": _brl(float(x["total"])),
                }
                for x in cats
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)


def _section_resumo_mensal(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
    *,
    trabalho_scope: Optional[str],
    proc_maps: ProcMaps,
):
    """
    Gráfico melhor:
    - barras agrupadas (Recebido / A receber / Despesas)
    - linha (Saldo do caixa = Recebido - Despesas)
    """
    with st.container(border=True):
        st.markdown("#### 🗓️ Resumo mensal")
        st.caption("Recebido × A receber × Despesas, com saldo do caixa.")
        subtle_divider()

        rows = _list_rows(
            owner_user_id=owner_user_id,
            processo_id_visao=processo_id_visao,
            dt_ini=dt_ini,
            dt_fim=dt_fim,
            tipo_val=None,
            q=None,
            limit=10000,
        )
        if not rows:
            st.info("Sem dados para os filtros atuais.")
            return

        agg: Dict[str, Dict[str, float]] = {}
        for x in rows:
            pid = getattr(x, "processo_id", None)
            if trabalho_scope == "sem_vinculo" and pid is not None:
                continue
            if trabalho_scope == "vinculado" and pid is None:
                continue

            mk = _month_key(x.data_lancamento)
            agg.setdefault(mk, {"Recebido": 0.0, "A receber": 0.0, "Despesas": 0.0})

            tipo = (x.tipo or "").lower().strip()
            v = float(x.valor or 0.0)

            if tipo == "despesa":
                agg[mk]["Despesas"] += v
            elif tipo == "receita":
                stt = _status_receita(x)
                if stt == "A receber":
                    agg[mk]["A receber"] += v
                elif stt == "Recebido" or not stt:
                    agg[mk]["Recebido"] += v
                else:
                    pass

        meses = sorted(agg.keys())
        df_m = pd.DataFrame(
            [
                {
                    "mes": m,
                    "Recebido": agg[m]["Recebido"],
                    "A receber": agg[m]["A receber"],
                    "Despesas": agg[m]["Despesas"],
                }
                for m in meses
            ]
        )
        df_m["Saldo (caixa)"] = df_m["Recebido"] - df_m["Despesas"]

        df_show = df_m.copy()
        for col in ["Recebido", "A receber", "Despesas", "Saldo (caixa)"]:
            df_show[col] = df_show[col].apply(lambda x: _brl(float(x)))
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        try:
            import altair as alt

            df_long = df_m.melt(
                id_vars=["mes"],
                value_vars=["Recebido", "A receber", "Despesas"],
                var_name="Série",
                value_name="Valor",
            )

            bars = (
                alt.Chart(df_long)
                .mark_bar()
                .encode(
                    x=alt.X("mes:N", title="Mês"),
                    xOffset="Série:N",
                    y=alt.Y("Valor:Q", title="R$"),
                    color="Série:N",
                    tooltip=["mes:N", "Série:N", alt.Tooltip("Valor:Q", format=",.2f")],
                )
            )

            line = (
                alt.Chart(df_m)
                .mark_line(point=True)
                .encode(
                    x=alt.X("mes:N", title="Mês"),
                    y=alt.Y("Saldo (caixa):Q", title="R$"),
                    tooltip=["mes:N", alt.Tooltip("Saldo (caixa):Q", format=",.2f")],
                )
            )

            chart = (
                alt.layer(bars, line).resolve_scale(y="shared").properties(height=320)
            )
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.caption("Gráfico (barras) — Recebido × A receber × Despesas")
            st.bar_chart(df_m.set_index("mes")[["Recebido", "A receber", "Despesas"]])
            st.caption("Gráfico (linha) — Saldo do caixa")
            st.line_chart(df_m.set_index("mes")[["Saldo (caixa)"]])


# ============================================================
# Page
# ============================================================
def render(owner_user_id: int) -> None:
    inject_global_css()

    clicked_refresh = page_header(
        "Financeiro",
        "Receitas e despesas por trabalho, com filtros e relatórios.",
        right_button_label="Recarregar",
        right_button_key="fin_btn_recarregar",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked_refresh:
        st.rerun()

    version = _data_version(owner_user_id)
    processos = _load_processos(owner_user_id, version)
    if not processos:
        st.info("Cadastre um trabalho primeiro para registrar lançamentos financeiros.")
        return

    proc_maps = _build_proc_maps(processos)
    _apply_pref_processo_defaults(proc_maps)

    processo_id_visao, dt_ini, dt_fim, trabalho_scope = _section_filters(proc_maps)

    _section_totals(
        owner_user_id, processo_id_visao, dt_ini, dt_fim, trabalho_scope=trabalho_scope
    )

    st.write("")
    _section_create(owner_user_id, proc_maps)
    st.write("")

    st.session_state.setdefault("financeiro_section", "Lançamentos")
    section = _section_tabs("financeiro_section")

    if section == "Lançamentos":
        _section_lancamentos(
            owner_user_id,
            processo_id_visao,
            dt_ini,
            dt_fim,
            proc_maps,
            trabalho_scope=trabalho_scope,
        )
    elif section == "Resumo":
        _section_resumo_por_processo(
            owner_user_id, processo_id_visao, dt_ini, dt_fim, proc_maps
        )
    elif section == "Categorias":
        _section_resumo_por_categoria(owner_user_id, processo_id_visao, dt_ini, dt_fim)
    else:
        _section_resumo_mensal(
            owner_user_id,
            processo_id_visao,
            dt_ini,
            dt_fim,
            trabalho_scope=trabalho_scope,
            proc_maps=proc_maps,
        )
