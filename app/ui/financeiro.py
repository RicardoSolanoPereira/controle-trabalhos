# app/ui/financeiro.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any

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

from app.ui.theme import inject_global_css, card
from app.ui.page_header import page_header


# -------------------------
# Helpers
# -------------------------
@dataclass(frozen=True)
class ProcMaps:
    labels: List[str]
    label_to_id: Dict[str, int]
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


def _lanc_label(l, proc_label_by_id: Dict[int, str]) -> str:
    proc = proc_label_by_id.get(l.processo_id, f"[{l.processo_id}]")
    dt = l.data_lancamento.strftime("%d/%m/%Y")
    tipo = (l.tipo or "").strip()
    cat = (l.categoria or "").strip()
    val = _brl(float(l.valor))
    return f"[#{l.id}] {dt} | {tipo} | {val} | {proc} | {cat}"


def _parse_lancamento_id_from_label(label: str) -> int:
    # "[#123] ..."
    head = label.split("]")[0]
    return int(head.replace("[#", "").strip())


def _load_processos(owner_user_id: int) -> List[Processo]:
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
    labels = [_proc_label(p) for p in processos]
    label_to_id = {_proc_label(p): int(p.id) for p in processos}
    label_by_id = {int(p.id): _proc_label(p) for p in processos}
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
    st.session_state.setdefault("fin_create_proc", pref_label)


def _section_tabs(key: str) -> str:
    options = ["Lançamentos", "Resumo", "Categorias", "Mensal"]
    if hasattr(st, "segmented_control"):
        return st.segmented_control(
            "Seção", options, key=key, label_visibility="collapsed"
        )
    return st.radio(
        "Seção", options, horizontal=True, key=key, label_visibility="collapsed"
    )


