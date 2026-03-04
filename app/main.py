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
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ------------------------------------------------------------
# APP IMPORTS
# ------------------------------------------------------------
from app.db import init_db
from app.db.connection import get_session
from app.db.models import User
from app.ui import dashboard, processos, prazos, agendamentos, andamentos, financeiro
from app.ui.theme import inject_global_css

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
    # Evita rodar init_db em todo rerun
    init_db()


@st.cache_resource
def _bootstrap_theme() -> None:
    # Injeta CSS 1x por sessão
    inject_global_css()


_bootstrap_db()
_bootstrap_theme()

# ------------------------------------------------------------
# DEFAULT USER (BOOTSTRAP)
# ------------------------------------------------------------
DEFAULT_EMAIL = os.getenv("DEFAULT_USER_EMAIL", "admin@local").strip()
DEFAULT_NAME = os.getenv("DEFAULT_USER_NAME", "Administrador").strip()


def get_or_create_owner_user_id(default_email: str, default_name: str) -> int:
    """
    Busca usuário pelo email.
    Se não existir, cria e retorna o id.
    """
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
            # corrida: outro worker criou o mesmo email
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
    """
    Cache por sessão para não bater no DB a cada rerun.
    Se você mudar DEFAULT_EMAIL/NAME e quiser refletir, reinicie a sessão.
    """
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
MENU_LABELS = {
    "Dashboard": "📊 Painel",
    "Processos": "📁 Trabalhos",
    "Prazos": "⏳ Prazos",
    "Agendamentos": "📅 Agenda",
    "Andamentos": "🧾 Andamentos",
    "Financeiro": "💰 Financeiro",
}

ROUTES = {
    "Dashboard": dashboard.render,
    "Processos": processos.render,
    "Prazos": prazos.render,
    "Agendamentos": agendamentos.render,
    "Andamentos": andamentos.render,
    "Financeiro": financeiro.render,
}


def _rerun_soft() -> None:
    """Recarrega UI sem limpar cache (útil quando só quer atualizar render)."""
    st.rerun()


def _sync_hard() -> None:
    """Sincronizar: limpa caches e rerun."""
    st.cache_data.clear()
    st.rerun()


def render_sidebar() -> str:
    # -------------------------
    # Header compacto (menos ruído)
    # -------------------------
    st.sidebar.markdown("## 📐 Gestão Técnica")
    st.sidebar.caption("Trabalhos • Prazos • Agenda • Financeiro")

    # Deep-link interno (session_state)
    if "nav_target" in st.session_state:
        st.session_state["sidebar_menu"] = st.session_state.pop("nav_target")

    st.sidebar.divider()

    # -------------------------
    # Menu (radio pill via CSS do theme.py)
    # -------------------------
    st.sidebar.subheader("Menu")
    menu = st.sidebar.radio(
        label="Menu",
        options=list(MENU_LABELS.keys()),
        format_func=lambda k: MENU_LABELS[k],
        key="sidebar_menu",
        label_visibility="collapsed",
    )

    st.sidebar.divider()

    # -------------------------
    # Ações rápidas (compactas)
    # - só o essencial visível
    # - resto fica recolhido em expanders
    # -------------------------
    st.sidebar.subheader("⚡ Ações rápidas")

    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.button(
            "🔄 Sincronizar", use_container_width=True, key="sidebar_sync_btn"
        ):
            _sync_hard()
    with c2:
        if st.button(
            "↻ Recarregar", use_container_width=True, key="sidebar_reload_btn"
        ):
            _rerun_soft()

    # -------------------------
    # Ajustes (UI) – recolhido
    # -------------------------
    with st.sidebar.expander("🎛️ Ajustes (UI)", expanded=False):
        st.caption("Preferências visuais (não afetam dados).")

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

    # -------------------------
    # Manutenção – recolhido e “técnico”
    # -------------------------
    with st.sidebar.expander("🧰 Manutenção", expanded=False):
        st.caption("Área técnica (opcional).")
        st.caption("Backup/alertas serão retomados quando necessário.")
        st.caption("Objetivo atual: refatorar UI/UX (mobile).")

        # Debug toggle só se você quiser usar no futuro
        st.checkbox(
            "Debug (UI)",
            value=bool(st.session_state.get("ui_debug", False)),
            key="ui_debug",
        )

        # Botão extra (se quiser) para limpar caches manualmente
        if st.button(
            "🧹 Limpar cache", use_container_width=True, key="sidebar_clear_cache_btn"
        ):
            st.cache_data.clear()
            st.toast("Cache limpo.", icon="🧹")

    st.sidebar.divider()

    # Rodapé discreto
    st.sidebar.markdown(
        f"<div style='font-size:0.78rem;opacity:0.68'>BUILD: {BUILD_ID}</div>",
        unsafe_allow_html=True,
    )

    return menu


def render_shell(menu: str) -> None:
    """
    Shell base do app.
    Mantém responsabilidades mínimas no main.
    """
    render_fn = ROUTES.get(menu)
    if not render_fn:
        st.error("Rota inválida.")
        return

    render_fn(owner_user_id)


# -------------------------
# APP ENTRY
# -------------------------
selected_menu = render_sidebar()
render_shell(selected_menu)
