# app/ui/theme.py
from __future__ import annotations

import html
import streamlit as st

# Versão do CSS (mude para forçar reinjeção na sessão)
_CSS_VERSION = "v4"  # <-- bump
_CSS_FLAG_KEY = f"_sp_css_injected_{_CSS_VERSION}"


def inject_global_css() -> None:
    """
    CSS global (tokens + componentes).
    Objetivos:
    - Padrão executivo / leve
    - Botões consistentes (primário grafite)
    - Tabs segmentadas
    - Sidebar tipo "pill menu" (compacto)
    - Responsivo mobile
    - FIX dropdown do selectbox (BaseWeb)
    """
    if st.session_state.get(_CSS_FLAG_KEY):
        return
    st.session_state[_CSS_FLAG_KEY] = True

    st.markdown(
        """
        <style>
          :root{
            /* ==================================================
               TOKENS
            ================================================== */
            --bg: #ffffff;
            --surface: #ffffff;
            --surface-2: #f8fafc;
            --border: #e5e7eb;

            --text: #0f172a;   /* slate-900 */
            --muted: #64748b;  /* slate-500 */

            /* Primário (botões primários) */
            --primary: #334155;        /* slate-700 */
            --primary-hover: #1e293b;  /* slate-800 */
            --primary-soft: rgba(51,65,85,0.10);

            /* Indicadores */
            --info: #2563eb;     /* blue-600 */
            --success: #16a34a;  /* green-600 */
            --warning: #f59e0b;  /* amber-500 */
            --danger: #dc2626;   /* red-600 */

            --radius-lg: 18px;
            --radius-md: 14px;

            --shadow: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-2: 0 8px 18px rgba(0,0,0,0.10);
          }

          /* ==================================================
             BASE APP
          ================================================== */
          .stApp{
            background: var(--bg);
            color: var(--text);
          }

          header[data-testid="stHeader"]{
            background: transparent;
          }

          /* Container principal */
          .block-container{
            padding-top: 1.35rem;
            padding-bottom: 1.6rem;
            max-width: 1400px;
            overflow: visible !important; /* ajuda com popovers/portais */
          }

          h1, h2, h3, h4{
            letter-spacing: -0.015em;
            color: var(--text);
          }

          .stCaption{
            color: var(--muted) !important;
          }

          /* Reduz espaços verticais padrão (sem “amassar”) */
          div[data-testid="stVerticalBlock"] > div{
            margin-bottom: 0.40rem;
          }

          /* ==================================================
             ✅ FIX: SELECTBOX / DROPDOWN (BaseWeb)
          ================================================== */
          section.main { overflow: visible !important; }

          div[role="listbox"]{
            z-index: 100000 !important;
          }

          div[role="listbox"] ul{
            max-height: 45vh !important;
            overflow-y: auto !important;
            padding-right: 6px;
          }

          div[role="listbox"] li{
            padding-top: 10px !important;
            padding-bottom: 10px !important;
          }

          /* ==================================================
             UTILITIES
          ================================================== */
          .sp-muted{ color: rgba(15,23,42,0.60); }

          .sp-surface{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 14px 16px;
            box-shadow: var(--shadow);
          }

          .sp-chip{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(15,23,42,0.04);
            border: 1px solid rgba(15,23,42,0.12);
            font-size: 0.82rem;
            color: rgba(15,23,42,0.84);
            white-space: nowrap;
          }

          /* ==================================================
             SIDEBAR (COMPACTO / MENOS POLUÍDO)
          ================================================== */
          section[data-testid="stSidebar"]{
            background-color: #f1f5f9; /* slate-100 */
            border-right: 1px solid var(--border);
          }

          /* Menos padding no sidebar */
          section[data-testid="stSidebar"] .block-container{
            padding-top: 0.75rem !important;
            padding-bottom: 0.75rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
          }

          /* Menos “respiro” entre elementos NO SIDEBAR (sem afetar o main) */
          section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div{
            margin-bottom: 0.26rem !important;
          }

          /* Dividers mais discretos no sidebar */
          section[data-testid="stSidebar"] hr{
            border-color: rgba(15,23,42,0.10) !important;
            margin: 0.55rem 0 !important;
          }

          /* Headers/labels do sidebar: compactar */
          section[data-testid="stSidebar"] h1,
          section[data-testid="stSidebar"] h2,
          section[data-testid="stSidebar"] h3{
            margin: 0.25rem 0 0.35rem 0 !important;
          }

          /* Radio -> pill menu (mais compacto) */
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
            padding: 8px 12px;              /* menor */
            border-radius: 12px;
            margin-bottom: 5px;             /* menor */
            cursor: pointer;
            transition: all 0.12s ease;
            border: 1px solid rgba(15,23,42,0.10);
            background: rgba(255,255,255,0.78);
            font-size: 0.92rem;             /* menor */
            line-height: 1.15;
          }

          section[data-testid="stSidebar"]
          div[role="radiogroup"]
          label[data-baseweb="radio"]:hover{
            background: rgba(15,23,42,0.05);
            border-color: rgba(15,23,42,0.18);
            transform: translateY(-1px);
          }

          section[data-testid="stSidebar"]
          div[role="radiogroup"]
          label[data-baseweb="radio"][aria-checked="true"]{
            background: rgba(51,65,85,0.10);
            border: 1px solid rgba(51,65,85,0.22);
            border-left: 4px solid var(--primary);
            padding-left: 10px;
            font-weight: 760;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            transform: none;
          }

          /* Alguns temas do Streamlit renderizam o item selecionado em div[role=radio] */
          section[data-testid="stSidebar"]
          div[role="radiogroup"]
          div[role="radio"][aria-checked="true"]{
            background: rgba(51,65,85,0.10) !important;
            border: 1px solid rgba(51,65,85,0.22) !important;
            border-left: 4px solid var(--primary) !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
          }

          /* Expanders no SIDEBAR: mais “flat” e compacto */
          section[data-testid="stSidebar"] details[data-testid="stExpander"]{
            border-radius: 12px;
            border: 1px solid rgba(15,23,42,0.12);
            background: rgba(255,255,255,0.85);
            box-shadow: none;
            overflow: hidden;
          }
          section[data-testid="stSidebar"] details[data-testid="stExpander"] summary{
            padding: 8px 10px !important;
          }
          section[data-testid="stSidebar"] details[data-testid="stExpander"] summary p{
            font-size: 0.92rem !important;
            font-weight: 700 !important;
          }

          /* ==================================================
             EXPANDER (fora do sidebar mantém seu estilo anterior)
          ================================================== */
          section.main details[data-testid="stExpander"]{
            border-radius: 14px;
            border: 1px solid rgba(15,23,42,0.14);
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            overflow: hidden;
          }
          section.main details[data-testid="stExpander"] summary{
            padding: 10px 12px;
          }

          /* ==================================================
             TABS (segmented)
          ================================================== */
          div[data-baseweb="tab-list"]{
            background: #ffffff !important;
            border: 1px solid rgba(15,23,42,0.16) !important;
            border-radius: 14px !important;
            padding: 6px !important;
            gap: 6px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
          }

          button[data-baseweb="tab"]{
            border-radius: 12px !important;
            padding: 9px 12px !important;
            font-weight: 700 !important;
            background: var(--surface-2) !important;
            border: 1px solid rgba(15,23,42,0.12) !important;
            color: rgba(15,23,42,0.86) !important;
            transition: all 0.12s ease !important;
            box-shadow: none !important;
          }

          button[data-baseweb="tab"]:hover{
            background: #ffffff !important;
            border-color: rgba(15,23,42,0.22) !important;
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
            border-radius: 12px;
            padding: 0.60rem 1rem;
            font-weight: 600;
            border: 1px solid rgba(15,23,42,0.15);
            background: transparent;
            color: rgba(15,23,42,0.90);
            transition: all 0.15s ease;
          }

          .stButton > button:hover{
            border-color: rgba(15,23,42,0.25);
            background: rgba(15,23,42,0.04);
            transform: translateY(-1px);
          }

          .stButton > button:focus{ outline: none !important; }

          .stButton > button:focus-visible{
            box-shadow: 0 0 0 3px rgba(51,65,85,0.14) !important;
            border-color: rgba(51,65,85,0.45) !important;
          }

          .stButton > button[kind="primary"]{
            background: var(--primary) !important;
            border: 1px solid var(--primary) !important;
            color: #ffffff !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
          }

          .stButton > button[kind="primary"]:hover{
            background: var(--primary-hover) !important;
            border-color: var(--primary-hover) !important;
          }

          .stButton > button[data-testid*="baseButton-primary"],
          .stButton > button[class*="primary"]{
            background: var(--primary) !important;
            border: 1px solid var(--primary) !important;
            color: #ffffff !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
          }

          /* Sidebar buttons: ligeiramente mais compactos (sem perder usabilidade) */
          section[data-testid="stSidebar"] .stButton > button{
            padding: 0.52rem 0.8rem !important;
            font-size: 0.92rem !important;
          }

          /* ==================================================
             INPUTS / SELECTS
          ================================================== */
          div[data-baseweb="input"] > div,
          div[data-baseweb="textarea"] > div,
          div[data-baseweb="select"] > div{
            border-radius: var(--radius-md) !important;
            border-color: rgba(15,23,42,0.14) !important;
            background: #ffffff !important;
          }

          div[data-baseweb="input"] > div:hover,
          div[data-baseweb="textarea"] > div:hover,
          div[data-baseweb="select"] > div:hover{
            border-color: rgba(15,23,42,0.24) !important;
          }

          div[data-baseweb="input"] > div:focus-within,
          div[data-baseweb="textarea"] > div:focus-within,
          div[data-baseweb="select"] > div:focus-within{
            border-color: rgba(51,65,85,0.52) !important;
            box-shadow: 0 0 0 3px rgba(51,65,85,0.12) !important;
          }

          div[data-baseweb="select"] svg{
            transform: none !important;
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
             CARDS (KPIs)
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
            font-weight: 720;
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
             DATAFRAME
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
             REDUZ MOTION (acessibilidade)
          ================================================== */
          @media (prefers-reduced-motion: reduce){
            *{
              transition: none !important;
              animation: none !important;
              scroll-behavior: auto !important;
            }
          }

          /* ==================================================
             RESPONSIVO (mobile)
          ================================================== */
          @media (max-width: 768px){
            .block-container{
              padding: 1rem !important;
              max-width: 100% !important;
            }

            section[data-testid="stSidebar"] .block-container{
              padding-top: 0.70rem !important;
              padding-bottom: 0.70rem !important;
              padding-left: 0.70rem !important;
              padding-right: 0.70rem !important;
            }

            .sp-card{
              padding: 12px !important;
            }

            .sp-card-value{
              font-size: 1.15rem !important;
            }

            .sp-card-value.emph{
              font-size: 1.45rem !important;
            }

            /* Botões touch-friendly (no mobile mantém 44px no main) */
            .stButton > button{
              min-height: 44px !important;
              padding: 0.72rem 1rem !important;
            }

            /* Inputs touch-friendly + evita zoom iOS */
            div[data-baseweb="input"] input,
            div[data-baseweb="textarea"] textarea{
              min-height: 44px !important;
              font-size: 16px !important;
            }
            div[data-baseweb="select"] > div{
              min-height: 44px !important;
            }

            button[data-baseweb="tab"]{
              padding: 8px 10px !important;
            }

            .sp-page-header div[data-testid="stHorizontalBlock"]{
              flex-wrap: wrap !important;
            }
            .sp-page-header div[data-testid="column"]{
              min-width: 100% !important;
              width: 100% !important;
            }

            div[data-testid="stDataFrame"]{
              border-radius: 12px !important;
            }

            div[role="listbox"] ul{
              max-height: 50vh !important;
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
    """Card/KPI padronizado (seguro para strings com caracteres especiais)."""
    tone = (tone or "neutral").strip().lower()
    if tone not in {"neutral", "danger", "warning", "success", "info"}:
        tone = "neutral"

    title_h = html.escape(title or "")
    value_h = html.escape(value or "")
    subtitle_h = html.escape(subtitle or "")

    emph_class = "emph" if emphasize else ""
    subtitle_html = f"<div class='sp-card-sub'>{subtitle_h}</div>" if subtitle_h else ""

    st.markdown(
        f"""
        <div class="sp-card sp-tone-{tone}">
          <div class="sp-card-title">{title_h}</div>
          <div class="sp-card-value {emph_class}">{value_h}</div>
          {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    st.markdown(f"#### {html.escape(text or '')}")


def subtle_divider() -> None:
    st.markdown(
        "<hr style='border:0;border-top:1px solid #e5e7eb;margin:0.8rem 0;'/>",
        unsafe_allow_html=True,
    )
