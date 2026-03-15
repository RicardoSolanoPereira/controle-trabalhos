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

MOBILE_FLAG_KEY = "force_mobile"

# ==========================================================
# Tokens de espaçamento e largura
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
# Helpers privados
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


def _clean_class_name(class_name: str | None) -> str:
    return (class_name or "").strip()


def _optional_style_attr(style: str | None) -> str:
    cleaned = (style or "").strip()
    if not cleaned:
        return ""
    return f' style="{_escape(cleaned, quote=True)}"'


def _optional_class_attr(class_name: str | None) -> str:
    cleaned = _clean_class_name(class_name)
    if not cleaned:
        return ""
    return f' class="{_escape(cleaned, quote=True)}"'


def _stack_slots(count: int) -> list:
    return [st.container() for _ in range(max(1, int(count)))]


def _wrap_columns(count: int, *, per_row: int, gap: str) -> list:
    total = max(1, int(count))
    cols_per_row = max(1, int(per_row))

    slots: list = []
    remaining = total

    while remaining > 0:
        current = min(cols_per_row, remaining)
        row = st.columns(current, gap=gap, vertical_alignment="top")
        slots.extend(list(row))
        remaining -= current

    return slots


def _two_column_row(
    *,
    left_ratio: float,
    right_ratio: float,
    gap: str,
    vertical_alignment: str = "center",
):
    return st.columns(
        [max(0.1, float(left_ratio)), max(0.1, float(right_ratio))],
        gap=gap,
        vertical_alignment=vertical_alignment,
    )


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
            <div class="sp-section-title-row">
                <div class="sp-section-title">{title_html}</div>
            </div>
            {subtitle_block}
        </div>
        """
    )


def _page_title_block(meta: "PageMeta") -> None:
    title_html = _escape(meta.title)
    subtitle_html = _escape(meta.subtitle) if meta.subtitle else ""

    subtitle_block = (
        f"<div class='sp-page-subtitle'>{subtitle_html}</div>'"
        if False
        else (
            f"<div class='sp-page-subtitle'>{subtitle_html}</div>"
            if subtitle_html
            else ""
        )
    )

    _render_html(
        f"""
        <div class="sp-page-header">
            <div class="sp-page-title-wrap">
                <div class="sp-page-title">{title_html}</div>
                {subtitle_block}
            </div>
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
        help="Simula layout mobile para validar empilhamento, espaçamentos e densidade visual.",
    )


# ==========================================================
# Espaçamento
# ==========================================================


def spacer(height_rem: float = SPACE_SM) -> None:
    height = _normalize_float(height_rem)
    _render_html(f"<div style='height:{height:.3f}rem'></div>")


def divider_space(top: float | None = None, bottom: float | None = None) -> None:
    top_value = SPACE_SM if top is None else _normalize_float(top)
    bottom_value = SPACE_SM if bottom is None else _normalize_float(bottom)

    if top_value > 0:
        spacer(top_value)

    st.divider()

    if bottom_value > 0:
        spacer(bottom_value)


def compact_gap() -> None:
    spacer(SPACE_XS if is_mobile() else SPACE_SM)


def section_gap() -> None:
    spacer(SPACE_SM if is_mobile() else SPACE_MD)


def page_gap() -> None:
    spacer(SPACE_MD if is_mobile() else SPACE_LG)


# ==========================================================
# Shell / largura útil
# ==========================================================


@contextmanager
def content_shell(
    *,
    max_width: str = PAGE_MAX_WIDTH,
    padding_inline: str | None = None,
    class_name: str | None = None,
) -> Iterator[None]:
    extra_class = _clean_class_name(class_name)

    shell_class = "sp-content-shell"
    if extra_class:
        shell_class = f"{shell_class} {extra_class}"

    effective_padding = (
        padding_inline
        if padding_inline is not None
        else (PAGE_PADDING_MOBILE if is_mobile() else PAGE_PADDING_DESKTOP)
    )

    style = (
        f"max-width:{max_width};"
        f"margin:0 auto;"
        f"width:100%;"
        f"padding-inline:{effective_padding};"
        f"box-sizing:border-box;"
    )

    _render_html(
        f"""
        <div class="{_escape(shell_class, quote=True)}" style="{_escape(style, quote=True)}">
        """
    )
    try:
        yield
    finally:
        _render_html("</div>")


