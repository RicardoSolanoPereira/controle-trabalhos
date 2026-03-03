# app/ui/layout.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, Sequence

import streamlit as st


MOBILE_FLAG_KEY = "force_mobile"


def is_mobile() -> bool:
    """
    Heurística estável:
    - por padrão: desktop
    - permite override manual via st.session_state["force_mobile"] = True/False

    Streamlit não expõe viewport de forma estável -> evitamos hacks.
    """
    forced = st.session_state.get(MOBILE_FLAG_KEY)
    if forced is True:
        return True
    if forced is False:
        return False
    return False


def mobile_debug_toggle(*, label: str = "Modo mobile (teste)") -> None:
    """
    Toggle opcional para testar layout mobile no desktop.
    Use no sidebar (ex.: no main.py) quando estiver refinando UX.
    """
    st.toggle(
        label,
        key=MOBILE_FLAG_KEY,
        value=bool(st.session_state.get(MOBILE_FLAG_KEY, False)),
    )


def spacer(height_rem: float = 0.6) -> None:
    """Espaçamento vertical simples."""
    st.markdown(
        f"<div style='height:{float(height_rem)}rem'></div>", unsafe_allow_html=True
    )


def grid(
    columns_desktop: int = 3,
    *,
    gap: str = "small",
    columns_mobile: int = 1,
) -> list:
    """
    Colunas responsivas (controladas por is_mobile()).

    Uso:
        c1, c2, c3 = grid(3)
        c1, c2 = grid(2, columns_mobile=1)
    """
    if is_mobile():
        return list(st.columns(max(1, int(columns_mobile)), gap=gap))

    return list(st.columns(max(1, int(columns_desktop)), gap=gap))


def grid_weights(
    weights_desktop: Sequence[float] = (1, 1, 1),
    *,
    gap: str = "small",
    weights_mobile: Sequence[float] = (1,),
) -> list:
    """
    Variante com pesos (melhor para header: título à esquerda e ações à direita).

    Uso:
        left, right = grid_weights((3, 2), weights_mobile=(1,))
    """
    weights = weights_mobile if is_mobile() else weights_desktop
    weights = tuple(float(w) for w in weights if float(w) > 0) or (1.0,)
    return list(st.columns(weights, gap=gap))


@contextmanager
def surface(*, padding: bool = True):
    """
    Surface padrão (usa CSS .sp-surface do theme.py).
    """
    # padding já está no .sp-surface; esse parâmetro fica para futuro/compat
    st.markdown('<div class="sp-surface">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def _section_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


@contextmanager
def section(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    divider: bool = False,
    header_actions: callable | None = None,
):
    """
    Seção padrão com surface.

    - title/subtitle opcionais
    - divider opcional
    - header_actions: callable para renderizar botões/filtros no cabeçalho (lado direito)

    Uso:
        with section("Prioridades", subtitle="Hoje", header_actions=lambda: st.button("Ver tudo")):
            ...
    """
    if title:
        if header_actions:
            left, right = grid_weights((3, 2), weights_mobile=(1,), gap="small")
            with left:
                _section_header(title, subtitle)
            with right:
                # ações alinhadas e sem “quebrar” em desktop
                st.markdown(
                    "<div style='display:flex;justify-content:flex-end;gap:0.5rem;flex-wrap:wrap'>",
                    unsafe_allow_html=True,
                )
                header_actions()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            _section_header(title, subtitle)

    if divider:
        st.divider()

    with surface():
        yield


@contextmanager
def section_surface(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    divider: bool = False,
    header_actions: callable | None = None,
):
    """
    Alias explícito para section(), mantido para compatibilidade.
    """
    with section(
        title, subtitle=subtitle, divider=divider, header_actions=header_actions
    ):
        yield
