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

_CSS_VERSION = "v15"
_CSS_FLAG_KEY = f"_sp_css_injected_{_CSS_VERSION}"

_ALLOWED_TONES = {"neutral", "danger", "warning", "success", "info"}

_GLOBAL_CSS = """
<style>

/* ======================================================
ROOT VARIABLES
====================================================== */

:root{

  --bg:#f6f8f7;
  --bg-soft:#fbfcfb;

  --surface:#ffffff;
  --surface-soft:#fcfdfc;
  --surface-muted:#f2f5f4;
  --surface-elevated:#ffffff;

  --border:#e2e8e5;
  --border-strong:#cfd8d3;
  --border-soft:rgba(15,23,42,0.06);

  --text:#0f172a;
  --text-soft:#344054;
  --muted:#667085;
  --muted-strong:#475467;

  --primary:#3f5f5a;
  --primary-hover:#314b47;
  --primary-soft:rgba(63,95,90,0.08);
  --primary-ring:rgba(63,95,90,0.14);

  --danger:#dc2626;
  --warning:#d97706;
  --success:#15803d;
  --info:#2563eb;
  --neutral:#64748b;

  --danger-bg:rgba(220,38,38,0.07);
  --warning-bg:rgba(217,119,6,0.09);
  --success-bg:rgba(21,128,61,0.08);
  --info-bg:rgba(37,99,235,0.08);
  --neutral-bg:rgba(15,23,42,0.04);

  --radius-xl:24px;
  --radius-lg:18px;
  --radius-md:14px;
  --radius-sm:12px;
  --radius-xs:10px;

  --shadow-xs:0 1px 2px rgba(15,23,42,0.04);
  --shadow-soft:0 6px 18px rgba(15,23,42,0.05);
  --shadow-md:0 10px 26px rgba(15,23,42,0.06);

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
    radial-gradient(circle at top right, rgba(63,95,90,0.035), transparent 24%),
    linear-gradient(180deg, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0.15) 100%),
    var(--bg);
}

header[data-testid="stHeader"]{
  background:transparent;
  height:0;
}

div[data-testid="stAppViewContainer"]{
  background:transparent;
}


/* ======================================================
LAYOUT COMPACTO
====================================================== */

.block-container{
  padding-top:0.70rem;
  padding-bottom:1.10rem;
  padding-left:1.15rem;
  padding-right:1.15rem;
  max-width:1380px;
  overflow:visible !important;
}

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.22rem;
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
  font-size:1.82rem;
  line-height:1.06;
  font-weight:840;
}

h2{
  font-size:1.34rem;
  line-height:1.12;
  font-weight:780;
}

h3{
  font-size:1.05rem;
  line-height:1.2;
  font-weight:730;
}

h4{
  font-size:0.96rem;
  line-height:1.25;
  font-weight:700;
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
  padding:0.02rem 0 0.02rem 0;
}

.sp-page-title{
  font-size:1.72rem;
  font-weight:860;
  line-height:1.04;
  letter-spacing:-0.028em;
  color:var(--text);
}

.sp-page-subtitle{
  margin-top:0.18rem;
  font-size:0.95rem;
  line-height:1.46;
  color:var(--muted);
  max-width:78ch;
}


/* ======================================================
SECTION HEADER
====================================================== */

.sp-section-header{
  margin-bottom:0.08rem;
}

.sp-section-title{
  font-size:1.01rem;
  font-weight:810;
  letter-spacing:-0.012em;
  color:var(--text);
}

.sp-section-subtitle{
  margin-top:0.08rem;
  font-size:0.90rem;
  line-height:1.42;
  color:var(--muted);
}


/* ======================================================
SURFACE
====================================================== */

.sp-surface{
  background:linear-gradient(180deg, rgba(255,255,255,0.98) 0%, #ffffff 100%);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
  box-shadow:var(--shadow-soft);
  transition:var(--transition);
}

.sp-surface:hover{
  border-color:var(--border-strong);
  box-shadow:var(--shadow-md);
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
  font-weight:650;
  line-height:1;
  color:var(--text-soft);
  white-space:nowrap;
}


/* ======================================================
SIDEBAR
====================================================== */

section[data-testid="stSidebar"]{
  background:linear-gradient(180deg, #f4f7f6 0%, #f1f5f4 100%);
  border-right:1px solid #dce4e1;
}

section[data-testid="stSidebar"] .block-container{
  padding:0.80rem !important;
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
  transform:translateX(1px);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"][aria-checked="true"]{
  background:var(--primary-soft);
  border-left:4px solid var(--primary);
  font-weight:760;
}


/* ======================================================
BUTTONS
====================================================== */

.stButton > button{
  border-radius:12px;
  padding:0.56rem 0.98rem;
  min-height:42px;
  font-weight:670;
  border:1px solid rgba(15,23,42,0.10);
  background:#ffffff;
  color:var(--text);
  transition:var(--transition);
  box-shadow:none;
}

.stButton > button:hover{
  background:rgba(15,23,42,0.025);
  border-color:rgba(15,23,42,0.18);
  transform:translateY(-1px);
}

.stButton > button:focus{
  outline:none !important;
  box-shadow:0 0 0 0.18rem rgba(63,95,90,0.10) !important;
}

.stButton > button[kind="primary"],
.stButton > button[class*="primary"]{
  background:var(--primary) !important;
  border:1px solid var(--primary) !important;
  color:#ffffff !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[class*="primary"]:hover{
  background:var(--primary-hover) !important;
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
  border-color:rgba(63,95,90,0.35) !important;
  box-shadow:0 0 0 0.18rem var(--primary-ring) !important;
}

label[data-testid="stWidgetLabel"] p{
  font-weight:620 !important;
  color:var(--text-soft) !important;
}


/* ======================================================
TABS
====================================================== */

button[data-baseweb="tab"]{
  border-radius:12px 12px 0 0 !important;
  font-weight:650 !important;
}

button[data-baseweb="tab"][aria-selected="true"]{
  color:var(--primary) !important;
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

div[data-testid="stDataFrame"] [role="grid"]{
  border:none !important;
}


/* ======================================================
EXPANDER
====================================================== */

details{
  border-radius:14px;
}

summary{
  border-radius:12px;
}


/* ======================================================
CARD KPI
====================================================== */

.sp-card{
  background:linear-gradient(180deg, rgba(255,255,255,0.99) 0%, #ffffff 100%);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
  box-shadow:var(--shadow-soft);
  transition:var(--transition);
  min-height:108px;
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
  font-weight:760;
  text-transform:uppercase;
  letter-spacing:0.04em;
}

.sp-card-value{
  font-size:1.42rem;
  font-weight:850;
  color:var(--text);
  line-height:1.08;
}

.sp-card-value.emph{
  font-size:1.72rem;
  font-weight:900;
}

.sp-card-sub{
  color:rgba(15,23,42,0.56);
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
  padding:28px 20px;
}

.sp-empty-state-icon{
  font-size:1.8rem;
  line-height:1;
  margin-bottom:10px;
}

.sp-empty-state-title{
  font-size:1rem;
  font-weight:800;
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
  background:linear-gradient(180deg, rgba(220,38,38,0.04) 0%, rgba(220,38,38,0.02) 100%);
  border:1px solid rgba(220,38,38,0.15);
  border-left:5px solid var(--danger);
  border-radius:16px;
  padding:14px 16px;
  margin-bottom:0.35rem;
}

.sp-app-error-title{
  color:#991b1b;
  font-size:0.98rem;
  font-weight:820;
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
  margin:0.55rem 0;
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

  .sp-page-subtitle{
    font-size:0.91rem;
  }

  .sp-card{
    min-height:auto;
  }

  .sp-card-value{
    font-size:1.14rem;
  }

  .sp-card-value.emph{
    font-size:1.34rem;
  }

  .sp-surface{
    padding:13px 14px;
  }

  .stButton > button{
    min-height:44px !important;
    padding:0.72rem 1rem !important;
  }

  .sp-chip{
    font-size:0.78rem;
  }
}

</style>
"""


