from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Callable, Sequence

import streamlit as st

from ui.layout import grid_weights, is_mobile, spacer

__all__ = [
    "HeaderAction",
    "page_header",
    "surface_start",
    "surface_end",
]


# ==========================================================
# Constantes
# ==========================================================

_PAGE_HEADER_CSS_KEY = "_sp_page_header_css_v7"


# ==========================================================
# Utils privados
# ==========================================================


def _render_html(content: str) -> None:
    """Renderiza HTML controlado pela aplicação."""
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None, *, quote: bool = False) -> str:
    """Escapa texto para uso seguro em HTML."""
    return html.escape(text or "", quote=quote)


def _safe_key(text: str) -> str:
    """Gera uma key estável para widgets."""
    normalized = (text or "").strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
    return normalized or "key"


def _normalize_actions(
    *,
    title: str,
    actions: list[HeaderAction] | None,
    right_button_label: str | None,
    right_button_key: str | None,
    right_button_help: str | None,
    right_button_on_click: Callable[[], None] | None,
) -> list["HeaderAction"]:
    """Normaliza ações do header mantendo compatibilidade com botão único."""
    if actions:
        return list(actions)

    if right_button_label:
        base_key = f"ph_{_safe_key(title)}"
        return [
            HeaderAction(
                label=right_button_label,
                key=right_button_key or f"{base_key}_btn",
                help=right_button_help,
                type="primary",
                on_click=right_button_on_click,
            )
        ]

    return []


def _normalize_actions_align(value: str | None) -> str:
    """Normaliza alinhamento das ações."""
    align = (value or "right").strip().lower()
    return align if align in {"left", "right"} else "right"


def _action_key(action: "HeaderAction", *, base_key: str) -> str:
    """Resolve key estável para um botão de ação."""
    return action.key or f"{base_key}_{_safe_key(action.label)}"


def _mobile_action(action: "HeaderAction") -> "HeaderAction":
    """Garante comportamento full width no mobile."""
    return HeaderAction(
        label=action.label,
        key=action.key,
        help=action.help,
        type=action.type,
        use_container_width=True,
        disabled=action.disabled,
        on_click=action.on_click,
    )


# ==========================================================
# Models
# ==========================================================


@dataclass(frozen=True)
class HeaderAction:
    label: str
    key: str | None = None
    help: str | None = None
    type: str = "primary"
    use_container_width: bool = True
    disabled: bool = False
    on_click: Callable[[], None] | None = None


# ==========================================================
# CSS local do header
# ==========================================================


def _inject_page_header_css() -> None:
    """Injeta CSS local do page header uma única vez por sessão."""
    if st.session_state.get(_PAGE_HEADER_CSS_KEY, False):
        return

    st.session_state[_PAGE_HEADER_CSS_KEY] = True

    _render_html(
        """
        <style>
        .sp-page-header-wrap{
            width:100%;
        }

        .sp-page-header{
            padding:0.02rem 0 0.02rem 0;
        }

        .sp-page-header-title{
            display:block;
            width:100%;
            min-width:0;
        }

        .sp-page-header-title-text{
            color:var(--text);
            letter-spacing:-0.025em;
            margin:0;
            display:block;
        }

        .sp-page-header-subtitle{
            margin-top:0.20rem;
            font-size:0.94rem;
            line-height:1.45;
            color:var(--muted);
            max-width:76ch;
        }

        .sp-page-header-actions{
            width:100%;
        }

        .sp-page-header-actions [data-testid="column"]{
            min-width:0 !important;
        }

        .sp-page-header-actions [data-testid="stButton"]{
            width:100%;
        }

        .sp-page-header-actions [data-testid="stButton"] > button{
            width:100%;
            height:42px !important;
            min-height:42px !important;
            max-height:42px !important;
            padding:0 14px !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            border-radius:12px;
            white-space:nowrap !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
        }

        .sp-page-header-actions [data-testid="stButton"] > button div[data-testid="stMarkdownContainer"]{
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            width:100%;
            line-height:1 !important;
        }

        .sp-page-header-actions [data-testid="stButton"] > button div[data-testid="stMarkdownContainer"] p{
            margin:0 !important;
            white-space:nowrap !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            line-height:1 !important;
        }

        .sp-page-header-actions-stack > div{
            margin-bottom:0.34rem;
        }

        .sp-page-header-actions-stack > div:last-child{
            margin-bottom:0;
        }

        .sp-page-header-more-actions details[data-testid="stExpander"]{
            margin-top:0.12rem;
        }

        .sp-page-header-more-actions summary{
            font-weight:650;
        }

        @media (max-width:768px){
            .sp-page-header{
                padding:0.02rem 0 0.02rem 0;
            }

            .sp-page-header-subtitle{
                font-size:0.92rem;
                margin-top:0.22rem;
                max-width:100%;
            }

            .sp-page-header-actions [data-testid="stButton"] > button{
                height:44px !important;
                min-height:44px !important;
                max-height:44px !important;
            }
        }
        </style>
        """
    )


# ==========================================================
# Render helpers
# ==========================================================


