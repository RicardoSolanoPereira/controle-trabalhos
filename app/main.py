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
# STREAMLIT CONFIG
# ------------------------------------------------------------
Path("data").mkdir(parents=True, exist_ok=True)
load_dotenv()

# Melhor para mobile: sidebar pode ser aberta quando precisar.
# No desktop continua fácil abrir/fechar.
DEFAULT_SIDEBAR_STATE = os.getenv("SIDEBAR_STATE", "collapsed").strip().lower()
if DEFAULT_SIDEBAR_STATE not in {"expanded", "collapsed"}:
    DEFAULT_SIDEBAR_STATE = "collapsed"

st.set_page_config(
    page_title="Gestão Técnica",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state=DEFAULT_SIDEBAR_STATE,
)

BUILD_ID = "2026-02-28-DEF-1"

# ------------------------------------------------------------
# BOOTSTRAP DB + THEME (1x)
# ------------------------------------------------------------
init_db()
inject_global_css()

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


try:
    owner_user_id = get_or_create_owner_user_id(DEFAULT_EMAIL, DEFAULT_NAME)
except Exception as e:
    st.error(f"Falha ao inicializar usuário padrão: {type(e).__name__}: {e}")
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


def render_sidebar() -> str:
    # Cabeçalho mais compacto (melhor no mobile)
    st.sidebar.markdown("## 📐 Gestão Técnica")
    st.sidebar.caption("Trabalhos • Prazos • Agenda • Financeiro")
    st.sidebar.markdown(
        f"<div style='font-size:0.80rem;opacity:0.72;margin-top:2px'>BUILD: {BUILD_ID}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    # Navegação segura (deep-link interno via session_state)
    if "nav_target" in st.session_state:
        st.session_state["sidebar_menu"] = st.session_state.pop("nav_target")

    # MENU
    st.sidebar.subheader("Menu")
    menu = st.sidebar.radio(
        label="Menu",
        options=list(MENU_LABELS.keys()),
        format_func=lambda k: MENU_LABELS[k],
        key="sidebar_menu",
        label_visibility="collapsed",
    )

    st.sidebar.divider()

    # AÇÕES RÁPIDAS (um único comando consistente)
    st.sidebar.subheader("⚡ Ações rápidas")

    sync_clicked = st.sidebar.button(
        "🔄 Sincronizar", use_container_width=True, key="sidebar_sync_btn"
    )
    if sync_clicked:
        # Sincronizar = limpar cache de dados + recarregar UI
        st.cache_data.clear()
        st.rerun()

    # Área técnica escondida (não polui o uso no celular)
    with st.sidebar.expander("🧰 Manutenção", expanded=False):
        st.caption("Área técnica (opcional).")
        st.caption("Backup/alertas serão retomados quando necessário.")
        st.caption("Objetivo atual: refatorar UI/UX (mobile).")

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
