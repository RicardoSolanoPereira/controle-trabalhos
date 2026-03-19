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

_PAGE_HEADER_CSS_KEY = "_sp_page_header_css_v41"
_MAX_INLINE_ACTIONS = 3
_ALLOWED_ACTION_TYPES = {"primary", "secondary"}
_ALLOWED_BADGE_TONES = {"neutral", "success", "warning", "danger", "info"}
_ALLOWED_EMPHASIS = {"default", "primary"}


# ==========================================================
# Utils privados
# ==========================================================


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None, *, quote: bool = False) -> str:
    return html.escape(str(text or ""), quote=quote)


def _safe_key(text: str) -> str:
    normalized = (text or "").strip().lower()
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
    return normalized or "key"


def _normalize_action_type(value: str | None) -> str:
    kind = (value or "primary").strip().lower()
    return kind if kind in _ALLOWED_ACTION_TYPES else "primary"


def _normalize_badge_tone(value: str | None) -> str:
    tone = (value or "neutral").strip().lower()
    return tone if tone in _ALLOWED_BADGE_TONES else "neutral"


def _normalize_emphasis(value: str | None) -> str:
    emphasis = (value or "default").strip().lower()
    return emphasis if emphasis in _ALLOWED_EMPHASIS else "default"


def _action_key(action: "HeaderAction", *, base_key: str) -> str:
    return action.key or f"{base_key}_{_safe_key(action.label)}"


def _action_label(action: "HeaderAction") -> str:
    if action.icon:
        return f"{action.icon} {action.label}"
    return action.label


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
    icon: str | None = None
    emphasis: str = "default"  # default | primary


# ==========================================================
# Normalização
# ==========================================================


def _normalize_actions(
    *,
    title: str,
    actions: Sequence[HeaderAction] | None,
    right_button_label: str | None,
    right_button_key: str | None,
    right_button_help: str | None,
    right_button_on_click: Callable[[], None] | None,
) -> list[HeaderAction]:
    normalized: list[HeaderAction] = []

    if actions:
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
                    icon=(action.icon or "").strip() or None,
                    emphasis=_normalize_emphasis(action.emphasis),
                )
            )
        return normalized

    if right_button_label and right_button_label.strip():
        base_key = f"ph_{_safe_key(title)}"
        normalized.append(
            HeaderAction(
                label=right_button_label.strip(),
                key=right_button_key or f"{base_key}_btn",
                help=right_button_help,
                type="primary",
                use_container_width=True,
                disabled=False,
                on_click=right_button_on_click,
                icon=None,
                emphasis="primary",
            )
        )

    return normalized


