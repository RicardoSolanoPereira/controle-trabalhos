from __future__ import annotations

import html

import streamlit as st

__all__ = [
    "inject_global_css",
    "card",
    "section_title",
    "subtle_divider",
    "app_error",
]

_CSS_VERSION = "v16"
_CSS_FLAG_KEY = f"_sp_css_injected_{_CSS_VERSION}"

_ALLOWED_TONES = {"neutral", "danger", "warning", "success", "info"}

_GLOBAL_CSS = """
<style>

/* ======================================================
ROOT VARIABLES
====================================================== */

:root{

  --bg:#f4f7f6;
  --bg-soft:#f8fbfa;
  --bg-panel:#eef3f1;

  --surface:#ffffff;
  --surface-soft:#fbfcfc;
  --surface-muted:#f3f6f5;
  --surface-elevated:#ffffff;

  --border:#dde5e1;
  --border-strong:#c9d5cf;
  --border-soft:rgba(15,23,42,0.06);

  --text:#0f172a;
  --text-soft:#334155;
  --muted:#667085;
  --muted-strong:#475467;

  --primary:#355e57;
  --primary-hover:#294942;
  --primary-soft:rgba(53,94,87,0.08);
  --primary-soft-2:rgba(53,94,87,0.12);
  --primary-ring:rgba(53,94,87,0.16);

  --danger:#dc2626;
  --warning:#d97706;
  --success:#15803d;
  --info:#2563eb;
  --neutral:#64748b;

  --danger-bg:rgba(220,38,38,0.075);
  --warning-bg:rgba(217,119,6,0.10);
  --success-bg:rgba(21,128,61,0.09);
  --info-bg:rgba(37,99,235,0.09);
  --neutral-bg:rgba(15,23,42,0.045);

  --radius-2xl:26px;
  --radius-xl:22px;
  --radius-lg:18px;
  --radius-md:14px;
  --radius-sm:12px;
  --radius-xs:10px;

  --shadow-xs:0 1px 2px rgba(15,23,42,0.04);
  --shadow-sm:0 4px 10px rgba(15,23,42,0.04);
  --shadow-soft:0 8px 22px rgba(15,23,42,0.05);
  --shadow-md:0 14px 32px rgba(15,23,42,0.07);

  --transition:all .18s ease;
}


/* ======================================================
BASE
====================================================== */

html, body, [class*="css"]{
  color:var(--text);
}

html{
  scroll-behavior:smooth;
}

body{
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
}

.stApp{
  background:
    radial-gradient(circle at top right, rgba(53,94,87,0.045), transparent 26%),
    radial-gradient(circle at top left, rgba(37,99,235,0.025), transparent 18%),
    linear-gradient(180deg, rgba(255,255,255,0.60) 0%, rgba(255,255,255,0.16) 100%),
    var(--bg);
}

header[data-testid="stHeader"]{
  background:transparent;
  height:0;
}

div[data-testid="stAppViewContainer"]{
  background:transparent;
}

section.main{
  overflow:visible !important;
}


/* ======================================================
LAYOUT COMPACTO
====================================================== */

.block-container{
  padding-top:0.55rem;
  padding-bottom:1.10rem;
  padding-left:1.10rem;
  padding-right:1.10rem;
  max-width:1360px;
  overflow:visible !important;
}

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.18rem;
}


/* ======================================================
TYPOGRAPHY
====================================================== */

h1,h2,h3,h4{
  letter-spacing:-0.02em;
  color:var(--text);
  margin-bottom:0.12rem;
}

h1{
  font-size:1.86rem;
  line-height:1.05;
  font-weight:850;
}

h2{
  font-size:1.36rem;
  line-height:1.10;
  font-weight:800;
}

h3{
  font-size:1.06rem;
  line-height:1.2;
  font-weight:750;
}

h4{
  font-size:0.96rem;
  line-height:1.25;
  font-weight:710;
}

p, li, label, span{
  color:var(--text);
}

small,
.stCaption{
  color:var(--muted) !important;
}


/* ======================================================
PAGE HEADER
====================================================== */

.sp-page-header{
  padding:0.02rem 0 0.04rem 0;
}

.sp-page-title{
  font-size:1.74rem;
  font-weight:870;
  line-height:1.03;
  letter-spacing:-0.030em;
  color:var(--text);
}

.sp-page-subtitle{
  margin-top:0.22rem;
  font-size:0.95rem;
  line-height:1.48;
  color:var(--muted);
  max-width:82ch;
}


/* ======================================================
SECTION HEADER
====================================================== */

.sp-section-header{
  margin-bottom:0.06rem;
}

.sp-section-title{
  font-size:1.02rem;
  font-weight:820;
  letter-spacing:-0.013em;
  color:var(--text);
}

.sp-section-subtitle{
  margin-top:0.08rem;
  font-size:0.90rem;
  line-height:1.42;
  color:var(--muted);
}


/* ======================================================
SHELL
====================================================== */

.sp-content-shell{
  width:100%;
}


/* ======================================================
SURFACE
====================================================== */

.sp-surface{
  background:
    linear-gradient(180deg, rgba(255,255,255,0.98) 0%, #ffffff 100%);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
  box-shadow:var(--shadow-soft);
  transition:var(--transition);
  overflow:visible;
}

.sp-surface:hover{
  border-color:var(--border-strong);
  box-shadow:var(--shadow-md);
}

.sp-surface-no-pad{
  padding:0 !important;
}


/* ======================================================
CHIPS
====================================================== */

.sp-chip{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:6px 10px;
  border-radius:999px;
  background:var(--neutral-bg);
  border:1px solid rgba(15,23,42,0.08);
  font-size:0.80rem;
  font-weight:660;
  line-height:1;
  color:var(--text-soft);
  white-space:nowrap;
}

.sp-chip-danger{
  background:var(--danger-bg);
  border-color:rgba(220,38,38,0.18);
  color:#991b1b;
}

.sp-chip-warning{
  background:var(--warning-bg);
  border-color:rgba(217,119,6,0.18);
  color:#92400e;
}

.sp-chip-success{
  background:var(--success-bg);
  border-color:rgba(21,128,61,0.16);
  color:#166534;
}

.sp-chip-info{
  background:var(--info-bg);
  border-color:rgba(37,99,235,0.16);
  color:#1d4ed8;
}


/* ======================================================
SIDEBAR
====================================================== */

section[data-testid="stSidebar"]{
  background:
    linear-gradient(180deg, #f3f7f5 0%, #eef4f1 100%);
  border-right:1px solid #dbe5e1;
}

section[data-testid="stSidebar"] .block-container{
  padding:0.82rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.20rem !important;
}


/* ======================================================
SIDEBAR MENU
====================================================== */

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"] > div:first-child{
  display:none !important;
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]{
  display:block;
  width:100%;
  padding:10px 12px;
  border-radius:14px;
  margin-bottom:5px;
  cursor:pointer;
  border:1px solid rgba(15,23,42,0.08);
  background:rgba(255,255,255,0.92);
  font-size:0.93rem;
  transition:var(--transition);
  box-shadow:0 1px 2px rgba(15,23,42,0.02);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]:hover{
  background:#ffffff;
  border-color:rgba(15,23,42,0.14);
  transform:translateX(1px);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"][aria-checked="true"]{
  background:linear-gradient(180deg, rgba(53,94,87,0.09) 0%, rgba(53,94,87,0.06) 100%);
  border-left:4px solid var(--primary);
  border-top-color:rgba(53,94,87,0.10);
  border-right-color:rgba(53,94,87,0.10);
  border-bottom-color:rgba(53,94,87,0.10);
  font-weight:780;
}


/* ======================================================
BUTTONS
====================================================== */

.stButton > button{
  border-radius:12px;
  padding:0.58rem 0.98rem;
  min-height:42px;
  font-weight:680;
  border:1px solid rgba(15,23,42,0.10);
  background:#ffffff;
  color:var(--text);
  transition:var(--transition);
  box-shadow:none;
}

.stButton > button:hover{
  background:rgba(15,23,42,0.026);
  border-color:rgba(15,23,42,0.18);
  transform:translateY(-1px);
}

.stButton > button:focus{
  outline:none !important;
  box-shadow:0 0 0 0.18rem rgba(53,94,87,0.12) !important;
}

.stButton > button[kind="primary"],
.stButton > button[class*="primary"]{
  background:linear-gradient(180deg, var(--primary) 0%, #2f544d 100%) !important;
  border:1px solid var(--primary) !important;
  color:#ffffff !important;
  box-shadow:0 8px 18px rgba(53,94,87,0.18) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[class*="primary"]:hover{
  background:linear-gradient(180deg, var(--primary-hover) 0%, #233f39 100%) !important;
  border-color:var(--primary-hover) !important;
}


/* ======================================================
INPUTS / SELECTS / TEXTAREA
====================================================== */

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div{
  border-radius:var(--radius-md) !important;
  border-color:rgba(15,23,42,0.10) !important;
  background:#ffffff !important;
  min-height:42px;
  transition:var(--transition) !important;
}

div[data-baseweb="input"] > div:hover,
div[data-baseweb="textarea"] > div:hover,
div[data-baseweb="select"] > div:hover{
  border-color:rgba(15,23,42,0.18) !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within{
  border-color:rgba(53,94,87,0.35) !important;
  box-shadow:0 0 0 0.18rem var(--primary-ring) !important;
}

label[data-testid="stWidgetLabel"] p{
  font-weight:630 !important;
  color:var(--text-soft) !important;
}


/* ======================================================
TABS
====================================================== */

div[data-testid="stTabs"]{
  gap:0.20rem;
}

button[data-baseweb="tab"]{
  border-radius:12px 12px 0 0 !important;
  font-weight:660 !important;
  color:var(--muted-strong) !important;
}

button[data-baseweb="tab"][aria-selected="true"]{
  color:var(--primary) !important;
  border-bottom-color:var(--primary) !important;
}


/* ======================================================
DATAFRAME
====================================================== */

div[data-testid="stDataFrame"]{
  border-radius:14px;
  overflow:hidden;
  border:1px solid var(--border);
  background:#ffffff;
  box-shadow:var(--shadow-xs);
}

div[data-testid="stDataFrame"] [role="grid"]{
  border:none !important;
}


/* ======================================================
EXPANDER
====================================================== */

details{
  border-radius:14px;
  border:1px solid var(--border);
  background:#ffffff;
}

summary{
  border-radius:12px;
}


/* ======================================================
CARD KPI
====================================================== */

.sp-card{
  background:
    linear-gradient(180deg, rgba(255,255,255,0.99) 0%, #ffffff 100%);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
  box-shadow:var(--shadow-soft);
  transition:var(--transition);
  min-height:112px;
  position:relative;
  overflow:hidden;
}

.sp-card::after{
  content:"";
  position:absolute;
  top:0;
  right:0;
  width:56px;
  height:56px;
  background:radial-gradient(circle, rgba(53,94,87,0.05) 0%, transparent 70%);
  pointer-events:none;
}

.sp-card:hover{
  border-color:var(--border-strong);
  transform:translateY(-1px);
  box-shadow:var(--shadow-md);
}

.sp-card-title{
  font-size:0.77rem;
  color:rgba(15,23,42,0.58);
  margin-bottom:7px;
  font-weight:780;
  text-transform:uppercase;
  letter-spacing:0.045em;
}

.sp-card-value{
  font-size:1.46rem;
  font-weight:860;
  color:var(--text);
  line-height:1.06;
}

.sp-card-value.emph{
  font-size:1.76rem;
  font-weight:900;
}

.sp-card-sub{
  color:rgba(15,23,42,0.58);
  font-size:0.84rem;
  margin-top:8px;
  line-height:1.35;
}


/* ======================================================
TONES
====================================================== */

.sp-tone-danger{
  border-left:5px solid var(--danger);
  padding-left:13px;
}

.sp-tone-warning{
  border-left:5px solid var(--warning);
  padding-left:13px;
}

.sp-tone-success{
  border-left:5px solid var(--success);
  padding-left:13px;
}

.sp-tone-info{
  border-left:5px solid var(--info);
  padding-left:13px;
}

.sp-tone-neutral{
  border-left:5px solid #cbd5e1;
  padding-left:13px;
}


/* ======================================================
EMPTY STATE
====================================================== */

.sp-empty-state{
  text-align:center;
  padding:30px 20px;
}

.sp-empty-state-icon{
  font-size:1.9rem;
  line-height:1;
  margin-bottom:10px;
}

.sp-empty-state-title{
  font-size:1rem;
  font-weight:820;
  color:var(--text);
}

.sp-empty-state-subtitle{
  margin-top:6px;
  color:var(--muted);
  font-size:0.91rem;
  line-height:1.45;
}


/* ======================================================
APP ERROR
====================================================== */

.sp-app-error{
  background:linear-gradient(180deg, rgba(220,38,38,0.045) 0%, rgba(220,38,38,0.025) 100%);
  border:1px solid rgba(220,38,38,0.15);
  border-left:5px solid var(--danger);
  border-radius:16px;
  padding:14px 16px;
  margin-bottom:0.35rem;
}

.sp-app-error-title{
  color:#991b1b;
  font-size:0.98rem;
  font-weight:830;
}

.sp-app-error-subtitle{
  color:#7f1d1d;
  margin-top:5px;
  font-size:0.90rem;
  line-height:1.45;
}


/* ======================================================
DIVIDER
====================================================== */

.sp-divider{
  border:0;
  border-top:1px solid #e5e7eb;
  margin:0.50rem 0;
}


/* ======================================================
HELPERS
====================================================== */

.sp-muted{
  color:var(--muted) !important;
}

.sp-text-soft{
  color:var(--text-soft) !important;
}


/* ======================================================
SCROLLBAR
====================================================== */

*::-webkit-scrollbar{
  width:10px;
  height:10px;
}

*::-webkit-scrollbar-track{
  background:rgba(15,23,42,0.04);
  border-radius:999px;
}

*::-webkit-scrollbar-thumb{
  background:rgba(53,94,87,0.22);
  border-radius:999px;
}

*::-webkit-scrollbar-thumb:hover{
  background:rgba(53,94,87,0.32);
}


/* ======================================================
MOBILE
====================================================== */

@media (max-width:768px){

  .block-container{
    padding:0.86rem !important;
    max-width:100% !important;
  }

  .sp-page-title{
    font-size:1.44rem;
  }

  .sp-page-subtitle{
    font-size:0.91rem;
  }

  .sp-card{
    min-height:auto;
    padding:13px 14px;
  }

  .sp-card-value{
    font-size:1.16rem;
  }

  .sp-card-value.emph{
    font-size:1.36rem;
  }

  .sp-surface{
    padding:13px 14px;
    border-radius:16px;
  }

  .stButton > button{
    min-height:44px !important;
    padding:0.72rem 1rem !important;
  }

  .sp-chip{
    font-size:0.78rem;
    padding:6px 9px;
  }

  .sp-section-title{
    font-size:0.98rem;
  }
}

</style>
"""


