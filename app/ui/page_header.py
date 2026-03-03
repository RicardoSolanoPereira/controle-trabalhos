# app/ui/page_header.py
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional

import streamlit as st


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
    # Desktop compacto por padrão; pode virar full-width por ação
    use_container_width: bool = False


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    # modo simples (compatível com seu uso atual)
    right_button_label: str | None = None,
    right_button_key: str | None = None,
    right_button_help: str | None = None,
    # modo avançado (opcional)
    actions: list[HeaderAction] | None = None,
    divider: bool = True,
) -> bool:
    """
    Header padrão.

    Desktop:
      - título à esquerda
      - ações à direita, em linha quando possível

    Mobile:
      - empilha via CSS do theme.py (wrap)
      - botões podem ficar maiores via CSS
    """
    title_h = html.escape(title or "")
    subtitle_h = html.escape(subtitle or "") if subtitle else ""

    st.markdown('<div class="sp-page-header">', unsafe_allow_html=True)

    # Normaliza ações (mantém compatibilidade do modo simples)
    normalized: list[HeaderAction] = []
    if actions:
        normalized = actions
    elif right_button_label:
        key = right_button_key or f"ph_btn_{_safe_key(title)}"
        normalized = [
            HeaderAction(
                label=right_button_label,
                key=key,
                help=right_button_help,
                type="primary",
                use_container_width=False,
            )
        ]

    clicked_any = False

    if normalized:
        # Peso mais generoso na direita para não “apertar” botões em telas médias
        left, right = st.columns([1, 0.45], vertical_alignment="center")

        with left:
            st.markdown(f"## {title_h}")
            if subtitle_h:
                st.caption(subtitle_h)

        with right:
            # Container flex para ações (wrap no mobile por CSS do theme)
            st.markdown(
                "<div style='display:flex;justify-content:flex-end;gap:0.5rem;flex-wrap:wrap'>",
                unsafe_allow_html=True,
            )

            for act in normalized:
                act_key = act.key or f"ph_act_{_safe_key(title)}_{_safe_key(act.label)}"
                clicked = st.button(
                    act.label,
                    key=act_key,
                    help=act.help,
                    use_container_width=act.use_container_width,
                    type=act.type,
                )
                clicked_any = clicked_any or bool(clicked)

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Sem ações: header simples (melhor responsividade)
        st.markdown(f"## {title_h}")
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
