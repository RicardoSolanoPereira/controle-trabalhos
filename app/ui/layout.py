from __future__ import annotations

from contextlib import contextmanager
import streamlit as st


def is_mobile() -> bool:
    """
    Heurística simples e estável:
    - se a sidebar começa colapsada, geralmente é uso mobile (ou desktop compacto)
    - você também pode forçar via session_state: st.session_state["force_mobile"]=True
    """
    if st.session_state.get("force_mobile") is True:
        return True
    if st.session_state.get("force_mobile") is False:
        return False

    # fallback: assume mobile quando sidebar estiver colapsada
    try:
        # Streamlit não expõe viewport. Então usamos uma heurística segura.
        return (
            st.get_option("client.showSidebarNavigation") is False
        )  # pode não existir
    except Exception:
        return False


def grid(columns_desktop: int = 3, *, gap: str = "small"):
    """
    Retorna colunas:
    - Desktop: N colunas
    - Mobile: 1 coluna (empilhado)
    """
    if is_mobile():
        return st.columns(1, gap=gap)
    columns_desktop = max(1, int(columns_desktop))
    return st.columns(columns_desktop, gap=gap)


def spacer(height_rem: float = 0.6) -> None:
    st.markdown(f"<div style='height:{height_rem}rem'></div>", unsafe_allow_html=True)


@contextmanager
def surface():
    """Surface padrão (usa CSS .sp-surface do theme.py)."""
    st.markdown('<div class="sp-surface">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def section(
    title: str | None = None, *, subtitle: str | None = None, divider: bool = False
):
    """
    Seção padrão:
    - título opcional
    - subtitle opcional
    - surface automática
    """
    if title:
        st.markdown(f"#### {title}")
        if subtitle:
            st.caption(subtitle)

    with surface():
        yield  # type: ignore[misc]  # usado como contextmanager via `with`


# Python não deixa yield em função normal com decorator facilmente sem contextmanager,
# então oferecemos uma versão contextmanager explícita:
@contextmanager
def section_surface(
    title: str | None = None, *, subtitle: str | None = None, divider: bool = False
):
    if title:
        st.markdown(f"#### {title}")
        if subtitle:
            st.caption(subtitle)
    if divider:
        st.divider()
    with surface():
        yield
