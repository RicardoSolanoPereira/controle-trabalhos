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


# ==========================================================
# Init
# ==========================================================


def init_state() -> None:
    """Inicializa valores padrão da UI."""
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ==========================================================
# Query params
# ==========================================================


def _get_qp():
    return st.query_params


def _normalize_qp_value(value: Any):
    """Normaliza valores para uso em query params do Streamlit."""
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
    """Atualiza query params preservando remoção explícita com valor None."""
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


def clear_qp_keys(*keys: str) -> None:
    """Remove chaves específicas dos query params."""
    if not keys:
        return

    qp = _get_qp()
    for key in keys:
        try:
            del qp[key]
        except Exception:
            pass


def get_qp_str(key: str, default: str | None = None) -> str | None:
    """Lê query param como string."""
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
    """Lê query param contendo JSON serializado."""
    value = get_qp_str(key)

    if value is None:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def get_qp_bool(key: str, default: bool = False) -> bool:
    """Lê query param booleano em formatos comuns."""
    value = get_qp_str(key)

    if value is None:
        return default

    return str(value).strip().lower() in {"1", "true", "yes", "on", "sim"}


# ==========================================================
# Menu / navegação
# ==========================================================


def is_valid_menu(menu: str | None, allowed: Iterable[str] | None = None) -> bool:
    """Valida se o menu é uma string válida e, se informado, pertence ao conjunto permitido."""
    if not isinstance(menu, str) or not menu.strip():
        return False

    if allowed is None:
        return True

    return menu in set(allowed)


def get_current_menu(default: str = MENU_DEFAULT) -> str:
    """Obtém o menu atual persistido na sessão."""
    value = st.session_state.get("_last_menu", default)

    if not isinstance(value, str) or not value.strip():
        return default

    return value


def set_current_menu(menu: str, *, update_qp: bool = True) -> None:
    """Define o menu atual e sincroniza os controles de navegação."""
    if not isinstance(menu, str) or not menu.strip():
        return

    st.session_state["_last_menu"] = menu
    st.session_state["sidebar_menu"] = menu
    st.session_state["top_nav_menu"] = menu

    if update_qp:
        _set_qp(menu=menu)


def navigate(
    menu: str | None = None, state: dict[str, Any] | None = None, **params: Any
) -> None:
    """
    Navega para um menu e opcionalmente injeta estado via query params.

    Exemplos:
        navigate("Prazos")
        navigate("Prazos", state={"prazos_section": "Lista"})
        navigate(menu="Financeiro", financeiro_section="Lançamentos")
    """
    payload: dict[str, Any] = {}

    if menu is not None:
        st.session_state["nav_target"] = menu
        payload["menu"] = menu

    if state:
        payload.update(state)

    if params:
        payload.update(params)

    _set_qp(**payload)


def consume_nav_target(default: str | None = None) -> str | None:
    """Consome o alvo de navegação pendente uma única vez."""
    target = st.session_state.get("nav_target")
    st.session_state["nav_target"] = None
    return target if target is not None else default


def on_top_nav_change() -> None:
    """Callback do menu superior."""
    menu = st.session_state.get("top_nav_menu", MENU_DEFAULT)

    if menu != st.session_state.get("_last_menu"):
        set_current_menu(menu)


def on_sidebar_menu_change() -> None:
    """Callback do menu lateral."""
    menu = st.session_state.get("sidebar_menu", MENU_DEFAULT)

    if menu != st.session_state.get("_last_menu"):
        set_current_menu(menu)


# ==========================================================
# Sync com query params
# ==========================================================


def apply_menu_from_qp(
    *, allowed: Iterable[str] | None = None, default: str = MENU_DEFAULT
) -> str:
    """
    Aplica o menu vindo da URL, se válido, e retorna o menu efetivo.
    Útil para manter navegação previsível após refresh ou links internos.
    """
    qp_menu = get_qp_str("menu")

    if is_valid_menu(qp_menu, allowed):
        set_current_menu(qp_menu, update_qp=False)
        return qp_menu  # type: ignore[return-value]

    current = get_current_menu(default=default)

    if not is_valid_menu(current, allowed):
        current = default
        set_current_menu(current, update_qp=False)

    return current


# ==========================================================
# Cache / refresh visual
# ==========================================================


def bump_data_version() -> int:
    """Incrementa a versão global de dados para invalidação de cache visual."""
    current = int(st.session_state.get("data_version", 0)) + 1
    st.session_state["data_version"] = current
    return current


def get_data_version() -> int:
    """Retorna a versão atual dos dados."""
    return int(st.session_state.get("data_version", 0))
