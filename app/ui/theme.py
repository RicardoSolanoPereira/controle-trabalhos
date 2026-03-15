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

_CSS_VERSION = "v31"
_CSS_FLAG_KEY = f"_sp_css_injected_{_CSS_VERSION}"

_ALLOWED_TONES = {"neutral", "danger", "warning", "success", "info"}

_GLOBAL_CSS = """
<style>

/* ======================================================
TOKENS
====================================================== */

:root{
  --bg:#f4f7f5;
  --bg-soft:#f8fbf9;
  --bg-elevated:#eef4f1;

  --surface:#ffffff;
  --surface-soft:#fcfdfd;
  --surface-muted:#f6f8f7;

  --border:#dde5e1;
  --border-strong:#ccd7d1;
  --border-soft:rgba(15,23,42,0.06);

  --text:#0f172a;
  --text-soft:#334155;
  --muted:#667085;
  --muted-strong:#475467;

  --primary:#355e57;
  --primary-hover:#2c4f49;
  --primary-soft:rgba(53,94,87,0.08);
  --primary-softer:rgba(53,94,87,0.04);
  --primary-ring:rgba(53,94,87,0.14);

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

  --radius-2xl:22px;
  --radius-xl:18px;
  --radius-lg:16px;
  --radius-md:12px;
  --radius-sm:10px;

  --shadow-xs:0 1px 2px rgba(15,23,42,0.03);
  --shadow-sm:0 8px 22px rgba(15,23,42,0.045);
  --shadow-md:0 18px 40px rgba(15,23,42,0.07);

  --transition-fast:all .14s ease;
  --transition:all .18s ease;
}


/* ======================================================
BASE
====================================================== */

html,
body{
  color:var(--text);
}

html{
  scroll-behavior:smooth;
}

body{
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
}

p,
li,
label,
span,
div{
  color:inherit;
}

.stApp{
  background:
    radial-gradient(circle at top right, rgba(53,94,87,0.03), transparent 22%),
    linear-gradient(180deg, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0.18) 100%),
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

iframe{
  border-radius:14px;
}


/* ======================================================
LAYOUT
====================================================== */

.block-container{
  max-width:1360px;
  padding-top:0.90rem;
  padding-right:1.10rem;
  padding-bottom:1.25rem;
  padding-left:1.10rem;
  overflow:visible !important;
}

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.18rem;
}

div[data-testid="stHorizontalBlock"]{
  align-items:stretch;
}


/* ======================================================
TYPOGRAPHY
====================================================== */

h1,
h2,
h3,
h4{
  margin-bottom:0.10rem;
  letter-spacing:-0.02em;
  color:var(--text);
}

h1{
  font-size:1.80rem;
  line-height:1.04;
  font-weight:800;
}

h2{
  font-size:1.28rem;
  line-height:1.12;
  font-weight:760;
}

h3{
  font-size:1.03rem;
  line-height:1.22;
  font-weight:720;
}

h4{
  font-size:0.94rem;
  line-height:1.28;
  font-weight:700;
}

small,
.stCaption{
  color:var(--muted) !important;
}

label[data-testid="stWidgetLabel"] p{
  font-weight:620 !important;
  color:var(--text-soft) !important;
}


/* ======================================================
PAGE HEADER
====================================================== */

.sp-page-header{
  padding:0.02rem 0 0.14rem 0;
}

.sp-page-title-wrap{
  display:flex;
  flex-direction:column;
  gap:0;
}

.sp-page-title{
  font-size:1.58rem;
  line-height:1.04;
  font-weight:820;
  letter-spacing:-0.03em;
  color:var(--text);
}

.sp-page-subtitle{
  margin-top:0.30rem;
  max-width:74ch;
  font-size:0.93rem;
  line-height:1.52;
  color:var(--muted);
}

.sp-page-header-actions,
.sp-page-header-actions-mobile,
.sp-toolbar-actions,
.sp-toolbar-actions-mobile,
.sp-section-actions,
.sp-section-actions-mobile{
  width:100%;
}

.sp-page-header-actions > div,
.sp-toolbar-actions > div,
.sp-section-actions > div{
  display:flex;
  justify-content:flex-end;
  align-items:center;
  gap:0.50rem;
  flex-wrap:wrap;
}

.sp-page-header-actions-mobile > div,
.sp-toolbar-actions-mobile > div,
.sp-section-actions-mobile > div{
  display:flex;
  justify-content:flex-start;
  align-items:center;
  gap:0.50rem;
  flex-wrap:wrap;
}


/* ======================================================
SECTION HEADER
====================================================== */

.sp-section-header{
  margin-bottom:0.04rem;
}

.sp-section-title-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:0.75rem;
}

.sp-section-title{
  font-size:0.99rem;
  font-weight:760;
  letter-spacing:-0.012em;
  color:var(--text);
}

.sp-section-subtitle{
  margin-top:0.12rem;
  font-size:0.88rem;
  line-height:1.48;
  color:var(--muted);
}


/* ======================================================
SURFACES
====================================================== */

.sp-surface{
  background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(251,253,252,1) 100%);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
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
TOPBAR / TOOLBAR
====================================================== */

.sp-topbar-shell{
  position:sticky;
  top:0;
  z-index:20;
  backdrop-filter:blur(8px);
}

.sp-topbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:9px 12px;
  border:1px solid rgba(15,23,42,0.06);
  border-radius:16px;
  background:rgba(255,255,255,0.80);
  box-shadow:var(--shadow-xs);
}

.sp-topbar-group{
  display:flex;
  align-items:center;
  gap:8px;
  flex-wrap:wrap;
}


/* ======================================================
SIDEBAR
====================================================== */

section[data-testid="stSidebar"]{
  background:linear-gradient(180deg, #f7faf9 0%, #edf4f1 100%);
  border-right:1px solid #e1e8e5;
}

section[data-testid="stSidebar"] .block-container{
  padding:0.90rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.16rem !important;
}


/* ======================================================
BUTTONS
====================================================== */

.stButton > button{
  min-height:42px;
  padding:0.60rem 0.95rem;
  border-radius:12px;
  border:1px solid rgba(15,23,42,0.10);
  background:#ffffff;
  color:var(--text);
  font-weight:660;
  transition:
    background-color .16s ease,
    border-color .16s ease,
    box-shadow .16s ease,
    transform .16s ease;
  box-shadow:none;
}

.stButton > button:hover{
  background:rgba(15,23,42,0.024);
  border-color:rgba(15,23,42,0.16);
  transform:translateY(-1px);
}

.stButton > button:focus,
.stButton > button:focus-visible{
  outline:none !important;
  box-shadow:0 0 0 0.18rem var(--primary-ring) !important;
}

.stButton > button[kind="primary"],
.stButton > button[class*="primary"]{
  background:var(--primary) !important;
  border:1px solid var(--primary) !important;
  color:#ffffff !important;
  box-shadow:0 8px 18px rgba(53,94,87,0.12) !important;
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
  min-height:42px;
  border-radius:12px !important;
  border-color:rgba(15,23,42,0.10) !important;
  background:#ffffff !important;
  transition:
    border-color .16s ease,
    box-shadow .16s ease,
    background-color .16s ease !important;
}

div[data-baseweb="input"] > div:hover,
div[data-baseweb="textarea"] > div:hover,
div[data-baseweb="select"] > div:hover{
  border-color:rgba(15,23,42,0.16) !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within{
  border-color:rgba(53,94,87,0.34) !important;
  box-shadow:0 0 0 0.18rem var(--primary-ring) !important;
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
DATA DISPLAY
====================================================== */

div[data-testid="stDataFrame"]{
  overflow:hidden;
  border:1px solid var(--border);
  border-radius:14px;
  background:#ffffff;
  box-shadow:var(--shadow-xs);
}

div[data-testid="stDataFrame"] [role="grid"]{
  border:none !important;
}

details{
  border:1px solid var(--border);
  border-radius:14px;
  background:#ffffff;
  box-shadow:var(--shadow-xs);
}

summary{
  border-radius:12px;
}


/* ======================================================
CARDS
====================================================== */

.sp-card{
  position:relative;
  overflow:hidden;
  min-height:108px;
  padding:14px 14px 13px 14px;
  border:1px solid var(--border);
  border-radius:16px;
  background:linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(250,252,251,1) 100%);
  box-shadow:var(--shadow-xs);
  transition:var(--transition);
}

.sp-card:hover{
  border-color:var(--border-strong);
  box-shadow:var(--shadow-sm);
  transform:translateY(-1px);
}

.sp-card-title{
  margin-bottom:6px;
  font-size:0.75rem;
  line-height:1.15;
  font-weight:760;
  letter-spacing:0.045em;
  text-transform:uppercase;
  color:rgba(15,23,42,0.56);
}

.sp-card-value{
  font-size:1.30rem;
  line-height:1.04;
  font-weight:820;
  color:var(--text);
}

.sp-card-value.emph{
  font-size:1.56rem;
  font-weight:850;
}

.sp-card-sub{
  margin-top:7px;
  font-size:0.82rem;
  line-height:1.40;
  color:rgba(15,23,42,0.58);
}

.sp-card-operational{
  min-height:auto;
  padding:14px;
}


/* ======================================================
TONES
====================================================== */

.sp-tone-danger{
  border-left:3px solid var(--danger);
  padding-left:12px;
}

.sp-tone-warning{
  border-left:3px solid var(--warning);
  padding-left:12px;
}

.sp-tone-success{
  border-left:3px solid var(--success);
  padding-left:12px;
}

.sp-tone-info{
  border-left:3px solid var(--info);
  padding-left:12px;
}

.sp-tone-neutral{
  border-left:3px solid #cbd5e1;
  padding-left:12px;
}


/* ======================================================
CHIPS / PILLS
====================================================== */

.sp-chip,
.sp-pill{
  display:inline-flex;
  align-items:center;
  gap:6px;
  border-radius:999px;
  line-height:1;
  white-space:nowrap;
}

.sp-chip{
  padding:5px 9px;
  background:var(--neutral-bg);
  border:1px solid rgba(15,23,42,0.08);
  font-size:0.78rem;
  font-weight:650;
  color:var(--text-soft);
}

.sp-pill{
  min-height:26px;
  padding:5px 10px;
  font-size:0.77rem;
  font-weight:730;
  border:1px solid rgba(15,23,42,0.08);
  background:#fff;
  color:var(--text-soft);
}

.sp-chip-danger,
.sp-pill-danger{
  background:var(--danger-bg);
  border-color:rgba(220,38,38,0.16);
  color:#991b1b;
}

.sp-chip-warning,
.sp-pill-warning{
  background:var(--warning-bg);
  border-color:rgba(217,119,6,0.16);
  color:#92400e;
}

.sp-chip-success,
.sp-pill-success{
  background:var(--success-bg);
  border-color:rgba(21,128,61,0.14);
  color:#166534;
}

.sp-chip-info,
.sp-pill-info{
  background:var(--info-bg);
  border-color:rgba(37,99,235,0.14);
  color:#1d4ed8;
}

.sp-pill-neutral{
  background:var(--neutral-bg);
  border-color:rgba(15,23,42,0.08);
  color:var(--text-soft);
}


/* ======================================================
KEY VALUE / STRIPS
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
  padding:9px 0;
  border-bottom:1px solid rgba(15,23,42,0.06);
}

.sp-kv:last-child{
  padding-bottom:0;
  border-bottom:none;
}

.sp-kv-label{
  font-size:0.83rem;
  line-height:1.35;
  color:var(--muted);
}

.sp-kv-value{
  text-align:right;
  font-size:0.87rem;
  line-height:1.35;
  font-weight:760;
  color:var(--text);
}


/* ======================================================
TIMELINE
====================================================== */

.sp-timeline{
  display:flex;
  flex-direction:column;
  gap:10px;
}

.sp-timeline-item{
  display:flex;
  align-items:stretch;
  gap:10px;
}

.sp-timeline-rail{
  width:18px;
  flex:0 0 18px;
  display:flex;
  justify-content:center;
}

.sp-timeline-rail-line{
  position:relative;
  width:2px;
  min-height:58px;
  border-radius:999px;
  background:rgba(15,23,42,0.08);
}

.sp-timeline-rail-line.last{
  background:transparent;
}

.sp-timeline-dot{
  position:absolute;
  top:0;
  left:50%;
  width:11px;
  height:11px;
  border-radius:999px;
  transform:translateX(-50%);
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
  font-size:0.76rem;
  font-weight:760;
  letter-spacing:0.04em;
  text-transform:uppercase;
  color:rgba(15,23,42,0.56);
}

.sp-timeline-title{
  line-height:1.32;
  font-weight:790;
  color:var(--text);
}

.sp-timeline-detail{
  margin-top:4px;
  font-size:0.86rem;
  line-height:1.42;
  color:rgba(15,23,42,0.70);
}

.sp-timeline-meta{
  margin-top:7px;
}


/* ======================================================
EMPTY / ERROR / DIVIDER
====================================================== */

.sp-empty-state{
  padding:28px 20px;
  text-align:center;
}

.sp-empty-state-icon{
  margin-bottom:9px;
  font-size:1.75rem;
  line-height:1;
}

.sp-empty-state-title{
  font-size:0.98rem;
  font-weight:800;
  color:var(--text);
}

.sp-empty-state-subtitle{
  margin-top:6px;
  font-size:0.89rem;
  line-height:1.46;
  color:var(--muted);
}

.sp-app-error{
  margin-bottom:0.36rem;
  padding:13px 15px;
  border:1px solid rgba(220,38,38,0.14);
  border-left:4px solid var(--danger);
  border-radius:14px;
  background:linear-gradient(180deg, rgba(220,38,38,0.04) 0%, rgba(220,38,38,0.022) 100%);
}

.sp-app-error-title{
  font-size:0.96rem;
  font-weight:800;
  color:#991b1b;
}

.sp-app-error-subtitle{
  margin-top:4px;
  font-size:0.89rem;
  line-height:1.44;
  color:#7f1d1d;
}

.sp-divider{
  border:0;
  border-top:1px solid #e5e7eb;
  margin:0.68rem 0;
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

@media (max-width: 768px){

  .block-container{
    max-width:100% !important;
    padding:0.88rem !important;
  }

  .sp-page-title{
    font-size:1.36rem;
  }

  .sp-page-subtitle{
    font-size:0.89rem;
  }

  .sp-topbar{
    padding:9px 11px;
    border-radius:15px;
  }

  .sp-card{
    min-height:auto;
    padding:13px;
  }

  .sp-card-value{
    font-size:1.12rem;
  }

  .sp-card-value.emph{
    font-size:1.28rem;
  }

  .sp-surface{
    padding:13px;
    border-radius:15px;
  }

  .stButton > button{
    min-height:44px !important;
    padding:0.70rem 0.95rem !important;
  }

  .sp-chip{
    padding:5px 8px;
    font-size:0.76rem;
  }

  .sp-section-title{
    font-size:0.96rem;
  }

  .sp-timeline-item{
    gap:9px;
  }

  .sp-timeline-rail{
    width:16px;
    flex-basis:16px;
  }

  .sp-timeline-rail-line{
    min-height:62px;
  }
}

</style>
"""


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None) -> str:
    return html.escape(text or "")


def _normalize_tone(tone: str | None) -> str:
    tone_norm = (tone or "neutral").strip().lower()
    return tone_norm if tone_norm in _ALLOWED_TONES else "neutral"


def inject_global_css() -> None:
    if st.session_state.get(_CSS_FLAG_KEY, False):
        return

    st.session_state[_CSS_FLAG_KEY] = True
    _render_html(_GLOBAL_CSS)


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

    emph_class = " emph" if emphasize else ""
    subtitle_block = (
        f"<div class='sp-card-sub'>{subtitle_html}</div>" if subtitle_html else ""
    )

    _render_html(
        f"""
        <div class="sp-card sp-tone-{tone_norm}">
            <div class="sp-card-title">{title_html}</div>
            <div class="sp-card-value{emph_class}">{value_html}</div>
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
