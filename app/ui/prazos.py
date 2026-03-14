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


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


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

    for row in filtered_items:
        dias = _dias_restantes(row.data_limite)
        status = "✅ Concluído" if row.concluido else _semaforo(dias)
        label = (
            f"[{int(row.prazo_id)}] {row.processo_numero} | "
            f"{row.evento} | {format_date_br(row.data_limite)} | {status}"
        )
        options.append(label)
        id_by_label[label] = int(row.prazo_id)

    selected = st.selectbox("Selecione um prazo", options, key="pz_quick_select")
    prazo_id = id_by_label[selected]

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

    if c3.button("🗑️ Excluir", key="pz_quick_del", use_container_width=True):
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


def _render_lista(
    *,
    owner_user_id: int,
    proc_labels: list[str],
    label_to_id: dict[str, int],
) -> None:
    _apply_requested_list_tab()

    version = _data_version(owner_user_id)
    all_rows = _dicts_to_dataclass(_cached_prazos_list_all(owner_user_id, version))

    with st.container(border=True):
        _section_card("Filtros", "A atuação filtra indicadores e listas.")
        subtle_divider()

        f1, f2 = st.columns(2)
        filtro_tipo = f1.selectbox(
            "Tipo de trabalho",
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

        busca = (
            st.text_input(
                "Buscar",
                placeholder="processo, evento, origem, referência, observações…",
                key=KEY_FILTER_BUSCA,
            )
            .strip()
            .lower()
        )

    tipo_val = None if filtro_tipo == "(Todos)" else filtro_tipo
    processo_id_val = (
        None if filtro_proc == "(Todos)" else int(label_to_id[filtro_proc])
    )

    filtered = _apply_lista_filters(
        all_rows,
        tipo_val=tipo_val,
        processo_id_val=processo_id_val,
        busca=busca,
    )

    abertos, atrasados, vencem7, concluidos = _split_status_groups(filtered)

    _kpis_grid(len(abertos), len(atrasados), len(vencem7), len(concluidos))

    with st.container(border=True):
        _top_prioridades_hoje(filtered)

    with st.container(border=True):
        _section_card("⚡ Ações rápidas", "Concluir, reabrir ou excluir rapidamente.")
        _quick_actions(filtered, owner_user_id)

    subtle_divider()
    chosen_view = _list_tabs_selector()

    if chosen_view == "Atrasados":
        items = atrasados
        df = _build_df(items, mode="open")
        if df is None:
            st.info("Nenhum prazo atrasado com os filtros atuais.")
            return

        df = df.sort_values(
            by=["dias_restantes", "_data_sort"],
            ascending=[True, True],
        ).drop(columns=["_data_sort"], errors="ignore")

        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias_restantes",
                "prioridade",
                "status",
            ],
            height=360,
        )
        return

    if chosen_view == "Vencem (7 dias)":
        items = vencem7
        df = _build_df(items, mode="open")
        if df is None:
            st.info("Nenhum prazo vencendo em até 7 dias com os filtros atuais.")
            return

        df = df.sort_values(
            by=["dias_restantes", "_data_sort"],
            ascending=[True, True],
        ).drop(columns=["_data_sort"], errors="ignore")

        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias_restantes",
                "prioridade",
                "status",
            ],
            height=360,
        )
        return

    if chosen_view == "Abertos":
        with st.container(border=True):
            c1, c2 = st.columns([2, 4])
            filtro_janela = c1.selectbox(
                "Janela",
                ["Todos", "Atrasados", "0–7 dias", "0–15 dias", "0–30 dias"],
                index=0,
                key=KEY_OPEN_WINDOW,
            )
            ordem = c2.selectbox(
                "Ordenar",
                ["Mais urgentes primeiro", "Mais distantes primeiro"],
                index=0,
                key=KEY_OPEN_ORDER,
            )

        items: list[PrazoRow] = []
        for row in filtered:
            if row.concluido:
                continue

            dias = _dias_restantes(row.data_limite)

            if filtro_janela == "Atrasados" and not (dias < 0):
                continue
            if filtro_janela == "0–7 dias" and not (0 <= dias <= 7):
                continue
            if filtro_janela == "0–15 dias" and not (0 <= dias <= 15):
                continue
            if filtro_janela == "0–30 dias" and not (0 <= dias <= 30):
                continue

            items.append(row)

        df = _build_df(items, mode="open")
        if df is None:
            st.info("Nenhum prazo aberto com os filtros atuais.")
            return

        asc = ordem == "Mais urgentes primeiro"
        df = df.sort_values(
            by=["dias_restantes", "_data_sort"],
            ascending=[asc, True],
        ).drop(columns=["_data_sort"], errors="ignore")

        _render_df(
            df,
            [
                "prazo_id",
                "processo",
                "evento",
                "data_limite",
                "dias_restantes",
                "prioridade",
                "status",
            ],
            height=460,
        )
        return

    items = concluidos
    df = _build_df(items, mode="done")
    if df is None:
        st.info("Nenhum prazo concluído com os filtros atuais.")
        return

    df = df.sort_values(by=["_data_sort"], ascending=False).drop(
        columns=["_data_sort"],
        errors="ignore",
    )

    _render_df(
        df,
        ["prazo_id", "processo", "evento", "data_limite", "prioridade"],
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
