# app/ui/layout.py
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Sequence

import streamlit as st


# ==========================================================
# Mobile / Responsivo
# ==========================================================
MOBILE_FLAG_KEY = "force_mobile"


def is_mobile() -> bool:
    """
    Heurística estável e prática para Streamlit:

    - Se o usuário forçou: st.session_state["force_mobile"] == True => mobile
    - Caso contrário: mantém desktop por padrão (Streamlit não expõe viewport de forma confiável)
    - Você pode acoplar outras heurísticas depois (JS, cookie, etc.)
    """
    forced = st.session_state.get(MOBILE_FLAG_KEY, None)
    return bool(forced is True)


def mobile_debug_toggle(*, label: str = "Forçar modo celular (teste)") -> None:
    """Toggle opcional para testar layout mobile no desktop."""
    st.toggle(
        label,
        key=MOBILE_FLAG_KEY,
        value=bool(st.session_state.get(MOBILE_FLAG_KEY, False)),
        help="Ativa layout empilhado para simular mobile no desktop.",
    )


# ==========================================================
# Espaçamento / Helpers básicos
# ==========================================================
def spacer(height_rem: float = 0.6) -> None:
    """Espaçamento vertical simples."""
    st.markdown(
        f"<div style='height:{float(height_rem)}rem'></div>",
        unsafe_allow_html=True,
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


# ==========================================================
# Grids responsivos
# ==========================================================
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


# ==========================================================
# Linhas de ação / Surface / Seções
# ==========================================================
@contextmanager
def surface(*, padding: bool = True):
    """
    Surface padrão (usa CSS .sp-surface do theme.py).

    Observação:
    - 'padding' é mantido para compatibilidade e extensões futuras.
    - O padding real é controlado pelo CSS (.sp-surface).
    """
    _ = padding
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
    header_actions: Callable[[], None] | None = None,
    top_pad_rem: float | None = None,
    bottom_pad_rem: float | None = None,
):
    """
    Seção padrão com header + surface.

    - header_actions: callable para renderizar ações no cabeçalho (lado direito)
    - top_pad_rem: respiro antes do header
    - bottom_pad_rem: respiro após a section
    """
    if top_pad_rem is not None:
        spacer(top_pad_rem)

    if title:
        if header_actions and not is_mobile():
            # Alinhamento REAL com colunas (Streamlit widgets respeitam)
            left, right = st.columns([3, 2], gap="small")
            with left:
                _section_header(title, subtitle)
            with right:
                # ações alinhadas naturalmente pela coluna
                header_actions()
        else:
            # Mobile ou sem ações: stack natural
            _section_header(title, subtitle)
            if header_actions:
                header_actions()

    if divider:
        st.divider()

    with surface():
        yield

    if bottom_pad_rem is not None:
        spacer(bottom_pad_rem)


@contextmanager
def section_surface(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    divider: bool = False,
    header_actions: Callable[[], None] | None = None,
    top_pad_rem: float | None = None,
    bottom_pad_rem: float | None = None,
):
    """Alias explícito para section(), mantido para compatibilidade."""
    with section(
        title,
        subtitle=subtitle,
        divider=divider,
        header_actions=header_actions,
        top_pad_rem=top_pad_rem,
        bottom_pad_rem=bottom_pad_rem,
    ):
        yield


# ==========================================================
# Toolbar (real) para filtros/ações
# ==========================================================
@contextmanager
def toolbar(*, right: bool = True, gap: str = "small"):
    """
    Toolbar para filtros/ações rápidas.

    Em desktop, você normalmente quer:
      - filtros à esquerda
      - ações à direita

    Como widgets Streamlit não respeitam <div> flex, usamos colunas.
    """
    if is_mobile():
        # Mobile: stack natural
        yield
        return

    if right:
        left, right_col = st.columns([3, 2], gap=gap)
        with left:
            yield  # o chamador coloca filtros aqui
        # não abrimos right_col automaticamente (senão vira confuso)
        # use toolbar_actions() abaixo para ações na coluna direita
    else:
        yield


def toolbar_actions(actions: Callable[[], None], *, gap: str = "small") -> None:
    """Ações na direita (desktop). Em mobile vira stack natural."""
    if is_mobile():
        actions()
        return
    _, right_col = st.columns([3, 2], gap=gap)
    with right_col:
        actions()


# ==========================================================
# Empty state
# ==========================================================
def empty_state(
    title: str = "Nada por aqui ainda",
    subtitle: str | None = "Quando você adicionar itens, eles vão aparecer aqui.",
) -> None:
    """Empty state leve para listas/sections vazias (UX)."""
    subtitle_html = (
        f"<div class='sp-muted' style='margin-top:6px'>{subtitle}</div>"
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="sp-surface" style="text-align:center;padding:22px 16px;">
          <div style="font-weight:800;font-size:1.02rem;">{title}</div>
          {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# Page header (novo helper: você vai usar no Painel/Trabalhos)
# ==========================================================
@dataclass(frozen=True)
class PageMeta:
    title: str
    subtitle: str | None = None


def page_header(
    meta: PageMeta, *, right_actions: Callable[[], None] | None = None
) -> None:
    """
    Cabeçalho padrão de página:
    - Desktop: título à esquerda, ações à direita
    - Mobile: stack natural
    """
    if not meta.title:
        return

    if right_actions and not is_mobile():
        left, right = st.columns([3, 2], gap="small", vertical_alignment="center")
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
            right_actions()
