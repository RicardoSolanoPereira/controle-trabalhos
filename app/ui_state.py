from __future__ import annotations
import json
import streamlit as st


# =========================
# Inicialização
# =========================


def init_state() -> None:

    defaults = {
        "menu": "Painel",
        "data_version": 0,
        "nav_target": None,
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

    if menu:
        st.session_state["menu"] = menu
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

    st.session_state["menu"] = menu
    _set_qp(menu=menu)


# =========================
# Controle de atualização
# =========================


def bump_data_version():

    if "data_version" not in st.session_state:
        st.session_state["data_version"] = 0

    st.session_state["data_version"] += 1


def get_data_version():

    return st.session_state.get("data_version", 0)
