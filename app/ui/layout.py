from __future__ import annotations

import html
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterator, Sequence

import streamlit as st

from . import theme

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
    "page_frame",
    "header_actions",
    "form_panel",
    "list_panel",
    "filters_bar",
]

MOBILE_FLAG_KEY = "force_mobile"

SPACE_2XS = 0.08
SPACE_XS = 0.16
SPACE_SM = 0.30
SPACE_MD = 0.54
SPACE_LG = 0.88
SPACE_XL = 1.20
SPACE_2XL = 1.60

PAGE_MAX_WIDTH = "1380px"
PAGE_PADDING_DESKTOP = "12px"
PAGE_PADDING_MOBILE = "10px"

DEFAULT_GRID_GAP = "medium"


def is_mobile() -> bool:
    return bool(st.session_state.get(MOBILE_FLAG_KEY, False))


def mobile_debug_toggle(label: str = "Forçar modo celular (teste)") -> None:
    current = is_mobile()
    toggled = st.toggle(
        label,
        value=current,
        help="Simula layout mobile para validar empilhamento, densidade e ordem visual.",
    )
    st.session_state[MOBILE_FLAG_KEY] = toggled


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None, *, quote: bool = False) -> str:
    return html.escape("" if text is None else str(text), quote=quote)


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
    try:
        return st.container(border=bordered)
    except TypeError:
        return st.container()


def _section_header_html(title: str, subtitle: str | None = None) -> None:
    subtitle_block = (
        f"<div class='sp-section-subtitle'>{_escape(subtitle)}</div>"
        if subtitle
        else ""
    )
    _render_html(
        f"""
        <div class="sp-section-header">
          <div class="sp-section-title">{_escape(title)}</div>
          {subtitle_block}
        </div>
        """
    )


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


@contextmanager
def content_shell(
    *,
    max_width: str = PAGE_MAX_WIDTH,
    padding_inline: str | None = None,
    class_name: str | None = None,
) -> Iterator[None]:
    del max_width, padding_inline, class_name
    with st.container():
        yield


@contextmanager
def page_stack(class_name: str | None = None) -> Iterator[None]:
    del class_name
    with st.container():
        yield


@contextmanager
def topbar_shell(class_name: str | None = None) -> Iterator[None]:
    del class_name
    with st.container():
        yield


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


@contextmanager
def plain_block(
    class_name: str | None = None,
    style: str | None = None,
) -> Iterator[None]:
    del class_name, style
    with st.container():
        yield


@contextmanager
def surface(
    class_name: str | None = None,
    style: str | None = None,
    padded: bool = True,
) -> Iterator[None]:
    del class_name, style, padded
    with _surface_container(bordered=True):
        yield


def _section_header(
    title: str,
    subtitle: str | None = None,
) -> None:
    _section_header_html(title, subtitle)


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
    del surface_class, surface_style, padded

    if title:
        if header_actions and not is_mobile():
            left, right = st.columns(
                [4, 1.3],
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
    render_actions()
    spacer(SPACE_SM)


def empty_state(
    title: str = "Nada por aqui ainda",
    subtitle: str | None = "Quando você adicionar itens, eles aparecerão aqui.",
    icon: str = "📭",
) -> None:
    theme.empty_state(title=title, subtitle=subtitle or "", icon=icon)


@dataclass(frozen=True)
class PageMeta:
    title: str
    subtitle: str | None = None


def _page_title(meta: PageMeta) -> None:
    subtitle_block = (
        f"<div class='sp-page-subtitle'>{_escape(meta.subtitle)}</div>"
        if meta.subtitle
        else ""
    )
    _render_html(
        f"""
        <div class="sp-page-header">
          <div class="sp-page-title">{_escape(meta.title)}</div>
          {subtitle_block}
        </div>
        """
    )


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


@contextmanager
def page_frame(
    meta: PageMeta,
    *,
    right_actions: Callable[[], None] | None = None,
    max_width: str = PAGE_MAX_WIDTH,
    class_name: str | None = None,
) -> Iterator[None]:
    del max_width, class_name
    with content_shell():
        with page_stack():
            page_header(meta, right_actions=right_actions)
            yield


def header_actions(
    actions: Sequence[Callable[[], None]],
    *,
    gap: str = "small",
) -> None:
    valid_actions = [action for action in actions if action is not None]
    if not valid_actions:
        return

    if is_mobile() or len(valid_actions) == 1:
        for idx, action in enumerate(valid_actions):
            action()
            if idx < len(valid_actions) - 1:
                compact_gap()
        return

    cols = st.columns(len(valid_actions), gap=gap, vertical_alignment="center")
    for col, action in zip(cols, valid_actions):
        with col:
            action()


@contextmanager
def form_panel(
    title: str,
    *,
    subtitle: str | None = None,
    compact: bool = False,
    header_actions: Callable[[], None] | None = None,
) -> Iterator[None]:
    with section_surface(
        title,
        subtitle=subtitle,
        compact=compact,
        header_actions=header_actions,
    ):
        yield


@contextmanager
def list_panel(
    title: str,
    *,
    subtitle: str | None = None,
    compact: bool = False,
    header_actions: Callable[[], None] | None = None,
) -> Iterator[None]:
    with section_surface(
        title,
        subtitle=subtitle,
        compact=compact,
        header_actions=header_actions,
    ):
        yield


@contextmanager
def filters_bar(
    title: str | None = "Filtros",
    *,
    subtitle: str | None = None,
    compact: bool = True,
) -> Iterator[None]:
    with section_surface(
        title,
        subtitle=subtitle,
        compact=compact,
    ):
        yield
