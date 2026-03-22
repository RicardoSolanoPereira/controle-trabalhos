from __future__ import annotations

import json
from typing import Any, Iterable

import streamlit as st

__all__ = [
    "MENU_DEFAULT",
    "STATE_DEFAULTS",
    "init_state",
    "has_state",
    "get_state",
    "set_state",
    "set_states",
    "del_state",
    "toggle_state_bool",
    "is_valid_menu",
    "get_current_menu",
    "set_current_menu",
    "get_current_section",
    "set_current_section",
    "navigate",
    "navigate_to_section",
    "consume_nav_target",
    "peek_nav_target",
    "on_top_nav_change",
    "on_sidebar_menu_change",
    "apply_menu_from_qp",
    "clear_qp_keys",
    "set_qp",
    "get_qp_str",
    "get_qp_json",
    "get_qp_bool",
    "get_qp_int",
    "get_ui_flag",
    "set_ui_flag",
    "toggle_ui_flag",
    "apply_ui_flags_from_qp",
    "sync_ui_flags_to_qp",
    "bump_data_version",
    "get_data_version",
    "reset_data_version",
]

MENU_DEFAULT = "Painel"

VALID_MENUS = {
    "Painel",
    "Trabalhos",
    "Processos",
    "Prazos",
    "Financeiro",
    "Agenda",
    "Andamentos",
    "Clientes",
    "Configurações",
    "Agendamentos",
}

_MENU_ALIASES: dict[str, str] = {
    "Agendamentos": "Agenda",
}

STATE_DEFAULTS: dict[str, Any] = {
    "sidebar_menu": MENU_DEFAULT,
    "top_nav_menu": MENU_DEFAULT,
    "_last_menu": MENU_DEFAULT,
    "nav_target": None,
    "ui_nav_mode": "sidebar",
    "dashboard_section": "Visão geral",
    "trabalhos_section": "Lista",
    "processos_section": "Lista",
    "prazos_section": "Lista",
    "financeiro_section": "Lançamentos",
    "agenda_section": "Agenda",
    "andamentos_section": "Lista",
    "clientes_section": "Lista",
    "configuracoes_section": "Geral",
    "agendamentos_section": "Agenda",
    "last_action_source": None,
    "last_action_label": None,
    "data_version": 0,
    "ui_show_top_nav": True,
    "ui_mobile_cards": False,
    "force_mobile": False,
    "ui_dense_mode": False,
    "ui_show_secondary_info": True,
    "ui_debug": False,
}

_TRUE_VALUES = {"1", "true", "yes", "on", "sim"}
_FALSE_VALUES = {"0", "false", "no", "off", "nao", "não"}

_UI_FLAG_TO_QP_KEY: dict[str, str] = {
    "ui_show_top_nav": "topnav",
    "ui_mobile_cards": "mobile_cards",
    "force_mobile": "force_mobile",
    "ui_dense_mode": "dense",
    "ui_show_secondary_info": "secondary",
    "ui_debug": "debug",
}

_MENU_TO_SECTION_KEY: dict[str, str] = {
    "Painel": "dashboard_section",
    "Trabalhos": "trabalhos_section",
    "Processos": "processos_section",
    "Prazos": "prazos_section",
    "Financeiro": "financeiro_section",
    "Agenda": "agenda_section",
    "Andamentos": "andamentos_section",
    "Clientes": "clientes_section",
    "Configurações": "configuracoes_section",
    "Agendamentos": "agenda_section",
}


# ==========================================================
# Helpers básicos
# ==========================================================


def has_state(key: str) -> bool:
    return key in st.session_state


