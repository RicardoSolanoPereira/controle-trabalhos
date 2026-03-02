import streamlit as st


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    right_button_label: str | None = None,
    right_button_key: str | None = None,
    right_button_help: str | None = None,
) -> bool:
    """
    Header padrão.

    Desktop:
      - título à esquerda
      - botão compacto à direita (não ocupa a coluna toda)

    Mobile:
      - empilha via CSS do theme.py
      - botão full width via CSS (media query)

    Retorna True se o botão foi clicado.
    """

    st.markdown('<div class="sp-page-header">', unsafe_allow_html=True)

    # mais espaço pro título, coluna do botão menor (compacta)
    left, right = st.columns([1, 0.22], vertical_alignment="center")

    with left:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)

    clicked = False
    with right:
        if right_button_label:
            # key automática se não vier
            key = right_button_key or f"ph_btn_{title}"

            # ✅ Desktop compacto: use_container_width=False
            # ✅ Mobile: CSS força width 100% nos botões
            clicked = st.button(
                right_button_label,
                key=key,
                help=right_button_help,
                use_container_width=False,
                type="primary",
            )

    st.markdown("</div>", unsafe_allow_html=True)
    st.divider()
    return bool(clicked)
