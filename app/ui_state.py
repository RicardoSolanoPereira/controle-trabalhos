"""
app/ui_state.py

Centraliza navegação e passagem de contexto entre telas.

- query params (ótimo para filtros em listas)
- session_state (ótimo para abrir uma seção específica: Lista/Editar etc.)
- política de limpeza por tela (evita "estado grudado")
- hook para troca de menu via sidebar (on_menu_change)
"""

from __future__ import annotations

from typing import Any

import streamlit as st


# ------------------------------------------------------------
# Política de limpeza de estado por tela (evita "estado grudado")
# ------------------------------------------------------------
_PAGE_STATE_KEYS: dict[str, set[str]] = {
    "Dashboard": {
        "dashboard_tab",
        "dashboard_filter_q",
    },
    "Prazos": {
        "prazos_section",
        "prazo_open_window",
        "prazo_selected_id",
        "prazos_filter_status",
        "prazos_filter_q",
    },
    "Processos": {
        "processos_section",
        "processo_selected_id",
        "processos_filter_status",
        "processos_filter_q",
    },
    "Andamentos": {
        "andamentos_section",
        "andamento_selected_id",
        "andamentos_filter_q",
    },
    "Financeiro": {
        "financeiro_section",
        "financeiro_selected_id",
    },
    "Agendamentos": {
        "agendamentos_section",
        "agendamento_selected_id",
    },
}

_LAST_MENU_KEY = "__last_menu"


# ------------------------------------------------------------
# Query params helpers (compatível com versões diferentes)
# ------------------------------------------------------------
def _qp_get_all() -> dict[str, Any]:
    """Retorna todos os query params em formato dict (compatível)."""
    try:
        # Streamlit novo
        return dict(st.query_params)  # type: ignore[attr-defined]
    except Exception:
        try:
            # Streamlit antigo
            return st.experimental_get_query_params()
        except Exception:
            return {}


def _qp_set_all(params: dict[str, Any]) -> None:
    """Seta query params de uma vez (compatível)."""
    try:
        st.query_params.clear()  # type: ignore[attr-defined]
        for k, v in params.items():
            st.query_params[k] = v  # type: ignore[attr-defined]
    except Exception:
        try:
            st.experimental_set_query_params(**params)
        except Exception:
            pass


def _qp_get(key: str) -> Any:
    """Obtém query param (pode vir como str, lista ou None)."""
    try:
        return st.query_params.get(key)  # type: ignore[attr-defined]
    except Exception:
        try:
            return st.experimental_get_query_params().get(key)
        except Exception:
            return None


def get_qp_str(key: str, default: str = "") -> str:
    v = _qp_get(key)
    if v is None:
        return default
    if isinstance(v, list):
        return str(v[0]) if v else default
    return str(v)


def get_qp_list(key: str) -> list[str]:
    v = _qp_get(key)
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None and x != ""]
    s = str(v).strip()
    return [s] if s else []


# ------------------------------------------------------------
# Internals
# ------------------------------------------------------------
def _normalize_qp_value(v: Any) -> Any:
    """
    Normaliza valores para query params:
    - None / "" => remove
    - list/tuple => lista de strings (sem vazios)
    - outros => string
    """
    if v is None or v == "":
        return None
    if isinstance(v, (list, tuple)):
        values = [str(x) for x in v if x is not None and x != ""]
        return values if values else None
    return str(v)


def _set_query_params(
    qp: dict[str, Any] | None, *, clear_existing: bool = False
) -> None:
    """
    Atualiza query params de forma robusta.

    Regras:
    - None / "" remove o parâmetro
    - list/tuple vira múltiplos valores
    - tudo vira str/list[str]
    """
    if qp is None and not clear_existing:
        return

    current = {} if clear_existing else _qp_get_all()
    current = {str(k): v for k, v in current.items()}

    if qp:
        for k, v in qp.items():
            k = str(k)
            nv = _normalize_qp_value(v)
            if nv is None:
                current.pop(k, None)
            else:
                current[k] = nv

    _qp_set_all(current)


def _set_state(state: dict[str, Any] | None) -> None:
    if not state:
        return
    for k, v in state.items():
        st.session_state[k] = v


def _clear_page_state(menu_key: str, incoming_state: dict[str, Any] | None) -> None:
    """
    Remove chaves de estado da tela destino, exceto as que vierem explicitamente em `incoming_state`.
    Evita herdar filtros/abas de uma visita anterior.
    """
    keys = _PAGE_STATE_KEYS.get(menu_key)
    if not keys:
        return

    incoming_state = incoming_state or {}
    for k in keys:
        if k not in incoming_state:
            st.session_state.pop(k, None)


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------
def on_menu_change(current_menu: str) -> None:
    """
    Chamar após o sidebar.radio retornar o menu selecionado.

    Se o usuário trocar de aba pelo menu (sem usar navigate()),
    limpamos o estado da tela destino para evitar 'estado grudado'.
    """
    last = st.session_state.get(_LAST_MENU_KEY)
    if last != current_menu:
        _clear_page_state(current_menu, incoming_state=None)
        st.session_state[_LAST_MENU_KEY] = current_menu


def bump_data_version(owner_user_id: int) -> int:
    """
    Invalida caches por usuário (dashboard/listas), sem depender só de TTL.
    Use após CREATE/UPDATE/DELETE em qualquer tela.
    """
    key = f"data_version_{owner_user_id}"
    st.session_state[key] = int(st.session_state.get(key, 0)) + 1
    return int(st.session_state[key])


def navigate(
    menu_key: str,
    *,
    qp: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    clear_qp: bool = False,
) -> None:
    """
    Navega para `menu_key` carregando parâmetros.
    """
    _clear_page_state(menu_key, state)
    _set_query_params(qp, clear_existing=clear_qp)
    _set_state(state)

    st.session_state[_LAST_MENU_KEY] = menu_key
    st.session_state["nav_target"] = menu_key
    st.rerun()
