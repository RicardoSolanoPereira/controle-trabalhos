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
from ui.theme import inject_global_css
from ui_state import (
    MENU_DEFAULT,
    consume_nav_target,
    get_current_menu,
    get_qp_str,
    init_state,
    is_valid_menu,
    on_sidebar_menu_change,
    on_top_nav_change,
    set_current_menu,
)

# ==========================================================
# Bootstrap local
# ==========================================================

Path("data").mkdir(parents=True, exist_ok=True)
load_dotenv()

DEBUG = os.getenv("DEBUG", "0").strip() == "1"

DEFAULT_SIDEBAR_STATE = os.getenv("SIDEBAR_STATE", "collapsed").strip().lower()
if DEFAULT_SIDEBAR_STATE not in {"expanded", "collapsed"}:
    DEFAULT_SIDEBAR_STATE = "collapsed"

BUILD_ID = os.getenv("BUILD_ID", "2026-02-28-DEF-1").strip()
TOP_NAV_DEFAULT = os.getenv("TOP_NAV_DEFAULT", "1").strip() == "1"

DEFAULT_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "admin@local").strip()
DEFAULT_NAME = os.getenv("DEFAULT_USER_NAME", "Administrador").strip()

st.set_page_config(
    page_title="Gestão Técnica",
    page_icon="📐",
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
# Estado inicial
# ==========================================================

init_state()


# ==========================================================
# Bootstrap cacheado
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
# Usuário dono padrão
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


try:
    owner_user_id = _get_owner_user_id_cached(DEFAULT_EMAIL, DEFAULT_NAME)
except Exception as e:
    st.error(f"Falha ao inicializar usuário padrão: {type(e).__name__}: {e}")
    if DEBUG:
        st.exception(e)
    st.stop()


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
# Utilitários de rerun / sync
# ==========================================================


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


# ==========================================================
# Top navigation
# ==========================================================


def _top_nav(current_menu: str) -> str:
    force_mobile = bool(st.session_state.get("force_mobile", False))
    show_top_nav = (
        bool(st.session_state.get("ui_show_top_nav", TOP_NAV_DEFAULT)) or force_mobile
    )

    if not show_top_nav:
        return current_menu

    left, right = st.columns([4, 1.3], gap="medium", vertical_alignment="center")

    with left:
        st.selectbox(
            "Navegação",
            MENU_KEYS,
            format_func=lambda k: MENU_LABELS.get(k, k),
            key="top_nav_menu",
            on_change=on_top_nav_change,
            label_visibility="collapsed",
        )

    with right:
        if st.button(
            "↻",
            help="Recarregar página atual",
            use_container_width=True,
            key="top_nav_reload",
        ):
            _rerun_soft()

    st.divider()
    return get_current_menu()


# ==========================================================
# Sidebar
# ==========================================================


def render_sidebar(current_menu: str) -> str:
    st.sidebar.markdown("### 📐 Gestão Técnica")

    force_mobile = bool(st.session_state.get("force_mobile", False))
    show_top_nav = bool(st.session_state.get("ui_show_top_nav", TOP_NAV_DEFAULT))
    sidebar_minimal = show_top_nav or force_mobile

    if not sidebar_minimal:
        st.sidebar.radio(
            label="Menu",
            options=MENU_KEYS,
            format_func=lambda k: MENU_LABELS.get(k, k),
            key="sidebar_menu",
            on_change=on_sidebar_menu_change,
            label_visibility="collapsed",
        )
        st.sidebar.divider()

    st.sidebar.markdown("**Ações**")
    col_sync, col_reload = st.sidebar.columns(2)

    with col_sync:
        if st.button(
            "🔄 Sync",
            use_container_width=True,
            key="sidebar_sync_btn",
            type="primary",
        ):
            _sync_hard()

    with col_reload:
        if st.button(
            "↻ Atual",
            use_container_width=True,
            key="sidebar_reload_btn",
        ):
            _rerun_soft()

    with st.sidebar.expander("⚙️ Config", expanded=False):
        st.checkbox("Mostrar navegação no topo", key="ui_show_top_nav")
        st.checkbox("Modo mobile (cards)", key="ui_mobile_cards")
        st.checkbox("Forçar modo celular (teste)", key="force_mobile")

        st.divider()

        st.checkbox("Debug (UI)", key="ui_debug")

        if bool(st.session_state.get("ui_debug", False)):
            if st.button(
                "🧹 Limpar cache",
                use_container_width=True,
                key="sidebar_clear_cache_btn",
            ):
                st.cache_data.clear()
                st.toast("Cache limpo.", icon="🧹")

    st.sidebar.markdown(
        (
            "<div style='font-size:0.72rem;opacity:0.55;margin-top:10px'>"
            f"BUILD {BUILD_ID}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    return get_current_menu(default=current_menu)


# ==========================================================
# Shell principal
# ==========================================================


def render_shell(menu: str, owner_user_id: int) -> None:
    render_fn = ROUTES.get(menu)

    if render_fn is None:
        st.error("Rota inválida.")
        return

    try:
        render_fn(owner_user_id)
    except Exception as e:
        st.error(f"Erro ao abrir a página '{menu}'.")
        if DEBUG:
            st.exception(e)
        else:
            st.caption(f"{type(e).__name__}: {e}")


# ==========================================================
# Execução principal
# ==========================================================

current_menu = get_current_menu()
current_menu = render_sidebar(current_menu)
current_menu = _top_nav(current_menu)
render_shell(current_menu, owner_user_id)
