from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.calendario_service import CalendarioService, RegrasCalendario
from services.prazos_service import PrazoCreate, PrazoUpdate, PrazosService
from services.utils import date_to_br_datetime, ensure_br, format_date_br, now_br
from ui.page_header import page_header
from ui.theme import card, subtle_divider
from ui_state import bump_data_version, get_data_version


# ============================================================
# CONFIG
# ============================================================

DEBUG_PRAZOS = False


# ============================================================
# CONSTANTES
# ============================================================

TIPOS_TRABALHO = (
    "Perito Judicial",
    "Assistente Técnico",
    "Trabalho Particular",
)

PRIORIDADES = ("Baixa", "Média", "Alta")

KEY_OWNER = "owner_user_id"

KEY_ACTIVE_TAB = "pz_active_tab"
KEY_NAV_TO = "pz_nav_to"

KEY_LIST_ACTIVE = "pz_list_active"
KEY_LIST_NAV_TO = "pz_list_nav_to"

KEY_C_PROC = "pz_create_proc"
KEY_C_MODE = "pz_create_mode"
KEY_C_BASE = "pz_create_base"
KEY_C_DIAS = "pz_create_dias"
KEY_C_USAR_TJSP = "pz_create_usar_tjsp"
KEY_C_LOCAL = "pz_create_local"
KEY_C_DATA_LIM = "pz_create_data_lim"
KEY_C_AUDIT = "pz_create_audit"
KEY_C_EVENTO = "pz_create_evento"
KEY_C_PRIO = "pz_create_prio"
KEY_C_ORIGEM = "pz_create_origem"
KEY_C_REF = "pz_create_ref"
KEY_C_OBS = "pz_create_obs"

KEY_FILTER_TIPO = "pz_filter_tipo_trabalho"
KEY_FILTER_PROC = "pz_filter_proc_global"
KEY_FILTER_BUSCA = "pz_filter_busca_global"

KEY_OPEN_WINDOW = "pz_open_window"
KEY_OPEN_ORDER = "pz_open_order"


# ============================================================
# TIPOS AUXILIARES
# ============================================================


@dataclass(frozen=True)
class PrazoRow:
    prazo_id: int
    processo_id: int
    processo_numero: str
    processo_tipo_acao: str | None
    processo_comarca: str | None
    processo_vara: str | None
    processo_contratante: str | None
    processo_papel: str | None

    evento: str
    data_limite: Any
    prioridade: str
    concluido: bool
    origem: str | None
    referencia: str | None
    observacoes: str | None


# ============================================================
# RENDER / ESTILO
# ============================================================


def _render_html(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: str | None) -> str | None:
    text = _safe_str(value)
    return text or None


