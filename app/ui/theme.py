from __future__ import annotations

import html
import streamlit as st

_CSS_VERSION = "v13"
_CSS_FLAG_KEY = f"_sp_css_injected_{_CSS_VERSION}"


# ==========================================================
# CSS global
# ==========================================================


def inject_global_css() -> None:
    """Injeta CSS global uma única vez por sessão."""
    if st.session_state.get(_CSS_FLAG_KEY):
        return

    st.session_state[_CSS_FLAG_KEY] = True

    st.markdown(
        """
<style>

/* ======================================================
ROOT VARIABLES
====================================================== */

:root{

  --bg:#f8fafb;

  --surface:#ffffff;
  --surface-soft:#fbfcfd;
  --surface-muted:#f1f5f4;
  --surface-elevated:#ffffff;

  --border:#e2e8e5;
  --border-strong:#cfd8d3;
  --border-soft:rgba(15,23,42,0.06);

  --text:#0f172a;
  --muted:#667085;
  --muted-strong:#475467;

  --primary:#3f5f5a;
  --primary-hover:#344e4a;
  --primary-soft:rgba(63,95,90,0.08);

  --danger:#dc2626;
  --warning:#d97706;
  --success:#15803d;
  --info:#3f5f5a;

  --danger-bg:rgba(220,38,38,0.07);
  --warning-bg:rgba(217,119,6,0.10);
  --success-bg:rgba(21,128,61,0.08);
  --info-bg:rgba(63,95,90,0.08);
  --neutral-bg:rgba(15,23,42,0.04);

  --radius-xl:22px;
  --radius-lg:18px;
  --radius-md:14px;
  --radius-sm:12px;
  --radius-xs:10px;

  --shadow:0 1px 2px rgba(15,23,42,0.04);
  --shadow-soft:0 4px 12px rgba(15,23,42,0.05);
  --shadow-strong:0 8px 20px rgba(15,23,42,0.07);

  --transition:all .15s ease;
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
    radial-gradient(circle at top right, rgba(63,95,90,0.03), transparent 22%),
    var(--bg);
}

header[data-testid="stHeader"]{
  background:transparent;
  height:0px;
}


/* ======================================================
LAYOUT COMPACTO
====================================================== */

.block-container{
  padding-top:0.65rem;
  padding-bottom:1.05rem;
  padding-left:1.10rem;
  padding-right:1.10rem;
  max-width:1380px;
  overflow:visible !important;
}

/* remove espaços exagerados */

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.25rem;
}

section.main{
  overflow:visible !important;
}


/* ======================================================
TYPOGRAPHY
====================================================== */

h1,h2,h3,h4{
  letter-spacing:-0.02em;
  color:var(--text);
  margin-bottom:0.15rem;
}

h1{
  font-size:1.80rem;
  line-height:1.08;
  font-weight:820;
}

h2{
  font-size:1.34rem;
  line-height:1.12;
  font-weight:760;
}

h3{
  font-size:1.04rem;
  line-height:1.2;
  font-weight:720;
}

h4{
  font-size:0.96rem;
  line-height:1.25;
  font-weight:700;
}

p, li, label{
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
  padding:0.05rem 0 0.02rem 0;
}

.sp-page-title{
  font-size:1.70rem;
  font-weight:860;
  line-height:1.05;
  letter-spacing:-0.025em;
  color:var(--text);
}

.sp-page-subtitle{
  margin-top:0.15rem;
  font-size:0.94rem;
  line-height:1.42;
  color:var(--muted);
  max-width:76ch;
}


/* ======================================================
SECTION HEADER
====================================================== */

.sp-section-header{
  margin-bottom:0.08rem;
}

.sp-section-title{
  font-size:1rem;
  font-weight:800;
  letter-spacing:-0.01em;
}

.sp-section-subtitle{
  margin-top:0.05rem;
  font-size:0.90rem;
  color:var(--muted);
}


/* ======================================================
SURFACE
====================================================== */

.sp-surface{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
  box-shadow:var(--shadow-soft);
  transition:var(--transition);
}

.sp-surface:hover{
  border-color:var(--border-strong);
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
  font-weight:600;
  line-height:1;
}


/* ======================================================
SIDEBAR
====================================================== */

section[data-testid="stSidebar"]{
  background:#f4f7f6;
  border-right:1px solid #dce4e1;
}

section[data-testid="stSidebar"] .block-container{
  padding:0.78rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.22rem !important;
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
  padding:9px 12px;

  border-radius:12px;

  margin-bottom:4px;

  cursor:pointer;

  border:1px solid rgba(15,23,42,0.08);

  background:rgba(255,255,255,0.92);

  font-size:0.92rem;

  transition:var(--transition);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]:hover{

  background:#ffffff;

  border-color:rgba(15,23,42,0.14);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"][aria-checked="true"]{

  background:var(--primary-soft);

  border-left:4px solid var(--primary);

  font-weight:750;
}


/* ======================================================
BUTTONS
====================================================== */

.stButton > button{

  border-radius:12px;

  padding:0.55rem 0.95rem;

  font-weight:650;

  border:1px solid rgba(15,23,42,0.10);

  background:#ffffff;

  color:var(--text);

  transition:var(--transition);
}

.stButton > button:hover{

  background:rgba(15,23,42,0.025);

  border-color:rgba(15,23,42,0.18);

  transform:translateY(-1px);
}

.stButton > button[kind="primary"],
.stButton > button[class*="primary"]{

  background:var(--primary) !important;

  border:1px solid var(--primary) !important;

  color:#fff !important;
}

.stButton > button[kind="primary"]:hover{

  background:var(--primary-hover) !important;
}


/* ======================================================
INPUTS
====================================================== */

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div{

  border-radius:var(--radius-md) !important;

  border-color:rgba(15,23,42,0.10) !important;

  background:#ffffff !important;

  min-height:42px;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within{

  border-color:rgba(63,95,90,0.35) !important;

  box-shadow:0 0 0 0.16rem rgba(63,95,90,0.09) !important;
}


/* ======================================================
DATAFRAME
====================================================== */

div[data-testid="stDataFrame"]{

  border-radius:14px;

  overflow:hidden;

  border:1px solid var(--border);

  background:#ffffff;
}


/* ======================================================
CARD KPI
====================================================== */

.sp-card{

  background:#ffffff;

  border:1px solid var(--border);

  border-radius:var(--radius-lg);

  padding:14px 16px;

  box-shadow:var(--shadow-soft);

  transition:var(--transition);

  min-height:100px;
}

.sp-card:hover{

  border-color:var(--border-strong);

  transform:translateY(-1px);
}

.sp-card-title{

  font-size:0.78rem;

  color:rgba(15,23,42,0.58);

  margin-bottom:7px;

  font-weight:760;

  text-transform:uppercase;

  letter-spacing:0.03em;
}

.sp-card-value{

  font-size:1.40rem;

  font-weight:850;

  color:var(--text);

  line-height:1.1;
}

.sp-card-value.emph{

  font-size:1.72rem;

  font-weight:900;
}

.sp-card-sub{

  color:rgba(15,23,42,0.56);

  font-size:0.84rem;

  margin-top:8px;
}


/* ======================================================
TONES
====================================================== */

.sp-tone-danger{border-left:5px solid var(--danger);padding-left:13px;}
.sp-tone-warning{border-left:5px solid var(--warning);padding-left:13px;}
.sp-tone-success{border-left:5px solid var(--success);padding-left:13px;}
.sp-tone-info{border-left:5px solid var(--info);padding-left:13px;}
.sp-tone-neutral{border-left:5px solid #cbd5e1;padding-left:13px;}


/* ======================================================
DIVIDER
====================================================== */

.sp-divider{

  border:0;

  border-top:1px solid #e5e7eb;

  margin:0.55rem 0;
}


/* ======================================================
MOBILE
====================================================== */

@media (max-width:768px){

.block-container{

padding:0.90rem !important;

max-width:100% !important;

}

.sp-page-title{

font-size:1.45rem;

}

.sp-card{

min-height:auto;

}

.sp-card-value{

font-size:1.15rem;

}

.stButton > button{

min-height:44px !important;

padding:0.72rem 1rem !important;

}

}

</style>
""",
        unsafe_allow_html=True,
    )


