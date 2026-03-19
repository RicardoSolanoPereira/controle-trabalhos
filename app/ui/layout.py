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
    "compact_gap",
    "section_gap",
    "page_gap",
    "divider_space",
    "grid",
    "grid_weights",
    "content_columns",
    "split_hero",
    "dashboard_rail",
    "content_shell",
    "page_stack",
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
        help="Simula layout mobile para validar empilhamento, densidade e ordem visual.",
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
SPACE_2XL = 1.60

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
    return html.escape(str(text or ""), quote=quote)


def _normalize_float(value: float | int | None, *, minimum: float = 0.0) -> float:
    if value is None:
        return minimum
    try:
        return max(minimum, float(value))
    except (TypeError, ValueError):
        return minimum


def _normalize_positive_sequence(values: Sequence[float] | None) -> tuple[float, ...]:
    if not values:
        return ()

    normalized: list[float] = []
    for value in values:
        try:
            weight = float(value)
        except (TypeError, ValueError):
            continue
        if weight > 0:
            normalized.append(weight)

    return tuple(normalized)


def _stacked_containers(total: int) -> list:
    return [st.container() for _ in range(max(1, total))]


def _surface_container(*, bordered: bool = True):
    """
    Wrapper nativo do Streamlit para evitar HTML envolvendo widgets.
    """
    try:
        return st.container(border=bordered)
    except TypeError:
        # compatibilidade com versões sem border=
        return st.container()


# ==========================================================
# Spacing system
# ==========================================================


def spacer(height_rem: float = SPACE_SM) -> None:
    height = _normalize_float(height_rem)
    _render_html(f"<div style='height:{height:.3f}rem'></div>")


def compact_gap() -> None:
    spacer(SPACE_XS if is_mobile() else SPACE_SM)


def section_gap() -> None:
    spacer(SPACE_SM if is_mobile() else SPACE_MD)


def page_gap() -> None:
    spacer(SPACE_MD if is_mobile() else SPACE_LG)


def divider_space(top: float | None = None, bottom: float | None = None) -> None:
    top_value = SPACE_SM if top is None else _normalize_float(top)
    bottom_value = SPACE_SM if bottom is None else _normalize_float(bottom)

    if top_value > 0:
        spacer(top_value)

    st.divider()

    if bottom_value > 0:
        spacer(bottom_value)


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
    """
    Mantido por compatibilidade.
    Não usa mais div HTML envolvendo widgets.
    """
    _ = max_width
    _ = padding_inline
    _ = class_name

    with st.container():
        yield


@contextmanager
def page_stack(class_name: str | None = None) -> Iterator[None]:
    _ = class_name
    with st.container():
        yield


@contextmanager
def topbar_shell(class_name: str | None = None) -> Iterator[None]:
    _ = class_name
    with st.container():
        yield


# ==========================================================
# Grid system
# ==========================================================


def grid(
    columns_desktop: int = 3,
    *,
    columns_mobile: int = 1,
    gap: str = DEFAULT_GRID_GAP,
) -> list:
    total = max(1, int(columns_desktop))

    if not is_mobile():
        return list(st.columns(total, gap=gap, vertical_alignment="top"))

    mobile_cols = max(1, int(columns_mobile))

    if mobile_cols == 1:
        return _stacked_containers(total)

    slots = []
    remaining = total

    while remaining > 0:
        current = min(mobile_cols, remaining)
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
    desktop = _normalize_positive_sequence(weights_desktop) or (1.0,)

    if not is_mobile():
        return list(st.columns(desktop, gap=gap, vertical_alignment="top"))

    mobile = _normalize_positive_sequence(weights_mobile)
    if not mobile:
        return _stacked_containers(len(desktop))

    return list(st.columns(mobile, gap=gap, vertical_alignment="top"))


# ==========================================================
# Common semantic layouts
# ==========================================================


def content_columns(left: float = 1.45, right: float = 1.0):
    if is_mobile():
        return st.container(), st.container()

    cols = st.columns([left, right], gap=DEFAULT_GRID_GAP, vertical_alignment="top")
    return cols[0], cols[1]


