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

_CSS_VERSION = "v19"
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

  --surface:#ffffff;
  --surface-soft:#fbfcfc;
  --surface-muted:#f3f6f5;

  --border:#dde5e1;
  --border-strong:#cfd9d4;
  --border-soft:rgba(15,23,42,0.06);

  --text:#0f172a;
  --text-soft:#334155;
  --muted:#667085;
  --muted-strong:#475467;

  --primary:#355e57;
  --primary-hover:#2b4c46;
  --primary-soft:rgba(53,94,87,0.08);
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

  --radius-xl:20px;
  --radius-lg:16px;
  --radius-md:12px;
  --radius-sm:10px;

  --shadow-xs:0 1px 2px rgba(15,23,42,0.04);
  --shadow-sm:0 6px 18px rgba(15,23,42,0.05);
  --shadow-md:0 12px 28px rgba(15,23,42,0.06);

  --transition:all .18s ease;
}


/* ======================================================
BASE
====================================================== */

html, body{
  color:var(--text);
}

html{
  scroll-behavior:smooth;
}

body{
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
}

p, li, label, span, div{
  color:inherit;
}

.stApp{
  background:
    radial-gradient(circle at top right, rgba(53,94,87,0.04), transparent 24%),
    linear-gradient(180deg, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0.16) 100%),
    var(--bg);
}

header[data-testid="stHeader"]{
  background:transparent !important;
  border:none !important;
}

div[data-testid="stToolbar"]{
  right:0.5rem;
}

div[data-testid="stAppViewContainer"]{
  background:transparent;
}

section.main{
  overflow:visible !important;
}


/* ======================================================
LAYOUT
====================================================== */

.block-container{
  padding-top:0.90rem;
  padding-bottom:1.25rem;
  padding-left:1.20rem;
  padding-right:1.20rem;
  max-width:1320px;
  overflow:visible !important;
}

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.28rem;
}


/* ======================================================
TYPOGRAPHY
====================================================== */

h1,h2,h3,h4{
  letter-spacing:-0.02em;
  color:var(--text);
  margin-bottom:0.14rem;
}

h1{
  font-size:1.78rem;
  line-height:1.08;
  font-weight:800;
}

h2{
  font-size:1.30rem;
  line-height:1.14;
  font-weight:760;
}

h3{
  font-size:1.03rem;
  line-height:1.24;
  font-weight:720;
}

h4{
  font-size:0.95rem;
  line-height:1.28;
  font-weight:700;
}

small,
.stCaption{
  color:var(--muted) !important;
}


/* ======================================================
PAGE HEADER
====================================================== */

.sp-page-header{
  padding:0.05rem 0 0.10rem 0;
}

.sp-page-title{
  font-size:1.62rem;
  font-weight:820;
  line-height:1.08;
  letter-spacing:-0.028em;
  color:var(--text);
}

.sp-page-subtitle{
  margin-top:0.28rem;
  font-size:0.95rem;
  line-height:1.50;
  color:var(--muted);
  max-width:78ch;
}


/* ======================================================
SECTION HEADER
====================================================== */

.sp-section-header{
  margin-bottom:0.10rem;
}

.sp-section-title{
  font-size:1rem;
  font-weight:760;
  letter-spacing:-0.012em;
  color:var(--text);
}

.sp-section-subtitle{
  margin-top:0.10rem;
  font-size:0.90rem;
  line-height:1.44;
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
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:15px 17px;
  box-shadow:var(--shadow-xs);
  transition:var(--transition);
  overflow:visible;
}

.sp-surface:hover{
  border-color:var(--border-strong);
  box-shadow:var(--shadow-sm);
}

.sp-surface-no-pad{
  padding:0 !important;
}