# ==========================================================
# Helpers privados
# ==========================================================


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None) -> str:
    return html.escape(text or "")


def _normalize_tone(tone: str | None) -> str:
    tone_norm = (tone or "neutral").strip().lower()
    return tone_norm if tone_norm in _ALLOWED_TONES else "neutral"


# ==========================================================
# CSS global
# ==========================================================


def inject_global_css() -> None:
    if st.session_state.get(_CSS_FLAG_KEY, False):
        return

    st.session_state[_CSS_FLAG_KEY] = True
    _render_html(_GLOBAL_CSS)


# ==========================================================
# Componentes públicos
# ==========================================================


def card(
    title: str,
    value: str,
    subtitle: str = "",
    *,
    tone: str = "neutral",
    emphasize: bool = False,
) -> None:
    tone_norm = _normalize_tone(tone)

    title_html = _escape(title)
    value_html = _escape(value)
    subtitle_html = _escape(subtitle)

    emph_class = "emph" if emphasize else ""
    subtitle_block = (
        f"<div class='sp-card-sub'>{subtitle_html}</div>" if subtitle_html else ""
    )

    _render_html(
        f"""
        <div class="sp-card sp-tone-{tone_norm}">
          <div class="sp-card-title">{title_html}</div>
          <div class="sp-card-value {emph_class}">{value_html}</div>
          {subtitle_block}
        </div>
        """
    )


def section_title(text: str) -> None:
    text_html = _escape(text)

    _render_html(
        f"""
        <div class="sp-section-header">
          <div class="sp-section-title">{text_html}</div>
        </div>
        """
    )


def subtle_divider() -> None:
    _render_html("<hr class='sp-divider'>")


def app_error(
    title: str,
    message: str,
    *,
    technical_details: str | None = None,
    details_expanded: bool = False,
) -> None:
    title_html = _escape(title or "Erro")
    message_html = _escape(message)
    details_text = technical_details or ""

    _render_html(
        f"""
        <div class="sp-app-error">
          <div class="sp-app-error-title">{title_html}</div>
          <div class="sp-app-error-subtitle">{message_html}</div>
        </div>
        """
    )

    if details_text:
        with st.expander("Detalhes técnicos", expanded=details_expanded):
            st.code(details_text, language="text")
