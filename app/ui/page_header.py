import streamlit as st


def page_header(
    title: str,
    subtitle: str | None = None,
    *,
    right_button_label: str | None = None,
    right_button_key: str | None = None,
    right_button_help: str | None = None,
    right_button_full: bool = True,
) -> bool:
    """
    Header padrão de página.
    - Desktop: título à esquerda + botão à direita
    - Mobile: empilha (botão abaixo, largura total)
    Retorna True se o botão foi clicado.
    """
    st.markdown('<div class="sp-page-header">', unsafe_allow_html=True)

    left, right = st.columns([1, 0.28], vertical_alignment="center")
    with left:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)

    clicked = False
    with right:
        if right_button_label:
            clicked = st.button(
                right_button_label,
                key=right_button_key,
                help=right_button_help,
                use_container_width=right_button_full,
                type="primary",
            )

    st.markdown("</div>", unsafe_allow_html=True)
    st.divider()
    return clicked
