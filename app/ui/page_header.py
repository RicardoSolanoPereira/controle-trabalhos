# app/ui/page_header.py
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional, Sequence

import streamlit as st

from app.ui.layout import grid_weights, is_mobile


def _safe_key(text: str) -> str:
    """Gera uma key estável e segura (sem espaços/acentos/símbolos)."""
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r"[^a-z0-9_]+", "", t)
    return t or "key"


@dataclass(frozen=True)
class HeaderAction:
    label: str
    key: str
    help: Optional[str] = None
    type: str = "primary"  # "primary" | "secondary"
    use_container_width: bool = True
    disabled: bool = False


def _render_actions(actions: Sequence[HeaderAction], *, base_key: str) -> bool:
    """
    Renderiza ações em linha usando columns (funciona com widgets).
    Retorna True se algum botão foi clicado.
    """
    if not actions:
        return False

    # Em mobile: 1 por linha (menos poluição e clique melhor)
    if is_mobile():
        clicked_any = False
        for act in actions:
            act_key = act.key or f"{base_key}_{_safe_key(act.label)}"
            clicked_any = (
                st.button(
                    act.label,
                    key=act_key,
                    help=act.help,
                    type=act.type,
                    use_container_width=True,
                    disabled=act.disabled,
                )
                or clicked_any
            )
        return bool(clicked_any)

    # Desktop: tenta colocar na mesma linha
    # Limite prático: até 3 ações lado a lado; mais do que isso vira ruído
    actions = list(actions)
    max_inline = 3
    head = actions[:max_inline]
    tail = actions[max_inline:]

    cols = st.columns(len(head), gap="small")
    clicked_any = False
    for col, act in zip(cols, head):
        act_key = act.key or f"{base_key}_{_safe_key(act.label)}"
        with col:
            clicked_any = (
                col.button(
                    act.label,
                    key=act_key,
                    help=act.help,
                    type=act.type,
                    use_container_width=act.use_container_width,
                    disabled=act.disabled,
                )
                or clicked_any
            )

    # Se tiver mais ações, empilha abaixo (sem poluir o header)
    if tail:
        with st.expander("Mais ações", expanded=False):
            for act in tail:
                act_key = act.key or f"{base_key}_{_safe_key(act.label)}"
                clicked_any = (
                    st.button(
                        act.label,
                        key=act_key,
                        help=act.help,
                        type=act.type,
                        use_container_width=True,
                        disabled=act.disabled,
                    )
                    or clicked_any
                )

    return bool(clicked_any)


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    # modo simples (compatível)
    right_button_label: str | None = None,
    right_button_key: str | None = None,
    right_button_help: str | None = None,
    # modo avançado
    actions: list[HeaderAction] | None = None,
    divider: bool = True,
    compact: bool = False,
    # novo: controle fino
    actions_align: str = "right",  # "right" | "left"
    actions_width_ratio: tuple[float, float] = (3.2, 1.8),
) -> bool:
    """
    Header padrão (UI/UX consistente).

    Desktop:
      - título à esquerda
      - ações à direita (columns reais, sem HTML flex)

    Mobile (force_mobile):
      - stack natural: título -> ações
    """
    title_h = html.escape(title or "")
    subtitle_h = html.escape(subtitle or "") if subtitle else ""

    st.markdown('<div class="sp-page-header">', unsafe_allow_html=True)

    base_key = f"ph_{_safe_key(title)}"
    normalized: list[HeaderAction] = []

    # Normaliza ações (mantém compatibilidade do modo simples)
    if actions:
        normalized = actions
    elif right_button_label:
        key = right_button_key or f"{base_key}_btn"
        normalized = [
            HeaderAction(
                label=right_button_label,
                key=key,
                help=right_button_help,
                type="primary",
                use_container_width=True,
            )
        ]

    clicked_any = False

    # ==========================================================
    # Mobile: stack natural (menos ruído)
    # ==========================================================
    if is_mobile():
        st.markdown(f"### {title_h}" if compact else f"## {title_h}")
        if subtitle_h:
            st.caption(subtitle_h)
        if normalized:
            clicked_any = _render_actions(normalized, base_key=base_key)

        st.markdown("</div>", unsafe_allow_html=True)
        if divider:
            st.divider()
        return bool(clicked_any)

    # ==========================================================
    # Desktop: colunas reais
    # ==========================================================
    if normalized:
        w_left, w_right = actions_width_ratio
        left, right = grid_weights((w_left, w_right), weights_mobile=(1,), gap="small")

        if actions_align == "left":
            with left:
                clicked_any = _render_actions(normalized, base_key=base_key)
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
                clicked_any = _render_actions(normalized, base_key=base_key)

    else:
        st.markdown(f"### {title_h}" if compact else f"## {title_h}")
        if subtitle_h:
            st.caption(subtitle_h)

    st.markdown("</div>", unsafe_allow_html=True)

    if divider:
        st.divider()

    return bool(clicked_any)


# Mantidos por compatibilidade (mas ideal é usar layout.surface() do layout.py)
def surface_start() -> None:
    st.markdown('<div class="sp-surface">', unsafe_allow_html=True)


def surface_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