def _section_card(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def _inject_segmented_radio_css() -> None:
    _render_html(
        """
        <style>
        div[data-testid="stRadio"] > div {
            flex-direction: row !important;
            gap: 8px !important;
            flex-wrap: wrap !important;
        }

        div[data-testid="stRadio"] label {
            border: 1px solid rgba(49, 51, 63, 0.18);
            padding: 8px 12px;
            border-radius: 10px;
            background: #ffffff;
            margin: 0 !important;
        }

        div[data-testid="stRadio"] label:hover {
            border-color: rgba(49, 51, 63, 0.38);
        }

        div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        div[data-testid="stRadio"] label span {
            font-size: 12px;
            font-weight: 600;
        }

        div[data-testid="stRadio"] input:checked + div {
            background: rgba(17, 25, 40, 0.06) !important;
            border-radius: 8px !important;
        }

        .pz-muted {
            color: rgba(49, 51, 63, 0.75);
            font-size: 0.92rem;
        }
        </style>
        """
    )


def _section_tabs(key: str) -> str:
    options = ["Cadastrar", "Lista", "Editar / Excluir"]

    if hasattr(st, "segmented_control"):
        return st.segmented_control(
            "Seção",
            options,
            key=key,
            label_visibility="collapsed",
        )

    _inject_segmented_radio_css()
    return st.radio(
        "Seção",
        options,
        horizontal=True,
        label_visibility="collapsed",
        key=key,
    )


def _list_tabs_selector() -> str:
    labels = ["📋 Abertos", "🔴 Atrasados", "🟠 Vencem (7 dias)", "✅ Concluídos"]
    label_to_value = {
        "📋 Abertos": "Abertos",
        "🔴 Atrasados": "Atrasados",
        "🟠 Vencem (7 dias)": "Vencem (7 dias)",
        "✅ Concluídos": "Concluídos",
    }
    value_to_label = {v: k for k, v in label_to_value.items()}

    current_value = st.session_state.get(KEY_LIST_ACTIVE, "Abertos")
    default_label = value_to_label.get(current_value, "📋 Abertos")
    st.session_state.setdefault("pz_list_selector", default_label)

    if hasattr(st, "segmented_control"):
        chosen_label = st.segmented_control(
            "Visão",
            labels,
            key="pz_list_selector",
            label_visibility="collapsed",
        )
    else:
        _inject_segmented_radio_css()
        chosen_label = st.radio(
            "Visão",
            labels,
            horizontal=True,
            key="pz_list_selector",
            label_visibility="collapsed",
            index=labels.index(st.session_state.get("pz_list_selector", default_label)),
        )

    chosen_value = label_to_value.get(chosen_label, "Abertos")
    st.session_state[KEY_LIST_ACTIVE] = chosen_value
    return chosen_value


# ============================================================
# DATA VERSION / CACHE
# ============================================================


def _data_version(owner_user_id: int) -> int:
    return get_data_version(owner_user_id)


def _pzproc_to_dict(prazo: Any, proc: Any) -> dict[str, Any]:
    return {
        "prazo": {
            "id": int(getattr(prazo, "id", 0) or 0),
            "evento": str(getattr(prazo, "evento", "") or ""),
            "data_limite": getattr(prazo, "data_limite", None),
            "prioridade": str(getattr(prazo, "prioridade", "Média") or "Média"),
            "concluido": bool(getattr(prazo, "concluido", False)),
            "origem": getattr(prazo, "origem", None),
            "referencia": getattr(prazo, "referencia", None),
            "observacoes": getattr(prazo, "observacoes", None),
            "processo_id": int(getattr(prazo, "processo_id", 0) or 0),
        },
        "proc": {
            "id": int(getattr(proc, "id", 0) or 0),
            "numero_processo": str(getattr(proc, "numero_processo", "") or ""),
            "tipo_acao": getattr(proc, "tipo_acao", None),
            "comarca": getattr(proc, "comarca", None),
            "vara": getattr(proc, "vara", None),
            "contratante": getattr(proc, "contratante", None),
            "papel": getattr(proc, "papel", None),
        },
    }


@st.cache_data(show_spinner=False, ttl=45)
def _cached_processos(owner_user_id: int, version: int) -> list[dict[str, Any]]:
    _ = version

    with get_session() as s:
        procs = (
            s.execute(
                select(Processo)
                .where(Processo.owner_user_id == owner_user_id)
                .order_by(Processo.id.desc())
            )
            .scalars()
            .all()
        )

    out: list[dict[str, Any]] = []
    for p in procs:
        out.append(
            {
                "id": int(p.id),
                "numero_processo": str(p.numero_processo or ""),
                "tipo_acao": p.tipo_acao,
                "comarca": p.comarca,
                "vara": p.vara,
                "contratante": p.contratante,
                "papel": p.papel,
            }
        )
    return out


@st.cache_data(show_spinner=False, ttl=45)
def _cached_prazos_list_all(owner_user_id: int, version: int) -> list[dict[str, Any]]:
    _ = version

    with get_session() as s:
        rows_all = PrazosService.list_all(s, owner_user_id, status="all")

    out: list[dict[str, Any]] = []
    for prazo, proc in rows_all:
        if prazo is None or proc is None:
            continue
        out.append(_pzproc_to_dict(prazo, proc))
    return out


# ============================================================
# NAVEGAÇÃO SEGURA
# ============================================================


def _request_tab(tab: str) -> None:
    st.session_state[KEY_NAV_TO] = tab


def _apply_requested_tab() -> None:
    legacy = st.session_state.pop("prazos_section", None)
    if legacy in ("Cadastrar", "Lista", "Editar / Excluir"):
        st.session_state[KEY_ACTIVE_TAB] = legacy

    nav = st.session_state.pop(KEY_NAV_TO, None)
    if nav in ("Cadastrar", "Lista", "Editar / Excluir"):
        st.session_state[KEY_ACTIVE_TAB] = nav

    st.session_state.setdefault(KEY_ACTIVE_TAB, "Cadastrar")


def _request_list_tab(tab: str) -> None:
    st.session_state[KEY_LIST_NAV_TO] = tab


def _apply_requested_list_tab() -> None:
    nav = st.session_state.pop(KEY_LIST_NAV_TO, None)
    if nav in ("Abertos", "Atrasados", "Vencem (7 dias)", "Concluídos"):
        st.session_state[KEY_LIST_ACTIVE] = nav

    st.session_state.setdefault(KEY_LIST_ACTIVE, "Abertos")


# ============================================================
# CONTEXTO DO TRABALHO
# ============================================================


def _chip(text: str) -> str:
    value = _safe_str(text)
    if not value:
        return ""
    return (
        "<span style='display:inline-block;padding:6px 10px;border-radius:999px;"
        "background:rgba(17,25,40,0.06);font-size:12px;font-weight:600;"
        "margin-right:6px;margin-bottom:6px;'>"
        f"{value}</span>"
    )


def _get_pref_context(proc_by_id: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return None

    try:
        pid = int(pref_id)
    except Exception:
        return None

    return proc_by_id.get(pid)


def _render_contexto_trabalho(proc: dict[str, Any] | None) -> None:
    if not proc:
        return

    numero = _safe_str(proc.get("numero_processo"))
    tipo_acao = _safe_str(proc.get("tipo_acao"))
    comarca = _safe_str(proc.get("comarca"))
    vara = _safe_str(proc.get("vara"))
    contratante = _safe_str(proc.get("contratante"))
    papel = _safe_str(proc.get("papel"))

    chips = []
    if numero:
        chips.append(_chip(f"📄 {numero}"))
    if tipo_acao:
        chips.append(_chip(f"🗂️ {tipo_acao}"))
    if papel:
        chips.append(_chip(f"⚖️ {papel}"))
    if comarca:
        chips.append(_chip(f"🏛 {comarca}"))
    if vara:
        chips.append(_chip(f"🏢 {vara}"))
    if contratante:
        chips.append(_chip(f"👤 {contratante}"))

    chips_html = " ".join([c for c in chips if c])

    _render_html(
        f"""
        <div style="
            border:1px solid rgba(49,51,63,0.12);
            border-radius:14px;
            padding:14px 16px;
            margin-bottom:12px;
            background:#fff;
        ">
            <div style="font-weight:800;font-size:1rem;margin-bottom:8px;">
                Contexto do trabalho
            </div>
            <div>{chips_html if chips_html else "<span class='pz-muted'>—</span>"}</div>
        </div>
        """
    )

    col_left, col_right = st.columns([0.82, 0.18], vertical_alignment="center")
    with col_right:
        if st.button("Limpar", key="pz_clear_pref_ctx", use_container_width=True):
            for key in ("pref_processo_id", "pref_processo_ref"):
                st.session_state.pop(key, None)
            st.rerun()


def _apply_pref_processo_defaults(
    proc_labels: list[str],
    label_to_id: dict[str, int],
) -> None:
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return

    try:
        pref_id = int(pref_id)
    except Exception:
        return

    chosen_label = None
    for label, pid in label_to_id.items():
        if int(pid) == pref_id:
            chosen_label = label
            break

    if not chosen_label:
        return

    st.session_state.setdefault(KEY_C_PROC, chosen_label)
    st.session_state.setdefault(KEY_FILTER_PROC, chosen_label)


# ============================================================
# HELPERS DE NEGÓCIO
# ============================================================


def _dias_restantes(dt_like: Any) -> int:
    dt_br = ensure_br(dt_like)
    hoje = now_br().date()
    return (dt_br.date() - hoje).days


def _semaforo(dias: int) -> str:
    if dias < 0:
        return "🔴 Atrasado"
    if dias <= 5:
        return "🟠 Urgente"
    if dias <= 10:
        return "🟡 Atenção"
    return "🟢 Ok"


def _proc_label_dict(p: dict[str, Any]) -> str:
    pid = int(p["id"])
    numero = str(p.get("numero_processo") or "")
    tipo = _safe_str(p.get("tipo_acao"))
    papel = _safe_str(p.get("papel"))

    label = f"[{pid}] {numero}"
    if tipo:
        label += f" – {tipo}"
    if papel:
        label += f"  •  {papel}"
    return label


def _filter_text(row: PrazoRow) -> str:
    parts = [
        row.processo_numero or "",
        row.processo_tipo_acao or "",
        row.processo_comarca or "",
        row.processo_vara or "",
        row.processo_contratante or "",
        row.processo_papel or "",
        row.evento or "",
        row.origem or "",
        row.referencia or "",
        row.observacoes or "",
    ]
    return " ".join(str(x) for x in parts).lower()


def _dicts_to_dataclass(items: list[dict[str, Any]]) -> list[PrazoRow]:
    out: list[PrazoRow] = []

    for item in items:
        prazo = item.get("prazo") or {}
        proc = item.get("proc") or {}

        out.append(
            PrazoRow(
                prazo_id=int(prazo.get("id") or 0),
                processo_id=int(proc.get("id") or 0),
                processo_numero=str(proc.get("numero_processo") or ""),
                processo_tipo_acao=proc.get("tipo_acao"),
                processo_comarca=proc.get("comarca"),
                processo_vara=proc.get("vara"),
                processo_contratante=proc.get("contratante"),
                processo_papel=proc.get("papel"),
                evento=str(prazo.get("evento") or ""),
                data_limite=prazo.get("data_limite"),
                prioridade=str(prazo.get("prioridade") or "Média"),
                concluido=bool(prazo.get("concluido") or False),
                origem=prazo.get("origem"),
                referencia=prazo.get("referencia"),
                observacoes=prazo.get("observacoes"),
            )
        )

    return out


def _build_df(items: list[PrazoRow], mode: str) -> pd.DataFrame | None:
    if not items:
        return None

    rows: list[dict[str, Any]] = []

    for item in items:
        dias = _dias_restantes(item.data_limite)
        dt_sort = ensure_br(item.data_limite)

        row: dict[str, Any] = {
            "prazo_id": int(item.prazo_id),
            "processo": f"{item.processo_numero} – {item.processo_tipo_acao or 'Sem tipo de ação'}",
            "evento": item.evento,
            "data_limite": format_date_br(item.data_limite),
            "prioridade": item.prioridade,
            "_data_sort": dt_sort,
        }

        if mode == "open":
            row["dias_restantes"] = int(dias)
            row["status"] = "✅ Concluído" if item.concluido else _semaforo(dias)

        rows.append(row)

    return pd.DataFrame(rows)


def _merge_obs_with_audit(obs: str | None, audit: str | None) -> str | None:
    base = _safe_str(obs)
    audit_txt = _safe_str(audit)

    if not base and not audit_txt:
        return None
    if base and not audit_txt:
        return base
    if not base and audit_txt:
        return f"🧮 {audit_txt}"
    return f"{base}\n🧮 {audit_txt}"


def _apply_lista_filters(
    rows: list[PrazoRow],
    *,
    tipo_val: str | None,
    processo_id_val: int | None,
    busca: str,
) -> list[PrazoRow]:
    filtered: list[PrazoRow] = []

    for row in rows:
        papel = _safe_str(row.processo_papel)

        if tipo_val and papel != tipo_val:
            continue
        if processo_id_val and int(row.processo_id) != int(processo_id_val):
            continue
        if busca and busca not in _filter_text(row):
            continue

        filtered.append(row)

    return filtered


def _split_status_groups(
    filtered: list[PrazoRow],
) -> tuple[list[PrazoRow], list[PrazoRow], list[PrazoRow], list[PrazoRow]]:
    abertos = [r for r in filtered if not r.concluido]
    atrasados = [
        r
        for r in filtered
        if (not r.concluido) and (_dias_restantes(r.data_limite) < 0)
    ]
    vencem7 = [
        r
        for r in filtered
        if (not r.concluido) and (0 <= _dias_restantes(r.data_limite) <= 7)
    ]
    concluidos = [r for r in filtered if r.concluido]
    return abertos, atrasados, vencem7, concluidos


# ============================================================
# UI DE TABELAS / KPIS
# ============================================================


def _render_df(df: pd.DataFrame, cols: list[str], height: int) -> None:
    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True,
        height=height,
    )


def _kpis_grid(abertos: int, atrasados: int, vencem7: int, concluidos: int) -> None:
    k1, k2 = st.columns(2)
    with k1:
        card("Abertos", f"{abertos}", "nos filtros", tone="info")
    with k2:
        card(
            "Atrasados",
            f"{atrasados}",
            "urgente",
            tone="danger" if atrasados else "neutral",
        )

    k3, k4 = st.columns(2)
    with k3:
        card(
            "Vencem (7d)",
            f"{vencem7}",
            "atenção",
            tone="warning" if vencem7 else "neutral",
        )
    with k4:
        card("Concluídos", f"{concluidos}", "finalizados", tone="neutral")


def _top_prioridades_hoje(filtered: list[PrazoRow]) -> None:
    atrasados = [
        row
        for row in filtered
        if (not row.concluido) and (_dias_restantes(row.data_limite) < 0)
    ]

    st.markdown("#### Prioridades de hoje")
    c_left, c_right = st.columns([0.62, 0.38], vertical_alignment="center")

    with c_right:
        if st.button(
            "Abrir atrasados",
            key="pz_btn_open_atrasados",
            use_container_width=True,
        ):
            _request_list_tab("Atrasados")
            st.rerun()

    with st.container(border=True):
        st.markdown("**Status de prazos**")
        st.caption("Acompanhe o que precisa de ação imediata.")
        if atrasados:
            st.markdown(f"🔴 **{len(atrasados)} prazo(s) atrasado(s)**")
        else:
            st.markdown("🟢 **Sem atrasos nos filtros atuais**")


# ============================================================
# AÇÕES RÁPIDAS / EDIÇÃO
# ============================================================


def _quick_actions(filtered_items: list[PrazoRow], owner_user_id: int) -> None:
    if not filtered_items:
        st.info("Nenhum prazo com os filtros atuais.")
        return

    options: list[str] = []
    id_by_label: dict[str, int] = {}

    ordered = sorted(
        filtered_items,
        key=lambda r: (
            r.concluido,
            _dias_restantes(r.data_limite),
            _priority_rank(r.prioridade),
            ensure_br(r.data_limite),
        ),
    )

    for row in ordered:
        label = _prazo_option_label(row)
        options.append(label)
        id_by_label[label] = int(row.prazo_id)

    st.caption("Ações aplicadas ao prazo selecionado.")

    selected = st.selectbox("Selecione um prazo", options, key=KEY_QUICK_SELECT)
    prazo_id = id_by_label[selected]

    selected_row = next((r for r in ordered if int(r.prazo_id) == int(prazo_id)), None)
    if not selected_row:
        st.info("Prazo não encontrado.")
        return

    dias = _dias_restantes(selected_row.data_limite)
    status_txt = _status_label(dias, selected_row.concluido)

    meta_cols = st.columns(4)
    with meta_cols[0]:
        card("Status", status_txt, "situação atual", tone="neutral")
    with meta_cols[1]:
        card(
            "Data",
            format_date_br(selected_row.data_limite),
            "vencimento",
            tone="neutral",
        )
    with meta_cols[2]:
        card("Prioridade", selected_row.prioridade, "nível operacional", tone="neutral")
    with meta_cols[3]:
        if dias < 0:
            sub = f"{abs(dias)} dia(s) em atraso"
            tone = "danger"
        elif dias == 0:
            sub = "vence hoje"
            tone = "warning"
        else:
            sub = f"{dias} dia(s) restantes"
            tone = "info"
        card("Prazo", sub, "janela temporal", tone=tone)

    c1, c2, c3 = st.columns(3)

    if c1.button("✅ Concluir", key="pz_quick_done", use_container_width=True):
        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(concluido=True),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo concluído.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao concluir: {e}")

    if c2.button("♻️ Reabrir", key="pz_quick_reopen", use_container_width=True):
        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(concluido=False),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo reaberto.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao reabrir: {e}")

    with c3:
        st.number_input(
            "Adiar (dias)",
            min_value=1,
            max_value=365,
            step=1,
            key=KEY_QUICK_DELAY_DAYS,
        )
        if st.button("↪️ Adiar", key="pz_quick_delay", use_container_width=True):
            try:
                add_days = int(st.session_state.get(KEY_QUICK_DELAY_DAYS, 1) or 1)
                nova_data = ensure_br(selected_row.data_limite).date() + timedelta(
                    days=add_days
                )

                with get_session() as s:
                    PrazosService.update(
                        s,
                        owner_user_id,
                        int(prazo_id),
                        PrazoUpdate(data_limite=date_to_br_datetime(nova_data)),
                    )
                bump_data_version(owner_user_id)
                st.success("Prazo reagendado.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao reagendar: {e}")

    with st.expander("Zona sensível", expanded=False):
        st.caption("Exclusão definitiva do prazo selecionado.")
        confirm = st.checkbox("Confirmo a exclusão", key=KEY_QUICK_CONFIRM_DELETE)
        if st.button(
            "🗑️ Excluir prazo",
            key="pz_quick_del",
            use_container_width=True,
            disabled=not confirm,
        ):
            try:
                with get_session() as s:
                    PrazosService.delete(s, owner_user_id, int(prazo_id))
                bump_data_version(owner_user_id)
                st.warning("Prazo excluído.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


def _editar_excluir_prazo(items: list[PrazoRow], owner_user_id: int) -> None:
    if not items:
        st.info("Nenhum prazo disponível para editar.")
        return

    options: list[str] = []
    id_by_label: dict[str, int] = {}

    for row in items:
        dias = _dias_restantes(row.data_limite)
        status = "✅ Concluído" if row.concluido else _semaforo(dias)
        label = (
            f"[{row.prazo_id}] {row.processo_numero} — "
            f"{row.evento} — {format_date_br(row.data_limite)} — {status}"
        )
        options.append(label)
        id_by_label[label] = int(row.prazo_id)

    selected = st.selectbox(
        "Selecione um prazo para editar",
        options,
        key="pz_edit_select",
    )
    prazo_id = id_by_label[selected]

    with get_session() as s:
        pz = PrazosService.get(s, owner_user_id, int(prazo_id))

    if not pz:
        st.error("Prazo não encontrado.")
        return

    try:
        pz_date = ensure_br(pz.data_limite).date()
    except Exception:
        pz_date = now_br().date()

    with st.form(f"form_prazo_edit_{prazo_id}"):
        c1, c2, c3 = st.columns(3)
        evento_e = c1.text_input("Evento *", value=str(getattr(pz, "evento", "") or ""))
        data_e = c2.date_input("Data limite *", value=pz_date)
        prio_e = c3.selectbox(
            "Prioridade",
            list(PRIORIDADES),
            index=(
                list(PRIORIDADES).index(pz.prioridade)
                if pz.prioridade in PRIORIDADES
                else 1
            ),
        )

        c4, c5 = st.columns(2)
        origem_e = c4.text_input("Origem", value=str(getattr(pz, "origem", "") or ""))
        referencia_e = c5.text_input(
            "Referência",
            value=str(getattr(pz, "referencia", "") or ""),
        )

        concl = st.checkbox("Concluído", value=bool(getattr(pz, "concluido", False)))
        obs_e = st.text_area(
            "Observações",
            value=str(getattr(pz, "observacoes", "") or ""),
        )

        b1, b2 = st.columns(2)
        salvar = b1.form_submit_button(
            "Salvar alterações",
            type="primary",
            use_container_width=True,
        )
        excluir = b2.form_submit_button(
            "Excluir (irreversível)",
            use_container_width=True,
        )

    if salvar:
        if not _safe_str(evento_e):
            st.error("Evento não pode ficar vazio.")
            return

        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(
                        evento=_safe_str(evento_e),
                        data_limite=date_to_br_datetime(data_e),
                        prioridade=prio_e,
                        concluido=concl,
                        origem=_norm(origem_e),
                        referencia=_norm(referencia_e),
                        observacoes=_norm(obs_e),
                    ),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo atualizado.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    if excluir:
        try:
            with get_session() as s:
                PrazosService.delete(s, owner_user_id, int(prazo_id))
            bump_data_version(owner_user_id)
            st.warning("Prazo excluído.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")


# ============================================================
# CADASTRO
# ============================================================


def _render_cadastro(
    *,
    owner_user_id: int,
    proc_labels: list[str],
    label_to_id: dict[str, int],
    proc_by_id: dict[int, dict[str, Any]],
) -> None:
    with st.container(border=True):
        _section_card(
            "Novo prazo",
            "Escolha o modo de contagem, confira a data final e salve.",
        )
        subtle_divider()

        sel_proc = st.selectbox("Trabalho *", proc_labels, index=0, key=KEY_C_PROC)
        processo_id = int(label_to_id[sel_proc])
        proc = proc_by_id.get(processo_id)
        comarca_proc = (_safe_str(proc.get("comarca")) or None) if proc else None

        st.markdown("**1) Modo de contagem**")
        modo = st.selectbox(
            "Modo",
            ["Manual", "Dias corridos", "Dias úteis"],
            key=KEY_C_MODE,
        )

        subtle_divider()
        st.markdown("**2) Base e cálculo**")

        if modo == "Manual":
            st.date_input("Data limite *", key=KEY_C_DATA_LIM)
            st.session_state[KEY_C_AUDIT] = ""

        elif modo == "Dias corridos":
            c1, c2 = st.columns(2)
            base = c1.date_input("Data base", key=KEY_C_BASE)
            dias = c2.number_input("Qtd dias", min_value=1, step=1, key=KEY_C_DIAS)

            nova = base + timedelta(days=int(dias))
            st.session_state[KEY_C_DATA_LIM] = nova
            st.session_state[KEY_C_AUDIT] = "Auto: dias corridos"

            card(
                "Data final",
                nova.strftime("%d/%m/%Y"),
                f"Base: {base.strftime('%d/%m/%Y')} • +{int(dias)} dia(s)",
                tone="info",
            )

        else:
            c1, c2 = st.columns(2)
            base = c1.date_input("Data base (disponibilização DJE)", key=KEY_C_BASE)
            dias = c2.number_input(
                "Qtd dias úteis",
                min_value=1,
                step=1,
                key=KEY_C_DIAS,
            )

            usar_tjsp = st.checkbox(
                "Considerar calendário TJSP (inclui CPC art. 220 automaticamente)",
                key=KEY_C_USAR_TJSP,
            )

            incluir_municipal = st.checkbox(
                "Incluir feriados municipais da comarca",
                key=KEY_C_LOCAL,
                disabled=not bool(comarca_proc),
                help="Requer 'Comarca' preenchida no trabalho.",
            )

            regras = RegrasCalendario(
                incluir_nacional=True,
                incluir_estadual_sp=True,
                incluir_tjsp_geral=bool(usar_tjsp),
                incluir_tjsp_comarca=bool(usar_tjsp),
                incluir_municipal=bool(incluir_municipal),
            )

            aplicar_local = bool(comarca_proc)

            nova = CalendarioService.prazo_dje_tjsp(
                disponibilizacao=base,
                dias_uteis=int(dias),
                comarca=comarca_proc,
                municipio=None,
                aplicar_local=aplicar_local,
                regras=regras,
            )

            st.session_state[KEY_C_DATA_LIM] = nova

            if usar_tjsp:
                if incluir_municipal and bool(comarca_proc):
                    st.session_state[KEY_C_AUDIT] = (
                        f"Auto: DJE + dias úteis (TJSP/CPC220 + municipal {comarca_proc})"
                    )
                else:
                    st.session_state[KEY_C_AUDIT] = (
                        "Auto: DJE + dias úteis (TJSP/CPC220)"
                    )
            else:
                if incluir_municipal and bool(comarca_proc):
                    st.session_state[KEY_C_AUDIT] = (
                        f"Auto: DJE + dias úteis (Nac/Estadual + municipal {comarca_proc})"
                    )
                else:
                    st.session_state[KEY_C_AUDIT] = (
                        "Auto: DJE + dias úteis (Nac/Estadual)"
                    )

            card(
                "Data final",
                nova.strftime("%d/%m/%Y"),
                f"Base: {base.strftime('%d/%m/%Y')} • {int(dias)} dia(s) úteis"
                + (
                    f" • Comarca: {comarca_proc}"
                    if (incluir_municipal and comarca_proc)
                    else ""
                ),
                tone="info",
            )

            if DEBUG_PRAZOS:
                from datetime import date as _date

                st.markdown("### 🔎 DEBUG PRAZO")
                st.write("comarca_proc:", repr(comarca_proc))
                st.write("aplicar_local:", aplicar_local)
                st.write("incluir_municipal:", bool(incluir_municipal))
                st.write("usar_tjsp:", bool(usar_tjsp))
                st.write("base:", base)
                st.write("dias:", int(dias))
                st.write("nova:", nova)

                ini = _date(2026, 1, 15)
                fim = _date(2026, 2, 15)
                fer_set = CalendarioService.feriados_aplicaveis(
                    ini,
                    fim,
                    comarca=comarca_proc,
                    municipio=None,
                    aplicar_local=aplicar_local,
                    regras=regras,
                )
                st.write("contém 02/02/2026?:", _date(2026, 2, 2) in fer_set)
                st.write("feriados janela:", sorted(list(fer_set)))

        subtle_divider()
        st.markdown("**3) Detalhes do prazo**")

        with st.form("form_prazo_create", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)

            evento = c1.text_input("Evento *", key=KEY_C_EVENTO)
            prioridade = c2.selectbox(
                "Prioridade",
                list(PRIORIDADES),
                index=1,
                key=KEY_C_PRIO,
            )
            origem = c3.selectbox(
                "Origem (opcional)",
                [
                    "",
                    "e-SAJ/TJ",
                    "Diário Oficial",
                    "E-mail",
                    "Cliente/Contratante",
                    "Outro",
                ],
                index=0,
                key=KEY_C_ORIGEM,
            )

            referencia = st.text_input(
                "Referência (opcional)",
                placeholder="Ex.: fls. 389 / ID 12345 / mov. 12.1",
                key=KEY_C_REF,
            )
            obs = st.text_area("Observações", key=KEY_C_OBS)

            salvar = st.form_submit_button(
                "Salvar",
                type="primary",
                use_container_width=True,
            )

        if salvar:
            if not _safe_str(evento):
                st.error("Informe o evento.")
                return

            try:
                data_final = st.session_state.get(KEY_C_DATA_LIM, now_br().date())
                dt_lim = date_to_br_datetime(data_final)

                audit_txt = _safe_str(st.session_state.get(KEY_C_AUDIT))
                obs_final = _merge_obs_with_audit(obs, audit_txt)

                with get_session() as s:
                    PrazosService.create(
                        s,
                        owner_user_id,
                        PrazoCreate(
                            processo_id=int(processo_id),
                            evento=_safe_str(evento),
                            data_limite=dt_lim,
                            prioridade=prioridade,
                            origem=(origem or None),
                            referencia=_norm(referencia),
                            observacoes=obs_final,
                        ),
                    )

                bump_data_version(owner_user_id)
                st.success("Prazo criado com sucesso.")
                _request_tab("Lista")
                _request_list_tab("Abertos")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao criar prazo: {e}")


# ============================================================
# LISTA
# ============================================================
def _render_lista_topbar() -> None:
    c1, c2 = st.columns([0.72, 0.28], vertical_alignment="center")

    with c1:
        st.markdown("#### Operação de prazos")
        st.caption(
            "Comece pelos itens mais críticos e depois refine a fila com os filtros."
        )

    with c2:
        if st.button(
            "➕ Novo prazo",
            key="pz_go_create_top",
            use_container_width=True,
            type="primary",
        ):
            _request_tab("Cadastrar")
            st.rerun()


def _render_lista(
    *,
    owner_user_id: int,
    proc_labels: list[str],
    label_to_id: dict[str, int],
) -> None:
    _apply_requested_list_tab()

    version = _data_version(owner_user_id)
    all_rows = _dicts_to_dataclass(_cached_prazos_list_all(owner_user_id, version))

    tipo_val = None
    processo_id_val = None
    prioridade_val = None
    origem_val = None
    busca = ""

    filtered_base = _apply_lista_filters(
        all_rows,
        tipo_val=tipo_val,
        processo_id_val=processo_id_val,
        prioridade_val=prioridade_val,
        origem_val=origem_val,
        busca=busca,
    )

    abertos_base, hoje_base, atrasados_base, vencem7_base, concluidos_base = (
        _split_status_groups(filtered_base)
    )

    _render_lista_topbar()

    _render_summary_kpis(
        abertos=len(abertos_base),
        hoje=len(hoje_base),
        atrasados=len(atrasados_base),
        vencem7=len(vencem7_base),
        concluidos=len(concluidos_base),
    )

    with st.container(border=True):
        _render_priority_queue(filtered_base)

    filtro_tipo, filtro_proc, filtro_prio, filtro_origem, busca = _render_filtros_lista(
        proc_labels
    )

    tipo_val = None if filtro_tipo == "(Todos)" else filtro_tipo
    processo_id_val = (
        None if filtro_proc == "(Todos)" else int(label_to_id[filtro_proc])
    )
    prioridade_val = None if filtro_prio == "(Todas)" else filtro_prio
    origem_val = None if filtro_origem == "(Todas)" else filtro_origem

    filtered = _apply_lista_filters(
        all_rows,
        tipo_val=tipo_val,
        processo_id_val=processo_id_val,
        prioridade_val=prioridade_val,
        origem_val=origem_val,
        busca=busca,
    )

    abertos, hoje, atrasados, vencem7, concluidos = _split_status_groups(filtered)

    with st.container(border=True):
        _section_card(
            "⚡ Ações rápidas", "Resolva operações frequentes sem sair da fila."
        )
        _quick_actions(filtered, owner_user_id)

    subtle_divider()
    chosen_view = _list_tabs_selector()

    if chosen_view == "Atrasados":
        items = sorted(
            atrasados,
            key=lambda r: (
                _dias_restantes(r.data_limite),
                _priority_rank(r.prioridade),
                ensure_br(r.data_limite),
            ),
        )
        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo atrasado com os filtros atuais.")
            return

        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[True, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=380,
        )
        return

    if chosen_view == "Hoje":
        items = sorted(
            hoje,
            key=lambda r: (
                _priority_rank(r.prioridade),
                ensure_br(r.data_limite),
                -int(r.prazo_id),
            ),
        )
        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo vencendo hoje com os filtros atuais.")
            return

        df = df.sort_values(by=["_sort_dt"], ascending=[True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "prioridade",
                "origem",
                "status",
            ],
            height=340,
        )
        return

    if chosen_view == "Vencem (7 dias)":
        items = sorted(
            vencem7,
            key=lambda r: (
                _dias_restantes(r.data_limite),
                _priority_rank(r.prioridade),
                ensure_br(r.data_limite),
            ),
        )
        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo vencendo em até 7 dias com os filtros atuais.")
            return

        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[True, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=380,
        )
        return

    if chosen_view == "Abertos":
        filtro_janela, ordem = _render_open_controls()
        items = _filter_open_window(filtered, filtro_janela)

        reverse_days = ordem == "Mais distantes primeiro"
        items = _sort_operational(items, reverse_days=reverse_days)

        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo aberto com os filtros atuais.")
            return

        asc = ordem == "Mais urgentes primeiro"
        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[asc, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=460,
        )
        return

    items = sorted(concluidos, key=lambda r: ensure_br(r.data_limite), reverse=True)
    df = _build_df(items, include_status=False)
    if df is None:
        st.info("Nenhum prazo concluído com os filtros atuais.")
        return

    df = df.sort_values(by=["_sort_dt"], ascending=False).drop(
        columns=["_sort_dt"], errors="ignore"
    )
    _render_df(
        df,
        ["prazo_id", "processo", "evento", "data_limite", "prioridade", "origem"],
        height=380,
    )


# ============================================================
# EDITAR
# ============================================================


def _render_editar(owner_user_id: int) -> None:
    with st.container(border=True):
        _section_card(
            "Editar / Excluir",
            "Selecione um prazo e ajuste os campos necessários.",
        )

        version = _data_version(owner_user_id)
        all_rows = _dicts_to_dataclass(_cached_prazos_list_all(owner_user_id, version))
        _editar_excluir_prazo(all_rows, owner_user_id)


# ============================================================
# RENDER PRINCIPAL
# ============================================================


def render(owner_user_id: int) -> None:
    st.session_state[KEY_OWNER] = owner_user_id

    clicked_refresh = page_header(
        "Prazos",
        "Cadastro, filtros e controle de prazos (judicial e extrajudicial).",
        right_button_label="Recarregar",
        right_button_key="pz_btn_recarregar",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked_refresh:
        st.rerun()

    with st.expander("Ferramentas", expanded=False):
        st.caption("Utilidades da tela.")
        if st.button(
            "Limpar cache de feriados",
            key="pz_btn_clear_cache",
            type="secondary",
        ):
            CalendarioService.clear_cache()
            st.success("Cache de feriados limpo.")
            st.rerun()

    version = _data_version(owner_user_id)
    processos = _cached_processos(owner_user_id, version)

    if not processos:
        st.info("Cadastre um trabalho primeiro.")
        return

    proc_labels = [_proc_label_dict(p) for p in processos]
    label_to_id = {
        proc_labels[i]: int(processos[i]["id"]) for i in range(len(processos))
    }
    proc_by_id = {int(p["id"]): p for p in processos}

    pref_proc = _get_pref_context(proc_by_id)
    _render_contexto_trabalho(pref_proc)

    hoje_sp = now_br().date()
    st.session_state.setdefault(KEY_C_MODE, "Manual")
    st.session_state.setdefault(KEY_C_DATA_LIM, hoje_sp)
    st.session_state.setdefault(KEY_C_AUDIT, "")
    st.session_state.setdefault(KEY_C_BASE, hoje_sp)
    st.session_state.setdefault(KEY_C_DIAS, 15)
    st.session_state.setdefault(KEY_C_USAR_TJSP, True)
    st.session_state.setdefault(KEY_C_LOCAL, True)
    st.session_state.setdefault(KEY_C_PROC, proc_labels[0] if proc_labels else "")

    _apply_pref_processo_defaults(proc_labels, label_to_id)
    _apply_requested_tab()

    with st.container(border=True):
        section = _section_tabs(KEY_ACTIVE_TAB)

    if section == "Cadastrar":
        _render_cadastro(
            owner_user_id=owner_user_id,
            proc_labels=proc_labels,
            label_to_id=label_to_id,
            proc_by_id=proc_by_id,
        )
    elif section == "Lista":
        _render_lista(
            owner_user_id=owner_user_id,
            proc_labels=proc_labels,
            label_to_id=label_to_id,
        )
    else:
        _render_editar(owner_user_id)


from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from db.connection import get_session
from db.models import Processo
from services.calendario_service import CalendarioService, RegrasCalendario
from services.prazos_service import PrazoCreate, PrazoUpdate, PrazosService
from services.utils import date_to_br_datetime, ensure_br, format_date_br, now_br
from ui.page_header import page_header
from ui.theme import card, subtle_divider
from ui_state import bump_data_version, get_data_version


# ============================================================
# CONFIG
# ============================================================

DEBUG_PRAZOS = False


# ============================================================
# CONSTANTES
# ============================================================

TIPOS_TRABALHO = (
    "Perito Judicial",
    "Assistente Técnico",
    "Trabalho Particular",
)

PRIORIDADES = ("Baixa", "Média", "Alta")

ORIGENS = (
    "",
    "e-SAJ/TJ",
    "Diário Oficial",
    "E-mail",
    "Cliente/Contratante",
    "Outro",
)

KEY_OWNER = "owner_user_id"

KEY_ACTIVE_TAB = "pz_active_tab"
KEY_NAV_TO = "pz_nav_to"

KEY_LIST_ACTIVE = "pz_list_active"
KEY_LIST_NAV_TO = "pz_list_nav_to"

KEY_C_PROC = "pz_create_proc"
KEY_C_MODE = "pz_create_mode"
KEY_C_BASE = "pz_create_base"
KEY_C_DIAS = "pz_create_dias"
KEY_C_USAR_TJSP = "pz_create_usar_tjsp"
KEY_C_LOCAL = "pz_create_local"
KEY_C_DATA_LIM = "pz_create_data_lim"
KEY_C_AUDIT = "pz_create_audit"
KEY_C_EVENTO = "pz_create_evento"
KEY_C_PRIO = "pz_create_prio"
KEY_C_ORIGEM = "pz_create_origem"
KEY_C_REF = "pz_create_ref"
KEY_C_OBS = "pz_create_obs"

KEY_FILTER_TIPO = "pz_filter_tipo_trabalho"
KEY_FILTER_PROC = "pz_filter_proc_global"
KEY_FILTER_BUSCA = "pz_filter_busca_global"
KEY_FILTER_PRIO = "pz_filter_prioridade"
KEY_FILTER_ORIGEM = "pz_filter_origem"

KEY_OPEN_WINDOW = "pz_open_window"
KEY_OPEN_ORDER = "pz_open_order"

KEY_QUICK_SELECT = "pz_quick_select"
KEY_QUICK_DELAY_DAYS = "pz_quick_delay_days"
KEY_QUICK_CONFIRM_DELETE = "pz_quick_confirm_delete"


# ============================================================
# TIPOS AUXILIARES
# ============================================================


@dataclass(frozen=True)
class PrazoRow:
    prazo_id: int
    processo_id: int
    processo_numero: str
    processo_tipo_acao: str | None
    processo_comarca: str | None
    processo_vara: str | None
    processo_contratante: str | None
    processo_papel: str | None

    evento: str
    data_limite: Any
    prioridade: str
    concluido: bool
    origem: str | None
    referencia: str | None
    observacoes: str | None


# ============================================================
# RENDER / ESTILO
# ============================================================


def _render_html(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: str | None) -> str | None:
    text = _safe_str(value)
    return text or None


def _section_card(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def _inject_segmented_radio_css() -> None:
    _render_html(
        """
        <style>
        div[data-testid="stRadio"] > div {
            flex-direction: row !important;
            gap: 8px !important;
            flex-wrap: wrap !important;
        }

        div[data-testid="stRadio"] label {
            border: 1px solid rgba(49, 51, 63, 0.18);
            padding: 8px 12px;
            border-radius: 10px;
            background: #ffffff;
            margin: 0 !important;
        }

        div[data-testid="stRadio"] label:hover {
            border-color: rgba(49, 51, 63, 0.38);
        }

        div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        div[data-testid="stRadio"] label span {
            font-size: 12px;
            font-weight: 700;
        }

        div[data-testid="stRadio"] input:checked + div {
            background: rgba(17, 25, 40, 0.06) !important;
            border-radius: 8px !important;
        }

        .pz-muted {
            color: rgba(49, 51, 63, 0.75);
            font-size: 0.92rem;
        }

        .pz-priority-card {
            border: 1px solid rgba(49,51,63,0.12);
            border-left: 5px solid rgba(17,25,40,0.18);
            border-radius: 14px;
            padding: 12px 14px;
            background: #fff;
            margin-bottom: 10px;
        }

        .pz-priority-card.is-overdue {
            border-left-color: #c62828;
            background: rgba(198,40,40,0.03);
        }

        .pz-priority-card.is-today {
            border-left-color: #ef6c00;
            background: rgba(239,108,0,0.04);
        }

        .pz-priority-card.is-soon {
            border-left-color: #f9a825;
            background: rgba(249,168,37,0.05);
        }

        .pz-meta {
            color: rgba(49, 51, 63, 0.78);
            font-size: 0.90rem;
        }

        .pz-badge {
            display: inline-block;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            margin-right: 6px;
            margin-bottom: 6px;
            background: rgba(17,25,40,0.06);
        }
        </style>
        """
    )


def _section_tabs(key: str) -> str:
    options = ["Cadastrar", "Lista", "Editar / Excluir"]

    if hasattr(st, "segmented_control"):
        return st.segmented_control(
            "Seção",
            options,
            key=key,
            label_visibility="collapsed",
        )

    _inject_segmented_radio_css()
    return st.radio(
        "Seção",
        options,
        horizontal=True,
        label_visibility="collapsed",
        key=key,
    )


def _list_tabs_selector() -> str:
    labels = [
        "📋 Abertos",
        "📅 Hoje",
        "🔴 Atrasados",
        "🟠 7 dias",
        "✅ Concluídos",
    ]
    label_to_value = {
        "📋 Abertos": "Abertos",
        "📅 Hoje": "Hoje",
        "🔴 Atrasados": "Atrasados",
        "🟠 7 dias": "Vencem (7 dias)",
        "✅ Concluídos": "Concluídos",
    }
    value_to_label = {v: k for k, v in label_to_value.items()}

    current_value = st.session_state.get(KEY_LIST_ACTIVE, "Abertos")
    default_label = value_to_label.get(current_value, "📋 Abertos")
    st.session_state.setdefault("pz_list_selector", default_label)

    if hasattr(st, "segmented_control"):
        chosen_label = st.segmented_control(
            "Visão",
            labels,
            key="pz_list_selector",
            label_visibility="collapsed",
        )
    else:
        _inject_segmented_radio_css()
        chosen_label = st.radio(
            "Visão",
            labels,
            horizontal=True,
            key="pz_list_selector",
            label_visibility="collapsed",
            index=labels.index(st.session_state.get("pz_list_selector", default_label)),
        )

    chosen_value = label_to_value.get(chosen_label, "Abertos")
    st.session_state[KEY_LIST_ACTIVE] = chosen_value
    return chosen_value


# ============================================================
# DATA VERSION / CACHE
# ============================================================


def _data_version(owner_user_id: int) -> int:
    return get_data_version(owner_user_id)


def _pzproc_to_dict(prazo: Any, proc: Any) -> dict[str, Any]:
    return {
        "prazo": {
            "id": int(getattr(prazo, "id", 0) or 0),
            "evento": str(getattr(prazo, "evento", "") or ""),
            "data_limite": getattr(prazo, "data_limite", None),
            "prioridade": str(getattr(prazo, "prioridade", "Média") or "Média"),
            "concluido": bool(getattr(prazo, "concluido", False)),
            "origem": getattr(prazo, "origem", None),
            "referencia": getattr(prazo, "referencia", None),
            "observacoes": getattr(prazo, "observacoes", None),
            "processo_id": int(getattr(prazo, "processo_id", 0) or 0),
        },
        "proc": {
            "id": int(getattr(proc, "id", 0) or 0),
            "numero_processo": str(getattr(proc, "numero_processo", "") or ""),
            "tipo_acao": getattr(proc, "tipo_acao", None),
            "comarca": getattr(proc, "comarca", None),
            "vara": getattr(proc, "vara", None),
            "contratante": getattr(proc, "contratante", None),
            "papel": getattr(proc, "papel", None),
        },
    }


@st.cache_data(show_spinner=False, ttl=45)
def _cached_processos(owner_user_id: int, version: int) -> list[dict[str, Any]]:
    _ = version

    with get_session() as s:
        procs = (
            s.execute(
                select(Processo)
                .where(Processo.owner_user_id == owner_user_id)
                .order_by(Processo.id.desc())
            )
            .scalars()
            .all()
        )

    out: list[dict[str, Any]] = []
    for p in procs:
        out.append(
            {
                "id": int(p.id),
                "numero_processo": str(p.numero_processo or ""),
                "tipo_acao": p.tipo_acao,
                "comarca": p.comarca,
                "vara": p.vara,
                "contratante": p.contratante,
                "papel": p.papel,
            }
        )
    return out


@st.cache_data(show_spinner=False, ttl=45)
def _cached_prazos_list_all(owner_user_id: int, version: int) -> list[dict[str, Any]]:
    _ = version

    with get_session() as s:
        rows_all = PrazosService.list_all(s, owner_user_id, status="all")

    out: list[dict[str, Any]] = []
    for prazo, proc in rows_all:
        if prazo is None or proc is None:
            continue
        out.append(_pzproc_to_dict(prazo, proc))
    return out


# ============================================================
# NAVEGAÇÃO SEGURA
# ============================================================


def _request_tab(tab: str) -> None:
    st.session_state[KEY_NAV_TO] = tab


def _apply_requested_tab() -> None:
    legacy = st.session_state.pop("prazos_section", None)
    if legacy in ("Cadastrar", "Lista", "Editar / Excluir"):
        st.session_state[KEY_ACTIVE_TAB] = legacy

    nav = st.session_state.pop(KEY_NAV_TO, None)
    if nav in ("Cadastrar", "Lista", "Editar / Excluir"):
        st.session_state[KEY_ACTIVE_TAB] = nav

    st.session_state.setdefault(KEY_ACTIVE_TAB, "Cadastrar")


def _request_list_tab(tab: str) -> None:
    st.session_state[KEY_LIST_NAV_TO] = tab


def _apply_requested_list_tab() -> None:
    nav = st.session_state.pop(KEY_LIST_NAV_TO, None)
    if nav in ("Abertos", "Hoje", "Atrasados", "Vencem (7 dias)", "Concluídos"):
        st.session_state[KEY_LIST_ACTIVE] = nav

    st.session_state.setdefault(KEY_LIST_ACTIVE, "Abertos")


# ============================================================
# CONTEXTO DO TRABALHO
# ============================================================


def _chip(text: str) -> str:
    value = _safe_str(text)
    if not value:
        return ""
    return (
        "<span style='display:inline-block;padding:6px 10px;border-radius:999px;"
        "background:rgba(17,25,40,0.06);font-size:12px;font-weight:700;"
        "margin-right:6px;margin-bottom:6px;'>"
        f"{value}</span>"
    )


def _get_pref_context(proc_by_id: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return None

    try:
        pid = int(pref_id)
    except Exception:
        return None

    return proc_by_id.get(pid)


def _count_proc_open_metrics(
    proc_id: int, rows: list["PrazoRow"]
) -> tuple[int, int, str | None]:
    abertos = [r for r in rows if r.processo_id == proc_id and not r.concluido]
    atrasados = [r for r in abertos if _dias_restantes(r.data_limite) < 0]
    proximos = sorted(abertos, key=lambda r: ensure_br(r.data_limite))

    prox_txt = format_date_br(proximos[0].data_limite) if proximos else None
    return len(abertos), len(atrasados), prox_txt


def _render_contexto_trabalho(
    proc: dict[str, Any] | None, all_rows: list["PrazoRow"]
) -> None:
    if not proc:
        return

    numero = _safe_str(proc.get("numero_processo"))
    tipo_acao = _safe_str(proc.get("tipo_acao"))
    comarca = _safe_str(proc.get("comarca"))
    vara = _safe_str(proc.get("vara"))
    contratante = _safe_str(proc.get("contratante"))
    papel = _safe_str(proc.get("papel"))
    proc_id = int(proc.get("id") or 0)

    chips = []
    if numero:
        chips.append(_chip(f"📄 {numero}"))
    if tipo_acao:
        chips.append(_chip(f"🗂️ {tipo_acao}"))
    if papel:
        chips.append(_chip(f"⚖️ {papel}"))
    if comarca:
        chips.append(_chip(f"🏛 {comarca}"))
    if vara:
        chips.append(_chip(f"🏢 {vara}"))
    if contratante:
        chips.append(_chip(f"👤 {contratante}"))

    abertos, atrasados, prox_txt = _count_proc_open_metrics(proc_id, all_rows)
    if abertos:
        chips.append(_chip(f"📋 {abertos} abertos"))
    if atrasados:
        chips.append(_chip(f"🔴 {atrasados} atrasados"))
    if prox_txt:
        chips.append(_chip(f"📅 Próximo: {prox_txt}"))

    chips_html = " ".join([c for c in chips if c])

    _render_html(
        f"""
        <div style="
            border:1px solid rgba(49,51,63,0.12);
            border-radius:14px;
            padding:14px 16px;
            margin-bottom:12px;
            background:#fff;
        ">
            <div style="font-weight:800;font-size:1rem;margin-bottom:8px;">
                Contexto do trabalho
            </div>
            <div>{chips_html if chips_html else "<span class='pz-muted'>—</span>"}</div>
        </div>
        """
    )

    _, col_right = st.columns([0.82, 0.18], vertical_alignment="center")
    with col_right:
        if st.button("Limpar", key="pz_clear_pref_ctx", use_container_width=True):
            for key in ("pref_processo_id", "pref_processo_ref"):
                st.session_state.pop(key, None)
            st.rerun()


def _apply_pref_processo_defaults(
    proc_labels: list[str],
    label_to_id: dict[str, int],
) -> None:
    pref_id = st.session_state.get("pref_processo_id")
    if not pref_id:
        return

    try:
        pref_id = int(pref_id)
    except Exception:
        return

    chosen_label = None
    for label, pid in label_to_id.items():
        if int(pid) == pref_id:
            chosen_label = label
            break

    if not chosen_label:
        return

    st.session_state.setdefault(KEY_C_PROC, chosen_label)
    st.session_state.setdefault(KEY_FILTER_PROC, chosen_label)


# ============================================================
# HELPERS DE NEGÓCIO
# ============================================================


def _dias_restantes(dt_like: Any) -> int:
    dt_br = ensure_br(dt_like)
    hoje = now_br().date()
    return (dt_br.date() - hoje).days


def _status_label(dias: int, concluido: bool) -> str:
    if concluido:
        return "✅ Concluído"
    if dias < 0:
        return "🔴 Atrasado"
    if dias == 0:
        return "📅 Hoje"
    if dias <= 5:
        return "🟠 Urgente"
    if dias <= 10:
        return "🟡 Atenção"
    return "🟢 Planejado"


def _priority_rank(prioridade: str) -> int:
    order = {"Alta": 0, "Média": 1, "Baixa": 2}
    return order.get(prioridade, 1)


def _proc_label_dict(p: dict[str, Any]) -> str:
    pid = int(p["id"])
    numero = str(p.get("numero_processo") or "")
    tipo = _safe_str(p.get("tipo_acao"))
    papel = _safe_str(p.get("papel"))

    label = f"[{pid}] {numero}"
    if tipo:
        label += f" – {tipo}"
    if papel:
        label += f"  •  {papel}"
    return label


def _filter_text(row: PrazoRow) -> str:
    parts = [
        row.processo_numero or "",
        row.processo_tipo_acao or "",
        row.processo_comarca or "",
        row.processo_vara or "",
        row.processo_contratante or "",
        row.processo_papel or "",
        row.evento or "",
        row.origem or "",
        row.referencia or "",
        row.observacoes or "",
        row.prioridade or "",
    ]
    return " ".join(str(x) for x in parts).lower()


def _dicts_to_dataclass(items: list[dict[str, Any]]) -> list[PrazoRow]:
    out: list[PrazoRow] = []

    for item in items:
        prazo = item.get("prazo") or {}
        proc = item.get("proc") or {}

        out.append(
            PrazoRow(
                prazo_id=int(prazo.get("id") or 0),
                processo_id=int(proc.get("id") or 0),
                processo_numero=str(proc.get("numero_processo") or ""),
                processo_tipo_acao=proc.get("tipo_acao"),
                processo_comarca=proc.get("comarca"),
                processo_vara=proc.get("vara"),
                processo_contratante=proc.get("contratante"),
                processo_papel=proc.get("papel"),
                evento=str(prazo.get("evento") or ""),
                data_limite=prazo.get("data_limite"),
                prioridade=str(prazo.get("prioridade") or "Média"),
                concluido=bool(prazo.get("concluido") or False),
                origem=prazo.get("origem"),
                referencia=prazo.get("referencia"),
                observacoes=prazo.get("observacoes"),
            )
        )

    return out


def _merge_obs_with_audit(obs: str | None, audit: str | None) -> str | None:
    base = _safe_str(obs)
    audit_txt = _safe_str(audit)

    if not base and not audit_txt:
        return None
    if base and not audit_txt:
        return base
    if not base and audit_txt:
        return f"🧮 {audit_txt}"
    return f"{base}\n🧮 {audit_txt}"


def _apply_lista_filters(
    rows: list[PrazoRow],
    *,
    tipo_val: str | None,
    processo_id_val: int | None,
    prioridade_val: str | None,
    origem_val: str | None,
    busca: str,
) -> list[PrazoRow]:
    filtered: list[PrazoRow] = []

    for row in rows:
        papel = _safe_str(row.processo_papel)
        origem = _safe_str(row.origem)
        prioridade = _safe_str(row.prioridade)

        if tipo_val and papel != tipo_val:
            continue
        if processo_id_val and int(row.processo_id) != int(processo_id_val):
            continue
        if prioridade_val and prioridade != prioridade_val:
            continue
        if origem_val and origem != origem_val:
            continue
        if busca and busca not in _filter_text(row):
            continue

        filtered.append(row)

    return filtered


def _split_status_groups(
    filtered: list[PrazoRow],
) -> tuple[
    list[PrazoRow], list[PrazoRow], list[PrazoRow], list[PrazoRow], list[PrazoRow]
]:
    abertos = [r for r in filtered if not r.concluido]
    hoje = [r for r in abertos if _dias_restantes(r.data_limite) == 0]
    atrasados = [r for r in abertos if _dias_restantes(r.data_limite) < 0]
    vencem7 = [r for r in abertos if 0 <= _dias_restantes(r.data_limite) <= 7]
    concluidos = [r for r in filtered if r.concluido]
    return abertos, hoje, atrasados, vencem7, concluidos


def _sort_operational(
    items: list[PrazoRow], reverse_days: bool = False
) -> list[PrazoRow]:
    return sorted(
        items,
        key=lambda r: (
            _dias_restantes(r.data_limite) * (-1 if reverse_days else 1),
            _priority_rank(r.prioridade),
            ensure_br(r.data_limite),
            -int(r.prazo_id),
        ),
    )


def _build_df(
    items: list[PrazoRow], include_status: bool = True
) -> pd.DataFrame | None:
    if not items:
        return None

    rows: list[dict[str, Any]] = []
    for item in items:
        dias = _dias_restantes(item.data_limite)
        row: dict[str, Any] = {
            "prazo_id": int(item.prazo_id),
            "processo": f"{item.processo_numero} – {item.processo_tipo_acao or 'Sem tipo de ação'}",
            "evento": item.evento,
            "data_limite": format_date_br(item.data_limite),
            "dias": int(dias),
            "prioridade": item.prioridade,
            "origem": _safe_str(item.origem) or "—",
            "_sort_dt": ensure_br(item.data_limite),
        }
        if include_status:
            row["status"] = _status_label(dias, item.concluido)
        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# UI DE TABELAS / KPIS
# ============================================================


def _render_df(df: pd.DataFrame, cols: list[str], height: int) -> None:
    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True,
        height=height,
    )


def _render_summary_kpis(
    abertos: int,
    hoje: int,
    atrasados: int,
    vencem7: int,
    concluidos: int,
) -> None:
    c1, c2 = st.columns(2)
    with c1:
        card("Abertos", f"{abertos}", "em acompanhamento", tone="info")
    with c2:
        card("Hoje", f"{hoje}", "vencem hoje", tone="warning" if hoje else "neutral")

    c3, c4 = st.columns(2)
    with c3:
        card(
            "Atrasados",
            f"{atrasados}",
            "ação imediata",
            tone="danger" if atrasados else "neutral",
        )
    with c4:
        card(
            "7 dias",
            f"{vencem7}",
            "janela curta",
            tone="warning" if vencem7 else "neutral",
        )

    c5, _ = st.columns(2)
    with c5:
        card("Concluídos", f"{concluidos}", "histórico finalizado", tone="neutral")


def _render_priority_queue(filtered: list[PrazoRow]) -> None:
    open_rows = [r for r in filtered if not r.concluido]
    top_items = sorted(
        open_rows,
        key=lambda r: (
            _dias_restantes(r.data_limite),
            _priority_rank(r.prioridade),
            ensure_br(r.data_limite),
        ),
    )[:5]

    st.markdown("#### Fila prioritária")
    st.caption("Veja primeiro o que exige ação imediata ou merece atenção próxima.")

    if not top_items:
        st.success("Nenhum prazo aberto com os filtros atuais.")
        return

    for row in top_items:
        dias = _dias_restantes(row.data_limite)
        status = _status_label(dias, row.concluido)

        if dias < 0:
            urgencia_txt = f"{abs(dias)} dia(s) em atraso"
            css_class = "pz-priority-card is-overdue"
        elif dias == 0:
            urgencia_txt = "vence hoje"
            css_class = "pz-priority-card is-today"
        elif dias <= 7:
            urgencia_txt = f"vence em {dias} dia(s)"
            css_class = "pz-priority-card is-soon"
        else:
            urgencia_txt = f"{dias} dia(s) restantes"
            css_class = "pz-priority-card"

        badges = [
            f"<span class='pz-badge'>{status}</span>",
            f"<span class='pz-badge'>Prioridade: {row.prioridade}</span>",
            f"<span class='pz-badge'>{urgencia_txt}</span>",
        ]
        if row.origem:
            badges.append(f"<span class='pz-badge'>{_safe_str(row.origem)}</span>")

        meta = [
            row.processo_numero or "Sem processo",
            row.processo_tipo_acao or "Sem tipo",
            f"Data: {format_date_br(row.data_limite)}",
        ]

        extra = []
        if row.referencia:
            extra.append(f"Referência: {_safe_str(row.referencia)}")
        if row.processo_contratante:
            extra.append(f"Contratante: {_safe_str(row.processo_contratante)}")

        _render_html(
            f"""
            <div class="{css_class}">
                <div style="font-weight:800;font-size:1rem;margin-bottom:4px;">
                    {row.evento}
                </div>
                <div class="pz-meta" style="margin-bottom:8px;">{" • ".join(meta)}</div>
                <div style="margin-bottom:6px;">{" ".join(badges)}</div>
                <div class="pz-meta">
                    {" • ".join(extra) if extra else ""}
                </div>
            </div>
            """
        )


# ============================================================
# AÇÕES RÁPIDAS / EDIÇÃO
# ============================================================


def _prazo_option_label(row: PrazoRow) -> str:
    dias = _dias_restantes(row.data_limite)
    status = _status_label(dias, row.concluido)
    return (
        f"[{int(row.prazo_id)}] {row.processo_numero} | "
        f"{row.evento} | {format_date_br(row.data_limite)} | {status}"
    )


def _quick_actions(filtered_items: list[PrazoRow], owner_user_id: int) -> None:
    if not filtered_items:
        st.info("Nenhum prazo com os filtros atuais.")
        return

    options: list[str] = []
    id_by_label: dict[str, int] = {}

    ordered = sorted(
        filtered_items,
        key=lambda r: (
            r.concluido,
            _dias_restantes(r.data_limite),
            _priority_rank(r.prioridade),
            ensure_br(r.data_limite),
        ),
    )

    for row in ordered:
        label = _prazo_option_label(row)
        options.append(label)
        id_by_label[label] = int(row.prazo_id)

    st.caption("Ações aplicadas ao prazo selecionado.")

    selected = st.selectbox("Selecione um prazo", options, key=KEY_QUICK_SELECT)
    prazo_id = id_by_label[selected]

    selected_row = next((r for r in ordered if int(r.prazo_id) == int(prazo_id)), None)
    if not selected_row:
        st.info("Prazo não encontrado.")
        return

    dias = _dias_restantes(selected_row.data_limite)
    status_txt = _status_label(dias, selected_row.concluido)

    meta_cols = st.columns(4)
    with meta_cols[0]:
        card("Status", status_txt, "situação atual", tone="neutral")
    with meta_cols[1]:
        card(
            "Data",
            format_date_br(selected_row.data_limite),
            "vencimento",
            tone="neutral",
        )
    with meta_cols[2]:
        card("Prioridade", selected_row.prioridade, "nível operacional", tone="neutral")
    with meta_cols[3]:
        if dias < 0:
            sub = f"{abs(dias)} dia(s) em atraso"
            tone = "danger"
        elif dias == 0:
            sub = "vence hoje"
            tone = "warning"
        else:
            sub = f"{dias} dia(s) restantes"
            tone = "info"
        card("Prazo", sub, "janela temporal", tone=tone)

    c1, c2, c3 = st.columns(3)

    if c1.button("✅ Concluir", key="pz_quick_done", use_container_width=True):
        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(concluido=True),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo concluído.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao concluir: {e}")

    if c2.button("♻️ Reabrir", key="pz_quick_reopen", use_container_width=True):
        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(concluido=False),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo reaberto.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao reabrir: {e}")

    with c3:
        st.number_input(
            "Adiar (dias)",
            min_value=1,
            max_value=365,
            step=1,
            key=KEY_QUICK_DELAY_DAYS,
        )
        if st.button("↪️ Adiar", key="pz_quick_delay", use_container_width=True):
            try:
                add_days = int(st.session_state.get(KEY_QUICK_DELAY_DAYS, 1) or 1)
                nova_data = ensure_br(selected_row.data_limite).date() + timedelta(
                    days=add_days
                )

                with get_session() as s:
                    PrazosService.update(
                        s,
                        owner_user_id,
                        int(prazo_id),
                        PrazoUpdate(data_limite=date_to_br_datetime(nova_data)),
                    )
                bump_data_version(owner_user_id)
                st.success("Prazo reagendado.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao reagendar: {e}")

    with st.expander("Zona sensível", expanded=False):
        st.caption("Exclusão definitiva do prazo selecionado.")
        confirm = st.checkbox("Confirmo a exclusão", key=KEY_QUICK_CONFIRM_DELETE)
        if st.button(
            "🗑️ Excluir prazo",
            key="pz_quick_del",
            use_container_width=True,
            disabled=not confirm,
        ):
            try:
                with get_session() as s:
                    PrazosService.delete(s, owner_user_id, int(prazo_id))
                bump_data_version(owner_user_id)
                st.warning("Prazo excluído.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


def _editar_excluir_prazo(items: list[PrazoRow], owner_user_id: int) -> None:
    if not items:
        st.info("Nenhum prazo disponível para editar.")
        return

    options: list[str] = []
    id_by_label: dict[str, int] = {}

    ordered = sorted(
        items,
        key=lambda r: (
            r.concluido,
            _dias_restantes(r.data_limite),
            _priority_rank(r.prioridade),
            ensure_br(r.data_limite),
        ),
    )

    for row in ordered:
        label = (
            f"[{row.prazo_id}] {row.processo_numero} — "
            f"{row.evento} — {format_date_br(row.data_limite)} — "
            f"{_status_label(_dias_restantes(row.data_limite), row.concluido)}"
        )
        options.append(label)
        id_by_label[label] = int(row.prazo_id)

    selected = st.selectbox(
        "Selecione um prazo para editar",
        options,
        key="pz_edit_select",
    )
    prazo_id = id_by_label[selected]

    with get_session() as s:
        pz = PrazosService.get(s, owner_user_id, int(prazo_id))

    if not pz:
        st.error("Prazo não encontrado.")
        return

    try:
        pz_date = ensure_br(pz.data_limite).date()
    except Exception:
        pz_date = now_br().date()

    with st.form(f"form_prazo_edit_{prazo_id}"):
        c1, c2, c3 = st.columns(3)
        evento_e = c1.text_input("Evento *", value=str(getattr(pz, "evento", "") or ""))
        data_e = c2.date_input("Data limite *", value=pz_date)
        prio_e = c3.selectbox(
            "Prioridade",
            list(PRIORIDADES),
            index=(
                list(PRIORIDADES).index(pz.prioridade)
                if pz.prioridade in PRIORIDADES
                else 1
            ),
        )

        c4, c5 = st.columns(2)
        origem_e = c4.selectbox(
            "Origem",
            list(ORIGENS),
            index=(
                list(ORIGENS).index(getattr(pz, "origem", "") or "")
                if (getattr(pz, "origem", "") or "") in ORIGENS
                else 0
            ),
        )
        referencia_e = c5.text_input(
            "Referência",
            value=str(getattr(pz, "referencia", "") or ""),
        )

        concl = st.checkbox("Concluído", value=bool(getattr(pz, "concluido", False)))
        obs_e = st.text_area(
            "Observações",
            value=str(getattr(pz, "observacoes", "") or ""),
        )

        b1, b2 = st.columns(2)
        salvar = b1.form_submit_button(
            "Salvar alterações",
            type="primary",
            use_container_width=True,
        )
        excluir = b2.form_submit_button(
            "Excluir (irreversível)",
            use_container_width=True,
        )

    if salvar:
        if not _safe_str(evento_e):
            st.error("Evento não pode ficar vazio.")
            return

        try:
            with get_session() as s:
                PrazosService.update(
                    s,
                    owner_user_id,
                    int(prazo_id),
                    PrazoUpdate(
                        evento=_safe_str(evento_e),
                        data_limite=date_to_br_datetime(data_e),
                        prioridade=prio_e,
                        concluido=concl,
                        origem=_norm(origem_e),
                        referencia=_norm(referencia_e),
                        observacoes=_norm(obs_e),
                    ),
                )
            bump_data_version(owner_user_id)
            st.success("Prazo atualizado.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    if excluir:
        try:
            with get_session() as s:
                PrazosService.delete(s, owner_user_id, int(prazo_id))
            bump_data_version(owner_user_id)
            st.warning("Prazo excluído.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")


# ============================================================
# CADASTRO
# ============================================================


def _render_cadastro(
    *,
    owner_user_id: int,
    proc_labels: list[str],
    label_to_id: dict[str, int],
    proc_by_id: dict[int, dict[str, Any]],
) -> None:
    with st.container(border=True):
        _section_card(
            "Novo prazo",
            "Defina o cálculo, confira a data final e cadastre o evento.",
        )
        subtle_divider()

        sel_proc = st.selectbox("Trabalho *", proc_labels, index=0, key=KEY_C_PROC)
        processo_id = int(label_to_id[sel_proc])
        proc = proc_by_id.get(processo_id)
        comarca_proc = (_safe_str(proc.get("comarca")) or None) if proc else None

        st.markdown("**1) Forma de cálculo**")
        modo = st.selectbox(
            "Modo",
            ["Manual", "Dias corridos", "Dias úteis"],
            key=KEY_C_MODE,
        )

        subtle_divider()
        st.markdown("**2) Cálculo da data**")

        if modo == "Manual":
            st.date_input("Data limite *", key=KEY_C_DATA_LIM)
            st.session_state[KEY_C_AUDIT] = ""

        elif modo == "Dias corridos":
            c1, c2 = st.columns(2)
            base = c1.date_input("Data base", key=KEY_C_BASE)
            dias = c2.number_input("Qtd dias", min_value=1, step=1, key=KEY_C_DIAS)

            nova = base + timedelta(days=int(dias))
            st.session_state[KEY_C_DATA_LIM] = nova
            st.session_state[KEY_C_AUDIT] = "Auto: dias corridos"

            card(
                "Data final",
                nova.strftime("%d/%m/%Y"),
                f"Base: {base.strftime('%d/%m/%Y')} • +{int(dias)} dia(s)",
                tone="info",
            )

        else:
            c1, c2 = st.columns(2)
            base = c1.date_input("Data base (disponibilização DJE)", key=KEY_C_BASE)
            dias = c2.number_input(
                "Qtd dias úteis", min_value=1, step=1, key=KEY_C_DIAS
            )

            usar_tjsp = st.checkbox(
                "Considerar calendário TJSP (inclui CPC art. 220 automaticamente)",
                key=KEY_C_USAR_TJSP,
            )

            incluir_municipal = st.checkbox(
                "Incluir feriados municipais da comarca",
                key=KEY_C_LOCAL,
                disabled=not bool(comarca_proc),
                help="Requer 'Comarca' preenchida no trabalho.",
            )

            regras = RegrasCalendario(
                incluir_nacional=True,
                incluir_estadual_sp=True,
                incluir_tjsp_geral=bool(usar_tjsp),
                incluir_tjsp_comarca=bool(usar_tjsp),
                incluir_municipal=bool(incluir_municipal),
            )

            aplicar_local = bool(comarca_proc)

            nova = CalendarioService.prazo_dje_tjsp(
                disponibilizacao=base,
                dias_uteis=int(dias),
                comarca=comarca_proc,
                municipio=None,
                aplicar_local=aplicar_local,
                regras=regras,
            )

            st.session_state[KEY_C_DATA_LIM] = nova

            if usar_tjsp:
                if incluir_municipal and bool(comarca_proc):
                    st.session_state[KEY_C_AUDIT] = (
                        f"Auto: DJE + dias úteis (TJSP/CPC220 + municipal {comarca_proc})"
                    )
                else:
                    st.session_state[KEY_C_AUDIT] = (
                        "Auto: DJE + dias úteis (TJSP/CPC220)"
                    )
            else:
                if incluir_municipal and bool(comarca_proc):
                    st.session_state[KEY_C_AUDIT] = (
                        f"Auto: DJE + dias úteis (Nac/Estadual + municipal {comarca_proc})"
                    )
                else:
                    st.session_state[KEY_C_AUDIT] = (
                        "Auto: DJE + dias úteis (Nac/Estadual)"
                    )

            card(
                "Data final",
                nova.strftime("%d/%m/%Y"),
                f"Base: {base.strftime('%d/%m/%Y')} • {int(dias)} dia(s) úteis"
                + (
                    f" • Comarca: {comarca_proc}"
                    if (incluir_municipal and comarca_proc)
                    else ""
                ),
                tone="info",
            )

            if DEBUG_PRAZOS:
                from datetime import date as _date

                st.markdown("### 🔎 DEBUG PRAZO")
                st.write("comarca_proc:", repr(comarca_proc))
                st.write("aplicar_local:", aplicar_local)
                st.write("incluir_municipal:", bool(incluir_municipal))
                st.write("usar_tjsp:", bool(usar_tjsp))
                st.write("base:", base)
                st.write("dias:", int(dias))
                st.write("nova:", nova)

                ini = _date(2026, 1, 15)
                fim = _date(2026, 2, 15)
                fer_set = CalendarioService.feriados_aplicaveis(
                    ini,
                    fim,
                    comarca=comarca_proc,
                    municipio=None,
                    aplicar_local=aplicar_local,
                    regras=regras,
                )
                st.write("contém 02/02/2026?:", _date(2026, 2, 2) in fer_set)
                st.write("feriados janela:", sorted(list(fer_set)))

        subtle_divider()
        st.markdown("**3) Detalhes do prazo**")

        preview_date = st.session_state.get(KEY_C_DATA_LIM, now_br().date())
        preview_event = _safe_str(st.session_state.get(KEY_C_EVENTO))
        preview_prio = _safe_str(st.session_state.get(KEY_C_PRIO) or "Média")

        p1, p2, p3 = st.columns(3)
        with p1:
            card(
                "Data apurada",
                format_date_br(preview_date),
                "resultado do cálculo",
                tone="info",
            )
        with p2:
            card(
                "Prioridade",
                preview_prio or "Média",
                "nível operacional",
                tone="neutral",
            )
        with p3:
            card(
                "Evento",
                preview_event or "A definir",
                "descrição principal",
                tone="neutral",
            )

        with st.form("form_prazo_create", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)

            evento = c1.text_input("Evento *", key=KEY_C_EVENTO)
            prioridade = c2.selectbox(
                "Prioridade",
                list(PRIORIDADES),
                index=1,
                key=KEY_C_PRIO,
            )
            origem = c3.selectbox(
                "Origem (opcional)",
                list(ORIGENS),
                index=0,
                key=KEY_C_ORIGEM,
            )

            referencia = st.text_input(
                "Referência (opcional)",
                placeholder="Ex.: fls. 389 / ID 12345 / mov. 12.1",
                key=KEY_C_REF,
            )
            obs = st.text_area("Observações", key=KEY_C_OBS)

            salvar = st.form_submit_button(
                "Salvar prazo",
                type="primary",
                use_container_width=True,
            )

        if salvar:
            if not _safe_str(evento):
                st.error("Informe o evento.")
                return

            try:
                data_final = st.session_state.get(KEY_C_DATA_LIM, now_br().date())
                dt_lim = date_to_br_datetime(data_final)

                audit_txt = _safe_str(st.session_state.get(KEY_C_AUDIT))
                obs_final = _merge_obs_with_audit(obs, audit_txt)

                with get_session() as s:
                    PrazosService.create(
                        s,
                        owner_user_id,
                        PrazoCreate(
                            processo_id=int(processo_id),
                            evento=_safe_str(evento),
                            data_limite=dt_lim,
                            prioridade=prioridade,
                            origem=(origem or None),
                            referencia=_norm(referencia),
                            observacoes=obs_final,
                        ),
                    )

                bump_data_version(owner_user_id)
                st.success("Prazo criado com sucesso.")
                _request_tab("Lista")
                _request_list_tab("Abertos")
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao criar prazo: {e}")


# ============================================================
# LISTA
# ============================================================


def _render_filtros_lista(proc_labels: list[str]) -> tuple[str, str, str, str, str]:
    with st.container(border=True):
        _section_card(
            "Filtros operacionais", "Use apenas quando precisar refinar a leitura."
        )
        subtle_divider()

        f1, f2, f3, f4 = st.columns(4)
        filtro_tipo = f1.selectbox(
            "Tipo",
            ["(Todos)"] + list(TIPOS_TRABALHO),
            index=0,
            key=KEY_FILTER_TIPO,
        )
        filtro_proc = f2.selectbox(
            "Trabalho",
            ["(Todos)"] + proc_labels,
            index=0,
            key=KEY_FILTER_PROC,
        )
        filtro_prio = f3.selectbox(
            "Prioridade",
            ["(Todas)"] + list(PRIORIDADES),
            index=0,
            key=KEY_FILTER_PRIO,
        )
        filtro_origem = f4.selectbox(
            "Origem",
            ["(Todas)"] + [o for o in ORIGENS if o],
            index=0,
            key=KEY_FILTER_ORIGEM,
        )

        busca = (
            st.text_input(
                "Buscar",
                placeholder="processo, evento, origem, referência, observações…",
                key=KEY_FILTER_BUSCA,
            )
            .strip()
            .lower()
        )

    return filtro_tipo, filtro_proc, filtro_prio, filtro_origem, busca


def _render_open_controls() -> tuple[str, str]:
    with st.container(border=True):
        c1, c2 = st.columns([2, 4])
        filtro_janela = c1.selectbox(
            "Janela",
            ["Todos", "Atrasados", "Hoje", "0–7 dias", "0–15 dias", "0–30 dias"],
            index=0,
            key=KEY_OPEN_WINDOW,
        )
        ordem = c2.selectbox(
            "Ordenar",
            ["Mais urgentes primeiro", "Mais distantes primeiro"],
            index=0,
            key=KEY_OPEN_ORDER,
        )
    return filtro_janela, ordem


def _filter_open_window(rows: list[PrazoRow], janela: str) -> list[PrazoRow]:
    items: list[PrazoRow] = []
    for row in rows:
        if row.concluido:
            continue
        dias = _dias_restantes(row.data_limite)

        if janela == "Atrasados" and not (dias < 0):
            continue
        if janela == "Hoje" and dias != 0:
            continue
        if janela == "0–7 dias" and not (0 <= dias <= 7):
            continue
        if janela == "0–15 dias" and not (0 <= dias <= 15):
            continue
        if janela == "0–30 dias" and not (0 <= dias <= 30):
            continue

        items.append(row)
    return items


def _render_lista_topbar() -> None:
    c1, c2 = st.columns([0.72, 0.28], vertical_alignment="center")

    with c1:
        st.markdown("#### Operação de prazos")
        st.caption(
            "Comece pelos itens mais críticos e depois refine a fila com os filtros."
        )

    with c2:
        if st.button(
            "➕ Novo prazo",
            key="pz_go_create_top",
            use_container_width=True,
            type="primary",
        ):
            _request_tab("Cadastrar")
            st.rerun()


def _render_lista(
    *,
    owner_user_id: int,
    proc_labels: list[str],
    label_to_id: dict[str, int],
) -> None:
    _apply_requested_list_tab()

    version = _data_version(owner_user_id)
    all_rows = _dicts_to_dataclass(_cached_prazos_list_all(owner_user_id, version))

    tipo_val = None
    processo_id_val = None
    prioridade_val = None
    origem_val = None
    busca = ""

    filtered_base = _apply_lista_filters(
        all_rows,
        tipo_val=tipo_val,
        processo_id_val=processo_id_val,
        prioridade_val=prioridade_val,
        origem_val=origem_val,
        busca=busca,
    )

    abertos_base, hoje_base, atrasados_base, vencem7_base, concluidos_base = (
        _split_status_groups(filtered_base)
    )

    _render_lista_topbar()

    _render_summary_kpis(
        abertos=len(abertos_base),
        hoje=len(hoje_base),
        atrasados=len(atrasados_base),
        vencem7=len(vencem7_base),
        concluidos=len(concluidos_base),
    )

    with st.container(border=True):
        _render_priority_queue(filtered_base)

    filtro_tipo, filtro_proc, filtro_prio, filtro_origem, busca = _render_filtros_lista(
        proc_labels
    )

    tipo_val = None if filtro_tipo == "(Todos)" else filtro_tipo
    processo_id_val = (
        None if filtro_proc == "(Todos)" else int(label_to_id[filtro_proc])
    )
    prioridade_val = None if filtro_prio == "(Todas)" else filtro_prio
    origem_val = None if filtro_origem == "(Todas)" else filtro_origem

    filtered = _apply_lista_filters(
        all_rows,
        tipo_val=tipo_val,
        processo_id_val=processo_id_val,
        prioridade_val=prioridade_val,
        origem_val=origem_val,
        busca=busca,
    )

    abertos, hoje, atrasados, vencem7, concluidos = _split_status_groups(filtered)

    with st.container(border=True):
        _section_card(
            "⚡ Ações rápidas", "Resolva operações frequentes sem sair da fila."
        )
        _quick_actions(filtered, owner_user_id)

    subtle_divider()
    chosen_view = _list_tabs_selector()

    if chosen_view == "Atrasados":
        items = sorted(
            atrasados,
            key=lambda r: (
                _dias_restantes(r.data_limite),
                _priority_rank(r.prioridade),
                ensure_br(r.data_limite),
            ),
        )
        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo atrasado com os filtros atuais.")
            return

        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[True, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=380,
        )
        return

    if chosen_view == "Hoje":
        items = sorted(
            hoje,
            key=lambda r: (
                _priority_rank(r.prioridade),
                ensure_br(r.data_limite),
                -int(r.prazo_id),
            ),
        )
        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo vencendo hoje com os filtros atuais.")
            return

        df = df.sort_values(by=["_sort_dt"], ascending=[True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "prioridade",
                "origem",
                "status",
            ],
            height=340,
        )
        return

    if chosen_view == "Vencem (7 dias)":
        items = sorted(
            vencem7,
            key=lambda r: (
                _dias_restantes(r.data_limite),
                _priority_rank(r.prioridade),
                ensure_br(r.data_limite),
            ),
        )
        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo vencendo em até 7 dias com os filtros atuais.")
            return

        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[True, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=380,
        )
        return

    if chosen_view == "Abertos":
        filtro_janela, ordem = _render_open_controls()
        items = _filter_open_window(filtered, filtro_janela)

        reverse_days = ordem == "Mais distantes primeiro"
        items = _sort_operational(items, reverse_days=reverse_days)

        df = _build_df(items, include_status=True)
        if df is None:
            st.info("Nenhum prazo aberto com os filtros atuais.")
            return

        asc = ordem == "Mais urgentes primeiro"
        df = df.sort_values(by=["dias", "_sort_dt"], ascending=[asc, True]).drop(
            columns=["_sort_dt"], errors="ignore"
        )
        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias",
                "prioridade",
                "origem",
                "status",
            ],
            height=460,
        )
        return

    items = sorted(concluidos, key=lambda r: ensure_br(r.data_limite), reverse=True)
    df = _build_df(items, include_status=False)
    if df is None:
        st.info("Nenhum prazo concluído com os filtros atuais.")
        return

    df = df.sort_values(by=["_sort_dt"], ascending=False).drop(
        columns=["_sort_dt"], errors="ignore"
    )
    _render_df(
        df,
        ["prazo_id", "processo", "evento", "data_limite", "prioridade", "origem"],
        height=380,
    )


# ============================================================
# EDITAR
# ============================================================


def _render_editar(owner_user_id: int) -> None:
    with st.container(border=True):
        _section_card(
            "Editar / Excluir",
            "Selecione um prazo e ajuste os campos necessários.",
        )

        version = _data_version(owner_user_id)
        all_rows = _dicts_to_dataclass(_cached_prazos_list_all(owner_user_id, version))
        _editar_excluir_prazo(all_rows, owner_user_id)


# ============================================================
# RENDER PRINCIPAL
# ============================================================


def render(owner_user_id: int) -> None:
    _inject_segmented_radio_css()
    st.session_state[KEY_OWNER] = owner_user_id

    clicked_refresh = page_header(
        "Prazos",
        "Cadastro, priorização e controle operacional de prazos.",
        right_button_label="Recarregar",
        right_button_key="pz_btn_recarregar",
        right_button_help="Recarrega a tela e os dados",
    )
    if clicked_refresh:
        st.rerun()

    with st.expander("Ferramentas", expanded=False):
        st.caption("Utilidades da tela.")
        if st.button(
            "Limpar cache de feriados",
            key="pz_btn_clear_cache",
            type="secondary",
        ):
            CalendarioService.clear_cache()
            st.success("Cache de feriados limpo.")
            st.rerun()

    version = _data_version(owner_user_id)
    processos = _cached_processos(owner_user_id, version)
    all_rows = _dicts_to_dataclass(_cached_prazos_list_all(owner_user_id, version))

    if not processos:
        st.info("Cadastre um trabalho primeiro.")
        return

    proc_labels = [_proc_label_dict(p) for p in processos]
    label_to_id = {
        proc_labels[i]: int(processos[i]["id"]) for i in range(len(processos))
    }
    proc_by_id = {int(p["id"]): p for p in processos}

    pref_proc = _get_pref_context(proc_by_id)
    _render_contexto_trabalho(pref_proc, all_rows)

    hoje_sp = now_br().date()
    st.session_state.setdefault(KEY_C_MODE, "Manual")
    st.session_state.setdefault(KEY_C_DATA_LIM, hoje_sp)
    st.session_state.setdefault(KEY_C_AUDIT, "")
    st.session_state.setdefault(KEY_C_BASE, hoje_sp)
    st.session_state.setdefault(KEY_C_DIAS, 15)
    st.session_state.setdefault(KEY_C_USAR_TJSP, True)
    st.session_state.setdefault(KEY_C_LOCAL, True)
    st.session_state.setdefault(KEY_C_PROC, proc_labels[0] if proc_labels else "")
    st.session_state.setdefault(KEY_FILTER_PRIO, "(Todas)")
    st.session_state.setdefault(KEY_FILTER_ORIGEM, "(Todas)")

    _apply_pref_processo_defaults(proc_labels, label_to_id)
    _apply_requested_tab()

    with st.container(border=True):
        section = _section_tabs(KEY_ACTIVE_TAB)

    if section == "Cadastrar":
        _render_cadastro(
            owner_user_id=owner_user_id,
            proc_labels=proc_labels,
            label_to_id=label_to_id,
            proc_by_id=proc_by_id,
        )
    elif section == "Lista":
        _render_lista(
            owner_user_id=owner_user_id,
            proc_labels=proc_labels,
            label_to_id=label_to_id,
        )
    else:
        _render_editar(owner_user_id)
