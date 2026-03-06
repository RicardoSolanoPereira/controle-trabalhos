from __future__ import annotations

import json
from typing import Any, Iterable

import streamlit as st

MENU_DEFAULT = "Painel"

STATE_DEFAULTS: dict[str, Any] = {
    "sidebar_menu": MENU_DEFAULT,
    "top_nav_menu": MENU_DEFAULT,
    "_last_menu": MENU_DEFAULT,
    "nav_target": None,
    "data_version": 0,
    "_qp_applied": None,
    "ui_show_top_nav": True,
    "ui_mobile_cards": True,
    "force_mobile": False,
    "ui_debug": False,
}


def init_state() -> None:
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _get_qp():
    return st.query_params


def _normalize_qp_value(value: Any):
    if value is None:
        return None
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _set_qp(**params: Any) -> None:
    qp = _get_qp()
    for key, value in params.items():
        normalized = _normalize_qp_value(value)

        if normalized is None:
            try:
                del qp[key]
            except Exception:
                pass
            continue

        qp[key] = normalized


def get_qp_str(key: str, default: str | None = None) -> str | None:
    qp = _get_qp()
    if key not in qp:
        return default

    value = qp[key]
    if isinstance(value, list):
        return str(value[0]) if value else default
    if value is None:
        return default
    return str(value)


def get_qp_json(key: str, default: Any = None) -> Any:
    value = get_qp_str(key)
    if value is None:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def is_valid_menu(menu: str | None, allowed: Iterable[str] | None = None) -> bool:
    if not isinstance(menu, str) or not menu.strip():
        return False
    if allowed is None:
        return True
    return menu in set(allowed)


def get_current_menu(default: str = MENU_DEFAULT) -> str:
    value = st.session_state.get("_last_menu", default)
    if not isinstance(value, str) or not value.strip():
        return default
    return value


def set_current_menu(menu: str, *, update_qp: bool = True) -> None:
    if not isinstance(menu, str) or not menu.strip():
        return

    st.session_state["_last_menu"] = menu
    st.session_state["sidebar_menu"] = menu
    st.session_state["top_nav_menu"] = menu

    if update_qp:
        _set_qp(menu=menu)


def navigate(menu: str | None = None, **params: Any) -> None:
    if menu is not None:
        st.session_state["nav_target"] = menu
        params["menu"] = menu
    _set_qp(**params)


def consume_nav_target(default: str | None = None) -> str | None:
    target = st.session_state.get("nav_target")
    st.session_state["nav_target"] = None
    return target if target is not None else default


def on_top_nav_change() -> None:
    menu = st.session_state.get("top_nav_menu", MENU_DEFAULT)
    if menu != st.session_state.get("_last_menu"):
        set_current_menu(menu)


def on_sidebar_menu_change() -> None:
    menu = st.session_state.get("sidebar_menu", MENU_DEFAULT)
    if menu != st.session_state.get("_last_menu"):
        set_current_menu(menu)


def bump_data_version() -> int:
    current = int(st.session_state.get("data_version", 0)) + 1
    st.session_state["data_version"] = current
    return current


def get_data_version() -> int:
    return int(st.session_state.get("data_version", 0))
