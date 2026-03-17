from __future__ import annotations

import html
from typing import Iterable

import streamlit as st

__all__ = [
    "inject_global_css",
    "card",
    "section_title",
    "subtle_divider",
    "app_error",
    "surface_start",
    "surface_end",
    "surface",
    "chip",
    "pill",
    "empty_state",
    "kv_row",
    "status_banner",
    "caption",
    "muted",
]

_CSS_VERSION = "v30"
_CSS_FLAG_KEY = f"_sp_css_injected_{_CSS_VERSION}"

_ALLOWED_TONES = {"neutral", "danger", "warning", "success", "info"}

_GLOBAL_CSS = """
<style>

/* ======================================================
TOKENS
====================================================== */

:root{
  --bg:#f6f8f7;
  --bg-accent:#eef4f1;
  --bg-soft:#fbfcfc;

  --surface:#ffffff;
  --surface-soft:#fcfdfd;
  --surface-muted:#f5f7f7;
  --surface-strong:#f1f5f3;

  --border:#dfe7e3;
  --border-strong:#cbd8d2;
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

  --radius-2xl:28px;
  --radius-xl:22px;
  --radius-lg:18px;
  --radius-md:14px;
  --radius-sm:12px;
  --radius-xs:10px;

  --shadow-xs:0 1px 2px rgba(15,23,42,0.04);
  --shadow-sm:0 6px 14px rgba(15,23,42,0.045);
  --shadow-md:0 10px 24px rgba(15,23,42,0.06);
  --shadow-lg:0 18px 38px rgba(15,23,42,0.07);

  --transition-fast:all .16s ease;
  --transition:all .18s ease;

  --sidebar-width:320px;
  --sidebar-item-height:40px;
  --sidebar-item-radius:12px;

  --container-max:1360px;
  --space-1:4px;
  --space-2:8px;
  --space-3:12px;
  --space-4:16px;
  --space-5:20px;
  --space-6:24px;
  --space-7:28px;
  --space-8:32px;
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
    radial-gradient(circle at top right, rgba(53,94,87,0.04), transparent 28%),
    linear-gradient(180deg, rgba(255,255,255,0.62) 0%, rgba(255,255,255,0.18) 100%),
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
  max-width:var(--container-max);
  padding-top:0.95rem;
  padding-right:1.20rem;
  padding-bottom:1.35rem;
  padding-left:1.20rem;
  overflow:visible !important;
}

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.30rem;
}

.sp-content-shell{
  width:100%;
}

.sp-stack-xs > * + *{ margin-top:6px; }
.sp-stack-sm > * + *{ margin-top:10px; }
.sp-stack-md > * + *{ margin-top:14px; }
.sp-stack-lg > * + *{ margin-top:18px; }
.sp-stack-xl > * + *{ margin-top:24px; }

/* ======================================================
TYPOGRAPHY
====================================================== */

h1,h2,h3,h4{
  margin-bottom:0.18rem;
  letter-spacing:-0.02em;
  color:var(--text);
}

h1{
  font-size:1.80rem;
  line-height:1.08;
  font-weight:820;
}

h2{
  font-size:1.34rem;
  line-height:1.14;
  font-weight:790;
}

h3{
  font-size:1.05rem;
  line-height:1.24;
  font-weight:740;
}

h4{
  font-size:0.96rem;
  line-height:1.28;
  font-weight:700;
}

small,
.stCaption{
  color:var(--muted) !important;
}

.sp-caption{
  color:var(--muted);
  font-size:0.82rem;
  line-height:1.4;
}

.sp-muted{
  color:var(--muted) !important;
}

.sp-text-soft{
  color:var(--text-soft) !important;
}

/* ======================================================
PAGE HEADER
====================================================== */

.sp-page-header{
  padding:0.02rem 0 0.12rem 0;
}

.sp-page-title{
  font-size:1.68rem;
  font-weight:820;
  line-height:1.06;
  letter-spacing:-0.028em;
  color:var(--text);
}

.sp-page-subtitle{
  margin-top:0.30rem;
  max-width:82ch;
  font-size:0.95rem;
  line-height:1.50;
  color:var(--muted);
}

/* ======================================================
SECTION HEADER
====================================================== */

.sp-section-header{
  margin-bottom:0.16rem;
}

.sp-section-title{
  font-size:1.00rem;
  font-weight:780;
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
SURFACES
====================================================== */

.sp-surface{
  overflow:visible;
  padding:16px 18px;
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  background:linear-gradient(180deg, rgba(255,255,255,0.99) 0%, #ffffff 100%);
  box-shadow:var(--shadow-xs);
  transition:var(--transition);
}

.sp-surface:hover{
  border-color:var(--border-strong);
  box-shadow:var(--shadow-sm);
}

.sp-surface-no-pad{
  padding:0 !important;
}

.sp-surface-muted{
  background:linear-gradient(180deg, #fcfdfd 0%, #f8faf9 100%);
}

.sp-surface-strong{
  background:linear-gradient(180deg, #ffffff 0%, #f6f9f8 100%);
}

/* ======================================================
CHIPS / PILLS
====================================================== */

.sp-chip{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:6px 10px;
  border:1px solid rgba(15,23,42,0.08);
  border-radius:999px;
  background:var(--neutral-bg);
  color:var(--text-soft);
  font-size:0.80rem;
  font-weight:660;
  line-height:1;
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

.sp-chip-neutral{
  background:var(--neutral-bg);
  border-color:rgba(15,23,42,0.08);
  color:var(--text-soft);
}

.sp-pill{
  display:inline-flex;
  align-items:center;
  gap:6px;
  min-height:28px;
  padding:5px 10px;
  border:1px solid rgba(15,23,42,0.08);
  border-radius:999px;
  background:#fff;
  color:var(--text-soft);
  font-size:0.78rem;
  font-weight:760;
  line-height:1;
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
  min-width:var(--sidebar-width) !important;
  max-width:var(--sidebar-width) !important;
  background:linear-gradient(180deg, #f3f7f5 0%, #eef4f1 100%);
  border-right:1px solid #dbe5e1;
}

section[data-testid="stSidebar"] .block-container{
  padding:0.90rem 0.85rem 0.80rem 0.85rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.16rem !important;
}

.sidebar-title{
  margin-bottom:0.30rem;
  font-size:1rem;
  font-weight:780;
  letter-spacing:-0.015em;
  color:var(--text);
}

.sidebar-section{
  margin-top:0.08rem;
  margin-bottom:0.36rem;
  font-size:0.78rem;
  font-weight:760;
  letter-spacing:0.04em;
  text-transform:uppercase;
  color:var(--muted);
}

.sidebar-build{
  margin-top:0.35rem;
  font-size:0.74rem;
  color:var(--muted);
}

section[data-testid="stSidebar"] div[role="radiogroup"]{
  gap:0.22rem !important;
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"] > div:first-child{
  display:none !important;
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]{
  display:flex !important;
  align-items:center;
  width:100%;
  min-height:var(--sidebar-item-height);
  margin:0 0 4px 0;
  padding:0 12px;
  border:1px solid transparent;
  border-radius:var(--sidebar-item-radius);
  background:transparent;
  box-shadow:none;
  cursor:pointer;
  font-size:0.93rem;
  transition:
    background-color .16s ease,
    border-color .16s ease,
    color .16s ease,
    box-shadow .16s ease;
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]:hover{
  background:rgba(255,255,255,0.70);
  border-color:rgba(15,23,42,0.06);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"][aria-checked="true"]{
  background:linear-gradient(180deg, rgba(53,94,87,0.10) 0%, rgba(53,94,87,0.07) 100%);
  border-color:rgba(53,94,87,0.10);
  box-shadow:0 1px 2px rgba(15,23,42,0.03);
  font-weight:760;
  color:var(--text);
}

section[data-testid="stSidebar"] details{
  border:1px solid rgba(15,23,42,0.08);
  border-radius:14px;
  background:rgba(255,255,255,0.78);
  box-shadow:none;
}

section[data-testid="stSidebar"] summary{
  min-height:42px;
  border-radius:14px;
}

section[data-testid="stSidebar"] details > div{
  padding-top:0.15rem;
}

/* ======================================================
BUTTONS
====================================================== */

.stButton > button{
  min-height:40px;
  padding:0.56rem 0.95rem;
  border:1px solid rgba(15,23,42,0.10);
  border-radius:12px;
  background:#ffffff;
  color:var(--text);
  font-weight:670;
  box-shadow:none;
  transition:
    background-color .18s ease,
    border-color .18s ease,
    box-shadow .18s ease,
    transform .18s ease;
}

.stButton > button:hover{
  background:rgba(15,23,42,0.022);
  border-color:rgba(15,23,42,0.18);
  transform:translateY(-1px);
}

.stButton > button:focus,
.stButton > button:focus-visible{
  outline:none !important;
  box-shadow:0 0 0 0.18rem rgba(53,94,87,0.12) !important;
}

.stButton > button[kind="primary"],
.stButton > button[class*="primary"]{
  background:linear-gradient(180deg, var(--primary) 0%, #2f544d 100%) !important;
  border:1px solid var(--primary) !important;
  color:#ffffff !important;
  box-shadow:0 8px 18px rgba(53,94,87,0.16) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[class*="primary"]:hover{
  background:linear-gradient(180deg, var(--primary-hover) 0%, #233f39 100%) !important;
  border-color:var(--primary-hover) !important;
}

section[data-testid="stSidebar"] .stButton > button{
  min-height:38px;
  padding:0.46rem 0.82rem;
  border-radius:12px;
  font-size:0.90rem;
}

/* ======================================================
INPUTS / SELECTS / TEXTAREA
====================================================== */

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div{
  min-height:42px;
  border-radius:var(--radius-md) !important;
  border-color:rgba(15,23,42,0.10) !important;
  background:#ffffff !important;
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
  color:var(--text-soft) !important;
  font-weight:630 !important;
  font-size:0.88rem !important;
}

section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p{
  font-size:0.84rem !important;
}

div[data-baseweb="select"]{
  width:100%;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div{
  box-shadow:none !important;
}

/* ======================================================
FORM CONTROLS / TABS / DATA
====================================================== */

div[data-testid="stCheckbox"]{
  margin-bottom:0.15rem;
}

div[data-testid="stRadio"] > div{
  gap:0.22rem !important;
}

div[data-testid="stTabs"]{
  gap:0.20rem;
}

button[data-baseweb="tab"]{
  border-radius:12px 12px 0 0 !important;
  color:var(--muted-strong) !important;
  font-weight:660 !important;
}

button[data-baseweb="tab"][aria-selected="true"]{
  color:var(--primary) !important;
  border-bottom-color:var(--primary) !important;
}

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
CARD KPI
====================================================== */

.sp-card{
  position:relative;
  overflow:hidden;
  min-height:108px;
  padding:15px 16px 14px 16px;
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  background:linear-gradient(180deg, rgba(255,255,255,0.99) 0%, #ffffff 100%);
  box-shadow:var(--shadow-sm);
  transition:var(--transition);
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
  box-shadow:var(--shadow-md);
  transform:translateY(-1px);
}

.sp-card-title{
  margin-bottom:7px;
  color:rgba(15,23,42,0.64);
  font-size:0.75rem;
  font-weight:780;
  line-height:1.2;
  text-transform:uppercase;
  letter-spacing:0.045em;
}

.sp-card-value{
  color:var(--text);
  font-size:1.42rem;
  font-weight:840;
  line-height:1.06;
}

.sp-card-value.emph{
  font-size:1.66rem;
  font-weight:880;
}

.sp-card-sub{
  margin-top:8px;
  color:rgba(15,23,42,0.58);
  font-size:0.83rem;
  line-height:1.35;
}

.sp-card-operational{
  min-height:auto;
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
STATUS BANNER
====================================================== */

.sp-status-banner{
  padding:14px 16px;
  border:1px solid var(--border);
  border-radius:16px;
  background:linear-gradient(180deg, rgba(255,255,255,0.98) 0%, #ffffff 100%);
  box-shadow:var(--shadow-xs);
}

.sp-status-banner-title{
  color:var(--text);
  font-size:0.98rem;
  font-weight:820;
  line-height:1.35;
}

.sp-status-banner-subtitle{
  margin-top:4px;
  color:var(--muted-strong);
  font-size:0.89rem;
  line-height:1.45;
}

/* ======================================================
KEY-VALUE / STRIPS
====================================================== */

.sp-kpi-strip{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
}

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
  padding-bottom:0;
  border-bottom:none;
}

.sp-kv-label{
  color:var(--muted);
  font-size:0.84rem;
  line-height:1.35;
}

.sp-kv-value{
  color:var(--text);
  font-size:0.88rem;
  font-weight:780;
  line-height:1.35;
  text-align:right;
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
  flex:0 0 20px;
  display:flex;
  justify-content:center;
}

.sp-timeline-rail-line{
  position:relative;
  width:2px;
  min-height:66px;
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
  width:12px;
  height:12px;
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
  color:rgba(15,23,42,0.58);
  font-size:0.78rem;
  font-weight:780;
  text-transform:uppercase;
  letter-spacing:0.04em;
}

.sp-timeline-title{
  color:var(--text);
  font-weight:820;
  line-height:1.35;
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
  padding:28px 20px;
  text-align:center;
}

.sp-empty-icon{
  margin-bottom:9px;
  font-size:1.75rem;
  line-height:1;
}

.sp-empty-title{
  color:var(--text);
  font-size:0.98rem;
  font-weight:800;
}

.sp-empty-subtitle{
  margin-top:6px;
  color:var(--muted);
  font-size:0.89rem;
  line-height:1.46;
}

/* ======================================================
APP ERROR
====================================================== */

.sp-app-error{
  margin-bottom:0.40rem;
  padding:14px 16px;
  border:1px solid rgba(220,38,38,0.15);
  border-left:5px solid var(--danger);
  border-radius:16px;
  background:linear-gradient(180deg, rgba(220,38,38,0.045) 0%, rgba(220,38,38,0.025) 100%);
}

.sp-app-error-title{
  color:#991b1b;
  font-size:0.98rem;
  font-weight:820;
}

.sp-app-error-subtitle{
  margin-top:5px;
  color:#7f1d1d;
  font-size:0.90rem;
  line-height:1.45;
}

/* ======================================================
DIVIDER
====================================================== */

.sp-divider{
  margin:0.72rem 0;
  border:0;
  border-top:1px solid #e7ebea;
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

@media (max-width: 768px){

  .block-container{
    max-width:100% !important;
    padding:0.92rem !important;
  }

  .sp-page-title{
    font-size:1.42rem;
  }

  .sp-page-subtitle{
    font-size:0.91rem;
  }

  .sp-surface{
    padding:13px 14px;
    border-radius:16px;
  }

  .sp-card{
    min-height:auto;
    padding:13px 14px;
  }

  .sp-card-value{
    font-size:1.16rem;
  }

  .sp-card-value.emph{
    font-size:1.34rem;
  }

  .stButton > button{
    min-height:42px !important;
    padding:0.66rem 0.94rem !important;
  }

  .sp-chip{
    padding:6px 9px;
    font-size:0.78rem;
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
    min-height:72px;
  }

  section[data-testid="stSidebar"]{
    min-width:100% !important;
    max-width:100% !important;
  }
}

</style>
"""


