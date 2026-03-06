from __future__ import annotations

import html

import streamlit as st

_CSS_VERSION = "v6"
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
:root{
  --bg:#ffffff;
  --surface:#ffffff;
  --surface-soft:#f8fafc;

  --border:#e5e7eb;

  --text:#0f172a;
  --muted:#64748b;

  --primary:#334155;
  --primary-hover:#1e293b;

  --danger:#dc2626;
  --warning:#f59e0b;
  --success:#16a34a;
  --info:#2563eb;

  --radius-lg:18px;
  --radius-md:14px;

  --shadow:0 1px 2px rgba(0,0,0,0.05);
  --shadow-soft:0 4px 10px rgba(0,0,0,0.06);
  --shadow-strong:0 8px 18px rgba(0,0,0,0.10);
}

/* ======================================================
BASE
====================================================== */

.stApp{
  background:var(--bg);
  color:var(--text);
}

header[data-testid="stHeader"]{
  background:transparent;
}

.block-container{
  padding-top:1.2rem;
  padding-bottom:1.6rem;
  max-width:1400px;
  overflow:visible !important;
}

h1,h2,h3,h4{
  letter-spacing:-0.015em;
  color:var(--text);
}

.stCaption{
  color:var(--muted) !important;
}

div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.42rem;
}

/* ======================================================
SELECT / POPOVER FIX
====================================================== */

section.main{
  overflow:visible !important;
}

div[role="listbox"]{
  z-index:99999 !important;
}

div[role="listbox"] ul{
  max-height:45vh !important;
  overflow-y:auto !important;
  padding-right:6px;
}

/* ======================================================
SURFACE
====================================================== */

.sp-surface{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
  box-shadow:var(--shadow);
}

/* ======================================================
MUTED UTILS
====================================================== */

.sp-muted{
  color:var(--muted);
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
  background:rgba(15,23,42,0.04);
  border:1px solid rgba(15,23,42,0.12);
  font-size:0.82rem;
  color:rgba(15,23,42,0.85);
  white-space:nowrap;
}

/* ======================================================
SIDEBAR
====================================================== */

section[data-testid="stSidebar"]{
  background:#f1f5f9;
  border-right:1px solid var(--border);
}

section[data-testid="stSidebar"] .block-container{
  padding:0.75rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div{
  margin-bottom:0.28rem !important;
}

/* ======================================================
SIDEBAR MENU (pill)
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
  padding:8px 12px;
  border-radius:12px;
  margin-bottom:5px;
  cursor:pointer;
  border:1px solid rgba(15,23,42,0.10);
  background:rgba(255,255,255,0.78);
  font-size:0.92rem;
  transition:all .12s ease;
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"]:hover{
  background:rgba(15,23,42,0.05);
  border-color:rgba(15,23,42,0.20);
}

section[data-testid="stSidebar"]
div[role="radiogroup"]
label[data-baseweb="radio"][aria-checked="true"]{
  background:rgba(51,65,85,0.10);
  border-left:4px solid var(--primary);
  font-weight:750;
}

/* ======================================================
EXPANDERS
====================================================== */

section.main details[data-testid="stExpander"]{
  border-radius:14px;
  border:1px solid rgba(15,23,42,0.14);
  background:#ffffff;
  box-shadow:var(--shadow);
}

section.main details[data-testid="stExpander"] summary{
  padding:10px 12px;
}

/* ======================================================
TABS
====================================================== */

div[data-baseweb="tab-list"]{
  background:#ffffff;
  border:1px solid rgba(15,23,42,0.16);
  border-radius:14px;
  padding:6px;
  gap:6px;
  box-shadow:var(--shadow);
}

button[data-baseweb="tab"]{
  border-radius:12px;
  padding:9px 12px;
  font-weight:700;
  background:var(--surface-soft);
  border:1px solid rgba(15,23,42,0.12);
  color:rgba(15,23,42,0.86);
  transition:all .12s ease;
}

button[data-baseweb="tab"]:hover{
  background:#ffffff;
  border-color:rgba(15,23,42,0.22);
}

button[data-baseweb="tab"][aria-selected="true"]{
  background:var(--primary);
  border-color:var(--primary);
  color:#ffffff;
  box-shadow:var(--shadow-strong);
}

div[data-baseweb="tab-highlight"]{
  display:none !important;
}

/* ======================================================
BUTTONS
====================================================== */

.stButton > button{
  border-radius:12px;
  padding:0.6rem 1rem;
  font-weight:600;
  border:1px solid rgba(15,23,42,0.15);
  background:transparent;
  transition:all .15s ease;
}

.stButton > button:hover{
  background:rgba(15,23,42,0.05);
  border-color:rgba(15,23,42,0.25);
  transform:translateY(-1px);
}

.stButton > button[kind="primary"],
.stButton > button[class*="primary"]{
  background:var(--primary) !important;
  border:1px solid var(--primary) !important;
  color:#fff !important;
  box-shadow:var(--shadow-soft);
}

.stButton > button[kind="primary"]:hover,
.stButton > button[class*="primary"]:hover{
  background:var(--primary-hover) !important;
  border-color:var(--primary-hover) !important;
}

/* ======================================================
INPUTS
====================================================== */

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div{
  border-radius:var(--radius-md) !important;
  border-color:rgba(15,23,42,0.14) !important;
  background:#ffffff !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within{
  border-color:rgba(51,65,85,0.52) !important;
  box-shadow:0 0 0 3px rgba(51,65,85,0.12) !important;
}

/* ======================================================
DATAFRAME
====================================================== */

div[data-testid="stDataFrame"]{
  border-radius:14px;
  overflow:hidden;
  border:1px solid var(--border);
}

/* ======================================================
CARD KPI
====================================================== */

.sp-card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  padding:14px 16px;
  box-shadow:var(--shadow);
}

.sp-card-title{
  font-size:0.78rem;
  color:rgba(15,23,42,0.62);
  margin-bottom:6px;
  font-weight:720;
}

.sp-card-value{
  font-size:1.42rem;
  font-weight:840;
  color:var(--text);
}

.sp-card-value.emph{
  font-size:1.8rem;
  font-weight:900;
}

.sp-card-sub{
  color:rgba(15,23,42,0.58);
  font-size:0.82rem;
  margin-top:6px;
}

/* ======================================================
TONES
====================================================== */

.sp-tone-danger{border-left:6px solid var(--danger);padding-left:12px;}
.sp-tone-warning{border-left:6px solid var(--warning);padding-left:12px;}
.sp-tone-success{border-left:6px solid var(--success);padding-left:12px;}
.sp-tone-info{border-left:6px solid var(--info);padding-left:12px;}
.sp-tone-neutral{border-left:6px solid #cbd5e1;padding-left:12px;}

/* ======================================================
MOBILE
====================================================== */

@media (max-width:768px){
  .block-container{
    padding:1rem !important;
    max-width:100% !important;
  }

  .sp-card,
  .sp-surface{
    padding:12px;
  }

  .sp-card-value{
    font-size:1.2rem;
  }

  .sp-card-value.emph{
    font-size:1.45rem;
  }

  .stButton > button{
    min-height:44px !important;
    padding:0.75rem 1rem !important;
  }

  div[data-baseweb="input"] input,
  div[data-baseweb="textarea"] textarea{
    font-size:16px !important;
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
    st.markdown(f"#### {html.escape(text or '')}")


def subtle_divider() -> None:
    st.markdown(
        "<hr style='border:0;border-top:1px solid #e5e7eb;margin:0.8rem 0;'>",
        unsafe_allow_html=True,
    )