/* ======================================================
CHIPS / PILLS
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

.sp-pill{
  display:inline-flex;
  align-items:center;
  gap:6px;
  min-height:28px;
  padding:5px 10px;
  border-radius:999px;
  font-size:0.78rem;
  font-weight:740;
  line-height:1;
  border:1px solid rgba(15,23,42,0.08);
  background:#fff;
  color:var(--text-soft);
}

.sp-pill-danger{
  background:var(--danger-bg);
  color:#991b1b;
  border-color:rgba(220,38,38,0.16);
}

.sp-pill-warning{
  background:var(--warning-bg);
  color:#92400e;
  border-color:rgba(217,119,6,0.16);
}

.sp-pill-success{
  background:var(--success-bg);
  color:#166534;
  border-color:rgba(21,128,61,0.15);
}

.sp-pill-info{
  background:var(--info-bg);
  color:#1d4ed8;
  border-color:rgba(37,99,235,0.15);
}

.sp-pill-neutral{
  background:var(--neutral-bg);
  color:var(--text-soft);
  border-color:rgba(15,23,42,0.08);
}


/* ======================================================
SIDEBAR
====================================================== */

section[data-testid="stSidebar"]{
  background:linear-gradient(180deg, #f4f8f6 0%, #eef4f1 100%);
  border-right:1px solid #dbe5e1;
}

section[data-testid="stSidebar"] .block-container{
  padding:0.92rem !important;
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
  padding:10px 12px;
  border-radius:12px;
  margin-bottom:5px;
  cursor:pointer;
  border:1px solid rgba(15,23,42,0.08);
  background:rgba(255,255,255,0.92);
  font-size:0.93rem;
  transition:background-color .18s ease, border-color .18s ease, box-shadow .18s ease;
  box-shadow:0 1px 2px rgba(15,23,42,0.02);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]:hover{
  background:#ffffff;
  border-color:rgba(15,23,42,0.14);
  box-shadow:0 2px 6px rgba(15,23,42,0.04);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"][aria-checked="true"]{
  background:rgba(53,94,87,0.08);
  border-left:4px solid var(--primary);
  border-top-color:rgba(53,94,87,0.12);
  border-right-color:rgba(53,94,87,0.12);
  border-bottom-color:rgba(53,94,87,0.12);
  font-weight:740;
}


/* ======================================================
BUTTONS
====================================================== */

.stButton > button{
  border-radius:12px;
  padding:0.60rem 1rem;
  min-height:42px;
  font-weight:660;
  border:1px solid rgba(15,23,42,0.10);
  background:#ffffff;
  color:var(--text);
  transition:background-color .18s ease, border-color .18s ease, box-shadow .18s ease, transform .18s ease;
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
  background:var(--primary) !important;
  border:1px solid var(--primary) !important;
  color:#ffffff !important;
  box-shadow:0 6px 14px rgba(53,94,87,0.14) !important;
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
  transition:border-color .18s ease, box-shadow .18s ease, background-color .18s ease !important;
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
  font-weight:620 !important;
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
  font-weight:650 !important;
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
  box-shadow:var(--shadow-xs);
}

summary{
  border-radius:12px;
}


/* ======================================================
CARD KPI
====================================================== */

.sp-card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:15px 16px;
  box-shadow:var(--shadow-xs);
  transition:var(--transition);
  min-height:110px;
  position:relative;
  overflow:hidden;
}

.sp-card:hover{
  border-color:var(--border-strong);
  box-shadow:var(--shadow-sm);
  transform:translateY(-1px);
}

.sp-card-title{
  font-size:0.77rem;
  color:rgba(15,23,42,0.64);
  margin-bottom:7px;
  font-weight:760;
  text-transform:uppercase;
  letter-spacing:0.045em;
}

.sp-card-value{
  font-size:1.42rem;
  font-weight:820;
  color:var(--text);
  line-height:1.08;
}

.sp-card-value.emph{
  font-size:1.66rem;
  font-weight:860;
}

.sp-card-sub{
  color:rgba(15,23,42,0.58);
  font-size:0.84rem;
  margin-top:8px;
  line-height:1.35;
}

.sp-card-operational{
  min-height:auto;
  padding:16px 16px 15px 16px;
}


/* ======================================================
TONES
====================================================== */

.sp-tone-danger{
  border-left:4px solid var(--danger);
  padding-left:13px;
}

.sp-tone-warning{
  border-left:4px solid var(--warning);
  padding-left:13px;
}

.sp-tone-success{
  border-left:4px solid var(--success);
  padding-left:13px;
}

