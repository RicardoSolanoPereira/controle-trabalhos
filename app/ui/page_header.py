from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional, Sequence

import streamlit as st

from ui.layout import grid_weights, is_mobile


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


# ---------------------------------------------------------
# Render Actions
# ---------------------------------------------------------


def _render_actions(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    """Renderiza os botões de ação do header."""

    if not actions:
        return False

    clicked = False
    actions = list(actions)

    # MOBILE
    if is_mobile():

        for act in actions:

            act_key = act.key or f"{base_key}_{_safe_key(act.label)}"

            if st.button(
                act.label,
                key=act_key,
                help=act.help,
                type=act.type,
                use_container_width=True,
                disabled=act.disabled,
            ):
                clicked = True

        return clicked

    # DESKTOP

    max_inline = 3

    inline_actions = actions[:max_inline]
    extra_actions = actions[max_inline:]

    cols = st.columns(len(inline_actions), gap="small")

    for col, act in zip(cols, inline_actions):

        act_key = act.key or f"{base_key}_{_safe_key(act.label)}"

        with col:

            if st.button(
                act.label,
                key=act_key,
                help=act.help,
                type=act.type,
                use_container_width=act.use_container_width,
                disabled=act.disabled,
            ):
                clicked = True

    if extra_actions:

        with st.expander("Mais ações", expanded=False):

            for act in extra_actions:

                act_key = act.key or f"{base_key}_{_safe_key(act.label)}"

                if st.button(
                    act.label,
                    key=act_key,
                    help=act.help,
                    type=act.type,
                    use_container_width=True,
                    disabled=act.disabled,
                ):
                    clicked = True

    return clicked


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
    actions: list[HeaderAction] | None = None,
    divider: bool = True,
    compact: bool = False,
    actions_align: str = "right",
    actions_width_ratio: tuple[float, float] = (3.2, 1.8),
) -> bool:
    """
    Renderiza header padrão de página.

    Retorna True se algum botão for clicado.
    """

    title_h = html.escape(title or "")
    subtitle_h = html.escape(subtitle or "") if subtitle else ""

    base_key = f"ph_{_safe_key(title)}"

    st.markdown('<div class="sp-page-header">', unsafe_allow_html=True)

    # -----------------------------------------------------
    # Normalize actions
    # -----------------------------------------------------

    normalized: list[HeaderAction] = []

    if actions:
        normalized = actions

    elif right_button_label:

        normalized = [
            HeaderAction(
                label=right_button_label,
                key=right_button_key or f"{base_key}_btn",
                help=right_button_help,
                type="primary",
            )
        ]

    clicked = False

    # -----------------------------------------------------
    # MOBILE
    # -----------------------------------------------------

    if is_mobile():

        st.markdown(f"### {title_h}" if compact else f"## {title_h}")

        if subtitle_h:
            st.caption(subtitle_h)

        if normalized:
            clicked = _render_actions(normalized, base_key=base_key)

        st.markdown("</div>", unsafe_allow_html=True)

        if divider:
            st.divider()

        return clicked

    # -----------------------------------------------------
    # DESKTOP
    # -----------------------------------------------------

    if normalized:

        w_left, w_right = actions_width_ratio

        left, right = grid_weights(
            (w_left, w_right),
            weights_mobile=(1,),
            gap="small",
        )

        if actions_align == "left":

            with left:
                clicked = _render_actions(normalized, base_key=base_key)

            with right:
                st.markdown(f"### {title_h}" if compact else f"## {title_h}")

                if subtitle_h:
                    st.caption(subtitle_h)

        else:

            with left:

                st.markdown(f"### {title_h}" if compact else f"## {title_h}")

                if subtitle_h:
                    st.caption(subtitle_h)

            with right:

                clicked = _render_actions(normalized, base_key=base_key)

    else:

        st.markdown(f"### {title_h}" if compact else f"## {title_h}")

        if subtitle_h:
            st.caption(subtitle_h)

    st.markdown("</div>", unsafe_allow_html=True)

    if divider:
        st.divider()

    return clicked


# ---------------------------------------------------------
# Surfaces
# ---------------------------------------------------------


def surface_start() -> None:
    st.markdown('<div class="sp-surface">', unsafe_allow_html=True)


def surface_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
