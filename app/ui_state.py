from __future__ import annotations

import json
import streamlit as st


# =========================
# Inicialização
# =========================
def init_state() -> None:
    defaults = {
        "sidebar_menu": "Painel",
        "top_nav_menu": "Painel",
        "data_version": 0,
        "nav_target": None,
        "_last_menu": "Painel",
        "_qp_applied": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# =========================
# Query Params
# =========================
def _get_qp():
    return st.query_params


def _normalize_value(v):
    if isinstance(v, dict):
        return json.dumps(v)
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v]
    return str(v)


def _set_qp(**params):
    qp = st.query_params
    for k, v in params.items():
        qp[k] = _normalize_value(v)


def get_qp_str(key: str, default: str | None = None) -> str | None:
    qp = _get_qp()
    if key not in qp:
        return default

    val = qp[key]
    if isinstance(val, list):
        return val[0]
    return val


def get_qp_json(key: str, default=None):
    val = get_qp_str(key)
    if val is None:
        return default
    try:
        return json.loads(val)
    except Exception:
        return default


# =========================
# Navegação
# =========================
def navigate(menu: str | None = None, **params):
    """
    Deep-link interno.

    Não altera diretamente chaves de widgets já instanciados.
    Apenas agenda a navegação e atualiza query params.
    O main.py aplicará o target ANTES de renderizar os widgets.
    """
    if menu:
        st.session_state["nav_target"] = menu
        params["menu"] = menu
    _set_qp(**params)


def consume_nav_target(default: str | None = None):
    target = st.session_state.get("nav_target")
    if target is None:
        return default
    st.session_state["nav_target"] = None
    return target


def on_menu_change(menu: str):
    """
    Atualiza somente o estado canônico de navegação e a URL.

    IMPORTANTE:
    - não altera top_nav_menu
    - não altera sidebar_menu

    Essas chaves pertencem aos widgets e não devem ser sobrescritas
    depois da instanciação.
    """
    prev = st.session_state.get("_last_menu")
    if prev == menu:
        return

    st.session_state["_last_menu"] = menu
    _set_qp(menu=menu)


# =========================
# Controle de atualização
# =========================
def bump_data_version():
    st.session_state["data_version"] = int(st.session_state.get("data_version", 0)) + 1


def get_data_version():
    return int(st.session_state.get("data_version", 0))
