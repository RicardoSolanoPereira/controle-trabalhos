# app/ui/theme.py
from __future__ import annotations
import streamlit as st


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
          :root{
            --bg: #F5F7FA;
            --surface: #ffffff;
            --border: #e5e7eb;

            --text: #0f172a;
            --muted: #64748b;

            --primary: #1E2A38;
            --primary-2: #2F4F6F;

            --info: #1976d2;
            --success: #2E7D32;
            --warning: #ED6C02;
            --danger: #C62828;

            --radius-lg: 16px;
            --radius-md: 12px;

            --shadow: 0 1px 2px rgba(0,0,0,0.045);
            --shadow-2: 0 4px 10px rgba(0,0,0,0.10);
          }

          /* ==================================================
             BASE APP
          ================================================== */
          .stApp{
            background: var(--bg);
            color: var(--text);
          }

          /* Container principal (desktop) */
          .block-container{
            padding-top: 1.4rem;
            padding-bottom: 1.4rem;
            max-width: 1400px;
          }

          header[data-testid="stHeader"]{
            background: transparent;
          }

          h1, h2, h3, h4{
            letter-spacing: -0.015em;
            color: var(--text);
          }

          .stCaption{
            color: var(--muted) !important;
          }

          /* Remove um pouco de “respiro” exagerado em alguns widgets */
          div[data-testid="stVerticalBlock"] > div:has(> .stMarkdown){
            margin-bottom: 0.35rem;
          }

          /* ==================================================
             UTILITIES
          ================================================== */
          .sp-muted{ color: rgba(15,23,42,0.58); }
          .sp-chip{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(30,42,56,0.06);
            border: 1px solid rgba(30,42,56,0.14);
            font-size: 0.82rem;
            color: rgba(15,23,42,0.82);
            white-space: nowrap;
          }

          .sp-surface{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 14px 16px;
            box-shadow: var(--shadow);
          }

          /* ==================================================
             SIDEBAR
          ================================================== */
          section[data-testid="stSidebar"]{
            background-color: #f4f6f8;
            border-right: 1px solid var(--border);
          }

          section[data-testid="stSidebar"] .block-container{
            padding-top: 1rem;
            padding-bottom: 1rem;
          }

          section[data-testid="stSidebar"] hr{
            border-color: var(--border) !important;
          }

          /* Radio -> pill menu */
          section[data-testid="stSidebar"]
          div[role="radiogroup"]
          label[data-baseweb="radio"] > div:first-child{
            display: none !important;
          }

          section[data-testid="stSidebar"]
          div[role="radiogroup"]
          label[data-baseweb="radio"]{
            display: block;
            width: 100%;
            padding: 10px 14px;
            border-radius: 12px;
            margin-bottom: 6px;
            cursor: pointer;
            transition: all 0.12s ease;
            border: 1px solid rgba(30,42,56,0.10);
            background: rgba(255,255,255,0.70);
          }

          section[data-testid="stSidebar"]
          div[role="radiogroup"]
          label[data-baseweb="radio"]:hover{
            background: rgba(30,42,56,0.06);
            border-color: rgba(30,42,56,0.22);
            transform: translateY(-1px);
          }

          section[data-testid="stSidebar"]
          div[role="radiogroup"]
          label[data-baseweb="radio"]:has(input:checked){
            background: rgba(30,42,56,0.12);
            border: 1px solid rgba(30,42,56,0.35);
            border-left: 5px solid var(--primary);
            padding-left: 11px;
            font-weight: 780;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            transform: none;
          }

          /* ==================================================
             TABS (segmented)
          ================================================== */
          div[data-baseweb="tab-list"]{
            background: #ffffff !important;
            border: 1px solid rgba(30,42,56,0.18) !important;
            border-radius: 14px !important;
            padding: 6px !important;
            gap: 6px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
          }

          button[data-baseweb="tab"]{
            border-radius: 12px !important;
            padding: 10px 14px !important;
            font-weight: 760 !important;
            background: #f8fafc !important;
            border: 1px solid rgba(30,42,56,0.16) !important;
            color: rgba(15,23,42,0.86) !important;
            transition: all 0.12s ease !important;
            box-shadow: none !important;
          }

          button[data-baseweb="tab"]:hover{
            background: #ffffff !important;
            border-color: rgba(30,42,56,0.30) !important;
            transform: translateY(-1px);
          }

          button[data-baseweb="tab"][aria-selected="true"]{
            background: var(--primary) !important;
            border-color: var(--primary) !important;
            color: #ffffff !important;
            box-shadow: var(--shadow-2) !important;
            transform: none !important;
          }

          div[data-baseweb="tab-highlight"]{
            display: none !important;
          }

          /* ==================================================
             BOTÕES
          ================================================== */
          .stButton > button{
            border-radius: var(--radius-md);
            padding: 0.55rem 0.95rem;
            font-weight: 720;
            border: 1px solid rgba(49,51,63,0.15);
            background: #ffffff;
            transition: all 0.12s ease;
          }

          .stButton > button:hover{
            border-color: rgba(30,42,56,0.30);
            transform: translateY(-1px);
          }

          .stButton > button:focus{
            outline: none !important;
          }

          .stButton > button:focus-visible{
            box-shadow: 0 0 0 3px rgba(30,42,56,0.18) !important;
            border-color: rgba(30,42,56,0.50) !important;
          }

          .stButton > button[kind="primary"]{
            background: var(--primary) !important;
            border-color: var(--primary) !important;
            color: #ffffff !important;
          }

          .stButton > button[kind="primary"]:hover{
            background: #16202B !important;
            border-color: #16202B !important;
          }

          /* ==================================================
             INPUTS / SELECTS
          ================================================== */
          div[data-baseweb="input"] > div,
          div[data-baseweb="textarea"] > div,
          div[data-baseweb="select"] > div{
            border-radius: var(--radius-md) !important;
            border-color: rgba(30,42,56,0.18) !important;
            background: #ffffff !important;
          }

          div[data-baseweb="input"] > div:hover,
          div[data-baseweb="textarea"] > div:hover,
          div[data-baseweb="select"] > div:hover{
            border-color: rgba(30,42,56,0.32) !important;
          }

          div[data-baseweb="input"] > div:focus-within,
          div[data-baseweb="textarea"] > div:focus-within,
          div[data-baseweb="select"] > div:focus-within{
            border-color: rgba(30,42,56,0.75) !important;
            box-shadow: 0 0 0 3px rgba(30,42,56,0.12) !important;
          }

          /* ==================================================
             ALERTAS
          ================================================== */
          div[data-testid="stAlert"]{
            border-radius: var(--radius-md) !important;
            padding: 10px 12px !important;
          }
          div[data-testid="stAlert"] p{
            margin: 0 !important;
          }

          /* ==================================================
             CARDS
          ================================================== */
          .sp-card{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 14px 16px;
            box-shadow: var(--shadow);
          }

          .sp-card-title{
            font-size: 0.78rem;
            color: rgba(15,23,42,0.62);
            margin-bottom: 6px;
            font-weight: 740;
          }

          .sp-card-value{
            font-size: 1.42rem;
            font-weight: 840;
            color: var(--text);
            line-height: 1.1;
          }

          .sp-card-value.emph{
            font-size: 1.8rem;
            font-weight: 900;
          }

          .sp-card-sub{
            color: rgba(15,23,42,0.58);
            font-size: 0.82rem;
            margin-top: 6px;
          }

          .sp-tone-danger{ border-left: 6px solid var(--danger); padding-left: 12px; }
          .sp-tone-warning{ border-left: 6px solid var(--warning); padding-left: 12px; }
          .sp-tone-success{ border-left: 6px solid var(--success); padding-left: 12px; }
          .sp-tone-info{ border-left: 6px solid var(--info); padding-left: 12px; }
          .sp-tone-neutral{ border-left: 6px solid #cbd5e1; padding-left: 12px; }

          /* ==================================================
             DATAFRAME (melhor leitura)
          ================================================== */
          div[data-testid="stDataFrame"]{
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--border);
            background: var(--surface);
          }

          /* ==================================================
             PAGE HEADER (responsivo)
          ================================================== */
          .sp-page-header div[data-testid="stHorizontalBlock"]{
            gap: 0.75rem !important;
          }

          /* ==================================================
             RESPONSIVO (mobile-first)
          ================================================== */
          @media (max-width: 768px){
            /* container geral */
            .block-container{
              padding: 1rem !important;
              max-width: 100% !important;
            }

            /* sidebar mais “compacta” */
            section[data-testid="stSidebar"] .block-container{
              padding-top: 0.85rem !important;
              padding-bottom: 0.85rem !important;
            }

            /* cards */
            .sp-card{
              padding: 12px !important;
            }

            .sp-card-value{
              font-size: 1.15rem !important;
            }

            .sp-card-value.emph{
              font-size: 1.45rem !important;
            }

            /* botões: touch friendly */
            .stButton > button{
              width: 100% !important;
              padding: 0.70rem 0.95rem !important;
            }

            /* tabs compactas */
            button[data-baseweb="tab"]{
              padding: 8px 10px !important;
            }

            /* header empilha (título + botão) */
            .sp-page-header div[data-testid="stHorizontalBlock"]{
              flex-wrap: wrap !important;
            }
            .sp-page-header div[data-testid="column"]{
              min-width: 100% !important;
              width: 100% !important;
            }

            /* dataframe: reduzir sensação de “tabela gigante” */
            div[data-testid="stDataFrame"]{
              border-radius: 12px !important;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def card(
    title: str,
    value: str,
    subtitle: str = "",
    *,
    tone: str = "neutral",
    emphasize: bool = False,
) -> None:
    tone = (tone or "neutral").strip().lower()
    if tone not in {"neutral", "danger", "warning", "success", "info"}:
        tone = "neutral"

    emph_class = "emph" if emphasize else ""
    st.markdown(
        f"""
        <div class="sp-card sp-tone-{tone}">
          <div class="sp-card-title">{title}</div>
          <div class="sp-card-value {emph_class}">{value}</div>
          <div class="sp-card-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    st.markdown(f"#### {text}")


def subtle_divider() -> None:
    st.markdown(
        "<hr style='border:0;border-top:1px solid #e5e7eb;margin:0.8rem 0;'/>",
        unsafe_allow_html=True,
    )
