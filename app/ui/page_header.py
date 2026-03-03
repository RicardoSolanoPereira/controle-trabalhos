from __future__ import annotations

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
    # Desktop compacto por padrão; mobile fica full via CSS do theme.py
    use_container_width: bool = False


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    # modo simples (compatível com seu uso atual)
    right_button_label: str | None = None,
    right_button_key: str | None = None,
    right_button_help: str | None = None,
    # modo avançado (opcional; se você não usar, nada muda)
    actions: list[HeaderAction] | None = None,
    divider: bool = True,
) -> bool:
    """
    Header padrão.

    Desktop:
      - título à esquerda
      - botão(es) compactos à direita (não ocupa coluna toda)

    Mobile:
      - empilha via CSS do theme.py
      - botões ficam full width via CSS (media query)

    Retorna True se:
      - no modo simples: o botão da direita foi clicado
      - no modo actions: qualquer ação foi clicada
    """
    st.markdown('<div class="sp-page-header">', unsafe_allow_html=True)

    # coluna do botão menor (compacta)
    left, right = st.columns([1, 0.22], vertical_alignment="center")

    with left:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)

    clicked_any = False
    with right:
        normalized: list[HeaderAction] = []

        # se vier actions, usa; senão mantém modo simples
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
                    use_container_width=False,  # desktop compacto
                )
            ]

        for act in normalized:
            clicked = st.button(
                act.label,
                key=act.key,
                help=act.help,
                use_container_width=act.use_container_width,
                type=act.type,
            )
            clicked_any = clicked_any or bool(clicked)

    st.markdown("</div>", unsafe_allow_html=True)

    if divider:
        st.divider()

    return bool(clicked_any)


def surface_start() -> None:
    """Abre um bloco visual 'surface' (card grande)."""
    st.markdown('<div class="sp-surface">', unsafe_allow_html=True)


def surface_end() -> None:
    """Fecha um bloco visual 'surface'."""
    st.markdown("</div>", unsafe_allow_html=True)