def _render_html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def _escape(text: str | None) -> str:
    return html.escape(str(text or ""))


def _normalize_tone(tone: str | None) -> str:
    tone_norm = (tone or "neutral").strip().lower()
    return tone_norm if tone_norm in _ALLOWED_TONES else "neutral"


def _join_classes(*classes: str) -> str:
    return " ".join(part for part in classes if part)


def inject_global_css() -> None:
    if st.session_state.get(_CSS_FLAG_KEY, False):
        return

    st.session_state[_CSS_FLAG_KEY] = True
    _render_html(_GLOBAL_CSS)


def surface_start(
    *,
    tone: str = "neutral",
    extra_classes: str = "",
    no_padding: bool = False,
) -> None:
    tone_norm = _normalize_tone(tone)
    classes = _join_classes(
        "sp-surface",
        f"sp-tone-{tone_norm}",
        "sp-surface-no-pad" if no_padding else "",
        extra_classes,
    )
    _render_html(f"<div class='{classes}'>")


def surface_end() -> None:
    _render_html("</div>")


def surface(
    content: str,
    *,
    tone: str = "neutral",
    extra_classes: str = "",
    no_padding: bool = False,
) -> None:
    tone_norm = _normalize_tone(tone)
    classes = _join_classes(
        "sp-surface",
        f"sp-tone-{tone_norm}",
        "sp-surface-no-pad" if no_padding else "",
        extra_classes,
    )
    _render_html(f"<div class='{classes}'>{content}</div>")


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


