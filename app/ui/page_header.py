from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import streamlit as st

from ui.layout import grid_weights, is_mobile, spacer


# ---------------------------------------------------------
# Utils
# ---------------------------------------------------------


def _safe_key(text: str) -> str:
    """Gera uma key estável para widgets."""
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"[^a-z0-9_]+", "", t)
    return t or "key"


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------


@dataclass(frozen=True)
class HeaderAction:
    label: str
    key: str | None = None
    help: Optional[str] = None
    type: str = "primary"
    use_container_width: bool = True
    disabled: bool = False
    on_click: Callable[[], None] | None = None


# ---------------------------------------------------------
# CSS local do header
# ---------------------------------------------------------


def _inject_page_header_css() -> None:
    css_key = "_sp_page_header_css_v5"
    if st.session_state.get(css_key):
        return

    st.session_state[css_key] = True

    st.markdown(
        """
        <style>
        .sp-page-header-wrap{
            width:100%;
        }

        .sp-page-header{
            padding:0.02rem 0 0.04rem 0;
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
            margin-top:0.22rem;
            font-size:0.94rem;
            line-height:1.42;
            color:var(--muted);
            max-width:72ch;
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
            margin-top:0.10rem;
        }

        @media (max-width: 768px){
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
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# Render helpers
# ---------------------------------------------------------


def _render_title_block(
    title: str,
    subtitle: str | None = None,
    *,
    compact: bool = False,
) -> None:
    title_h = html.escape(title or "")
    subtitle_h = html.escape(subtitle or "") if subtitle else ""

    if compact:
        title_size = "1.06rem"
        title_weight = "800"
        title_line_height = "1.16"
        subtitle_size = "0.89rem"
    else:
        title_size = "1.72rem"
        title_weight = "860"
        title_line_height = "1.06"
        subtitle_size = "0.94rem"

    subtitle_block = (
        f"""
        <div class="sp-page-header-subtitle" style="font-size:{subtitle_size};">
            {subtitle_h}
        </div>
        """
        if subtitle_h
        else ""
    )

    st.markdown(
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
            {title_h}
          </div>
          {subtitle_block}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_single_action(act: HeaderAction, *, key: str) -> bool:
    return st.button(
        act.label,
        key=key,
        help=act.help,
        type=act.type,
        use_container_width=act.use_container_width,
        disabled=act.disabled,
        on_click=act.on_click,
    )


def _render_actions_mobile(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    clicked = False

    spacer(0.20)

    st.markdown('<div class="sp-page-header-actions-stack">', unsafe_allow_html=True)
    try:
        for act in actions:
            act_key = act.key or f"{base_key}_{_safe_key(act.label)}"
            mobile_act = HeaderAction(
                label=act.label,
                key=act.key,
                help=act.help,
                type=act.type,
                use_container_width=True,
                disabled=act.disabled,
                on_click=act.on_click,
            )
            if _render_single_action(mobile_act, key=act_key):
                clicked = True
    finally:
        st.markdown("</div>", unsafe_allow_html=True)

    return clicked


def _render_actions_desktop(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    clicked = False
    actions = list(actions)

    max_inline = 3
    inline_actions = actions[:max_inline]
    extra_actions = actions[max_inline:]

    if inline_actions:
        cols = st.columns(len(inline_actions), gap="small")
        for col, act in zip(cols, inline_actions):
            act_key = act.key or f"{base_key}_{_safe_key(act.label)}"
            with col:
                if _render_single_action(act, key=act_key):
                    clicked = True

    if extra_actions:
        st.markdown('<div class="sp-page-header-more-actions">', unsafe_allow_html=True)
        try:
            with st.expander("Mais ações", expanded=False):
                for act in extra_actions:
                    act_key = act.key or f"{base_key}_{_safe_key(act.label)}"
                    extra_act = HeaderAction(
                        label=act.label,
                        key=act.key,
                        help=act.help,
                        type=act.type,
                        use_container_width=True,
                        disabled=act.disabled,
                        on_click=act.on_click,
                    )
                    if _render_single_action(extra_act, key=act_key):
                        clicked = True
        finally:
            st.markdown("</div>", unsafe_allow_html=True)

    return clicked


def _render_actions(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    if not actions:
        return False

    st.markdown('<div class="sp-page-header-actions">', unsafe_allow_html=True)
    try:
        if is_mobile():
            return _render_actions_mobile(actions, base_key=base_key)

        return _render_actions_desktop(actions, base_key=base_key)
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Page Header
# ---------------------------------------------------------


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

    normalized: list[HeaderAction] = []
    if actions:
        normalized = list(actions)
    elif right_button_label:
        normalized = [
            HeaderAction(
                label=right_button_label,
                key=right_button_key or f"{base_key}_btn",
                help=right_button_help,
                type="primary",
                on_click=right_button_on_click,
            )
        ]

    actions_align = (actions_align or "right").strip().lower()
    if actions_align not in {"left", "right"}:
        actions_align = "right"

    if top_spacing_rem:
        spacer(top_spacing_rem)

    clicked = False

    st.markdown('<div class="sp-page-header-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="sp-page-header">', unsafe_allow_html=True)
    try:
        if is_mobile():
            _render_title_block(title, subtitle, compact=compact)

            if normalized:
                clicked = _render_actions(normalized, base_key=base_key)

        else:
            if normalized:
                w_left, w_right = actions_width_ratio

                left, right = grid_weights(
                    (w_left, w_right),
                    weights_mobile=(1,),
                    gap="large",
                )

                if actions_align == "left":
                    with left:
                        clicked = _render_actions(normalized, base_key=base_key)
                    with right:
                        _render_title_block(title, subtitle, compact=compact)
                else:
                    with left:
                        _render_title_block(title, subtitle, compact=compact)
                    with right:
                        clicked = _render_actions(normalized, base_key=base_key)
            else:
                _render_title_block(title, subtitle, compact=compact)
    finally:
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if divider:
        spacer(0.14)
        st.divider()

    if bottom_spacing_rem:
        spacer(bottom_spacing_rem)

    return clicked


# ---------------------------------------------------------
# Surfaces
# ---------------------------------------------------------


def surface_start(class_name: str | None = None, style: str | None = None) -> None:
    classes = "sp-surface"
    if class_name:
        classes = f"{classes} {class_name.strip()}"

    classes_attr = html.escape(classes, quote=True)
    style_attr = f' style="{html.escape(style, quote=True)}"' if style else ""

    st.markdown(f'<div class="{classes_attr}"{style_attr}>', unsafe_allow_html=True)


def surface_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
