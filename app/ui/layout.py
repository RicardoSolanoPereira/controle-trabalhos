from __future__ import annotations

import html
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Sequence

import streamlit as st


# ==========================================================
# Public API
# ==========================================================

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
    "topbar_shell",
    "surface",
    "plain_block",
    "section",
    "section_surface",
    "toolbar_row",
    "actions_row",
    "empty_state",
    "page_header",
]

# ==========================================================
# Mobile state
# ==========================================================

MOBILE_FLAG_KEY = "force_mobile"


def is_mobile() -> bool:
    return bool(st.session_state.get(MOBILE_FLAG_KEY, False))


def mobile_debug_toggle(label: str = "Forçar modo celular (teste)") -> None:
    st.toggle(
        label,
        key=MOBILE_FLAG_KEY,
        value=is_mobile(),
        help="Simula layout mobile para validar empilhamento e densidade visual.",
    )


# ==========================================================
# Layout tokens
# ==========================================================

SPACE_2XS = 0.08
SPACE_XS = 0.16
SPACE_SM = 0.30
SPACE_MD = 0.54
SPACE_LG = 0.88
SPACE_XL = 1.20

PAGE_MAX_WIDTH = "1360px"

PAGE_PADDING_DESKTOP = "12px"
PAGE_PADDING_MOBILE = "10px"

DEFAULT_GRID_GAP = "medium"


# ==========================================================
# Internal helpers
# ==========================================================


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None, *, quote: bool = False) -> str:
    return html.escape(text or "", quote=quote)


def _normalize_float(value: float | int | None, *, minimum: float = 0.0) -> float:
    if value is None:
        return minimum
    try:
        return max(minimum, float(value))
    except (TypeError, ValueError):
        return minimum


def _class_attr(name: str | None) -> str:
    if not name:
        return ""
    return f' class="{_escape(name.strip(), quote=True)}"'


def _style_attr(style: str | None) -> str:
    if not style:
        return ""
    return f' style="{_escape(style.strip(), quote=True)}"'


# ==========================================================
# Spacing
# ==========================================================


def spacer(height_rem: float = SPACE_SM) -> None:
    height = _normalize_float(height_rem)
    _render_html(f"<div style='height:{height:.3f}rem'></div>")


def divider_space(top: float | None = None, bottom: float | None = None) -> None:

    top = SPACE_SM if top is None else _normalize_float(top)
    bottom = SPACE_SM if bottom is None else _normalize_float(bottom)

    if top > 0:
        spacer(top)

    st.divider()

    if bottom > 0:
        spacer(bottom)


def compact_gap() -> None:
    spacer(SPACE_XS if is_mobile() else SPACE_SM)


def section_gap() -> None:
    spacer(SPACE_SM if is_mobile() else SPACE_MD)


def page_gap() -> None:
    spacer(SPACE_MD if is_mobile() else SPACE_LG)


# ==========================================================
# Page shell
# ==========================================================


@contextmanager
def content_shell(
    *,
    max_width: str = PAGE_MAX_WIDTH,
    padding_inline: str | None = None,
    class_name: str | None = None,
) -> Iterator[None]:

    padding = (
        padding_inline
        if padding_inline
        else (PAGE_PADDING_MOBILE if is_mobile() else PAGE_PADDING_DESKTOP)
    )

    style = (
        f"max-width:{max_width};"
        f"margin:0 auto;"
        f"width:100%;"
        f"padding-inline:{padding};"
        f"box-sizing:border-box;"
    )

    _render_html(
        f'<div class="sp-content-shell {_escape(class_name or "")}" style="{style}">'
    )

    try:
        yield
    finally:
        _render_html("</div>")


@contextmanager
def topbar_shell(class_name: str | None = None) -> Iterator[None]:

    classes = "sp-topbar-shell"

    if class_name:
        classes += f" {class_name}"

    _render_html(f'<div class="{_escape(classes)}">')

    try:
        with plain_block("sp-topbar"):
            yield
    finally:
        _render_html("</div>")


# ==========================================================
# Grid system
# ==========================================================


def grid(
    columns_desktop: int = 3,
    *,
    columns_mobile: int = 1,
    gap: str = DEFAULT_GRID_GAP,
) -> list:

    total = max(1, columns_desktop)

    if not is_mobile():
        return list(st.columns(total, gap=gap, vertical_alignment="top"))

    if columns_mobile == 1:
        return [st.container() for _ in range(total)]

    slots = []
    remaining = total

    while remaining > 0:
        current = min(columns_mobile, remaining)
        row = st.columns(current, gap=gap, vertical_alignment="top")
        slots.extend(row)
        remaining -= current

    return slots