def _render_title_block(
    title: str,
    subtitle: str | None = None,
    *,
    compact: bool = False,
) -> None:
    """Renderiza bloco de título e subtítulo."""
    title_html = _escape(title)
    subtitle_html = _escape(subtitle) if subtitle else ""

    if compact:
        title_size = "1.05rem"
        title_weight = "800"
        title_line_height = "1.16"
        subtitle_size = "0.88rem"
    else:
        title_size = "1.72rem"
        title_weight = "860"
        title_line_height = "1.05"
        subtitle_size = "0.94rem"

    subtitle_block = (
        f"""
        <div class="sp-page-header-subtitle" style="font-size:{subtitle_size};">
            {subtitle_html}
        </div>
        """
        if subtitle_html
        else ""
    )

    _render_html(
        f"""
        <div class="sp-page-header-title">
          <div
            class="sp-page-header-title-text"
            style="
              font-size:{title_size};
              font-weight:{title_weight};
              line-height:{title_line_height};
            "
          >
            {title_html}
          </div>
          {subtitle_block}
        </div>
        """
    )


def _render_single_action(action: HeaderAction, *, key: str) -> bool:
    """Renderiza um botão de ação individual."""
    return st.button(
        action.label,
        key=key,
        help=action.help,
        type=action.type,
        use_container_width=action.use_container_width,
        disabled=action.disabled,
        on_click=action.on_click,
    )


def _render_actions_mobile(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    """Renderiza ações empilhadas no mobile."""
    clicked = False

    spacer(0.20)
    _render_html('<div class="sp-page-header-actions-stack">')
    try:
        for action in actions:
            resolved_key = _action_key(action, base_key=base_key)
            if _render_single_action(_mobile_action(action), key=resolved_key):
                clicked = True
    finally:
        _render_html("</div>")

    return clicked


def _render_actions_desktop(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    """Renderiza ações em linha no desktop com overflow em expander."""
    clicked = False
    action_list = list(actions)

    max_inline = 3
    inline_actions = action_list[:max_inline]
    extra_actions = action_list[max_inline:]

    if inline_actions:
        cols = st.columns(len(inline_actions), gap="small")
        for col, action in zip(cols, inline_actions):
            with col:
                if _render_single_action(
                    action, key=_action_key(action, base_key=base_key)
                ):
                    clicked = True

    if extra_actions:
        _render_html('<div class="sp-page-header-more-actions">')
        try:
            with st.expander("Mais ações", expanded=False):
                for action in extra_actions:
                    resolved_key = _action_key(action, base_key=base_key)
                    if _render_single_action(_mobile_action(action), key=resolved_key):
                        clicked = True
        finally:
            _render_html("</div>")

    return clicked


def _render_actions(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    """Renderiza bloco de ações conforme contexto responsivo."""
    if not actions:
        return False

    _render_html('<div class="sp-page-header-actions">')
    try:
        if is_mobile():
            return _render_actions_mobile(actions, base_key=base_key)
        return _render_actions_desktop(actions, base_key=base_key)
    finally:
        _render_html("</div>")


# ==========================================================
# Page Header
# ==========================================================


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    right_button_label: str | None = None,
    right_button_key: str | None = None,
    right_button_help: str | None = None,
    right_button_on_click: Callable[[], None] | None = None,
    actions: list[HeaderAction] | None = None,
    divider: bool = True,
    compact: bool = False,
    actions_align: str = "right",
    actions_width_ratio: tuple[float, float] = (4.8, 2.2),
    top_spacing_rem: float = 0.04,
    bottom_spacing_rem: float = 0.16,
) -> bool:
    """
    Renderiza header padrão de página.
    Retorna True se algum botão foi clicado.
    """
    _inject_page_header_css()

    if not title:
        return False

    base_key = f"ph_{_safe_key(title)}"
    normalized_actions = _normalize_actions(
        title=title,
        actions=actions,
        right_button_label=right_button_label,
        right_button_key=right_button_key,
        right_button_help=right_button_help,
        right_button_on_click=right_button_on_click,
    )
    align = _normalize_actions_align(actions_align)

    if top_spacing_rem:
        spacer(top_spacing_rem)

    clicked = False

    _render_html('<div class="sp-page-header-wrap">')
    _render_html('<div class="sp-page-header">')
    try:
        if is_mobile():
            _render_title_block(title, subtitle, compact=compact)
            if normalized_actions:
                clicked = _render_actions(normalized_actions, base_key=base_key)
        else:
            if normalized_actions:
                left_ratio, right_ratio = actions_width_ratio
                left, right = grid_weights(
                    (left_ratio, right_ratio),
                    weights_mobile=(1, 1),
                    gap="medium",
                )

                if align == "left":
                    with left:
                        clicked = _render_actions(normalized_actions, base_key=base_key)
                    with right:
                        _render_title_block(title, subtitle, compact=compact)
                else:
                    with left:
                        _render_title_block(title, subtitle, compact=compact)
                    with right:
                        clicked = _render_actions(normalized_actions, base_key=base_key)
            else:
                _render_title_block(title, subtitle, compact=compact)
    finally:
        _render_html("</div>")
        _render_html("</div>")

    if divider:
        spacer(0.14)
        st.divider()

    if bottom_spacing_rem:
        spacer(bottom_spacing_rem)

    return clicked


# ==========================================================
# Surfaces
# ==========================================================


def surface_start(class_name: str | None = None, style: str | None = None) -> None:
    """Abre manualmente uma surface HTML."""
    classes = "sp-surface"
    if class_name and class_name.strip():
        classes = f"{classes} {class_name.strip()}"

    class_attr = _escape(classes, quote=True)
    style_attr = f' style="{_escape(style, quote=True)}"' if style else ""

    _render_html(f'<div class="{class_attr}"{style_attr}>')


def surface_end() -> None:
    """Fecha manualmente uma surface HTML."""
    _render_html("</div>")
