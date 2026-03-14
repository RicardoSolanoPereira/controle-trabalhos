from __future__ import annotations

import html
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Sequence

import streamlit as st

__all__ = [
    "MOBILE_FLAG_KEY",
    "PageMeta",
    "is_mobile",
    "mobile_debug_toggle",
    "spacer",
    "divider_space",
    "compact_gap",
    "section_gap",
    "page_gap",
    "grid",
    "grid_weights",
    "content_columns",
    "split_hero",
    "content_shell",
    "surface",
    "plain_block",
    "section",
    "section_surface",
    "toolbar",
    "toolbar_actions",
    "toolbar_row",
    "actions_row",
    "empty_state",
    "page_header",
]

MOBILE_FLAG_KEY = "force_mobile"


# ==========================================================
# Helpers privados
# ==========================================================


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None, *, quote: bool = False) -> str:
    return html.escape(text or "", quote=quote)


def _normalize_rem(value: float | int | None, *, minimum: float = 0.0) -> float:
    if value is None:
        return minimum
    return max(minimum, float(value))


def _optional_style_attr(style: str | None) -> str:
    if not style:
        return ""
    return f' style="{_escape(style, quote=True)}"'


def _optional_class_attr(class_name: str | None) -> str:
    if not class_name:
        return ""
    cleaned = class_name.strip()
    if not cleaned:
        return ""
    return f' class="{_escape(cleaned, quote=True)}"'


def _stack_slots(count: int) -> list:
    total = max(1, int(count))
    return [st.container() for _ in range(total)]


def _wrap_columns(count: int, *, per_row: int, gap: str) -> list:
    total = max(1, int(count))
    columns_per_row = max(1, int(per_row))

    slots: list = []
    remaining = total

    while remaining > 0:
        current = min(columns_per_row, remaining)
        row = st.columns(current, gap=gap, vertical_alignment="top")
        slots.extend(list(row))
        remaining -= current

    return slots


def _section_header(title: str, subtitle: str | None = None) -> None:
    title_html = _escape(title)
    subtitle_html = _escape(subtitle) if subtitle else ""

    subtitle_block = (
        f"<div class='sp-section-subtitle'>{subtitle_html}</div>"
        if subtitle_html
        else ""
    )

    _render_html(
        f"""
        <div class="sp-section-header">
          <div class="sp-section-title">{title_html}</div>
          {subtitle_block}
        </div>
        """
    )


def _page_title_block(meta: "PageMeta") -> None:
    title_html = _escape(meta.title)
    subtitle_html = _escape(meta.subtitle) if meta.subtitle else ""

    subtitle_block = (
        f"<div class='sp-page-subtitle'>{subtitle_html}</div>" if subtitle_html else ""
    )

    _render_html(
        f"""
        <div class="sp-page-header">
          <div class="sp-page-title">{title_html}</div>
          {subtitle_block}
        </div>
        """
    )


# ==========================================================
# Mobile
# ==========================================================


def is_mobile() -> bool:
    return bool(st.session_state.get(MOBILE_FLAG_KEY, False))


def mobile_debug_toggle(label: str = "Forçar modo celular (teste)") -> None:
    st.toggle(
        label,
        key=MOBILE_FLAG_KEY,
        value=is_mobile(),
        help="Simula layout mobile para validar empilhamento, cards e espaçamentos.",
    )


# ==========================================================
# Espaçamento
# ==========================================================


def spacer(height_rem: float = 0.5) -> None:
    height = _normalize_rem(height_rem)
    _render_html(f"<div style='height:{height:.3f}rem'></div>")


def divider_space(top: float = 0.18, bottom: float = 0.20) -> None:
    top_value = _normalize_rem(top)
    bottom_value = _normalize_rem(bottom)

    if top_value > 0:
        spacer(top_value)

    st.divider()

    if bottom_value > 0:
        spacer(bottom_value)


def compact_gap() -> None:
    spacer(0.14 if is_mobile() else 0.16)


def section_gap() -> None:
    spacer(0.26 if is_mobile() else 0.34)


def page_gap() -> None:
    spacer(0.34 if is_mobile() else 0.46)


# ==========================================================
# Shell / largura útil
# ==========================================================


