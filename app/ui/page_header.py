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
]

_PAGE_HEADER_CSS_KEY = "_sp_page_header_css_v11"
_MAX_INLINE_ACTIONS = 3


# ==========================================================
# Utils privados
# ==========================================================


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None, *, quote: bool = False) -> str:
    return html.escape(text or "", quote=quote)


def _safe_key(text: str) -> str:
    normalized = (text or "").strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
    return normalized or "key"


def _normalize_action_type(value: str | None) -> str:
    kind = (value or "primary").strip().lower()
    return kind if kind in {"primary", "secondary"} else "primary"


def _action_key(action: "HeaderAction", *, base_key: str) -> str:
    return action.key or f"{base_key}_{_safe_key(action.label)}"


def _normalize_actions(
    *,
    title: str,
    actions: Sequence["HeaderAction"] | None,
    right_button_label: str | None,
    right_button_key: str | None,
    right_button_help: str | None,
    right_button_on_click: Callable[[], None] | None,
) -> list["HeaderAction"]:
    if actions:
        normalized: list[HeaderAction] = []

        for action in actions:
            label = (action.label or "").strip()
            if not label:
                continue

            normalized.append(
                HeaderAction(
                    label=label,
                    key=action.key,
                    help=action.help,
                    type=_normalize_action_type(action.type),
                    use_container_width=bool(action.use_container_width),
                    disabled=bool(action.disabled),
                    on_click=action.on_click,
                )
            )

        return normalized

    if right_button_label and right_button_label.strip():
        base_key = f"ph_{_safe_key(title)}"
        return [
            HeaderAction(
                label=right_button_label.strip(),
                key=right_button_key or f"{base_key}_btn",
                help=right_button_help,
                type="primary",
                use_container_width=True,
                disabled=False,
                on_click=right_button_on_click,
            )
        ]

    return []


def _mobile_action(action: "HeaderAction") -> "HeaderAction":
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
# Model
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
# CSS local
# ==========================================================


def _inject_page_header_css() -> None:
    if st.session_state.get(_PAGE_HEADER_CSS_KEY, False):
        return

    st.session_state[_PAGE_HEADER_CSS_KEY] = True

    _render_html(
        """
        <style>
        .sp-page-header-wrap{
            width:100%;
        }

        .sp-page-header-local{
            width:100%;
        }

        .sp-page-header-title-block{
            min-width:0;
            width:100%;
        }

        .sp-page-header-title-text{
            display:block;
            margin:0;
            min-width:0;
            color:var(--text);
            letter-spacing:-0.03em;
        }

        .sp-page-header-subtitle-text{
            margin-top:0.34rem;
            max-width:78ch;
            color:var(--muted);
            line-height:1.55;
        }

        .sp-page-header-actions{
            width:100%;
        }

        .sp-page-header-actions [data-testid="column"]{
            min-width:0 !important;
        }

        .sp-page-header-actions .stButton{
            width:100%;
        }

        .sp-page-header-actions .stButton > button{
            width:100%;
            min-height:42px !important;
            border-radius:12px !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            white-space:nowrap !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
        }

        .sp-page-header-actions-inline{
            width:100%;
        }

        .sp-page-header-actions-stack > div{
            margin-bottom:0.42rem;
        }

        .sp-page-header-actions-stack > div:last-child{
            margin-bottom:0;
        }

        .sp-page-header-more-actions{
            margin-top:0.45rem;
        }

        .sp-page-header-more-actions summary{
            font-weight:650;
        }

        .sp-page-header-more-actions details{
            background:transparent;
            box-shadow:none;
        }

        @media (max-width:768px){
            .sp-page-header-subtitle-text{
                max-width:100%;
                font-size:0.91rem;
            }

            .sp-page-header-actions .stButton > button{
                min-height:44px !important;
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
    title_html = _escape(title)
    subtitle_html = _escape(subtitle) if subtitle else ""

    if compact:
        title_size = "1.06rem"
        title_weight = "760"
        title_line_height = "1.18"
        subtitle_size = "0.88rem"
    else:
        title_size = "1.68rem"
        title_weight = "820"
        title_line_height = "1.04"
        subtitle_size = "0.95rem"

    subtitle_block = (
        f"""
        <div class="sp-page-header-subtitle-text" style="font-size:{subtitle_size};">
            {subtitle_html}
        </div>
        """
        if subtitle_html
        else ""
    )

    _render_html(
        f"""
        <div class="sp-page-header-title-block">
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
    clicked = False

    spacer(0.22)
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
    clicked = False
    action_list = list(actions)

    inline_actions = action_list[:_MAX_INLINE_ACTIONS]
    extra_actions = action_list[_MAX_INLINE_ACTIONS:]

    if inline_actions:
        _render_html('<div class="sp-page-header-actions-inline">')
        try:
            cols = st.columns(len(inline_actions), gap="small")
            for col, action in zip(cols, inline_actions):
                with col:
                    resolved_key = _action_key(action, base_key=base_key)
                    if _render_single_action(action, key=resolved_key):
                        clicked = True
        finally:
            _render_html("</div>")

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
    actions: Sequence[HeaderAction] | None = None,
    divider: bool = False,
    compact: bool = False,
    actions_width_ratio: tuple[float, float] = (4.3, 1.9),
    top_spacing_rem: float = 0.10,
    bottom_spacing_rem: float = 0.40,
) -> bool:
    """
    Renderiza o header padrão de página.
    Retorna True se algum botão foi clicado.
    """
    _inject_page_header_css()

    if not (title or "").strip():
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

    if top_spacing_rem > 0:
        spacer(top_spacing_rem)

    clicked = False

    _render_html('<div class="sp-page-header-wrap">')
    _render_html('<div class="sp-page-header-local">')
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
        spacer(0.22)
        st.divider()

    if bottom_spacing_rem > 0:
        spacer(bottom_spacing_rem)

    return clicked