@contextmanager
def topbar_shell(class_name: str | None = None) -> Iterator[None]:
    classes = ["sp-topbar-shell"]
    extra_class = _clean_class_name(class_name)
    if extra_class:
        classes.append(extra_class)

    _render_html(f'<div class="{_escape(" ".join(classes), quote=True)}">')
    try:
        with plain_block(class_name="sp-topbar"):
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
    gap: str = DEFAULT_GRID_GAP,
) -> list:
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
    gap: str = DEFAULT_GRID_GAP,
) -> list:
    desktop_weights = tuple(
        w for w in (float(v) for v in weights_desktop) if w > 0
    ) or (1.0,)

    if not is_mobile():
        return list(st.columns(desktop_weights, gap=gap, vertical_alignment="top"))

    if not weights_mobile:
        return _stack_slots(len(desktop_weights))

    mobile_weights_clean = tuple(w for w in (float(v) for v in weights_mobile) if w > 0)

    if not mobile_weights_clean:
        return _stack_slots(len(desktop_weights))

    return list(st.columns(mobile_weights_clean, gap=gap, vertical_alignment="top"))


def content_columns(
    left: float = 1.45,
    right: float = 1.0,
    *,
    gap: str = DEFAULT_GRID_GAP,
) -> tuple:
    if is_mobile():
        return st.container(), st.container()

    cols = st.columns([left, right], gap=gap, vertical_alignment="top")
    return cols[0], cols[1]


def split_hero(
    *,
    left_ratio: float = 1.20,
    right_ratio: float = 1.0,
    gap: str = DEFAULT_GRID_GAP,
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
    classes = ["sp-surface"]

    if not padded:
        classes.append("sp-surface-no-pad")

    extra_class = _clean_class_name(class_name)
    if extra_class:
        classes.append(extra_class)

    class_attr = f' class="{_escape(" ".join(classes), quote=True)}"'
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
    top_pad = (
        _normalize_float(top_pad_rem, minimum=0.0) if top_pad_rem is not None else 0.0
    )
    bottom_pad = (
        _normalize_float(bottom_pad_rem, minimum=0.0)
        if bottom_pad_rem is not None
        else 0.0
    )

    if top_pad > 0:
        spacer(top_pad)

    if title:
        if header_actions and not is_mobile():
            left, right = _two_column_row(
                left_ratio=4.0,
                right_ratio=1.5,
                gap=DEFAULT_GRID_GAP,
                vertical_alignment="center",
            )
            with left:
                _section_header(title, subtitle)
            with right:
                with plain_block(class_name="sp-section-actions"):
                    header_actions()
        else:
            _section_header(title, subtitle)
            if header_actions:
                compact_gap()
                with plain_block(
                    class_name="sp-section-actions sp-section-actions-mobile"
                ):
                    header_actions()

    if divider:
        divider_space(SPACE_XS, SPACE_SM)
    elif title:
        spacer(SPACE_2XS if compact else SPACE_XS)

    if use_surface:
        with surface(class_name=surface_class, style=surface_style):
            yield
    else:
        with st.container():
            yield

    if bottom_pad > 0:
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
# Toolbar / actions
# ==========================================================


def toolbar_row(
    left_content: Callable[[], None] | None = None,
    right_actions: Callable[[], None] | None = None,
    *,
    gap: str = DEFAULT_GRID_GAP,
    left_ratio: float = 3.0,
    right_ratio: float = 2.0,
    bottom_space: float = SPACE_SM,
) -> None:
    if is_mobile():
        if left_content:
            left_content()

        if right_actions:
            compact_gap()
            with plain_block(class_name="sp-toolbar-actions-mobile"):
                right_actions()

        if bottom_space > 0:
            spacer(bottom_space)
        return

    left, right = _two_column_row(
        left_ratio=left_ratio,
        right_ratio=right_ratio,
        gap=gap,
        vertical_alignment="center",
    )

    with left:
        if left_content:
            left_content()

    with right:
        if right_actions:
            with plain_block(class_name="sp-toolbar-actions"):
                right_actions()

    if bottom_space > 0:
        spacer(bottom_space)


def actions_row(
    render_actions: Callable[[], None],
    *,
    bottom_space: float = SPACE_SM,
) -> None:
    with plain_block(class_name="sp-actions-row"):
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
# Page Header
# ==========================================================


@dataclass(frozen=True)
class PageMeta:
    title: str
    subtitle: str | None = None


def page_header(
    meta: PageMeta,
    *,
    right_actions: Callable[[], None] | None = None,
    bottom_space: float = SPACE_MD,
) -> None:
    if not meta.title:
        return

    spacer(SPACE_2XS)

    if right_actions and not is_mobile():
        left, right = _two_column_row(
            left_ratio=4.0,
            right_ratio=1.5,
            gap=DEFAULT_GRID_GAP,
            vertical_alignment="center",
        )

        with left:
            _page_title_block(meta)

        with right:
            with plain_block(class_name="sp-page-header-actions"):
                right_actions()
    else:
        _page_title_block(meta)

        if right_actions:
            compact_gap()
            with plain_block(
                class_name="sp-page-header-actions sp-page-header-actions-mobile"
            ):
                right_actions()

    if bottom_space > 0:
        spacer(bottom_space)
