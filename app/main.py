from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.connection import session_scope
from db.init_db import init_db
from db.models import User

from ui import agendamentos, andamentos, dashboard, financeiro, prazos, processos
from ui.layout import content_shell
from ui.theme import app_error, inject_global_css
from ui_state import (
    MENU_DEFAULT,
    consume_nav_target,
    get_current_menu,
    get_qp_str,
    init_state,
    is_valid_menu,
    on_top_nav_change,
    set_current_menu,
)

# ==========================================================
# Bootstrap
# ==========================================================

Path("data").mkdir(parents=True, exist_ok=True)
load_dotenv()

DEBUG = os.getenv("DEBUG", "0").strip() == "1"

DEFAULT_SIDEBAR_STATE = os.getenv("SIDEBAR_STATE", "collapsed").strip().lower()
if DEFAULT_SIDEBAR_STATE not in {"expanded", "collapsed"}:
    DEFAULT_SIDEBAR_STATE = "collapsed"

BUILD_ID = os.getenv("BUILD_ID", "2026-02-28-DEF-1").strip()
DEFAULT_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "admin@local").strip()
DEFAULT_NAME = os.getenv("DEFAULT_USER_NAME", "Administrador").strip()

APP_TITLE = "Gestão Técnica"
APP_ICON = "📐"

NAV_MODE_KEY = "ui_nav_mode"

SIDEBAR_MENU_KEY = "sidebar_menu_radio"
TOP_NAV_MENU_KEY = "top_nav_menu"

SIDEBAR_NAV_MODE_WIDGET_KEY = "sidebar_nav_mode_widget"
TOP_NAV_MODE_WIDGET_KEY = "top_nav_mode_widget"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state=DEFAULT_SIDEBAR_STATE,
)

# ==========================================================
# Menu / rotas
# ==========================================================

MENU_KEYS = [
    "Painel",
    "Trabalhos",
    "Prazos",
    "Agenda",
    "Andamentos",
    "Financeiro",
]

MENU_LABELS = {
    "Painel": "📊 Painel",
    "Trabalhos": "📁 Trabalhos",
    "Prazos": "⏳ Prazos",
    "Agenda": "📅 Agenda",
    "Andamentos": "🧾 Andamentos",
    "Financeiro": "💰 Financeiro",
}

ROUTES: dict[str, Callable[[int], None]] = {
    "Painel": dashboard.render,
    "Trabalhos": processos.render,
    "Prazos": prazos.render,
    "Agenda": agendamentos.render,
    "Andamentos": andamentos.render,
    "Financeiro": financeiro.render,
}

# ==========================================================
# Estado base
# ==========================================================

init_state()

st.session_state.setdefault(NAV_MODE_KEY, "sidebar")
st.session_state.setdefault("force_mobile", False)
st.session_state.setdefault("ui_mobile_cards", False)
st.session_state.setdefault("ui_debug", False)

# ==========================================================
# Bootstrap cache
# ==========================================================


@st.cache_resource
def _bootstrap_db() -> bool:
    init_db()
    return True


@st.cache_resource
def _bootstrap_theme() -> bool:
    inject_global_css()
    return True


_bootstrap_db()
_bootstrap_theme()

# ==========================================================
# Usuário padrão
# ==========================================================


def get_or_create_owner_user_id(default_email: str, default_name: str) -> int:
    with session_scope() as s:
        user = (
            s.execute(select(User).where(User.email == default_email)).scalars().first()
        )
        if user:
            return int(user.id)

        try:
            user = User(name=default_name, email=default_email)
            s.add(user)
            s.flush()
            s.refresh(user)
            return int(user.id)
        except IntegrityError:
            s.rollback()
            user = (
                s.execute(select(User).where(User.email == default_email))
                .scalars()
                .first()
            )
            if not user:
                raise
            return int(user.id)


@st.cache_resource
def _get_owner_user_id_cached(email: str, name: str) -> int:
    return get_or_create_owner_user_id(email, name)


