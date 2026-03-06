from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# ------------------------------------------------------------
# APP IMPORTS
# ------------------------------------------------------------
from app.db.connection import session_scope
from app.db.init_db import init_db
from app.db.models import User

from app.ui import agendamentos, andamentos, dashboard, financeiro, prazos, processos
from app.ui.theme import inject_global_css
from app.ui_state import (
    consume_nav_target,
    get_qp_str,
    init_state,
    on_menu_change,
)

# ------------------------------------------------------------
# LOCAL SETUP
# ------------------------------------------------------------
Path("data").mkdir(parents=True, exist_ok=True)
load_dotenv()

DEBUG = os.getenv("DEBUG", "0") == "1"

DEFAULT_SIDEBAR_STATE = os.getenv("SIDEBAR_STATE", "collapsed").strip().lower()
if DEFAULT_SIDEBAR_STATE not in {"expanded", "collapsed"}:
    DEFAULT_SIDEBAR_STATE = "collapsed"

BUILD_ID = os.getenv("BUILD_ID", "2026-02-28-DEF-1")
TOP_NAV_DEFAULT = os.getenv("TOP_NAV_DEFAULT", "1").strip() == "1"

st.set_page_config(
    page_title="Gestão Técnica",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state=DEFAULT_SIDEBAR_STATE,
)

# Estado base
init_state()


# ------------------------------------------------------------
# BOOTSTRAP DB + THEME
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# DEFAULT USER (BOOTSTRAP)
# ------------------------------------------------------------
DEFAULT_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "admin@local").strip()
DEFAULT_NAME = os.getenv("DEFAULT_USER_NAME", "Administrador").strip()


def get_or_create_owner_user_id(default_email: str, default_name: str) -> int:
    with session_scope() as s:
        user = (
            s.execute(select(User).where(User.email == default_email)).scalars().first()
        )
        if user:
            return user.id

        try:
            user = User(name=default_name, email=default_email)
            s.add(user)
            s.flush()
            s.refresh(user)
            return user.id

        except IntegrityError:
            s.rollback()
            user = (
                s.execute(select(User).where(User.email == default_email))
                .scalars()
                .first()
            )
            if not user:
                raise
            return user.id


@st.cache_resource
def _get_owner_user_id_cached(email: str, name: str) -> int:
    return get_or_create_owner_user_id(email, name)


try:
    owner_user_id = _get_owner_user_id_cached(DEFAULT_EMAIL, DEFAULT_NAME)
except Exception as e:
    st.error(f"Falha ao inicializar usuário padrão: {type(e).__name__}: {e}")
    if DEBUG:
        st.exception(e)
    st.stop()

# ------------------------------------------------------------
# NAV / ROUTES
# ------------------------------------------------------------
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

ROUTES = {
    "Painel": dashboard.render,
    "Trabalhos": processos.render,
    "Prazos": prazos.render,
    "Agenda": agendamentos.render,
    "Andamentos": andamentos.render,
    "Financeiro": financeiro.render,
}


# ------------------------------------------------------------
# Query param / nav target sync
# ------------------------------------------------------------
def _apply_initial_route_sync() -> None:
    """
    Aplica sincronização ANTES de renderizar widgets de navegação.
    Isso evita conflito com session_state de widgets já instanciados.
    """
    qp_menu = get_qp_str("menu")
    nav_target = consume_nav_target(default=None)

    target = None
    if nav_target in MENU_KEYS:
        target = nav_target
    elif qp_menu in MENU_KEYS:
        target = qp_menu

    if not target:
        target = st.session_state.get("_last_menu", "Painel")
        if target not in MENU_KEYS:
            target = "Painel"

    st.session_state["sidebar_menu"] = target
    st.session_state["top_nav_menu"] = target

    if st.session_state.get("_last_menu") != target:
        on_menu_change(target)


_apply_initial_route_sync()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _rerun_soft() -> None:
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


def _sync_hard() -> None:
    st.cache_data.clear()
    _rerun_soft()