def section_title(text: str, subtitle: str = "") -> None:
    text_html = _escape(text)
    subtitle_html = _escape(subtitle)

    subtitle_block = (
        f"<div class='sp-section-subtitle'>{subtitle_html}</div>"
        if subtitle_html
        else ""
    )

    _render_html(
        f"""
        <div class="sp-section-header">
          <div class="sp-section-title">{text_html}</div>
          {subtitle_block}
        </div>
        """
    )


def subtle_divider() -> None:
    _render_html("<hr class='sp-divider'>")


def chip(text: str, *, tone: str = "neutral") -> None:
    tone_norm = _normalize_tone(tone)
    _render_html(f"<span class='sp-chip sp-chip-{tone_norm}'>{_escape(text)}</span>")


def pill(text: str, *, tone: str = "neutral") -> None:
    tone_norm = _normalize_tone(tone)
    _render_html(f"<span class='sp-pill sp-pill-{tone_norm}'>{_escape(text)}</span>")


def empty_state(
    title: str,
    subtitle: str,
    *,
    icon: str = "○",
) -> None:
    _render_html(
        f"""
        <div class="sp-surface">
          <div class="sp-empty-state">
            <div class="sp-empty-icon">{_escape(icon)}</div>
            <div class="sp-empty-title">{_escape(title)}</div>
            <div class="sp-empty-subtitle">{_escape(subtitle)}</div>
          </div>
        </div>
        """
    )


def kv_row(label: str, value: str) -> None:
    _render_html(
        f"""
        <div class="sp-kv">
          <div class="sp-kv-label">{_escape(label)}</div>
          <div class="sp-kv-value">{_escape(value)}</div>
        </div>
        """
    )


def status_banner(
    title: str,
    subtitle: str = "",
    *,
    tone: str = "neutral",
) -> None:
    tone_norm = _normalize_tone(tone)
    subtitle_block = (
        f"<div class='sp-status-banner-subtitle'>{_escape(subtitle)}</div>"
        if subtitle
        else ""
    )
    _render_html(
        f"""
        <div class="sp-status-banner sp-tone-{tone_norm}">
          <div class="sp-status-banner-title">{_escape(title)}</div>
          {subtitle_block}
        </div>
        """
    )


def caption(text: str) -> None:
    _render_html(f"<div class='sp-caption'>{_escape(text)}</div>")


def muted(text: str) -> None:
    _render_html(f"<div class='sp-muted'>{_escape(text)}</div>")


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
