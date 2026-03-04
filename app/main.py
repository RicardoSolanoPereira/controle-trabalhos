# app/main.py
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# ------------------------------------------------------------
# PATH / IMPORT FIX (root)
# ------------------------------------------------------------
ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ------------------------------------------------------------
# APP IMPORTS
# ------------------------------------------------------------
from app.db import init_db
from app.db.connection import get_session
from app.db.models import User

# Suas páginas (mantendo nomes atuais dos módulos)
from app.ui import agendamentos, andamentos, dashboard, financeiro, prazos, processos

from app.ui.theme import inject_global_css
from app.ui_state import consume_nav_target, on_menu_change

# ------------------------------------------------------------
# LOCAL SETUP
# ------------------------------------------------------------
Path("data").mkdir(parents=True, exist_ok=True)
load_dotenv()

DEBUG = os.getenv("DEBUG", "0") == "1"

# Melhor para mobile: sidebar colapsada por padrão (config via env)
DEFAULT_SIDEBAR_STATE = os.getenv("SIDEBAR_STATE", "collapsed").strip().lower()
if DEFAULT_SIDEBAR_STATE not in {"expanded", "collapsed"}:
    DEFAULT_SIDEBAR_STATE = "collapsed"

BUILD_ID = os.getenv("BUILD_ID", "2026-02-28-DEF-1")

# Exibir navegação no topo (melhor para mobile).
# Pode deixar sempre True, ou usar env para controlar.
TOP_NAV_DEFAULT = os.getenv("TOP_NAV_DEFAULT", "1").strip() == "1"

st.set_page_config(
    page_title="Gestão Técnica",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state=DEFAULT_SIDEBAR_STATE,
)


# ------------------------------------------------------------
# BOOTSTRAP DB + THEME (1x por sessão)
# ------------------------------------------------------------
@st.cache_resource
def _bootstrap_db() -> None:
    init_db()


@st.cache_resource
def _bootstrap_theme() -> None:
    inject_global_css()


_bootstrap_db()
_bootstrap_theme()

# ------------------------------------------------------------
# DEFAULT USER (BOOTSTRAP)
# ------------------------------------------------------------
DEFAULT_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "admin@local").strip()
DEFAULT_NAME = os.getenv("DEFAULT_USER_NAME", "Administrador").strip()


def get_or_create_owner_user_id(default_email: str, default_name: str) -> int:
    """Busca usuário pelo email. Se não existir, cria e retorna o id."""
    with get_session() as s:
        try:
            user = (
                s.execute(select(User).where(User.email == default_email))
                .scalars()
                .first()
            )
            if user:
                return user.id

            user = User(name=default_name, email=default_email)
            s.add(user)
            s.commit()
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

        except Exception:
            s.rollback()
            raise


@st.cache_resource
def _get_owner_user_id_cached(email: str, name: str) -> int:
    """Cache por sessão para não bater no DB a cada rerun."""
    return get_or_create_owner_user_id(email, name)


try:
    owner_user_id = _get_owner_user_id_cached(DEFAULT_EMAIL, DEFAULT_NAME)
except Exception as e:
    st.error(f"Falha ao inicializar usuário padrão: {type(e).__name__}: {e}")
    if DEBUG:
        st.exception(e)
    st.stop()

# ------------------------------------------------------------
# NAV / ROUTES (menu canônico: Painel → Trabalhos → ...)
# ------------------------------------------------------------
# Chaves que o ui_state deve conhecer (e que você vai ver na UI)
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

# Mantém os seus módulos atuais, mas com nomes de rota mais “humanos”
ROUTES = {
    "Painel": dashboard.render,
    "Trabalhos": processos.render,  # módulo processos.py renderiza Trabalhos
    "Prazos": prazos.render,
    "Agenda": agendamentos.render,  # módulo agendamentos.py renderiza Agenda
    "Andamentos": andamentos.render,
    "Financeiro": financeiro.render,
}


# ------------------------------------------------------------
# RERUN / SYNC helpers (compatíveis)
# ------------------------------------------------------------
def _rerun_soft() -> None:
    """Recarrega UI sem limpar cache."""
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass


def _sync_hard() -> None:
    """Sincronizar: limpa caches e rerun."""
    st.cache_data.clear()
    _rerun_soft()


# ------------------------------------------------------------
# Top nav (mobile-friendly)
# ------------------------------------------------------------
def _top_nav(current_menu: str) -> str:
    """
    Navegação no topo (ótima para mobile e também útil no desktop).
    Usa session_state para manter seleção consistente com o sidebar.
    """
    # permite “forçar” mobile via sidebar, mas também pode ficar sempre ligado
    force_mobile = bool(st.session_state.get("force_mobile", False))
    show_top_nav = (
        bool(st.session_state.get("ui_show_top_nav", TOP_NAV_DEFAULT)) or force_mobile
    )

    if not show_top_nav:
        return current_menu

    # Barra compacta
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
        # Um “botão rápido” bem mobile-friendly
        if st.button(
            "↻", help="Recarregar", use_container_width=True, key="top_nav_reload"
        ):
            _rerun_soft()

    # Se mudou no top-nav, sincroniza com sidebar e aplica política de limpeza
    if menu != current_menu:
        st.session_state["sidebar_menu"] = menu
        on_menu_change(menu)

    st.divider()
    return menu


# ------------------------------------------------------------
# Sidebar (desktop-friendly, mas funcionando no mobile também)
# ------------------------------------------------------------
def render_sidebar() -> str:
    # Header minimalista (sem caption grande)
    st.sidebar.markdown("### 📐 Gestão Técnica")

    # Deep-link interno (session_state) via ui_state.navigate()
    target = consume_nav_target(default=None)
    if target and target in MENU_KEYS:
        st.session_state["sidebar_menu"] = target
        st.session_state["top_nav_menu"] = target

    # Se top-nav estiver ligado ou forçando mobile, sidebar fica “utilitário”
    force_mobile = bool(st.session_state.get("force_mobile", False))
    show_top_nav = bool(st.session_state.get("ui_show_top_nav", TOP_NAV_DEFAULT))
    sidebar_minimal = show_top_nav or force_mobile

    # MENU (só quando NÃO estiver minimal)
    if not sidebar_minimal:
        menu = st.sidebar.radio(
            label="Menu",
            options=MENU_KEYS,
            format_func=lambda k: MENU_LABELS.get(k, k),
            key="sidebar_menu",
            label_visibility="collapsed",
        )
        on_menu_change(menu)
        st.sidebar.divider()
    else:
        # mantém seleção atual, mas não mostra menu (top-nav manda)
        menu = str(st.session_state.get("sidebar_menu", "Painel"))

    # AÇÕES (compactas)
    st.sidebar.markdown("**Ações**")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        if c1.button(
            "🔄 Sync", use_container_width=True, key="sidebar_sync_btn", type="primary"
        ):
            _sync_hard()
    with c2:
        if c2.button("↻ Atual", use_container_width=True, key="sidebar_reload_btn"):
            _rerun_soft()

    # CONFIG (uma única seção)
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

        # Manutenção só aparece quando debug ligado (não polui o usuário comum)
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

    # Rodapé discreto (sem muito espaço)
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
    render_fn(owner_user_id)


# ------------------------------------------------------------
# APP ENTRY
# ------------------------------------------------------------
selected_menu = render_sidebar()

# Para mobile: top-nav pode prevalecer (e sincroniza com sidebar)
selected_menu = _top_nav(selected_menu)

render_shell(selected_menu)