def grid_weights(
    weights_desktop: Sequence[float],
    *,
    weights_mobile: Sequence[float] | None = None,
    gap: str = DEFAULT_GRID_GAP,
):

    desktop = tuple(float(w) for w in weights_desktop if w > 0) or (1,)

    if not is_mobile():
        return list(st.columns(desktop, gap=gap))

    if not weights_mobile:
        return [st.container() for _ in desktop]

    mobile = tuple(float(w) for w in weights_mobile if w > 0)

    if not mobile:
        return [st.container() for _ in desktop]

    return list(st.columns(mobile, gap=gap))


# ==========================================================
# Common column layouts
# ==========================================================


def content_columns(left: float = 1.45, right: float = 1.0):

    if is_mobile():
        return st.container(), st.container()

    cols = st.columns([left, right], gap=DEFAULT_GRID_GAP)
    return cols[0], cols[1]


def split_hero(left_ratio: float = 1.2, right_ratio: float = 1.0):

    if is_mobile():
        return st.container(), st.container()

    cols = st.columns([left_ratio, right_ratio], gap=DEFAULT_GRID_GAP)
    return cols[0], cols[1]


# ==========================================================
# Surface containers
# ==========================================================


@contextmanager
def surface(
    class_name: str | None = None,
    style: str | None = None,
    padded: bool = True,
):

    classes = ["sp-surface"]

    if not padded:
        classes.append("sp-surface-no-pad")

    if class_name:
        classes.append(class_name)

    _render_html(f'<div class="{" ".join(classes)}"{_style_attr(style)}>')

    try:
        yield
    finally:
        _render_html("</div>")


@contextmanager
def plain_block(class_name: str | None = None, style: str | None = None):

    _render_html(f"<div{_class_attr(class_name)}{_style_attr(style)}>")

    try:
        yield
    finally:
        _render_html("</div>")


# ==========================================================
# Section layout
# ==========================================================


def _section_header(title: str, subtitle: str | None = None):

    title_html = _escape(title)

    subtitle_block = (
        f"<div class='sp-section-subtitle'>{_escape(subtitle)}</div>"
        if subtitle
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


@contextmanager
def section(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    header_actions: Callable[[], None] | None = None,
    divider: bool = False,
    compact: bool = False,
):
    if title:
        _section_header(title, subtitle)

    if header_actions:
        with plain_block("sp-section-actions"):
            header_actions()

    if divider:
        divider_space(SPACE_XS, SPACE_SM)
    elif title:
        if compact:
            spacer(SPACE_2XS)
        else:
            spacer(SPACE_XS)

    with surface():
        yield


@contextmanager
def section_surface(title: str | None = None, **kwargs):

    with section(title, **kwargs):
        yield


# ==========================================================
# Toolbars
# ==========================================================


def toolbar_row(
    left_content: Callable[[], None] | None = None,
    right_actions: Callable[[], None] | None = None,
):

    if is_mobile():

        if left_content:
            left_content()

        if right_actions:
            compact_gap()
            right_actions()

        spacer(SPACE_SM)
        return

    left, right = st.columns([3, 2], gap=DEFAULT_GRID_GAP)

    with left:
        if left_content:
            left_content()

    with right:
        if right_actions:
            right_actions()

    spacer(SPACE_SM)


def actions_row(render_actions: Callable[[], None]):

    with plain_block("sp-actions-row"):
        render_actions()

    spacer(SPACE_SM)


# ==========================================================
# Empty state
# ==========================================================


def empty_state(
    title: str = "Nada por aqui ainda",
    subtitle: str | None = "Quando você adicionar itens, eles aparecerão aqui.",
    icon: str = "📭",
):

    _render_html(
        f"""
        <div class="sp-surface sp-empty-state">
            <div class="sp-empty-icon">{_escape(icon)}</div>
            <div class="sp-empty-title">{_escape(title)}</div>
            <div class="sp-empty-subtitle">{_escape(subtitle)}</div>
        </div>
        """
    )


# ==========================================================
# Page header
# ==========================================================


@dataclass(frozen=True)
class PageMeta:
    title: str
    subtitle: str | None = None


def page_header(
    meta: PageMeta,
    *,
    right_actions: Callable[[], None] | None = None,
):

    spacer(SPACE_XS)

    if right_actions and not is_mobile():

        left, right = st.columns([4, 1.5], gap=DEFAULT_GRID_GAP)

        with left:
            _page_title(meta)

        with right:
            right_actions()

    else:

        _page_title(meta)

        if right_actions:
            compact_gap()
            right_actions()

    spacer(SPACE_MD)


def _page_title(meta: PageMeta):

    subtitle = (
        f"<div class='sp-page-subtitle'>{_escape(meta.subtitle)}</div>"
        if meta.subtitle
        else ""
    )

    _render_html(
        f"""
        <div class="sp-page-header">
            <div class="sp-page-title">{_escape(meta.title)}</div>
            {subtitle}
        </div>
        """
    )
