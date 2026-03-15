from __future__ import annotations

import json
from typing import Any, Iterable

import streamlit as st

MENU_DEFAULT = "Painel"

STATE_DEFAULTS: dict[str, Any] = {
    # navegação
    "sidebar_menu": MENU_DEFAULT,
    "top_nav_menu": MENU_DEFAULT,
    "_last_menu": MENU_DEFAULT,
    "nav_target": None,
    # sincronização / refresh
    "data_version": 0,
    "_qp_applied": None,
    # preferências visuais
    "ui_show_top_nav": True,
    "ui_mobile_cards": True,
    "force_mobile": False,
    # suporte / diagnóstico
    "ui_debug": False,
}

_TRUE_VALUES = {"1", "true", "yes", "on", "sim"}
_FALSE_VALUES = {"0", "false", "no", "off", "nao", "não"}


# ==========================================================
# Init
# ==========================================================


def init_state() -> None:
    """Inicializa os valores padrão da UI apenas uma vez por sessão."""
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ==========================================================
# Helpers de sessão
# ==========================================================


def _get_state(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def _set_state(key: str, value: Any) -> None:
    st.session_state[key] = value


def _as_clean_str(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default

    text = str(value).strip()
    return text if text else default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    normalized = str(value).strip().lower()

    if normalized in _TRUE_VALUES:
        return True

    if normalized in _FALSE_VALUES:
        return False

    return default


# ==========================================================
# Query params
# ==========================================================


def _get_qp():
    return st.query_params


def _normalize_qp_value(value: Any) -> Any:
    """
    Normaliza valores para uso nos query params do Streamlit.

    Regras:
    - None remove a chave
    - dict vira JSON string
    - list/tuple/set vira lista de strings
    - bool vira "1" / "0"
    - demais tipos viram string
    """
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
    """
    Atualiza query params.
    Valor None remove explicitamente a chave.
    """
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
    """Lê um query param como string."""
    qp = _get_qp()

    if key not in qp:
        return default

    value = qp[key]

    if isinstance(value, list):
        return _as_clean_str(value[0], default=default) if value else default

    return _as_clean_str(value, default=default)


def get_qp_json(key: str, default: Any = None) -> Any:
    """Lê um query param contendo JSON serializado."""
    value = get_qp_str(key)

    if value is None:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def get_qp_bool(key: str, default: bool = False) -> bool:
    """Lê um query param booleano em formatos comuns."""
    value = get_qp_str(key)
    return _as_bool(value, default=default)


# ==========================================================
# Menu / navegação
# ==========================================================


def is_valid_menu(menu: str | None, allowed: Iterable[str] | None = None) -> bool:
    """
    Valida se o menu é uma string não vazia e, se informado,
    pertence ao conjunto permitido.
    """
    menu_value = _as_clean_str(menu)
    if not menu_value:
        return False

    if allowed is None:
        return True

    allowed_set = {
        item.strip() for item in allowed if isinstance(item, str) and item.strip()
    }
    return menu_value in allowed_set


def get_current_menu(default: str = MENU_DEFAULT) -> str:
    """Retorna o menu atual persistido na sessão."""
    value = _as_clean_str(_get_state("_last_menu"), default=default)
    return value or default


def _sync_menu_controls(menu: str) -> None:
    _set_state("_last_menu", menu)
    _set_state("sidebar_menu", menu)
    _set_state("top_nav_menu", menu)


def set_current_menu(menu: str, *, update_qp: bool = True) -> None:
    """
    Define o menu atual e sincroniza os controles visuais de navegação.
    Esta é a fonte oficial de verdade do menu corrente.
    """
    menu_value = _as_clean_str(menu)
    if not menu_value:
        return

    _sync_menu_controls(menu_value)
    _set_state("nav_target", None)

    if update_qp:
        _set_qp(menu=menu_value)


def navigate(
    menu: str | None = None,
    state: dict[str, Any] | None = None,
    **params: Any,
) -> None:
    """
    Solicita navegação para um menu e injeta estado opcional via query params.

    Exemplos:
        navigate("Prazos")
        navigate("Prazos", state={"prazos_section": "Lista"})
        navigate(menu="Financeiro", financeiro_section="Lançamentos")
    """
    payload: dict[str, Any] = {}

    menu_value = _as_clean_str(menu)
    if menu_value:
        _set_state("nav_target", menu_value)
        payload["menu"] = menu_value

    if state:
        payload.update(state)

    if params:
        payload.update(params)

    if payload:
        _set_qp(**payload)


def consume_nav_target(default: str | None = None) -> str | None:
    """Consome uma única vez o alvo de navegação pendente."""
    target = _as_clean_str(_get_state("nav_target"), default=default)
    _set_state("nav_target", None)
    return target


def on_top_nav_change() -> None:
    """Callback do menu superior."""
    menu = _as_clean_str(_get_state("top_nav_menu"), default=MENU_DEFAULT)
    if menu and menu != _get_state("_last_menu"):
        set_current_menu(menu)


def on_sidebar_menu_change() -> None:
    """Callback do menu lateral."""
    menu = _as_clean_str(_get_state("sidebar_menu"), default=MENU_DEFAULT)
    if menu and menu != _get_state("_last_menu"):
        set_current_menu(menu)


# ==========================================================
# Sync com query params
# ==========================================================


def apply_menu_from_qp(
    *,
    allowed: Iterable[str] | None = None,
    default: str = MENU_DEFAULT,
) -> str:
    """
    Aplica o menu vindo da URL, se válido, e retorna o menu efetivo.
    Mantém a navegação previsível após refresh ou links internos.
    """
    qp_menu = get_qp_str("menu")

    if is_valid_menu(qp_menu, allowed):
        menu_value = _as_clean_str(qp_menu, default=default) or default
        set_current_menu(menu_value, update_qp=False)
        return menu_value

    current = get_current_menu(default=default)

    if not is_valid_menu(current, allowed):
        current = default
        set_current_menu(current, update_qp=False)

    return current


# ==========================================================
# Preferências visuais
# ==========================================================


def get_ui_flag(key: str, default: bool = False) -> bool:
    return _as_bool(_get_state(key, default), default=default)


def set_ui_flag(key: str, value: bool) -> None:
    _set_state(key, bool(value))


# ==========================================================
# Refresh / cache visual
# ==========================================================


def _global_data_version_key() -> str:
    return "data_version"


def _user_data_version_key(owner_user_id: int) -> str:
    return f"data_version_{int(owner_user_id)}"


def _resolve_data_version_key(owner_user_id: int | None = None) -> str:
    return (
        _global_data_version_key()
        if owner_user_id is None
        else _user_data_version_key(owner_user_id)
    )


def bump_data_version(owner_user_id: int | None = None) -> int:
    """
    Incrementa a versão de dados para invalidação de cache visual.

    Compatibilidade:
    - bump_data_version() -> versão global
    - bump_data_version(owner_user_id) -> versão por usuário
    """
    key = _resolve_data_version_key(owner_user_id)

    current = int(_get_state(key, 0)) + 1
    _set_state(key, current)

    # Compatibilidade com telas legadas que dependem da versão global
    if owner_user_id is not None:
        global_key = _global_data_version_key()
        _set_state(global_key, int(_get_state(global_key, 0)) + 1)

    return current


def get_data_version(owner_user_id: int | None = None) -> int:
    """
    Retorna a versão atual dos dados.

    Compatibilidade:
    - get_data_version() -> versão global
    - get_data_version(owner_user_id) -> versão por usuário
    """
    key = _resolve_data_version_key(owner_user_id)
    return int(_get_state(key, 0))


def reset_data_version(owner_user_id: int | None = None) -> None:
    """
    Reseta a versão de dados.

    Compatibilidade:
    - reset_data_version() -> global
    - reset_data_version(owner_user_id) -> por usuário
    """
    key = _resolve_data_version_key(owner_user_id)
    _set_state(key, 0)
