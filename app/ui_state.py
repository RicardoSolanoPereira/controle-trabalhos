"""
app/ui_state.py

Centraliza navegação e passagem de contexto entre telas.

- query params (ótimo para filtros em listas)
- session_state (ótimo para abrir uma seção específica: Lista/Editar etc.)
- política de limpeza por tela (evita "estado grudado")
- hook para troca de menu via sidebar (on_menu_change)
"""

from __future__ import annotations

from typing import Any, Iterable

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
_NAV_TARGET_KEY = "nav_target"


# ------------------------------------------------------------
# Query params helpers (compatível com versões diferentes)
# ------------------------------------------------------------
def _qp_get_all() -> dict[str, Any]:
    """Retorna todos os query params em formato dict (compatível)."""
    try:
        # Streamlit novo (st.query_params é mapping-like)
        return dict(st.query_params)  # type: ignore[attr-defined]
    except Exception:
        try:
            # Streamlit antigo
            return st.experimental_get_query_params()
        except Exception:
            return {}


def _qp_set_all(params: dict[str, Any]) -> None:
    """
    Seta query params de uma vez (compatível).

    Regras:
    - valores podem ser str ou list[str]
    """
    try:
        # Streamlit novo
        st.query_params.clear()  # type: ignore[attr-defined]
        for k, v in params.items():
            st.query_params[str(k)] = v  # type: ignore[attr-defined]
    except Exception:
        try:
            # Streamlit antigo
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
    """Lê query param como string (primeiro valor, se vier lista)."""
    v = _qp_get(key)
    if v is None:
        return default
    if isinstance(v, list):
        return str(v[0]) if v else default
    return str(v)


def get_qp_list(key: str) -> list[str]:
    """Lê query param como lista de strings (sem vazios)."""
    v = _qp_get(key)
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None and str(x).strip() != ""]
    s = str(v).strip()
    return [s] if s else []


# ------------------------------------------------------------
# Internals
# ------------------------------------------------------------
def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return True
    return False


def _normalize_qp_value(v: Any) -> Any:
    """
    Normaliza valores para query params:
    - None / "" => remove
    - list/tuple => lista de strings (sem vazios)
    - outros => string
    """
    if _is_empty(v):
        return None

    if isinstance(v, (list, tuple)):
        values = [str(x) for x in v if not _is_empty(x)]
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
    """Seta chaves no session_state (sem limpar nada)."""
    if not state:
        return
    for k, v in state.items():
        st.session_state[k] = v


def _clear_keys(keys: Iterable[str], *, keep: set[str] | None = None) -> None:
    """Remove várias chaves do session_state (com allowlist)."""
    keep = keep or set()
    for k in keys:
        if k in keep:
            continue
        st.session_state.pop(k, None)


def _clear_page_state(menu_key: str, incoming_state: dict[str, Any] | None) -> None:
    """
    Remove chaves de estado da tela destino, exceto as que vierem explicitamente em `incoming_state`.
    Evita herdar filtros/abas de uma visita anterior.
    """
    keys = _PAGE_STATE_KEYS.get(menu_key)
    if not keys:
        return

    incoming_state = incoming_state or {}
    _clear_keys(keys, keep=set(incoming_state.keys()))


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


def consume_nav_target(default: str | None = None) -> str | None:
    """
    Lê e consome (remove) um alvo de navegação setado por navigate().
    Útil no app.py para decidir qual página renderizar uma vez e evitar "loop".

    Retorna:
      - menu_key (str) se existir
      - default se não existir
    """
    target = st.session_state.pop(_NAV_TARGET_KEY, None)
    if target is None:
        return default
    return str(target)


def navigate(
    menu_key: str,
    *,
    qp: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
    clear_qp: bool = False,
) -> None:
    """
    Navega para `menu_key` carregando parâmetros.

    - menu_key: chave do menu (ex: "Prazos")
    - qp: query params (ex: {"q": "abc", "status": ["aberto","vencido"]})
    - state: session_state (ex: {"prazos_section": "editar", "prazo_selected_id": 123})
    - clear_qp: se True, limpa query params existentes antes de aplicar qp

    Observação:
    - Seta nav_target para o app principal decidir renderizar a página
    - Faz rerun no final
    """
    _clear_page_state(menu_key, state)
    _set_query_params(qp, clear_existing=clear_qp)
    _set_state(state)

    st.session_state[_LAST_MENU_KEY] = menu_key
    st.session_state[_NAV_TARGET_KEY] = menu_key
    st.rerun()