# ==========================================================
# Helpers privados
# ==========================================================


def _render_html(content: str) -> None:
    """Renderiza HTML seguro para componentes controlados pelo app."""
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None) -> str:
    """Escapa conteúdo textual para uso em HTML."""
    return html.escape(text or "")


def _normalize_tone(tone: str | None) -> str:
    """Normaliza o tom visual para um valor permitido."""
    tone_norm = (tone or "neutral").strip().lower()
    return tone_norm if tone_norm in _ALLOWED_TONES else "neutral"


# ==========================================================
# CSS global
# ==========================================================


def inject_global_css() -> None:
    """Injeta CSS global uma única vez por sessão."""
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
    """Renderiza card KPI com título, valor e subtítulo opcional."""
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
    """Renderiza título simples de seção."""
    text_html = _escape(text)

    _render_html(
        f"""
        <div class="sp-section-header">
          <div class="sp-section-title">{text_html}</div>
        </div>
        """
    )


def subtle_divider() -> None:
    """Renderiza divisor horizontal discreto."""
    _render_html("<hr class='sp-divider'>")


def app_error(
    title: str,
    message: str,
    *,
    technical_details: str | None = None,
    details_expanded: bool = False,
) -> None:
    """Exibe erro amigável da aplicação com detalhes técnicos opcionais."""
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
