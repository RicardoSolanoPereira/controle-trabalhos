from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Sequence

import streamlit as st

MOBILE_FLAG_KEY = "force_mobile"


# ==========================================================
# Mobile
# ==========================================================


def is_mobile() -> bool:
    """Determina se o layout deve usar modo mobile."""
    return bool(st.session_state.get(MOBILE_FLAG_KEY, False))


def mobile_debug_toggle(label: str = "Forçar modo celular (teste)") -> None:
    """Permite testar layout mobile no desktop."""
    st.toggle(
        label,
        key=MOBILE_FLAG_KEY,
        value=is_mobile(),
        help="Simula layout mobile.",
    )


# ==========================================================
# Espaçamento
# ==========================================================


def spacer(height_rem: float = 0.6) -> None:
    """Insere espaçamento vertical consistente."""
    st.markdown(
        f"<div style='height:{max(0.0, float(height_rem))}rem'></div>",
        unsafe_allow_html=True,
    )


# ==========================================================
# Slots / grids
# ==========================================================


def _stack_slots(n: int) -> list:
    """Retorna N containers empilhados."""
    return [st.container() for _ in range(max(1, int(n)))]


def _wrap_columns(n: int, *, per_row: int, gap: str) -> list:
    """
    Cria N slots distribuídos em múltiplas linhas.
    Útil para mobile quando se quer mais de 1 coluna por linha.
    """
    total = max(1, int(n))
    per_row = max(1, int(per_row))

    slots: list = []
    remaining = total

    while remaining > 0:
        cols_in_row = min(per_row, remaining)
        row = st.columns(cols_in_row, gap=gap)
        slots.extend(list(row))
        remaining -= cols_in_row

    return slots


def grid(
    columns_desktop: int = 3,
    *,
    columns_mobile: int = 1,
    gap: str = "small",
) -> list:
    """
    Grid responsivo.

    Sempre retorna o mesmo número total de slots
    para evitar quebra em unpack no código chamador.
    """
    total = max(1, int(columns_desktop))

    if not is_mobile():
        return list(st.columns(total, gap=gap))

    mobile_cols = max(1, int(columns_mobile))
    if mobile_cols == 1:
        return _stack_slots(total)

    return _wrap_columns(total, per_row=mobile_cols, gap=gap)


def grid_weights(
    weights_desktop: Sequence[float],
    *,
    weights_mobile: Sequence[float] = (1,),
    gap: str = "small",
) -> list:
    """
    Grid com pesos no desktop.
    No mobile, empilha mantendo o mesmo número de slots.
    """
    weights = tuple(float(w) for w in weights_desktop if float(w) > 0) or (1.0,)

    if is_mobile():
        mobile_count = len(tuple(weights_mobile)) if weights_mobile else len(weights)
        return _stack_slots(max(1, mobile_count))

    return list(st.columns(weights, gap=gap))


# ==========================================================
# Surface
# ==========================================================


@contextmanager
def surface() -> Iterator[None]:
    """Container visual padrão."""
    st.markdown('<div class="sp-surface">', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
# Section
# ==========================================================


def _section_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


@contextmanager
def section(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    header_actions: Callable[[], None] | None = None,
    divider: bool = False,
    top_pad_rem: float | None = None,
    bottom_pad_rem: float | None = None,
) -> Iterator[None]:
    """
    Seção padrão com header e surface.

    - Em desktop: header e ações ficam lado a lado.
    - Em mobile: ações descem para baixo do título.
    """
    if top_pad_rem:
        spacer(top_pad_rem)

    if title:
        if header_actions and not is_mobile():
            left, right = st.columns([3, 2], gap="small")

            with left:
                _section_header(title, subtitle)

            with right:
                header_actions()
        else:
            _section_header(title, subtitle)

            if header_actions:
                spacer(0.3)
                header_actions()

    if divider:
        st.divider()

    with surface():
        yield

    if bottom_pad_rem:
        spacer(bottom_pad_rem)


@contextmanager
def section_surface(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    header_actions: Callable[[], None] | None = None,
    divider: bool = False,
    top_pad_rem: float | None = None,
    bottom_pad_rem: float | None = None,
) -> Iterator[None]:
    """Alias de compatibilidade para section()."""
    with section(
        title=title,
        subtitle=subtitle,
        header_actions=header_actions,
        divider=divider,
        top_pad_rem=top_pad_rem,
        bottom_pad_rem=bottom_pad_rem,
    ):
        yield


# ==========================================================
# Toolbar
# ==========================================================


@contextmanager
def toolbar(gap: str = "small") -> Iterator[None]:
    """
    Área principal de toolbar.
    Em desktop rende a área da esquerda.
    Em mobile rende inline.
    """
    if is_mobile():
        yield
        return

    left, _ = st.columns([3, 2], gap=gap)
    with left:
        yield


def toolbar_actions(actions: Callable[[], None], *, gap: str = "small") -> None:
    """Renderiza ações da toolbar alinhadas à direita no desktop."""
    if is_mobile():
        actions()
        return

    _, right = st.columns([3, 2], gap=gap)
    with right:
        actions()


# ==========================================================
# Empty state
# ==========================================================


def empty_state(
    title: str = "Nada por aqui ainda",
    subtitle: str | None = "Quando você adicionar itens, eles vão aparecer aqui.",
) -> None:
    subtitle_html = (
        f"<div class='sp-muted' style='margin-top:6px'>{subtitle}</div>"
        if subtitle
        else ""
    )

    st.markdown(
        f"""
        <div class="sp-surface" style="text-align:center;padding:30px 18px;">
            <div style="font-size:30px;margin-bottom:8px">📭</div>
            <div style="font-weight:700;font-size:1.05rem">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# Page Header simples
# ==========================================================


@dataclass(frozen=True)
class PageMeta:
    title: str
    subtitle: str | None = None


def page_header(
    meta: PageMeta,
    *,
    right_actions: Callable[[], None] | None = None,
) -> None:
    """Header simples de página para telas que não usam page_header dedicado."""
    if not meta.title:
        return

    spacer(0.2)

    if right_actions and not is_mobile():
        left, right = st.columns([4, 2], gap="small", vertical_alignment="center")

        with left:
            st.markdown(f"## {meta.title}")
            if meta.subtitle:
                st.caption(meta.subtitle)

        with right:
            right_actions()
    else:
        st.markdown(f"## {meta.title}")

        if meta.subtitle:
            st.caption(meta.subtitle)

        if right_actions:
            spacer(0.4)
            right_actions()

    spacer(0.6)