# ==========================================================
# Componentes Python
# ==========================================================

_ALLOWED_TONES = {"neutral", "danger", "warning", "success", "info"}


def _normalize_tone(tone: str | None) -> str:
    tone_norm = (tone or "neutral").strip().lower()
    return tone_norm if tone_norm in _ALLOWED_TONES else "neutral"


def card(
    title: str,
    value: str,
    subtitle: str = "",
    *,
    tone: str = "neutral",
    emphasize: bool = False,
) -> None:
    tone_norm = _normalize_tone(tone)

    title_html = html.escape(title or "")
    value_html = html.escape(value or "")
    subtitle_html = html.escape(subtitle or "")

    emph_class = "emph" if emphasize else ""
    subtitle_block = (
        f"<div class='sp-card-sub'>{subtitle_html}</div>" if subtitle_html else ""
    )

    st.markdown(
        f"""
        <div class="sp-card sp-tone-{tone_norm}">
          <div class="sp-card-title">{title_html}</div>
          <div class="sp-card-value {emph_class}">{value_html}</div>
          {subtitle_block}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    text_html = html.escape(text or "")

    st.markdown(
        f"""
        <div class="sp-section-header">
          <div class="sp-section-title">{text_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def subtle_divider() -> None:
    st.markdown("<hr class='sp-divider'>", unsafe_allow_html=True)


def app_error(
    title: str,
    message: str,
    *,
    technical_details: str | None = None,
    details_expanded: bool = False,
) -> None:
    """Exibe erro amigável para a aplicação."""
    title_html = html.escape(title or "Erro")
    message_html = html.escape(message or "")
    details_html = html.escape(technical_details or "")

    st.markdown(
        f"""
        <div class="sp-app-error">
          <div class="sp-app-error-title">{title_html}</div>
          <div class="sp-app-error-subtitle">{message_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if details_html:
        with st.expander("Detalhes técnicos", expanded=details_expanded):
            st.code(details_html, language="text")
