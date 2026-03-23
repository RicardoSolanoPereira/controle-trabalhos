from __future__ import annotations

import streamlit as st


def section_card(title: str, description: str | None = None) -> None:
    st.markdown(f"### {title}")
    if description:
        st.markdown(
            f"<div style='color:#6b7280;font-size:0.95rem;margin-bottom:0.5rem;'>{description}</div>",
            unsafe_allow_html=True,
        )
