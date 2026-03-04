# app/ui/layout.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Sequence

import streamlit as st


MOBILE_FLAG_KEY = "force_mobile"


def is_mobile() -> bool:
    """
    Heurística estável:
    - por padrão: desktop
    - permite override manual via st.session_state["force_mobile"] = True/False
    """
    forced = st.session_state.get(MOBILE_FLAG_KEY, None)
    return True if forced is True else False


def mobile_debug_toggle(*, label: str = "Forçar modo celular (teste)") -> None:
    """Toggle opcional para testar layout mobile no desktop."""
    st.toggle(
        label,
        key=MOBILE_FLAG_KEY,
        value=bool(st.session_state.get(MOBILE_FLAG_KEY, False)),
        help="Ativa layout empilhado para simular mobile no desktop.",
    )


def spacer(height_rem: float = 0.6) -> None:
    """Espaçamento vertical simples."""
    st.markdown(
        f"<div style='height:{float(height_rem)}rem'></div>", unsafe_allow_html=True
    )


def _stack_slots(n: int) -> list:
    """Retorna N slots empilhados (containers) — mantém compatibilidade com unpack."""
    n = max(1, int(n))
    return [st.container() for _ in range(n)]


def _wrap_columns(n: int, *, per_row: int, gap: str) -> list:
    """
    Mobile em "linhas" (wrap):
    - devolve sempre N slots
    - distribui em linhas com 'per_row' colunas por linha
    """
    n = max(1, int(n))
    per_row = max(1, int(per_row))
    slots: list = []

    remaining = n
    while remaining > 0:
        row_cols = min(per_row, remaining)
        row = st.columns(row_cols, gap=gap)
        slots.extend(list(row))
        remaining -= row_cols

    return slots


def grid(
    columns_desktop: int = 3,
    *,
    gap: str = "small",
    columns_mobile: int = 1,
) -> list:
    """
    Colunas responsivas (controladas por is_mobile()).

    Regra IMPORTANTÍSSIMA:
    - Sempre devolve exatamente `columns_desktop` slots (para não quebrar unpack).

    Desktop: colunas lado a lado.
    Mobile:
      - columns_mobile == 1 -> devolve containers empilhados (N slots).
      - columns_mobile > 1 -> wrap em linhas, mantendo N slots.
    """
    n = max(1, int(columns_desktop))

    if is_mobile():
        m = max(1, int(columns_mobile))
        if m == 1:
            return _stack_slots(n)
        return _wrap_columns(n, per_row=m, gap=gap)

    return list(st.columns(n, gap=gap))


def grid_weights(
    weights_desktop: Sequence[float] = (1, 1, 1),
    *,
    gap: str = "small",
    weights_mobile: Sequence[float] = (1,),
) -> list:
    """
    Variante com pesos.

    Desktop: retorna colunas com pesos.
    Mobile: devolve o mesmo número de slots do desktop, empilhados, para não quebrar unpack.
    """
    w_desktop = tuple(float(w) for w in weights_desktop if float(w) > 0) or (1.0,)
    _ = weights_mobile  # mantido para compatibilidade futura

    if is_mobile():
        return _stack_slots(len(w_desktop))

    return list(st.columns(w_desktop, gap=gap))


@contextmanager
def actions_row(*, right: bool = True, gap_px: int = 8):
    """Linha de ações (botões) com alinhamento e wrap — context manager correto."""
    justify = "flex-end" if right else "flex-start"
    st.markdown(
        f"<div style='display:flex;justify-content:{justify};gap:{int(gap_px)}px;flex-wrap:wrap;align-items:center;'>",
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


@contextmanager
def surface(*, padding: bool = True):
    """Surface padrão (usa CSS .sp-surface do theme.py)."""
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
    top_pad_rem: float | None = None,
):
    """
    Seção padrão com surface.

    - header_actions: callable para renderizar ações no cabeçalho (lado direito)
    - top_pad_rem: respiro antes do header (ajuda dropdown perto do topo)
    """
    if top_pad_rem is not None:
        spacer(top_pad_rem)

    if title:
        if header_actions:
            left, right = grid_weights((3, 2), weights_mobile=(1,), gap="small")
            with left:
                _section_header(title, subtitle)
            with right:
                with actions_row(right=True):
                    header_actions()
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
    top_pad_rem: float | None = None,
):
    """Alias explícito para section(), mantido para compatibilidade."""
    with section(
        title,
        subtitle=subtitle,
        divider=divider,
        header_actions=header_actions,
        top_pad_rem=top_pad_rem,
    ):
        yield