@contextmanager
def content_shell(
    *,
    max_width: str = "1320px",
    padding_inline: str = "0px",
    class_name: str | None = None,
) -> Iterator[None]:
    """
    Centraliza e limita a largura útil do conteúdo.
    Útil para reduzir sensação de espaço vazio em telas largas.
    """
    extra_class = f" {class_name.strip()}" if class_name and class_name.strip() else ""
    style = f"max-width:{max_width}; margin:0 auto; width:100%; padding-inline:{padding_inline};"

    _render_html(
        f"""
        <div class="sp-content-shell{_escape(extra_class, quote=True)}" style="{_escape(style, quote=True)}">
        """
    )
    try:
        yield
    finally:
        _render_html("</div>")


# ==========================================================
# Slots / grids
# ==========================================================


def grid(
    columns_desktop: int = 3,
    *,
    columns_mobile: int = 1,
    gap: str = "medium",
) -> list:
    """
    Grid responsivo.
    Sempre retorna o mesmo número total de slots.
    """
    total = max(1, int(columns_desktop))

    if not is_mobile():
        return list(st.columns(total, gap=gap, vertical_alignment="top"))

    mobile_cols = max(1, int(columns_mobile))
    if mobile_cols == 1:
        return _stack_slots(total)

    return _wrap_columns(total, per_row=mobile_cols, gap=gap)


def grid_weights(
    weights_desktop: Sequence[float],
    *,
    weights_mobile: Sequence[float] | None = None,
    gap: str = "medium",
) -> list:
    """
    Grid com pesos no desktop.
    Em mobile:
    - sem weights_mobile: empilha
    - com weights_mobile: cria linha(s) com a quantidade indicada
    """
    desktop_weights = tuple(float(w) for w in weights_desktop if float(w) > 0) or (1.0,)

    if not is_mobile():
        return list(st.columns(desktop_weights, gap=gap, vertical_alignment="top"))

    if not weights_mobile:
        return _stack_slots(len(desktop_weights))

    mobile_weights_clean = tuple(float(w) for w in weights_mobile if float(w) > 0)
    if not mobile_weights_clean:
        return _stack_slots(len(desktop_weights))

    return list(st.columns(mobile_weights_clean, gap=gap, vertical_alignment="top"))


def content_columns(
    left: float = 1.65,
    right: float = 1.0,
    *,
    gap: str = "medium",
) -> tuple:
    if is_mobile():
        return st.container(), st.container()

    cols = st.columns([left, right], gap=gap, vertical_alignment="top")
    return cols[0], cols[1]


def split_hero(
    *,
    left_ratio: float = 1.45,
    right_ratio: float = 1.0,
    gap: str = "medium",
) -> tuple:
    if is_mobile():
        return st.container(), st.container()

    cols = st.columns([left_ratio, right_ratio], gap=gap, vertical_alignment="top")
    return cols[0], cols[1]


# ==========================================================
# Surface / blocks
# ==========================================================


@contextmanager
def surface(
    *,
    class_name: str | None = None,
    style: str | None = None,
    padded: bool = True,
) -> Iterator[None]:
    classes = "sp-surface"
    if not padded:
        classes += " sp-surface-no-pad"
    if class_name and class_name.strip():
        classes = f"{classes} {class_name.strip()}"

    class_attr = f' class="{_escape(classes, quote=True)}"'
    style_attr = _optional_style_attr(style)

    _render_html(f"<div{class_attr}{style_attr}>")
    try:
        yield
    finally:
        _render_html("</div>")


@contextmanager
def plain_block(
    *,
    class_name: str | None = None,
    style: str | None = None,
) -> Iterator[None]:
    class_attr = _optional_class_attr(class_name)
    style_attr = _optional_style_attr(style)

    _render_html(f"<div{class_attr}{style_attr}>")
    try:
        yield
    finally:
        _render_html("</div>")


# ==========================================================
# Section
# ==========================================================


@contextmanager
def section(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    header_actions: Callable[[], None] | None = None,
    divider: bool = False,
    top_pad_rem: float | None = None,
    bottom_pad_rem: float | None = None,
    surface_class: str | None = None,
    surface_style: str | None = None,
    use_surface: bool = True,
    compact: bool = False,
) -> Iterator[None]:
    """
    Seção padrão com header opcional e surface opcional.
    """
    top_pad = (
        _normalize_rem(top_pad_rem, minimum=0.0) if top_pad_rem is not None else None
    )
    bottom_pad = (
        _normalize_rem(bottom_pad_rem, minimum=0.0)
        if bottom_pad_rem is not None
        else None
    )

    if top_pad is not None and top_pad > 0:
        spacer(top_pad)

    if title:
        if header_actions and not is_mobile():
            left, right = st.columns(
                [4.2, 1.8],
                gap="medium",
                vertical_alignment="center",
            )

            with left:
                _section_header(title, subtitle)

            with right:
                _render_html("<div style='height:0.08rem'></div>")
                header_actions()
        else:
            _section_header(title, subtitle)

            if header_actions:
                compact_gap()
                header_actions()

    if divider:
        divider_space(0.10, 0.18)
    elif title:
        spacer(0.10 if compact else 0.14)

    if use_surface:
        with surface(class_name=surface_class, style=surface_style):
            yield
    else:
        with st.container():
            yield

    if bottom_pad is not None and bottom_pad > 0:
        spacer(bottom_pad)