def split_hero(left_ratio: float = 1.2, right_ratio: float = 1.0):
    if is_mobile():
        return st.container(), st.container()

    cols = st.columns(
        [left_ratio, right_ratio],
        gap=DEFAULT_GRID_GAP,
        vertical_alignment="top",
    )
    return cols[0], cols[1]


def dashboard_rail(main: float = 1.55, aside: float = 1.0):
    if is_mobile():
        return st.container(), st.container()

    cols = st.columns([main, aside], gap=DEFAULT_GRID_GAP, vertical_alignment="top")
    return cols[0], cols[1]


# ==========================================================
# Primitive containers
# ==========================================================


@contextmanager
def plain_block(
    class_name: str | None = None,
    style: str | None = None,
) -> Iterator[None]:
    """
    Mantido por compatibilidade.
    Não envolve widgets com HTML.
    """
    _ = class_name
    _ = style
    with st.container():
        yield


@contextmanager
def surface(
    class_name: str | None = None,
    style: str | None = None,
    padded: bool = True,
) -> Iterator[None]:
    """
    Superfície nativa do Streamlit.
    class_name/style ficam mantidos só por compatibilidade de assinatura.
    """
    _ = class_name
    _ = style
    _ = padded

    with _surface_container(bordered=True):
        yield


# ==========================================================
# Section layout
# ==========================================================


def _section_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"### {_escape(title)}")
    if subtitle:
        st.caption(subtitle)


@contextmanager
def section(
    title: str | None = None,
    *,
    subtitle: str | None = None,
    header_actions: Callable[[], None] | None = None,
    divider: bool = False,
    compact: bool = False,
    surface_class: str | None = None,
    surface_style: str | None = None,
    padded: bool = True,
) -> Iterator[None]:
    _ = surface_class
    _ = surface_style
    _ = padded

    if title:
        if header_actions and not is_mobile():
            left, right = st.columns(
                [4, 1.2],
                gap=DEFAULT_GRID_GAP,
                vertical_alignment="center",
            )

            with left:
                _section_header(title, subtitle)

            with right:
                header_actions()
        else:
            _section_header(title, subtitle)

            if header_actions:
                compact_gap()
                header_actions()

    if divider:
        divider_space(SPACE_XS, SPACE_SM)
    elif title:
        spacer(SPACE_2XS if compact else SPACE_XS)

    with _surface_container(bordered=True):
        yield


@contextmanager
def section_surface(title: str | None = None, **kwargs) -> Iterator[None]:
    with section(title, **kwargs):
        yield


# ==========================================================
# Toolbars / action rows
# ==========================================================


def toolbar_row(
    left_content: Callable[[], None] | None = None,
    right_actions: Callable[[], None] | None = None,
) -> None:
    if is_mobile():
        if left_content:
            left_content()

        if right_actions:
            compact_gap()
            right_actions()

        spacer(SPACE_SM)
        return

    left, right = st.columns([3, 2], gap=DEFAULT_GRID_GAP, vertical_alignment="center")

    with left:
        if left_content:
            left_content()

    with right:
        if right_actions:
            right_actions()

    spacer(SPACE_SM)


def actions_row(render_actions: Callable[[], None]) -> None:
    with st.container():
        render_actions()
    spacer(SPACE_SM)


# ==========================================================
# Empty state
# ==========================================================


def empty_state(
    title: str = "Nada por aqui ainda",
    subtitle: str | None = "Quando você adicionar itens, eles aparecerão aqui.",
    icon: str = "📭",
) -> None:
    text = f"{icon} **{title}**"
    if subtitle:
        text += f"\n\n{subtitle}"
    st.info(text)


# ==========================================================
# Page header
# ==========================================================


@dataclass(frozen=True)
class PageMeta:
    title: str
    subtitle: str | None = None


def _page_title(meta: PageMeta) -> None:
    st.title(meta.title)
    if meta.subtitle:
        st.caption(meta.subtitle)


def page_header(
    meta: PageMeta,
    *,
    right_actions: Callable[[], None] | None = None,
) -> None:
    spacer(SPACE_XS)

    if right_actions and not is_mobile():
        left, right = st.columns(
            [4, 1.5],
            gap=DEFAULT_GRID_GAP,
            vertical_alignment="center",
        )

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