owner_user_id = _get_owner_user_id_cached(DEFAULT_EMAIL, DEFAULT_NAME)

# ==========================================================
# Roteamento inicial
# ==========================================================


def _apply_initial_route_sync() -> None:
    nav_target = consume_nav_target(default=None)
    qp_menu = get_qp_str("menu")

    if is_valid_menu(nav_target, MENU_KEYS):
        set_current_menu(str(nav_target), update_qp=False)
        return

    if is_valid_menu(qp_menu, MENU_KEYS):
        set_current_menu(str(qp_menu), update_qp=False)
        return

    current = get_current_menu(default=MENU_DEFAULT)
    if not is_valid_menu(current, MENU_KEYS):
        set_current_menu(MENU_DEFAULT, update_qp=False)


_apply_initial_route_sync()

# ==========================================================
# Utilidades
# ==========================================================


def _rerun_soft() -> None:
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()


def _sync_hard() -> None:
    st.cache_data.clear()
    _rerun_soft()


def _menu_format(menu_key: str) -> str:
    return MENU_LABELS.get(menu_key, menu_key)


def _go_to_menu(menu_key: str) -> None:
    set_current_menu(menu_key)
    _rerun_soft()


def _clear_ui_cache() -> None:
    st.cache_data.clear()
    st.toast("Cache limpo", icon="🧹")


# ==========================================================
# Navegação
# ==========================================================


def _normalize_nav_mode(value: str | None) -> str:
    mode = str(value or "sidebar").strip().lower()
    return mode if mode in {"sidebar", "topbar"} else "sidebar"


def _nav_mode() -> str:
    return _normalize_nav_mode(st.session_state.get(NAV_MODE_KEY, "sidebar"))


def _set_nav_mode(mode: str) -> None:
    st.session_state[NAV_MODE_KEY] = _normalize_nav_mode(mode)


def _show_sidebar() -> bool:
    return _nav_mode() == "sidebar"


def _show_top_nav() -> bool:
    return _nav_mode() == "topbar"


def _nav_mode_label(mode: str) -> str:
    return "Topo" if _normalize_nav_mode(mode) == "topbar" else "Sidebar"


def _nav_mode_from_label(label: str | None) -> str:
    value = str(label or "").strip().lower()
    return "topbar" if value in {"topo", "topbar"} else "sidebar"


# ==========================================================
# Callbacks
# ==========================================================


def _on_sidebar_nav_mode_change() -> None:
    selected_label = st.session_state.get(SIDEBAR_NAV_MODE_WIDGET_KEY, "Sidebar")
    _set_nav_mode(_nav_mode_from_label(selected_label))
    _rerun_soft()


def _on_top_nav_mode_change() -> None:
    selected_label = st.session_state.get(TOP_NAV_MODE_WIDGET_KEY, "Topo")
    _set_nav_mode(_nav_mode_from_label(selected_label))
    _rerun_soft()


# ==========================================================
# Top navigation
# ==========================================================


def _top_nav(current_menu: str) -> str:
    if not _show_top_nav():
        return current_menu

    current_value = get_current_menu(default=current_menu)

    st.session_state[TOP_NAV_MENU_KEY] = current_value
    st.session_state[TOP_NAV_MODE_WIDGET_KEY] = _nav_mode_label(_nav_mode())

    with content_shell():
        col_menu, col_mode, col_action = st.columns(
            [4.0, 1.3, 1.2],
            gap="medium",
            vertical_alignment="center",
        )

        with col_menu:
            st.selectbox(
                "Ir para",
                MENU_KEYS,
                index=MENU_KEYS.index(current_value),
                format_func=_menu_format,
                key=TOP_NAV_MENU_KEY,
                on_change=on_top_nav_change,
                label_visibility="collapsed",
            )

        with col_mode:
            st.selectbox(
                "Modo de navegação",
                ["Sidebar", "Topo"],
                key=TOP_NAV_MODE_WIDGET_KEY,
                on_change=_on_top_nav_mode_change,
                label_visibility="collapsed",
            )

        with col_action:
            if st.button(
                "Atualizar",
                help="Recarregar a página atual",
                use_container_width=True,
            ):
                _rerun_soft()

        st.divider()

    return get_current_menu(default=current_menu)


