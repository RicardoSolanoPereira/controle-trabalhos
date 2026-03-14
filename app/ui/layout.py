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
    total = max(1, int(count))
    return [st.container() for _ in range(total)]


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
    height = _normalize_float(height_rem)
    _render_html(f"<div style='height:{height:.3f}rem'></div>")


def divider_space(top: float = 0.20, bottom: float = 0.22) -> None:
    top_value = _normalize_float(top)
    bottom_value = _normalize_float(bottom)

    if top_value > 0:
        spacer(top_value)

    st.divider()

    if bottom_value > 0:
        spacer(bottom_value)


def compact_gap() -> None:
    spacer(0.16 if is_mobile() else 0.20)


def section_gap() -> None:
    spacer(0.30 if is_mobile() else 0.40)


def page_gap() -> None:
    spacer(0.42 if is_mobile() else 0.56)


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
    extra_class = _clean_class_name(class_name)
    shell_class = "sp-content-shell"
    if extra_class:
        shell_class = f"{shell_class} {extra_class}"

    style = (
        f"max-width:{max_width}; "
        f"margin:0 auto; "
        f"width:100%; "
        f"padding-inline:{padding_inline};"
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


# ==========================================================
# Slots / grids
# ==========================================================


def grid(
    columns_desktop: int = 3,
    *,
    columns_mobile: int = 1,
    gap: str = "medium",
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
    gap: str = "medium",
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
        _normalize_float(top_pad_rem, minimum=0.0) if top_pad_rem is not None else None
    )
    bottom_pad = (
        _normalize_float(bottom_pad_rem, minimum=0.0)
        if bottom_pad_rem is not None
        else None
    )

    if top_pad and top_pad > 0:
        spacer(top_pad)

    if title:
        if header_actions and not is_mobile():
            left, right = _two_column_row(
                left_ratio=4.2,
                right_ratio=1.8,
                gap="medium",
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
        divider_space(0.12, 0.20)
    elif title:
        spacer(0.10 if compact else 0.16)

    if use_surface:
        with surface(class_name=surface_class, style=surface_style):
            yield
    else:
        with st.container():
            yield

    if bottom_pad and bottom_pad > 0:
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

    left, _ = _two_column_row(
        left_ratio=left_ratio,
        right_ratio=right_ratio,
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

    _, right = _two_column_row(
        left_ratio=left_ratio,
        right_ratio=right_ratio,
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
    bottom_space: float = 0.26,
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
            right_actions()

    if bottom_space > 0:
        spacer(bottom_space)


def actions_row(
    render_actions: Callable[[], None],
    *,
    bottom_space: float = 0.20,
) -> None:
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
    bottom_space: float = 0.32,
) -> None:
    if not meta.title:
        return

    spacer(0.03 if is_mobile() else 0.05)

    if right_actions and not is_mobile():
        left, right = _two_column_row(
            left_ratio=4.2,
            right_ratio=1.8,
            gap="medium",
            vertical_alignment="center",
        )

        with left:
            _page_title_block(meta)

        with right:
            right_actions()
    else:
        _page_title_block(meta)

        if right_actions:
            spacer(0.18 if is_mobile() else 0.24)
            right_actions()

    if bottom_space > 0:
        spacer(bottom_space)
