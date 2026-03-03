"""
app/ui_state.py

Centraliza navegação e passagem de contexto entre telas.

O projeto usa um mecanismo de navegação "segura" via `nav_target` aplicado
no `app/main.py` antes do `st.sidebar.radio()` existir.

Aqui empacotamos:
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
    "Financeiro": {
        "financeiro_section",
        "financeiro_selected_id",
    },
    "Agendamentos": {
        "agendamentos_section",
        "agendamento_selected_id",
    },
    # Se quiser, já deixa pronto (sem efeito se não usar):
    # "Andamentos": {"andamentos_section", "andamento_selected_id"},
    # "Dashboard": set(),
}

_LAST_MENU_KEY = "__last_menu"


# ------------------------------------------------------------
# Query params helpers (compatível com versões diferentes)
# ------------------------------------------------------------
def _qp_get(key: str) -> Any:
    """Obtém query param (pode vir como str, lista ou None)."""
    try:
        return st.query_params.get(key)  # type: ignore[attr-defined]
    except Exception:
        # fallback para versões antigas
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
def _set_query_params(qp: dict[str, Any] | None) -> None:
    """Atualiza query params de forma robusta.

    Regras:
    - None / "" remove o parâmetro
    - list/tuple vira múltiplos valores
    - tudo é convertido para str
    """
    if not qp:
        return

    for k, v in qp.items():
        if v is None or v == "":
            # remoção segura (compatível com versões que não suportam `del`)
            try:
                st.query_params.pop(k, None)  # type: ignore[attr-defined]
            except Exception:
                try:
                    # fallback antigo (reconstrói qp)
                    params = st.experimental_get_query_params()
                    params.pop(k, None)
                    st.experimental_set_query_params(**params)
                except Exception:
                    pass
            continue

        if isinstance(v, (list, tuple)):
            values = [str(x) for x in v if x is not None and x != ""]
            try:
                st.query_params[k] = values  # type: ignore[attr-defined]
            except Exception:
                try:
                    params = st.experimental_get_query_params()
                    params[k] = values
                    st.experimental_set_query_params(**params)
                except Exception:
                    pass
        else:
            try:
                st.query_params[k] = str(v)  # type: ignore[attr-defined]
            except Exception:
                try:
                    params = st.experimental_get_query_params()
                    params[k] = str(v)
                    st.experimental_set_query_params(**params)
                except Exception:
                    pass


def _set_state(state: dict[str, Any] | None) -> None:
    if not state:
        return
    for k, v in state.items():
        st.session_state[k] = v


def _clear_page_state(menu_key: str, incoming_state: dict[str, Any] | None) -> None:
    """Remove chaves de estado da tela destino, exceto as que vierem explicitamente em `incoming_state`.

    Isso evita herdar filtros/abas de uma visita anterior (ex.: prazo_open_window=Atrasados).
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
    """Chamar após o sidebar.radio retornar o menu selecionado.

    Se o usuário trocar de aba pelo menu (sem usar navigate()),
    limpamos o estado da tela destino para evitar 'estado grudado'.
    """
    last = st.session_state.get(_LAST_MENU_KEY)
    if last != current_menu:
        _clear_page_state(current_menu, incoming_state=None)
        st.session_state[_LAST_MENU_KEY] = current_menu


def navigate(
    menu_key: str,
    *,
    qp: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> None:
    """Navega para `menu_key` carregando parâmetros.

    Args:
        menu_key: chave do MENU (ex.: "Processos", "Prazos", "Financeiro").
        qp: query params (ex.: {"status": "Ativo"}).
        state: session_state extra (ex.: {"processos_section": "Lista"}).
    """
    # 1) Limpa o estado da tela destino (para evitar herança indevida)
    _clear_page_state(menu_key, state)

    # 2) Aplica qp/state
    _set_query_params(qp)
    _set_state(state)

    # 3) Marca "último menu" também (mantém consistência)
    st.session_state[_LAST_MENU_KEY] = menu_key

    # 4) Navegação segura (main.py aplica antes do radio existir)
    st.session_state["nav_target"] = menu_key
    st.rerun()