# ------------------------------------------------------------
# Top nav
# ------------------------------------------------------------
def _top_nav(current_menu: str) -> str:
    force_mobile = bool(st.session_state.get("force_mobile", False))
    show_top_nav = (
        bool(st.session_state.get("ui_show_top_nav", TOP_NAV_DEFAULT)) or force_mobile
    )

    if not show_top_nav:
        return current_menu

    c1, c2 = st.columns([3, 1], vertical_alignment="center")

    with c1:
        menu = st.selectbox(
            "Navegação",
            MENU_KEYS,
            index=MENU_KEYS.index(current_menu) if current_menu in MENU_KEYS else 0,
            format_func=lambda k: MENU_LABELS.get(k, k),
            key="top_nav_menu",
            label_visibility="collapsed",
        )

    with c2:
        if st.button(
            "↻",
            help="Recarregar",
            use_container_width=True,
            key="top_nav_reload",
        ):
            _rerun_soft()

    if menu != current_menu:
        st.session_state["sidebar_menu"] = menu
        on_menu_change(menu)

    st.divider()
    return menu


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
def render_sidebar() -> str:
    st.sidebar.markdown("### 📐 Gestão Técnica")

    force_mobile = bool(st.session_state.get("force_mobile", False))
    show_top_nav = bool(st.session_state.get("ui_show_top_nav", TOP_NAV_DEFAULT))
    sidebar_minimal = show_top_nav or force_mobile

    if not sidebar_minimal:
        menu = st.sidebar.radio(
            label="Menu",
            options=MENU_KEYS,
            format_func=lambda k: MENU_LABELS.get(k, k),
            key="sidebar_menu",
            label_visibility="collapsed",
        )

        if menu != st.session_state.get("_last_menu"):
            on_menu_change(menu)

        st.sidebar.divider()
    else:
        menu = str(st.session_state.get("sidebar_menu", "Painel"))

    st.sidebar.markdown("**Ações**")
    c1, c2 = st.sidebar.columns(2)

    with c1:
        if st.button(
            "🔄 Sync",
            use_container_width=True,
            key="sidebar_sync_btn",
            type="primary",
        ):
            _sync_hard()

    with c2:
        if st.button(
            "↻ Atual",
            use_container_width=True,
            key="sidebar_reload_btn",
        ):
            _rerun_soft()

    with st.sidebar.expander("⚙️ Config", expanded=False):
        st.checkbox(
            "Mostrar navegação no topo",
            value=bool(st.session_state.get("ui_show_top_nav", TOP_NAV_DEFAULT)),
            key="ui_show_top_nav",
        )
        st.checkbox(
            "Modo mobile (cards)",
            value=bool(st.session_state.get("ui_mobile_cards", True)),
            key="ui_mobile_cards",
        )
        st.checkbox(
            "Forçar modo celular (teste)",
            value=bool(st.session_state.get("force_mobile", False)),
            key="force_mobile",
        )

        st.divider()

        st.checkbox(
            "Debug (UI)",
            value=bool(st.session_state.get("ui_debug", False)),
            key="ui_debug",
        )

        if st.session_state.get("ui_debug", False):
            if st.button(
                "🧹 Limpar cache",
                use_container_width=True,
                key="sidebar_clear_cache_btn",
            ):
                st.cache_data.clear()
                st.toast("Cache limpo.", icon="🧹")

    st.sidebar.markdown(
        f"<div style='font-size:0.72rem;opacity:0.55;margin-top:10px'>BUILD {BUILD_ID}</div>",
        unsafe_allow_html=True,
    )

    return menu


# ------------------------------------------------------------
# Shell / Router
# ------------------------------------------------------------
def render_shell(menu: str) -> None:
    render_fn = ROUTES.get(menu)
    if not render_fn:
        st.error("Rota inválida.")
        return

    try:
        render_fn(owner_user_id)
    except TypeError:
        render_fn()
    except Exception as e:
        st.error(f"Erro ao abrir a página '{menu}'.")
        st.exception(e)


# ------------------------------------------------------------
# APP ENTRY
# ------------------------------------------------------------
selected_menu = render_sidebar()
selected_menu = _top_nav(selected_menu)

# garante consistência final do estado canônico
if selected_menu != st.session_state.get("_last_menu"):
    on_menu_change(selected_menu)

render_shell(selected_menu)