def get_state(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    st.session_state[key] = value


def set_states(values: dict[str, Any]) -> None:
    for key, value in values.items():
        st.session_state[key] = value


def del_state(key: str) -> None:
    try:
        del st.session_state[key]
    except Exception:
        pass


def toggle_state_bool(key: str, default: bool = False) -> bool:
    current = _as_bool(get_state(key, default), default=default)
    updated = not current
    set_state(key, updated)
    return updated


# ==========================================================
# Init
# ==========================================================


def init_state() -> None:
    """
    Inicializa a sessão com defaults sem sobrescrever valores já existentes.
    Também normaliza chaves legadas.
    """
    for key, value in STATE_DEFAULTS.items():
        st.session_state.setdefault(key, value)

    _normalize_legacy_state()


def _normalize_legacy_state() -> None:
    """
    Compatibilidade com nomenclaturas antigas.
    Esta função roda no início do script, antes da renderização dos widgets.
    """
    current_menu = _normalize_menu(get_state("_last_menu"), default=MENU_DEFAULT)
    sidebar_menu = _normalize_menu(get_state("sidebar_menu"), default=MENU_DEFAULT)
    top_nav_menu = _normalize_menu(get_state("top_nav_menu"), default=MENU_DEFAULT)
    nav_target = _normalize_menu(get_state("nav_target"), default=None)

    set_states(
        {
            "_last_menu": current_menu,
            "sidebar_menu": sidebar_menu,
            "top_nav_menu": top_nav_menu,
            "nav_target": nav_target,
        }
    )

    agenda_section = get_state("agenda_section")
    agendamentos_section = get_state("agendamentos_section")

    if agenda_section is None and agendamentos_section is not None:
        agenda_section = agendamentos_section

    if agenda_section is None:
        agenda_section = STATE_DEFAULTS["agenda_section"]

    set_state("agenda_section", agenda_section)
    set_state("agendamentos_section", agenda_section)


# ==========================================================
# Conversores internos
# ==========================================================


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


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default

    if isinstance(value, bool):
        return int(value)

    try:
        return int(str(value).strip())
    except Exception:
        return default


def _json_dumps_safe(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _normalize_menu(menu: Any, default: str | None = None) -> str | None:
    menu_value = _as_clean_str(menu, default=default)
    if not menu_value:
        return default
    return _MENU_ALIASES.get(menu_value, menu_value)


def _normalize_section_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Garante compatibilidade entre agenda_section e agendamentos_section.
    """
    normalized = dict(payload)

    if "agendamentos_section" in normalized and "agenda_section" not in normalized:
        normalized["agenda_section"] = normalized["agendamentos_section"]

    if "agenda_section" in normalized:
        normalized["agendamentos_section"] = normalized["agenda_section"]

    return normalized


# ==========================================================
# Query params
# ==========================================================


def _get_qp():
    return st.query_params


def _normalize_qp_value(value: Any) -> Any:
    """
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
        return _json_dumps_safe(value)

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


def set_qp(**params: Any) -> None:
    _set_qp(**params)


def clear_qp_keys(*keys: str) -> None:
    if not keys:
        return

    qp = _get_qp()
    for key in keys:
        try:
            del qp[key]
        except Exception:
            pass


def get_qp_str(key: str, default: str | None = None) -> str | None:
    qp = _get_qp()

    if key not in qp:
        return default

    value = qp[key]

    if isinstance(value, list):
        return _as_clean_str(value[0], default=default) if value else default

    return _as_clean_str(value, default=default)


def get_qp_json(key: str, default: Any = None) -> Any:
    value = get_qp_str(key)
    if value is None:
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def get_qp_bool(key: str, default: bool = False) -> bool:
    return _as_bool(get_qp_str(key), default=default)


def get_qp_int(key: str, default: int = 0) -> int:
    return _as_int(get_qp_str(key), default=default)


# ==========================================================
# Navegação
# ==========================================================


def is_valid_menu(menu: str | None, allowed: Iterable[str] | None = None) -> bool:
    menu_value = _normalize_menu(menu)
    if not menu_value:
        return False

    if allowed is None:
        return menu_value in {_normalize_menu(item) for item in VALID_MENUS}

    allowed_set = {
        _normalize_menu(item)
        for item in allowed
        if isinstance(item, str) and item.strip()
    }
    return menu_value in allowed_set


def _sync_menu_controls(menu: str) -> None:
    """
    Mantém o estado lógico da navegação alinhado sem alterar widgets já instanciados.
    """
    menu_value = _normalize_menu(menu, default=MENU_DEFAULT) or MENU_DEFAULT
    set_state("_last_menu", menu_value)


def get_current_menu(default: str = MENU_DEFAULT) -> str:
    value = _normalize_menu(get_state("_last_menu"), default=default)
    return value or default


def set_current_menu(menu: str, *, update_qp: bool = True) -> None:
    menu_value = _normalize_menu(menu)
    if not menu_value:
        return

    _sync_menu_controls(menu_value)
    set_state("nav_target", None)

    if update_qp:
        _set_qp(menu=menu_value)


def get_current_section(
    menu: str | None = None, default: str | None = None
) -> str | None:
    menu_value = _normalize_menu(menu, default=get_current_menu())
    if not menu_value:
        return default

    section_key = _MENU_TO_SECTION_KEY.get(menu_value)
    if not section_key:
        return default

    return _as_clean_str(get_state(section_key), default=default)


def set_current_section(menu: str, section: str, *, update_qp: bool = False) -> None:
    menu_value = _normalize_menu(menu)
    section_value = _as_clean_str(section)

    if not menu_value or not section_value:
        return

    section_key = _MENU_TO_SECTION_KEY.get(menu_value)
    if not section_key:
        return

    set_state(section_key, section_value)

    if menu_value == "Agenda":
        set_state("agendamentos_section", section_value)

    if update_qp:
        _set_qp(section=section_value)


def navigate(
    menu: str | None = None,
    state: dict[str, Any] | None = None,
    update_session: bool = True,
    clear_keys: Iterable[str] | None = None,
    **params: Any,
) -> None:
    """
    Solicita navegação e sincroniza parâmetros opcionais via URL.
    """
    payload: dict[str, Any] = {}

    menu_value = _normalize_menu(menu)
    if menu_value:
        if update_session:
            set_state("nav_target", menu_value)
            _sync_menu_controls(menu_value)
        payload["menu"] = menu_value

    normalized_state = _normalize_section_payload(state or {})
    normalized_params = _normalize_section_payload(params or {})

    if normalized_state:
        if update_session:
            set_states(normalized_state)
        payload.update(normalized_state)

    if normalized_params:
        if update_session:
            set_states(normalized_params)
        payload.update(normalized_params)

    if clear_keys:
        clear_qp_keys(*list(clear_keys))

    if payload:
        _set_qp(**payload)


def navigate_to_section(
    menu: str,
    section: str,
    *,
    state: dict[str, Any] | None = None,
    source: str | None = None,
    action_label: str | None = None,
    update_qp: bool = True,
) -> None:
    """
    Navegação padronizada para atalhos internos e ações rápidas.
    """
    menu_value = _normalize_menu(menu)
    section_value = _as_clean_str(section)

    if not menu_value or not section_value:
        return

    section_key = _MENU_TO_SECTION_KEY.get(menu_value)
    payload_state: dict[str, Any] = {}

    if section_key:
        payload_state[section_key] = section_value

    if menu_value == "Agenda":
        payload_state["agendamentos_section"] = section_value

    if state:
        payload_state.update(state)

    if source:
        payload_state["last_action_source"] = source

    if action_label:
        payload_state["last_action_label"] = action_label

    payload_state = _normalize_section_payload(payload_state)

    navigate(
        menu=menu_value,
        state=payload_state,
        update_session=True,
    )

    if update_qp:
        _set_qp(menu=menu_value, section=section_value)


def peek_nav_target(default: str | None = None) -> str | None:
    return _normalize_menu(get_state("nav_target"), default=default)


def consume_nav_target(default: str | None = None) -> str | None:
    target = _normalize_menu(get_state("nav_target"), default=default)
    set_state("nav_target", None)
    return target


def on_top_nav_change() -> None:
    menu = _normalize_menu(get_state("top_nav_menu"), default=MENU_DEFAULT)
    if menu and menu != get_state("_last_menu"):
        set_current_menu(menu)


def on_sidebar_menu_change() -> None:
    menu = _normalize_menu(get_state("sidebar_menu"), default=MENU_DEFAULT)
    if menu and menu != get_state("_last_menu"):
        set_current_menu(menu)


def apply_menu_from_qp(
    *,
    allowed: Iterable[str] | None = None,
    default: str = MENU_DEFAULT,
) -> str:
    """
    Aplica o menu vindo da URL, se válido, e retorna o menu efetivo.
    """
    qp_menu = _normalize_menu(get_qp_str("menu"))
    qp_section = get_qp_str("section")

    if is_valid_menu(qp_menu, allowed):
        menu_value = _normalize_menu(qp_menu, default=default) or default
        _sync_menu_controls(menu_value)
        set_state("nav_target", None)

        if qp_section:
            set_current_section(menu_value, qp_section, update_qp=False)

        return menu_value

    current = get_current_menu(default=default)

    if not is_valid_menu(current, allowed):
        current = default
        _sync_menu_controls(current)
        set_state("nav_target", None)

    return current


# ==========================================================
# Preferências visuais
# ==========================================================


def get_ui_flag(key: str, default: bool = False) -> bool:
    return _as_bool(get_state(key, default), default=default)


def set_ui_flag(key: str, value: bool) -> None:
    set_state(key, bool(value))


def toggle_ui_flag(key: str, default: bool = False) -> bool:
    current = get_ui_flag(key, default=default)
    updated = not current
    set_ui_flag(key, updated)
    return updated


def apply_ui_flags_from_qp() -> None:
    """
    Aplica preferências visuais vindas da URL.
    """
    for state_key, qp_key in _UI_FLAG_TO_QP_KEY.items():
        qp_value = get_qp_str(qp_key)
        if qp_value is None:
            continue
        set_state(state_key, _as_bool(qp_value, default=get_ui_flag(state_key)))


def sync_ui_flags_to_qp(*, only_existing_keys: bool = False) -> None:
    """
    Sincroniza flags visuais com a URL.
    """
    payload: dict[str, Any] = {}

    for state_key, qp_key in _UI_FLAG_TO_QP_KEY.items():
        if only_existing_keys and get_qp_str(qp_key) is None:
            continue
        payload[qp_key] = get_ui_flag(state_key)

    if payload:
        _set_qp(**payload)


# ==========================================================
# Refresh / invalidação visual
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
    Incrementa a versão de dados.
    """
    key = _resolve_data_version_key(owner_user_id)
    current = _as_int(get_state(key, 0), default=0) + 1
    set_state(key, current)

    if owner_user_id is not None:
        global_key = _global_data_version_key()
        global_current = _as_int(get_state(global_key, 0), default=0) + 1
        set_state(global_key, global_current)

    return current


def get_data_version(owner_user_id: int | None = None) -> int:
    key = _resolve_data_version_key(owner_user_id)
    return _as_int(get_state(key, 0), default=0)


def reset_data_version(owner_user_id: int | None = None) -> None:
    key = _resolve_data_version_key(owner_user_id)
    set_state(key, 0)