@contextmanager
def section_surface(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    header_actions: Callable[[], None] | None = None,
    divider: bool = False,
    top_pad_rem: float | None = None,
    bottom_pad_rem: float | None = None,
    surface_class: str | None = None,
    surface_style: str | None = None,
    compact: bool = False,
) -> Iterator[None]:
    with section(
        title=title,
        subtitle=subtitle,
        header_actions=header_actions,
        divider=divider,
        top_pad_rem=top_pad_rem,
        bottom_pad_rem=bottom_pad_rem,
        surface_class=surface_class,
        surface_style=surface_style,
        use_surface=True,
        compact=compact,
    ):
        yield


# ==========================================================
# Toolbar
# ==========================================================


@contextmanager
def toolbar(
    gap: str = "medium",
    *,
    left_ratio: float = 3.2,
    right_ratio: float = 2.0,
) -> Iterator[None]:
    if is_mobile():
        with st.container():
            yield
        return

    left, _ = st.columns(
        [left_ratio, right_ratio],
        gap=gap,
        vertical_alignment="center",
    )
    with left:
        yield


def toolbar_actions(
    actions: Callable[[], None],
    *,
    gap: str = "medium",
    left_ratio: float = 3.2,
    right_ratio: float = 2.0,
) -> None:
    if is_mobile():
        compact_gap()
        actions()
        return

    _, right = st.columns(
        [left_ratio, right_ratio],
        gap=gap,
        vertical_alignment="center",
    )
    with right:
        actions()


def toolbar_row(
    left_content: Callable[[], None] | None = None,
    right_actions: Callable[[], None] | None = None,
    *,
    gap: str = "medium",
    left_ratio: float = 3.2,
    right_ratio: float = 2.0,
    bottom_space: float = 0.24,
) -> None:
    if is_mobile():
        if left_content:
            left_content()
        if right_actions:
            compact_gap()
            right_actions()
        if bottom_space > 0:
            spacer(bottom_space)
        return

    left, right = st.columns(
        [left_ratio, right_ratio],
        gap=gap,
        vertical_alignment="center",
    )

    with left:
        if left_content:
            left_content()

    with right:
        if right_actions:
            right_actions()

    if bottom_space > 0:
        spacer(bottom_space)


def actions_row(
    render_actions: Callable[[], None],
    *,
    bottom_space: float = 0.18,
) -> None:
    """
    Linha simples para ações.
    Em mobile fica empilhado naturalmente.
    """
    with st.container():
        render_actions()

    if bottom_space > 0:
        spacer(bottom_space)


# ==========================================================
# Empty state
# ==========================================================


def empty_state(
    title: str = "Nada por aqui ainda",
    subtitle: str | None = "Quando você adicionar itens, eles vão aparecer aqui.",
    icon: str = "📭",
) -> None:
    title_html = _escape(title)
    subtitle_html = _escape(subtitle) if subtitle else ""
    icon_html = _escape(icon or "📭")

    subtitle_block = (
        f"<div class='sp-empty-state-subtitle'>{subtitle_html}</div>"
        if subtitle_html
        else ""
    )

    _render_html(
        f"""
        <div class="sp-surface sp-empty-state">
            <div class="sp-empty-state-icon">{icon_html}</div>
            <div class="sp-empty-state-title">{title_html}</div>
            {subtitle_block}
        </div>
        """
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
    bottom_space: float = 0.30,
) -> None:
    if not meta.title:
        return

    spacer(0.02 if is_mobile() else 0.04)

    if right_actions and not is_mobile():
        left, right = st.columns(
            [4.2, 1.8],
            gap="medium",
            vertical_alignment="center",
        )

        with left:
            _page_title_block(meta)

        with right:
            _render_html("<div style='height:0.06rem'></div>")
            right_actions()
    else:
        _page_title_block(meta)

        if right_actions:
            spacer(0.16 if is_mobile() else 0.22)
            right_actions()

    if bottom_space > 0:
        spacer(bottom_space)