def _mobile_action(action: HeaderAction) -> HeaderAction:
    return HeaderAction(
        label=action.label,
        key=action.key,
        help=action.help,
        type=action.type,
        use_container_width=True,
        disabled=action.disabled,
        on_click=action.on_click,
        icon=action.icon,
        emphasis=action.emphasis,
    )


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
        .sp-page-header-shell{
            width:100%;
            border:1px solid rgba(15,23,42,0.06);
            border-radius:18px;
            background:
                linear-gradient(
                    180deg,
                    rgba(255,255,255,0.84) 0%,
                    rgba(255,255,255,0.68) 100%
                );
            box-shadow:
                0 1px 2px rgba(15,23,42,0.03),
                0 12px 30px rgba(15,23,42,0.035);
            padding:1rem 1.05rem;
        }

        .sp-page-header-title-block{
            min-width:0;
            width:100%;
        }

        .sp-page-header-meta{
            display:flex;
            align-items:center;
            gap:0.5rem;
            flex-wrap:wrap;
            margin-bottom:0.32rem;
        }

        .sp-page-header-eyebrow{
            display:inline-flex;
            align-items:center;
            min-height:24px;
            padding:0 0.62rem;
            border-radius:999px;
            font-size:0.72rem;
            font-weight:800;
            letter-spacing:0.08em;
            text-transform:uppercase;
            background:rgba(15,23,42,0.055);
            color:rgba(15,23,42,0.72);
            border:1px solid rgba(15,23,42,0.05);
        }

        .sp-page-header-badge{
            display:inline-flex;
            align-items:center;
            min-height:24px;
            padding:0 0.62rem;
            border-radius:999px;
            font-size:0.74rem;
            font-weight:700;
            border:1px solid transparent;
            white-space:nowrap;
        }

        .sp-page-header-badge--neutral{
            background:rgba(15,23,42,0.055);
            color:rgba(15,23,42,0.76);
            border-color:rgba(15,23,42,0.06);
        }

        .sp-page-header-badge--success{
            background:rgba(22,163,74,0.10);
            color:#166534;
            border-color:rgba(22,163,74,0.18);
        }

        .sp-page-header-badge--warning{
            background:rgba(245,158,11,0.12);
            color:#92400e;
            border-color:rgba(245,158,11,0.20);
        }

        .sp-page-header-badge--danger{
            background:rgba(239,68,68,0.10);
            color:#b91c1c;
            border-color:rgba(239,68,68,0.18);
        }

        .sp-page-header-badge--info{
            background:rgba(59,130,246,0.10);
            color:#1d4ed8;
            border-color:rgba(59,130,246,0.18);
        }

        .sp-page-header-title-text{
            display:block;
            margin:0;
            min-width:0;
            color:var(--text);
            letter-spacing:-0.035em;
        }

        .sp-page-header-subtitle-text{
            margin-top:0.34rem;
            max-width:74ch;
            color:var(--muted);
            line-height:1.56;
        }

        .sp-page-header-subtitle-text strong{
            color:var(--text);
            font-weight:700;
        }

        .sp-page-header-actions .stButton{
            width:100%;
        }

        .sp-page-header-actions [data-testid="column"]{
            min-width:0 !important;
        }

        .sp-page-header-actions .stButton > button{
            width:100%;
            min-height:44px !important;
            border-radius:14px !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            white-space:nowrap !important;
            word-break:keep-all !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            padding-inline:14px !important;
            font-weight:650 !important;
            transition:
                transform 120ms ease,
                box-shadow 120ms ease,
                border-color 120ms ease !important;
            box-shadow:0 1px 2px rgba(15,23,42,0.04);
        }

        .sp-page-header-actions .stButton > button:hover{
            transform:translateY(-1px);
            box-shadow:0 8px 18px rgba(15,23,42,0.08);
        }

        .sp-page-header-divider-space{
            margin-top:0.18rem;
        }

        @media (max-width:768px){
            .sp-page-header-shell{
                border-radius:16px;
                padding:0.90rem 0.92rem;
            }

            .sp-page-header-subtitle-text{
                max-width:100%;
                font-size:0.90rem;
            }

            .sp-page-header-actions .stButton > button{
                min-height:46px !important;
            }
        }
        </style>
        """
    )


# ==========================================================
# Render helpers
# ==========================================================


def _render_meta_row(
    *,
    eyebrow: str | None = None,
    badge: str | None = None,
    badge_tone: str = "neutral",
) -> None:
    eyebrow_html = _escape(eyebrow) if eyebrow else ""
    badge_html = _escape(badge) if badge else ""

    if not eyebrow_html and not badge_html:
        return

    tone = _normalize_badge_tone(badge_tone)

    eyebrow_block = (
        f'<div class="sp-page-header-eyebrow">{eyebrow_html}</div>'
        if eyebrow_html
        else ""
    )

    badge_block = (
        f'<div class="sp-page-header-badge sp-page-header-badge--{tone}">{badge_html}</div>'
        if badge_html
        else ""
    )

    _render_html(
        f"""
        <div class="sp-page-header-meta">
            {eyebrow_block}
            {badge_block}
        </div>
        """
    )


def _render_title_block(
    title: str,
    subtitle: str | None = None,
    *,
    eyebrow: str | None = None,
    badge: str | None = None,
    badge_tone: str = "neutral",
    compact: bool = False,
) -> None:
    title_html = _escape(title)
    subtitle_html = _escape(subtitle) if subtitle else ""

    if compact:
        title_size = "1.04rem"
        title_weight = "780"
        title_line_height = "1.16"
        subtitle_size = "0.86rem"
    else:
        title_size = "1.62rem"
        title_weight = "820"
        title_line_height = "1.03"
        subtitle_size = "0.93rem"

    subtitle_block = (
        f"""
        <div class="sp-page-header-subtitle-text" style="font-size:{subtitle_size};">
            {subtitle_html}
        </div>
        """
        if subtitle_html
        else ""
    )

    with st.container():
        _render_html('<div class="sp-page-header-title-block">')
        _render_meta_row(eyebrow=eyebrow, badge=badge, badge_tone=badge_tone)
        _render_html(
            f"""
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
            """
        )


def _render_single_action(action: HeaderAction, *, key: str) -> bool:
    button_type = "primary" if action.emphasis == "primary" else action.type

    return st.button(
        _action_label(action),
        key=key,
        help=action.help,
        type=button_type,
        use_container_width=action.use_container_width,
        disabled=action.disabled,
        on_click=action.on_click,
    )


def _render_actions_mobile(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    clicked = False

    spacer(0.18)
    with st.container():
        for action in actions:
            resolved_key = _action_key(action, base_key=base_key)
            if _render_single_action(_mobile_action(action), key=resolved_key):
                clicked = True

    return clicked


def _render_actions_desktop(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    clicked = False
    action_list = list(actions)

    primary_actions = [a for a in action_list if a.emphasis == "primary"]
    default_actions = [a for a in action_list if a.emphasis != "primary"]

    ordered_actions = primary_actions[:1] + default_actions + primary_actions[1:]

    inline_actions = ordered_actions[:_MAX_INLINE_ACTIONS]
    extra_actions = ordered_actions[_MAX_INLINE_ACTIONS:]

    if inline_actions:
        cols = st.columns(len(inline_actions), gap="small")
        for col, action in zip(cols, inline_actions):
            with col:
                resolved_key = _action_key(action, base_key=base_key)
                if _render_single_action(action, key=resolved_key):
                    clicked = True

    if extra_actions:
        with st.expander("Mais ações", expanded=False):
            for action in extra_actions:
                resolved_key = _action_key(action, base_key=base_key)
                if _render_single_action(_mobile_action(action), key=resolved_key):
                    clicked = True

    return clicked


def _render_actions(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    if not actions:
        return False

    with st.container():
        _render_html('<div class="sp-page-header-actions">')
        if is_mobile():
            return _render_actions_mobile(actions, base_key=base_key)
        return _render_actions_desktop(actions, base_key=base_key)


# ==========================================================
# Public API
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
    actions_width_ratio: tuple[float, float] = (4.2, 2.6),
    top_spacing_rem: float = 0.06,
    bottom_spacing_rem: float = 0.28,
    eyebrow: str | None = None,
    badge: str | None = None,
    badge_tone: str = "neutral",
    surface: bool = True,
) -> bool:
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

    container = st.container(border=True) if surface else st.container()
    with container:
        if surface:
            _render_html('<div class="sp-page-header-shell">')

        if is_mobile():
            _render_title_block(
                title=title,
                subtitle=subtitle,
                eyebrow=eyebrow,
                badge=badge,
                badge_tone=badge_tone,
                compact=compact,
            )
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
                    _render_title_block(
                        title=title,
                        subtitle=subtitle,
                        eyebrow=eyebrow,
                        badge=badge,
                        badge_tone=badge_tone,
                        compact=compact,
                    )

                with right:
                    clicked = _render_actions(normalized_actions, base_key=base_key)
            else:
                _render_title_block(
                    title=title,
                    subtitle=subtitle,
                    eyebrow=eyebrow,
                    badge=badge,
                    badge_tone=badge_tone,
                    compact=compact,
                )

    if divider:
        _render_html('<div class="sp-page-header-divider-space"></div>')
        st.divider()

    if bottom_spacing_rem > 0:
        spacer(bottom_spacing_rem)

    return clicked
