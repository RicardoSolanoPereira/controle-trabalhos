from __future__ import annotations

import html
from contextlib import contextmanager
from typing import Final, Iterator

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
    "surface_container",
    "chip",
    "pill",
    "empty_state",
    "kv_row",
    "status_banner",
    "caption",
    "muted",
    "hero_banner",
    "metric_card",
]

_CSS_VERSION: Final[str] = "v40"
_CSS_FLAG_KEY: Final[str] = f"_sp_css_injected_{_CSS_VERSION}"

DEFAULT_TONE: Final[str] = "neutral"
ALLOWED_TONES: Final[set[str]] = {"neutral", "danger", "warning", "success", "info"}


_GLOBAL_CSS = """
<style>

/* ======================================================
TOKENS
====================================================== */

:root{
  --bg:#f4f7f5;
  --bg-accent:#edf3f0;
  --bg-soft:#fafcfb;

  --surface:#ffffff;
  --surface-soft:#fbfcfc;
  --surface-muted:#f5f7f6;
  --surface-strong:#eef3f0;
  --surface-elevated:#ffffff;
  --surface-interactive:#fcfdfd;

  --border:#dbe5e0;
  --border-strong:#c7d6cf;
  --border-soft:rgba(15,23,42,0.06);

  --text:#0f172a;
  --text-soft:#334155;
  --muted:#667085;
  --muted-strong:#475467;

  --primary:#355e57;
  --primary-hover:#294942;
  --primary-soft:rgba(53,94,87,0.08);
  --primary-soft-2:rgba(53,94,87,0.13);
  --primary-ring:rgba(53,94,87,0.18);
  --primary-gradient:linear-gradient(180deg, #3c6a62 0%, #2f544d 100%);
  --hero-gradient:
    radial-gradient(circle at top right, rgba(53,94,87,0.10), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(247,250,249,0.98) 100%);

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

  --radius-3xl:32px;
  --radius-2xl:28px;
  --radius-xl:22px;
  --radius-lg:18px;
  --radius-md:14px;
  --radius-sm:12px;
  --radius-xs:10px;

  --shadow-xs:0 1px 2px rgba(15,23,42,0.04);
  --shadow-sm:0 6px 14px rgba(15,23,42,0.045);
  --shadow-md:0 12px 26px rgba(15,23,42,0.06);
  --shadow-lg:0 18px 38px rgba(15,23,42,0.075);
  --shadow-float:0 24px 54px rgba(15,23,42,0.08);

  --transition-fast:all .16s ease;
  --transition:all .18s ease;

  --sidebar-width:318px;
  --sidebar-item-height:42px;
  --sidebar-item-radius:14px;

  --container-max:1380px;

  --space-1:4px;
  --space-2:8px;
  --space-3:12px;
  --space-4:16px;
  --space-5:20px;
  --space-6:24px;
  --space-7:28px;
  --space-8:32px;
  --space-9:40px;
  --space-10:48px;

  --fs-2xs:0.72rem;
  --fs-xs:0.80rem;
  --fs-sm:0.88rem;
  --fs-md:0.95rem;
  --fs-base:1rem;
  --fs-lg:1.12rem;
  --fs-xl:1.34rem;
  --fs-2xl:1.72rem;
  --fs-3xl:2.08rem;

  --lh-tight:1.08;
  --lh-snug:1.22;
  --lh-base:1.45;
  --lh-relaxed:1.58;
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
    radial-gradient(circle at top right, rgba(53,94,87,0.05), transparent 28%),
    linear-gradient(180deg, rgba(255,255,255,0.64) 0%, rgba(255,255,255,0.22) 100%),
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
  padding-top:1.05rem;
  padding-right:1.25rem;
  padding-bottom:1.50rem;
  padding-left:1.25rem;
  overflow:visible !important;
}

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.34rem;
}

.sp-content-shell{
  width:100%;
}

.sp-stack-2xs > * + *{ margin-top:4px; }
.sp-stack-xs > * + *{ margin-top:6px; }
.sp-stack-sm > * + *{ margin-top:10px; }
.sp-stack-md > * + *{ margin-top:14px; }
.sp-stack-lg > * + *{ margin-top:18px; }
.sp-stack-xl > * + *{ margin-top:24px; }
.sp-stack-2xl > * + *{ margin-top:32px; }

/* ======================================================
TYPOGRAPHY
====================================================== */

h1,h2,h3,h4{
  margin-bottom:0.18rem;
  letter-spacing:-0.02em;
  color:var(--text);
}

h1{
  font-size:var(--fs-2xl);
  line-height:var(--lh-tight);
  font-weight:840;
}

h2{
  font-size:var(--fs-xl);
  line-height:var(--lh-snug);
  font-weight:800;
}

h3{
  font-size:1.04rem;
  line-height:1.24;
  font-weight:760;
}

h4{
  font-size:0.96rem;
  line-height:1.28;
  font-weight:720;
}

small,
.stCaption{
  color:var(--muted) !important;
}

.sp-caption{
  color:var(--muted);
  font-size:0.82rem;
  line-height:1.42;
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
  padding:0.04rem 0 0.16rem 0;
}

.sp-page-title{
  font-size:1.76rem;
  font-weight:840;
  line-height:1.04;
  letter-spacing:-0.03em;
  color:var(--text);
}

.sp-page-subtitle{
  margin-top:0.34rem;
  max-width:84ch;
  font-size:0.96rem;
  line-height:1.54;
  color:var(--muted);
}

/* ======================================================
SECTION HEADER
====================================================== */

.sp-section-header{
  margin-bottom:0.14rem;
}

.sp-section-title{
  font-size:1.02rem;
  font-weight:790;
  letter-spacing:-0.012em;
  color:var(--text);
}

.sp-section-subtitle{
  margin-top:0.12rem;
  font-size:0.90rem;
  line-height:1.46;
  color:var(--muted);
}

/* ======================================================
SURFACES
====================================================== */

.sp-surface{
  position:relative;
  overflow:visible;
  padding:18px 20px;
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

.sp-surface::before{
  content:"";
  position:absolute;
  inset:0;
  border-radius:inherit;
  pointer-events:none;
  background:linear-gradient(180deg, rgba(255,255,255,0.34), transparent 26%);
  opacity:.9;
}

.sp-surface-no-pad{
  padding:0 !important;
}

.sp-surface-muted{
  background:linear-gradient(180deg, #fcfdfd 0%, #f8faf9 100%);
}

.sp-surface-strong{
  background:linear-gradient(180deg, #ffffff 0%, #f3f8f6 100%);
}

.sp-surface-hero{
  padding:22px 24px;
  border-radius:22px;
  background:var(--hero-gradient);
  box-shadow:var(--shadow-md);
}

.sp-surface-elevated{
  box-shadow:var(--shadow-md);
}

.sp-surface-interactive{
  cursor:default;
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
}

.sp-surface-interactive:hover{
  transform:translateY(-1px);
  box-shadow:var(--shadow-md);
}

/* ======================================================
HERO
====================================================== */

.sp-hero{
  position:relative;
  overflow:hidden;
}

.sp-hero::after{
  content:"";
  position:absolute;
  top:-40px;
  right:-20px;
  width:180px;
  height:180px;
  border-radius:999px;
  background:radial-gradient(circle, rgba(53,94,87,0.10), transparent 68%);
  pointer-events:none;
}

.sp-hero-eyebrow{
  color:var(--primary);
  font-size:0.78rem;
  font-weight:780;
  text-transform:uppercase;
  letter-spacing:0.06em;
}

.sp-hero-title{
  margin-top:6px;
  color:var(--text);
  font-size:1.42rem;
  font-weight:840;
  line-height:1.08;
  letter-spacing:-0.03em;
}

.sp-hero-subtitle{
  margin-top:8px;
  max-width:72ch;
  color:var(--muted-strong);
  font-size:0.93rem;
  line-height:1.52;
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
  font-weight:680;
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
  font-weight:780;
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
  background:
    linear-gradient(180deg, #f3f7f5 0%, #edf4f0 100%);
  border-right:1px solid #d7e2dc;
}

section[data-testid="stSidebar"] .block-container{
  padding:1rem 0.88rem 0.86rem 0.88rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.18rem !important;
}

.sidebar-title{
  margin-bottom:0.32rem;
  font-size:1.02rem;
  font-weight:800;
  letter-spacing:-0.016em;
  color:var(--text);
}

.sidebar-section{
  margin-top:0.10rem;
  margin-bottom:0.40rem;
  font-size:0.76rem;
  font-weight:800;
  letter-spacing:0.05em;
  text-transform:uppercase;
  color:var(--muted);
}

.sidebar-build{
  margin-top:0.40rem;
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
    box-shadow .16s ease,
    transform .16s ease;
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]:hover{
  background:rgba(255,255,255,0.76);
  border-color:rgba(15,23,42,0.06);
  transform:translateX(1px);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"][aria-checked="true"]{
  background:linear-gradient(180deg, rgba(53,94,87,0.11) 0%, rgba(53,94,87,0.07) 100%);
  border-color:rgba(53,94,87,0.12);
  box-shadow:0 1px 2px rgba(15,23,42,0.03);
  font-weight:780;
  color:var(--text);
}

section[data-testid="stSidebar"] details{
  border:1px solid rgba(15,23,42,0.08);
  border-radius:14px;
  background:rgba(255,255,255,0.80);
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
  padding:0.56rem 0.96rem;
  border:1px solid rgba(15,23,42,0.10);
  border-radius:12px;
  background:#ffffff;
  color:var(--text);
  font-weight:690;
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
  background:var(--primary-gradient) !important;
  border:1px solid var(--primary) !important;
  color:#ffffff !important;
  box-shadow:0 10px 20px rgba(53,94,87,0.16) !important;
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
  font-weight:640 !important;
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
  font-weight:680 !important;
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
CARDS
====================================================== */

.sp-card{
  position:relative;
  overflow:hidden;
  min-height:110px;
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
  width:64px;
  height:64px;
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
  font-weight:800;
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

.sp-metric-trend{
  margin-top:10px;
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding:5px 8px;
  border-radius:999px;
  font-size:0.77rem;
  font-weight:760;
  line-height:1;
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
  padding:30px 22px;
  text-align:center;
}

.sp-empty-icon{
  margin-bottom:10px;
  font-size:1.85rem;
  line-height:1;
}

.sp-empty-title{
  color:var(--text);
  font-size:0.99rem;
  font-weight:820;
}

.sp-empty-subtitle{
  margin-top:6px;
  color:var(--muted);
  font-size:0.89rem;
  line-height:1.48;
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
  margin:0.80rem 0;
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
    padding:0.95rem !important;
  }

  .sp-page-title{
    font-size:1.46rem;
  }

  .sp-page-subtitle{
    font-size:0.91rem;
  }

  .sp-surface{
    padding:14px 15px;
    border-radius:16px;
  }

  .sp-surface-hero{
    padding:18px 16px;
    border-radius:18px;
  }

  .sp-hero-title{
    font-size:1.16rem;
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


def _escape(text: object | None) -> str:
    return html.escape("" if text is None else str(text))


def _normalize_tone(tone: str | None) -> str:
    tone_normalized = (tone or DEFAULT_TONE).strip().lower()
    return tone_normalized if tone_normalized in ALLOWED_TONES else DEFAULT_TONE


def _join_classes(*classes: str | None) -> str:
    return " ".join(part.strip() for part in classes if part and part.strip())


def _tone_class(tone: str | None) -> str:
    return f"sp-tone-{_normalize_tone(tone)}"


def _surface_classes(
    *,
    tone: str = DEFAULT_TONE,
    extra_classes: str = "",
    no_padding: bool = False,
) -> str:
    return _join_classes(
        "sp-surface",
        _tone_class(tone),
        "sp-surface-no-pad" if no_padding else "",
        extra_classes,
    )


def _render_text_block(css_class: str, text: str) -> None:
    _render_html(f"<div class='{css_class}'>{_escape(text)}</div>")


def inject_global_css() -> None:
    if st.session_state.get(_CSS_FLAG_KEY):
        return
    st.session_state[_CSS_FLAG_KEY] = True
    _render_html(_GLOBAL_CSS)


def surface_start(
    *,
    tone: str = DEFAULT_TONE,
    extra_classes: str = "",
    no_padding: bool = False,
) -> None:
    _render_html(
        f"<div class='{_surface_classes(tone=tone, extra_classes=extra_classes, no_padding=no_padding)}'>"
    )


def surface_end() -> None:
    _render_html("</div>")


@contextmanager
def surface_container(
    *,
    tone: str = DEFAULT_TONE,
    extra_classes: str = "",
    no_padding: bool = False,
) -> Iterator[None]:
    surface_start(tone=tone, extra_classes=extra_classes, no_padding=no_padding)
    try:
        yield
    finally:
        surface_end()


def surface(
    content: str,
    *,
    tone: str = DEFAULT_TONE,
    extra_classes: str = "",
    no_padding: bool = False,
) -> None:
    _render_html(
        f"<div class='{_surface_classes(tone=tone, extra_classes=extra_classes, no_padding=no_padding)}'>{content}</div>"
    )


def card(
    title: str,
    value: str,
    subtitle: str = "",
    *,
    tone: str = DEFAULT_TONE,
    emphasize: bool = False,
) -> None:
    title_html = _escape(title)
    value_html = _escape(value)
    subtitle_html = _escape(subtitle)

    value_classes = _join_classes("sp-card-value", "emph" if emphasize else "")
    subtitle_block = (
        f"<div class='sp-card-sub'>{subtitle_html}</div>" if subtitle_html else ""
    )

    _render_html(
        f"""
        <div class="sp-card {_tone_class(tone)}">
          <div class="sp-card-title">{title_html}</div>
          <div class="{value_classes}">{value_html}</div>
          {subtitle_block}
        </div>
        """
    )


def metric_card(
    title: str,
    value: str,
    subtitle: str = "",
    *,
    tone: str = DEFAULT_TONE,
    trend: str = "",
    emphasize: bool = False,
) -> None:
    title_html = _escape(title)
    value_html = _escape(value)
    subtitle_html = _escape(subtitle)
    trend_html = _escape(trend)
    value_classes = _join_classes("sp-card-value", "emph" if emphasize else "")
    subtitle_block = (
        f"<div class='sp-card-sub'>{subtitle_html}</div>" if subtitle_html else ""
    )
    trend_block = (
        f"<div class='sp-metric-trend sp-chip sp-chip-{_normalize_tone(tone)}'>{trend_html}</div>"
        if trend_html
        else ""
    )

    _render_html(
        f"""
        <div class="sp-card {_tone_class(tone)}">
          <div class="sp-card-title">{title_html}</div>
          <div class="{value_classes}">{value_html}</div>
          {subtitle_block}
          {trend_block}
        </div>
        """
    )


def hero_banner(
    title: str,
    subtitle: str = "",
    *,
    eyebrow: str = "",
    tone: str = DEFAULT_TONE,
) -> None:
    eyebrow_block = (
        f"<div class='sp-hero-eyebrow'>{_escape(eyebrow)}</div>" if eyebrow else ""
    )
    subtitle_block = (
        f"<div class='sp-hero-subtitle'>{_escape(subtitle)}</div>" if subtitle else ""
    )

    _render_html(
        f"""
        <div class="sp-surface sp-surface-hero sp-hero {_tone_class(tone)}">
          {eyebrow_block}
          <div class="sp-hero-title">{_escape(title)}</div>
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