# ==========================================================
# Sidebar
# ==========================================================


def _render_sidebar_brand() -> None:
    st.sidebar.markdown(
        f"<div class='sidebar-title'>{APP_ICON} {APP_TITLE}</div>",
        unsafe_allow_html=True,
    )


def _render_sidebar_navigation(current_menu: str) -> None:
    st.sidebar.markdown(
        "<div class='sidebar-section'>Navegação</div>",
        unsafe_allow_html=True,
    )

    selected = st.sidebar.radio(
        "Menu principal",
        MENU_KEYS,
        index=MENU_KEYS.index(current_menu) if current_menu in MENU_KEYS else 0,
        format_func=_menu_format,
        label_visibility="collapsed",
        key=SIDEBAR_MENU_KEY,
    )

    if selected != current_menu:
        _go_to_menu(selected)


def _render_sidebar_quick_actions() -> None:
    st.sidebar.markdown(
        "<div class='sidebar-section'>Ações</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.sidebar.columns(2, gap="small")

    with col1:
        if st.button("Sincronizar", use_container_width=True, type="primary"):
            _sync_hard()

    with col2:
        if st.button("Atualizar", use_container_width=True):
            _rerun_soft()


def _render_sidebar_config() -> None:
    st.session_state[SIDEBAR_NAV_MODE_WIDGET_KEY] = _nav_mode_label(_nav_mode())

    with st.sidebar.expander("Configurações", expanded=False):
        st.radio(
            "Modo de navegação",
            options=["Sidebar", "Topo"],
            key=SIDEBAR_NAV_MODE_WIDGET_KEY,
            on_change=_on_sidebar_nav_mode_change,
            horizontal=False,
        )

        st.checkbox("Modo mobile (cards compactos)", key="ui_mobile_cards")
        st.checkbox("Forçar densidade mobile", key="force_mobile")

        st.divider()

        st.checkbox("Debug UI", key="ui_debug")

        if bool(st.session_state.get("ui_debug", False)):
            if st.button("Limpar cache", use_container_width=True):
                _clear_ui_cache()


def _render_sidebar_build() -> None:
    st.sidebar.markdown(
        f"<div class='sidebar-build'>build {BUILD_ID}</div>",
        unsafe_allow_html=True,
    )


def render_sidebar(current_menu: str) -> str:
    if not _show_sidebar():
        return current_menu

    _render_sidebar_brand()
    _render_sidebar_navigation(current_menu)

    st.sidebar.divider()

    _render_sidebar_quick_actions()

    st.sidebar.divider()

    _render_sidebar_config()
    _render_sidebar_build()

    return get_current_menu(default=current_menu)


# ==========================================================
# Shell principal
# ==========================================================


def _render_invalid_route(menu: str) -> None:
    with content_shell():
        app_error(
            title="Rota inválida",
            message=f"A seção '{menu}' não está disponível no momento.",
        )


def _render_page_error(menu: str, exc: Exception) -> None:
    with content_shell():
        app_error(
            title=f"Não foi possível abrir '{menu}'",
            message="A página não pôde ser carregada agora. Tente atualizar a tela.",
            technical_details=str(exc) if DEBUG else None,
            details_expanded=False,
        )

        if DEBUG:
            st.exception(exc)


def render_shell(menu: str, owner_user_id: int) -> None:
    render_fn = ROUTES.get(menu)

    if render_fn is None:
        _render_invalid_route(menu)
        return

    try:
        render_fn(owner_user_id)
    except Exception as exc:
        _render_page_error(menu, exc)


# ==========================================================
# Execução
# ==========================================================

current_menu = get_current_menu(default=MENU_DEFAULT)

if _show_sidebar():
    current_menu = render_sidebar(current_menu)

if _show_top_nav():
    current_menu = _top_nav(current_menu)

render_shell(current_menu, owner_user_id)