.sp-tone-info{
  border-left:4px solid var(--info);
  padding-left:13px;
}

.sp-tone-neutral{
  border-left:4px solid #cbd5e1;
  padding-left:13px;
}


/* ======================================================
STRIPS / KEY VALUE
====================================================== */

.sp-kpi-strip,
.sp-highlight-strip{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
}

.sp-kv{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:12px;
  padding:10px 0;
  border-bottom:1px solid rgba(15,23,42,0.06);
}

.sp-kv:last-child{
  border-bottom:none;
  padding-bottom:0;
}

.sp-kv-label{
  color:var(--muted);
  font-size:0.84rem;
  line-height:1.35;
}

.sp-kv-value{
  color:var(--text);
  font-weight:760;
  text-align:right;
  font-size:0.88rem;
  line-height:1.35;
}


/* ======================================================
TIMELINE
====================================================== */

.sp-timeline{
  display:flex;
  flex-direction:column;
  gap:12px;
}

.sp-timeline-item{
  display:flex;
  align-items:stretch;
  gap:12px;
}

.sp-timeline-rail{
  width:20px;
  display:flex;
  justify-content:center;
  flex:0 0 20px;
}

.sp-timeline-rail-line{
  position:relative;
  width:2px;
  min-height:64px;
  background:rgba(15,23,42,0.08);
  border-radius:999px;
}

.sp-timeline-rail-line.last{
  background:transparent;
}

.sp-timeline-dot{
  position:absolute;
  top:0;
  left:50%;
  transform:translateX(-50%);
  width:12px;
  height:12px;
  border-radius:999px;
  box-shadow:0 0 0 4px rgba(255,255,255,0.96);
}

.sp-timeline-dot-danger{ background:var(--danger); }
.sp-timeline-dot-warning{ background:var(--warning); }
.sp-timeline-dot-success{ background:var(--success); }
.sp-timeline-dot-info{ background:var(--info); }
.sp-timeline-dot-neutral{ background:#94a3b8; }

.sp-timeline-content{
  flex:1 1 auto;
  min-width:0;
}

.sp-timeline-kind{
  color:rgba(15,23,42,0.58);
  font-weight:760;
  font-size:0.78rem;
  text-transform:uppercase;
  letter-spacing:0.04em;
}

.sp-timeline-title{
  font-weight:800;
  line-height:1.35;
  color:var(--text);
}

.sp-timeline-detail{
  margin-top:5px;
  color:rgba(15,23,42,0.72);
  font-size:0.88rem;
  line-height:1.42;
}

.sp-timeline-meta{
  margin-top:8px;
}


/* ======================================================
EMPTY STATE
====================================================== */

.sp-empty-state{
  text-align:center;
  padding:32px 20px;
}

.sp-empty-state-icon{
  font-size:1.9rem;
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
  background:linear-gradient(180deg, rgba(220,38,38,0.045) 0%, rgba(220,38,38,0.025) 100%);
  border:1px solid rgba(220,38,38,0.15);
  border-left:4px solid var(--danger);
  border-radius:14px;
  padding:14px 16px;
  margin-bottom:0.40rem;
}

.sp-app-error-title{
  color:#991b1b;
  font-size:0.98rem;
  font-weight:800;
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
  margin:0.70rem 0;
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
  background:rgba(53,94,87,0.30);
}


/* ======================================================
MOBILE
====================================================== */

@media (max-width:768px){

  .block-container{
    padding:0.92rem !important;
    max-width:100% !important;
  }

  .sp-page-title{
    font-size:1.38rem;
  }

  .sp-page-subtitle{
    font-size:0.91rem;
  }

  .sp-card{
    min-height:auto;
    padding:13px 14px;
  }

  .sp-card-value{
    font-size:1.14rem;
  }

  .sp-card-value.emph{
    font-size:1.30rem;
  }

  .sp-surface{
    padding:13px 14px;
    border-radius:15px;
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

  .sp-timeline-item{
    gap:10px;
  }

  .sp-timeline-rail{
    width:18px;
    flex-basis:18px;
  }

  .sp-timeline-rail-line{
    min-height:68px;
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