def chip(text: str, *, tone: str = DEFAULT_TONE) -> None:
    tone_normalized = _normalize_tone(tone)
    _render_html(
        f"<span class='sp-chip sp-chip-{tone_normalized}'>{_escape(text)}</span>"
    )


def pill(text: str, *, tone: str = DEFAULT_TONE) -> None:
    tone_normalized = _normalize_tone(tone)
    _render_html(
        f"<span class='sp-pill sp-pill-{tone_normalized}'>{_escape(text)}</span>"
    )


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
    tone: str = DEFAULT_TONE,
) -> None:
    subtitle_block = (
        f"<div class='sp-status-banner-subtitle'>{_escape(subtitle)}</div>"
        if subtitle
        else ""
    )

    _render_html(
        f"""
        <div class="sp-status-banner {_tone_class(tone)}">
          <div class="sp-status-banner-title">{_escape(title)}</div>
          {subtitle_block}
        </div>
        """
    )


def caption(text: str) -> None:
    _render_text_block("sp-caption", text)


def muted(text: str) -> None:
    _render_text_block("sp-muted", text)


def app_error(
    title: str,
    message: str,
    *,
    technical_details: str | None = None,
    details_expanded: bool = False,
) -> None:
    title_html = _escape(title or "Erro")
    message_html = _escape(message)

    _render_html(
        f"""
        <div class="sp-app-error">
          <div class="sp-app-error-title">{title_html}</div>
          <div class="sp-app-error-subtitle">{message_html}</div>
        </div>
        """
    )

    if technical_details:
        with st.expander("Detalhes técnicos", expanded=details_expanded):
            st.code(technical_details, language="text")