# -------------------------
# Filtros
# -------------------------
def _section_filters(
    proc_maps: ProcMaps,
) -> Tuple[Optional[int], Optional[datetime], Optional[datetime]]:
    with st.container(border=True):
        st.markdown("#### 🔎 Filtros")
        st.caption(
            "Filtre por trabalho e período. Se não preencher datas, mostra tudo."
        )

        c1, c2, c3 = st.columns([3, 1, 1])

        # Mantém compatível com setdefault(pref)
        proc_sel = c1.selectbox(
            "Trabalho",
            ["(Todos)"] + proc_maps.labels,
            index=0,
            key="fin_visao_proc",
        )

        # Datas opcionais (sem value=None no widget, para não quebrar em versões)
        st.session_state.setdefault("fin_dt_ini", None)
        st.session_state.setdefault("fin_dt_fim", None)

        dt_ini_d = c2.date_input(
            "De",
            value=st.session_state.fin_dt_ini or date.today(),
            key="fin_dt_ini_ui",
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

        # aplica flags
        st.session_state.fin_dt_ini = dt_ini_d if usar_ini else None
        st.session_state.fin_dt_fim = dt_fim_d if usar_fim else None

        processo_id_visao = None
        if proc_sel != "(Todos)":
            processo_id_visao = int(proc_maps.label_to_id[proc_sel])

        dt_ini = _dt_ini_from_date(st.session_state.fin_dt_ini)
        dt_fim = _dt_fim_from_date(st.session_state.fin_dt_fim)

        if dt_ini and dt_fim and dt_ini > dt_fim:
            st.error("Período inválido: **'De'** não pode ser maior que **'Até'**.")
            dt_ini, dt_fim = None, None

        # botão rápido
        cA, cB = st.columns([1, 3])
        if cA.button("Limpar datas", use_container_width=True, key="fin_clear_dates"):
            st.session_state.fin_dt_ini = None
            st.session_state.fin_dt_fim = None
            st.session_state.fin_use_ini = False
            st.session_state.fin_use_fim = False
            st.rerun()
        cB.caption("Dica: marque **Usar** para ativar o filtro por data.")

    return processo_id_visao, dt_ini, dt_fim


# -------------------------
# Totais
# -------------------------
def _section_totals(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
) -> None:
    with get_session() as s:
        tot = FinanceiroService.totals(
            s,
            owner_user_id=owner_user_id,
            processo_id=processo_id_visao,
            dt_ini=dt_ini,
            dt_fim=dt_fim,
        )

    with st.container(border=True):
        st.markdown("#### 📌 Totais (com filtros)")
        c1, c2, c3 = st.columns(3)
        card("Receitas", _brl(float(tot["receitas"])), "no período", tone="success")
        card("Despesas", _brl(float(tot["despesas"])), "no período", tone="warning")
        card("Saldo", _brl(float(tot["saldo"])), "resultado", tone="info")


# -------------------------
# Criar lançamento
# -------------------------
def _section_create(owner_user_id: int, proc_maps: ProcMaps) -> None:
    with st.container(border=True):
        st.markdown("#### ➕ Novo lançamento")
        st.caption("Registre receita/despesa vinculada a um trabalho.")

        with st.form("form_fin_create", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            proc_lbl = c1.selectbox(
                "Trabalho *", proc_maps.labels, key="fin_create_proc"
            )
            tipo = c2.selectbox("Tipo *", ["Receita", "Despesa"], key="fin_create_tipo")
            d = c3.date_input("Data *", value=date.today(), key="fin_create_data")

            c4, c5 = st.columns([2, 1])
            categoria = c4.text_input(
                "Categoria",
                placeholder="Honorários / Custas / Deslocamento...",
                key="fin_create_cat",
            )
            valor = c5.number_input(
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
            processo_id = int(proc_maps.label_to_id[proc_lbl])
            dt = datetime(d.year, d.month, d.day, 12, 0, 0)  # padrão meio-dia

            payload = LancamentoCreate(
                processo_id=processo_id,
                data_lancamento=dt,
                tipo=tipo,
                categoria=(categoria or "").strip() or None,
                descricao=(descricao or "").strip() or None,
                valor=float(valor),
            )

            with get_session() as s:
                FinanceiroService.create(
                    s, owner_user_id=owner_user_id, payload=payload
                )

            st.success("Lançamento criado.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao criar lançamento: {e}")


# -------------------------
# Lista + Editar/Excluir
# -------------------------
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
    """
    Picker de edição independente dos filtros da lista
    (igual Agendamentos), para evitar sumir item.
    """
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


def _rows_to_df(rows, proc_label_by_id: Dict[int, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": l.id,
                "trabalho": proc_label_by_id.get(l.processo_id, f"[{l.processo_id}]"),
                "data": l.data_lancamento.strftime("%d/%m/%Y"),
                "tipo": l.tipo,
                "categoria": l.categoria or "",
                "descricao": l.descricao or "",
                "valor": float(l.valor),
            }
            for l in rows
        ]
    )


def _section_lancamentos(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
    proc_maps: ProcMaps,
):
    with st.container(border=True):
        st.markdown("#### 📋 Lançamentos")
        st.caption(
            "Lista por filtros atuais. Edição abaixo é independente dos filtros."
        )

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

        # KPIs rápidos
        total = len(rows or [])
        receitas = sum(
            float(x.valor) for x in (rows or []) if (x.tipo or "").lower() == "receita"
        )
        despesas = sum(
            float(x.valor) for x in (rows or []) if (x.tipo or "").lower() == "despesa"
        )

        k1, k2, k3 = st.columns(3)
        card("Qtd", f"{total}", "itens", tone="info")
        card("Receitas", _brl(receitas), "na lista", tone="success")
        card("Despesas", _brl(despesas), "na lista", tone="warning")

        st.write("")
        if not rows:
            st.info("Nenhum lançamento cadastrado para os filtros atuais.")
        else:
            df = _rows_to_df(rows, proc_maps.label_by_id)
            df_display = df.copy()
            df_display["valor"] = df_display["valor"].apply(_brl)

            st.dataframe(
                df_display[
                    ["trabalho", "data", "tipo", "categoria", "descricao", "valor"]
                ],
                use_container_width=True,
                hide_index=True,
                height=420,
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

        all_for_edit = _load_lancamentos_for_edit_picker(owner_user_id, limit=500)
        if not all_for_edit:
            st.info("Nenhum lançamento cadastrado.")
            return

        labels = [_lanc_label(l, proc_maps.label_by_id) for l in all_for_edit]
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
        lanc_id = _parse_lancamento_id_from_label(selected_label)

        with get_session() as s:
            l = FinanceiroService.get(s, owner_user_id, int(lanc_id))
        if not l:
            st.error("Lançamento não encontrado.")
            return

        proc_atual_lbl = proc_maps.label_by_id.get(l.processo_id, proc_maps.labels[0])

        with st.form("form_fin_edit"):
            c1, c2, c3 = st.columns([3, 1, 1])

            proc_lbl_e = c1.selectbox(
                "Trabalho",
                proc_maps.labels,
                index=(
                    proc_maps.labels.index(proc_atual_lbl)
                    if proc_atual_lbl in proc_maps.labels
                    else 0
                ),
                key="fin_edit_proc",
            )
            tipo_e = c2.selectbox(
                "Tipo",
                ["Receita", "Despesa"],
                index=0 if (l.tipo or "") == "Receita" else 1,
                key="fin_edit_tipo",
            )
            d_e = c3.date_input(
                "Data", value=l.data_lancamento.date(), key="fin_edit_data"
            )

            c4, c5 = st.columns([2, 1])
            cat_e = c4.text_input(
                "Categoria", value=l.categoria or "", key="fin_edit_cat"
            )
            valor_e = c5.number_input(
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
                processo_id_e = int(proc_maps.label_to_id[proc_lbl_e])
                dt_e = datetime(d_e.year, d_e.month, d_e.day, 12, 0, 0)

                payload = LancamentoUpdate(
                    processo_id=processo_id_e,
                    data_lancamento=dt_e,
                    tipo=tipo_e,
                    categoria=(cat_e or "").strip() or None,
                    descricao=(desc_e or "").strip() or None,
                    valor=float(valor_e),
                )

                with get_session() as s:
                    FinanceiroService.update(s, owner_user_id, int(lanc_id), payload)

                st.success("Lançamento atualizado.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")

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
                st.success("Lançamento excluído.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


# -------------------------
# Resumos
# -------------------------
def _section_resumo_por_processo(
    owner_user_id: int,
    processo_id_visao: Optional[int],
    dt_ini: Optional[datetime],
    dt_fim: Optional[datetime],
    proc_maps: ProcMaps,
):
    with st.container(border=True):
        st.markdown("#### 📊 Resumo por trabalho")
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
                    "receitas": _brl(float(x["receitas"])),
                    "despesas": _brl(float(x["despesas"])),
                    "saldo": _brl(float(x["saldo"])),
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
):
    with st.container(border=True):
        st.markdown("#### 🗓️ Resumo mensal")
        with get_session() as s:
            mens = FinanceiroService.resumo_mensal(
                s,
                owner_user_id=owner_user_id,
                processo_id=processo_id_visao,
                dt_ini=dt_ini,
                dt_fim=dt_fim,
            )

        if not mens:
            st.info("Sem dados para os filtros atuais.")
            return

        df_m = pd.DataFrame(mens)
        df_display = df_m.copy()
        df_display["receitas"] = df_display["receitas"].apply(lambda x: _brl(float(x)))
        df_display["despesas"] = df_display["despesas"].apply(lambda x: _brl(float(x)))
        df_display["saldo"] = df_display["saldo"].apply(lambda x: _brl(float(x)))

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.caption("Gráfico (saldo por mês)")
        st.line_chart(df_m.set_index("mes")[["saldo"]])


# -------------------------
# Page
# -------------------------
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

    processos = _load_processos(owner_user_id)
    if not processos:
        st.info("Cadastre um trabalho primeiro para registrar lançamentos financeiros.")
        return

    proc_maps = _build_proc_maps(processos)
    _apply_pref_processo_defaults(proc_maps)

    processo_id_visao, dt_ini, dt_fim = _section_filters(proc_maps)

    _section_totals(owner_user_id, processo_id_visao, dt_ini, dt_fim)

    st.write("")

    _section_create(owner_user_id, proc_maps)

    st.write("")

    st.session_state.setdefault("financeiro_section", "Lançamentos")
    section = _section_tabs("financeiro_section")

    if section == "Lançamentos":
        _section_lancamentos(
            owner_user_id, processo_id_visao, dt_ini, dt_fim, proc_maps
        )
    elif section == "Resumo":
        _section_resumo_por_processo(
            owner_user_id, processo_id_visao, dt_ini, dt_fim, proc_maps
        )
    elif section == "Categorias":
        _section_resumo_por_categoria(owner_user_id, processo_id_visao, dt_ini, dt_fim)
    else:
        _section_resumo_mensal(owner_user_id, processo_id_visao, dt_ini, dt_fim)
