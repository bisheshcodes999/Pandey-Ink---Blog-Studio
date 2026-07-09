"""Design tokens and global CSS for the app.

One stylesheet, injected once per page load via inject(). Every other
ui module builds on the classes defined here (.bwa-*) instead of
hand-rolling inline styles, so the look stays consistent everywhere.
"""
from __future__ import annotations

import streamlit as st

# ------------------------------------------------------------------
# Design tokens (kept in one place so spacing/color stay consistent)
# ------------------------------------------------------------------
COLOR_ACCENT = "#2563EB"       # single blue accent, used everywhere
COLOR_ACCENT_SOFT = "#EFF6FF"
COLOR_SUCCESS = "#059669"
COLOR_SUCCESS_SOFT = "#ECFDF5"
COLOR_WARNING = "#D97706"
COLOR_WARNING_SOFT = "#FFFBEB"
COLOR_DANGER = "#DC2626"
COLOR_DANGER_SOFT = "#FEF2F2"

RADIUS_SM = "10px"
RADIUS_MD = "16px"
RADIUS_LG = "22px"

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Poppins:wght@600;700;800&display=swap');

:root {
    --bwa-bg: #F5F8FE;
    --bwa-surface: #ECF2FC;
    --bwa-surface-2: #E3EBFA;
    --bwa-sidebar-bg: #E1E9FB;
    --bwa-border: #DCE5F5;
    --bwa-border-soft: #E7EDFA;
    --bwa-text: #0F172A;
    --bwa-text-muted: #64748B;
    --bwa-text-faint: #94A3B8;
    --bwa-accent: #2563EB;
    --bwa-accent-hover: #1D4ED8;
    --bwa-accent-soft: #EFF6FF;
    --bwa-accent-border: rgba(37, 99, 235, 0.22);
    --bwa-success: #059669;
    --bwa-success-soft: #ECFDF5;
    --bwa-success-border: rgba(5, 150, 105, 0.22);
    --bwa-warning: #D97706;
    --bwa-warning-soft: #FFFBEB;
    --bwa-warning-border: rgba(217, 119, 6, 0.22);
    --bwa-danger: #DC2626;
    --bwa-danger-soft: #FEF2F2;
    --bwa-radius-sm: 10px;
    --bwa-radius-md: 16px;
    --bwa-radius-lg: 22px;
    --bwa-label-blue: #3355D6;
    --bwa-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
    --bwa-shadow-md: 0 1px 3px rgba(15, 23, 42, 0.06), 0 4px 12px rgba(15, 23, 42, 0.04);
}

/* ---------------------------------------------------------------
   Base -- forced with !important because a user/global Streamlit
   config (~/.streamlit/config.toml) can set a dark theme that would
   otherwise bleed through on the native chrome (header, toolbar,
   input internals) that this stylesheet doesn't directly own. The
   project also ships its own .streamlit/config.toml with a light
   theme, so this is belt-and-suspenders.
--------------------------------------------------------------- */
html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: var(--bwa-bg) !important;
}
header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"] {
    background: var(--bwa-bg) !important;
    color: var(--bwa-text) !important;
}
/* IMPORTANT: this must NOT match Streamlit's own icon spans (the
   sidebar collapse arrow, the status-widget chevron, etc). Those are
   rendered as literal text like "keyboard_double_arrow_left" that a
   ligature icon font turns into a glyph -- forcing Inter onto them
   makes the raw ligature name show up as overlapping text instead of
   an icon. `:not()` here is what keeps this safe. */
.stApp :not([data-testid*="Icon"]):not([class*="material"]),
h1, h2, h3, h4, h5, .stMarkdown, .stCaption {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.stApp, .stApp p, .stApp li, .stApp label,
h1, h2, h3, h4, h5, .stMarkdown, .stCaption {
    color: var(--bwa-text);
}
/* Explicitly protect every known Streamlit icon-font element so no
   later rule in this file can accidentally re-target it either. */
[data-testid*="Icon"], [class*="material-symbols"], [class*="material-icons"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
}

/* Tighten Streamlit's default vertical rhythm so spacing feels designed,
   not auto-generated. */
.block-container {
    padding-top: 2.25rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}
div[data-testid="stVerticalBlock"] > div { gap: 0.75rem; }

/* ---------------------------------------------------------------
   Sidebar
--------------------------------------------------------------- */
section[data-testid="stSidebar"] {
    background: var(--bwa-sidebar-bg);
    border-right: 1px solid var(--bwa-border);
    /* anchor point for repositioning the native collapse button below */
    position: relative;
}
/* Streamlit's own collapse ("<<") toggle lives in this header row at
   the very top of the sidebar by default, which is what pushed the
   brand lockup down. Pulling it out of normal flow and pinning it to
   the vertical middle of the panel instead means the brand can sit
   right at the top, with the toggle still reachable lower down.
   `left: 100%` + `translate(-50%, -50%)` centers it exactly ON the
   sidebar's right border line (half in, half out) instead of floating
   inside the panel body - the familiar "edge handle" look.
   NOTE: stSidebarHeader is Streamlit's own test id for this row - if a
   future Streamlit version renames it, this rule just stops matching
   and the toggle reverts to its default top-of-sidebar spot. */
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
    position: absolute;
    top: 50%;
    left: 100%;
    transform: translate(-50%, -50%);
    height: auto;
    min-height: 0;
    padding: 0;
    z-index: 20;
}
/* The toggle button itself -- round, sitting on the edge, with a
   little hover pop so it reads as interactive rather than a static
   fixture of the layout. */
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button {
    border-radius: 999px !important;
    background: #FFFFFF !important;
    border: 1px solid var(--bwa-border) !important;
    box-shadow: var(--bwa-shadow-sm);
    transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease;
}
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button:hover {
    background: var(--bwa-accent-soft) !important;
    border-color: var(--bwa-accent) !important;
    box-shadow: var(--bwa-shadow-md);
    transform: scale(1.15);
}
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button:active {
    transform: scale(0.95);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 2.25rem !important;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
}
section[data-testid="stSidebar"] hr {
    margin: 0.9rem 0;
    border-color: var(--bwa-border);
}

/* ---------------------------------------------------------------
   Inputs -- explicit background/text colors (not just border-radius)
   so a dark global Streamlit theme can't leave these looking like
   black boxes with white text.
--------------------------------------------------------------- */
.stTextArea textarea, .stTextInput input, .stDateInput input,
div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
    background: #FFFFFF !important;
    color: var(--bwa-text) !important;
    border-radius: var(--bwa-radius-sm) !important;
    border-color: var(--bwa-border) !important;
    font-size: 0.9rem !important;
}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {
    color: var(--bwa-text-faint) !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--bwa-accent) !important;
    box-shadow: 0 0 0 3px var(--bwa-accent-soft) !important;
}
/* Length/Tone (and any other) select boxes -- color shift on hover so
   they feel clickable/interactive, not just static boxes. */
div[data-baseweb="select"] > div:hover {
    border-color: var(--bwa-accent) !important;
    background: var(--bwa-accent-soft) !important;
    cursor: pointer;
}
/* Disabled inputs -- keep them legible instead of falling back to a
   washed-out/dark disabled style. */
div[data-baseweb="select"][aria-disabled="true"] > div,
.stTextInput input:disabled, .stDateInput input:disabled {
    background: var(--bwa-surface) !important;
    color: var(--bwa-text-muted) !important;
    opacity: 1 !important;
}
/* Select dropdown menus render in a portal, outside .stApp, so they
   need their own explicit light styling. */
div[data-baseweb="popover"] div[data-baseweb="menu"],
ul[data-baseweb="menu"] {
    background: #FFFFFF !important;
    border: 1px solid var(--bwa-border) !important;
    border-radius: var(--bwa-radius-sm) !important;
}
li[role="option"] {
    background: #FFFFFF !important;
    color: var(--bwa-text) !important;
    font-size: 0.88rem !important;
}
li[role="option"]:hover, li[aria-selected="true"] {
    background: var(--bwa-accent-soft) !important;
    color: var(--bwa-accent) !important;
}
label[data-testid="stWidgetLabel"] p {
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    color: var(--bwa-label-blue) !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ---------------------------------------------------------------
   Buttons -- one primary style, everything else plain/secondary.
   No icons: kept intentionally text-only (see ui/sidebar.py) since
   Streamlit's Material icon font depends on a web font that may not
   load in a fully offline/local environment, and falls back to
   showing its raw ligature name as text instead of a glyph.
--------------------------------------------------------------- */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
    border-radius: var(--bwa-radius-sm);
    font-family: 'Poppins', 'Inter', sans-serif;
    font-weight: 700;
    font-size: 0.88rem;
    padding: 0.5rem 1rem;
    transition: all 120ms ease;
    border: 1px solid var(--bwa-border);
}
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
    background: #4E85F4;
    border-color: #4E85F4;
    box-shadow: var(--bwa-shadow-sm);
}
.stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {
    background: var(--bwa-accent);
    border-color: var(--bwa-accent);
}
.stButton button[kind="secondary"], .stDownloadButton button {
    background: var(--bwa-accent-soft);
    color: var(--bwa-accent);
    border-color: var(--bwa-accent-border);
}
.stButton button[kind="secondary"]:hover, .stDownloadButton button:hover {
    border-color: var(--bwa-accent);
    color: #FFFFFF;
    background: var(--bwa-accent);
    box-shadow: var(--bwa-shadow-sm);
}
/* Topic-idea chip buttons ("Photosynthesis", etc.) -- italic so they
   read as example prompts to click, not regular commands. */
.st-key-bwa_topic_chips .stButton button {
    font-style: italic;
}

/* ---------------------------------------------------------------
   Tabs
--------------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.25rem;
    border-bottom: 1px solid var(--bwa-border);
}
.stTabs [data-baseweb="tab"] {
    height: auto;
    padding: 0.55rem 0.9rem;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--bwa-text-muted);
}
.stTabs [aria-selected="true"] {
    color: var(--bwa-accent) !important;
}
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--bwa-accent); }

/* ---------------------------------------------------------------
   Status / expander widgets
--------------------------------------------------------------- */
div[data-testid="stStatusWidget"], div[data-testid="stExpander"] {
    border: 1px solid var(--bwa-border) !important;
    border-radius: var(--bwa-radius-md) !important;
    box-shadow: var(--bwa-shadow-sm);
}

/* ---------------------------------------------------------------
   Metrics
--------------------------------------------------------------- */
div[data-testid="stMetric"] {
    background: var(--bwa-surface);
    border: 1px solid var(--bwa-border);
    border-radius: var(--bwa-radius-md);
    padding: 0.85rem 1rem 0.7rem 1rem;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--bwa-text-muted) !important;
}
div[data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
    color: var(--bwa-text) !important;
}

/* ---------------------------------------------------------------
   Dataframes
--------------------------------------------------------------- */
div[data-testid="stDataFrame"] {
    border: 1px solid var(--bwa-border);
    border-radius: var(--bwa-radius-md);
    overflow: hidden;
}

/* =================================================================
   Reusable component classes
================================================================= */

/* ---- App header ---- */
.bwa-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    padding: 0 0 1.25rem 0;
    border-bottom: 1px solid var(--bwa-border);
    margin-bottom: 1.4rem;
}
.bwa-header-left { display: flex; flex-direction: column; gap: 0.35rem; }
.bwa-header h1 {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 0;
    color: var(--bwa-text);
    line-height: 1.2;
}
/* "PandeyInk" in the page title -- the brand name reads as an accent,
   the "- Blog Studio" part stays the default heading color. */
.bwa-title-accent { color: var(--bwa-accent); }
.bwa-header p {
    color: var(--bwa-text-muted);
    font-size: 0.92rem;
    margin: 0;
    max-width: 46rem;
}
.bwa-header-badges { display: flex; gap: 0.4rem; flex-wrap: wrap; }

/* ---- Sidebar brand lockup ---- */
.bwa-brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    /* margin, not just the sidebar's own padding-top, so there's a
       guaranteed gap above the logo even if something upstream (a
       Streamlit version bump, another rule) changes the container's
       padding again later. */
    margin-top: 0.9rem;
    margin-bottom: 1.2rem;
}
.bwa-brand-mark {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: linear-gradient(135deg, var(--bwa-accent), #60A5FA);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
    box-shadow: var(--bwa-shadow-sm);
}
.bwa-brand-mark svg { width: 18px; height: 18px; }
.bwa-brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.bwa-brand-title { font-weight: 700; font-size: 1.18rem; color: var(--bwa-text); }
.bwa-brand-sub { font-size: 0.85rem; color: var(--bwa-text); }

/* ---- Sidebar section labels ---- */
.bwa-section-label {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--bwa-label-blue);
    margin: 0.1rem 0 0.5rem 0;
}
.bwa-section-label svg { width: 13px; height: 13px; }

/* ---- "Need an idea?" prompt -- a bit more fun/modern than a plain
   gray caption, since it's an invitation to click, not a status line. */
.bwa-idea-prompt {
    display: inline-block;
    font-size: 0.86rem;
    font-weight: 600;
    font-style: italic;
    letter-spacing: 0.01em;
    background: linear-gradient(135deg, var(--bwa-accent), #60A5FA);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin: 0 0 0.5rem 0;
}

/* ---- Pills / badges ---- */
.bwa-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.28rem 0.7rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 600;
    background: var(--bwa-accent-soft);
    color: var(--bwa-accent);
    border: 1px solid var(--bwa-accent-border);
    margin: 0 0.35rem 0.35rem 0;
}
.bwa-pill svg { width: 12px; height: 12px; }
.bwa-pill.muted { background: var(--bwa-surface); color: var(--bwa-text-muted); border-color: var(--bwa-border); }
.bwa-pill.success { background: var(--bwa-success-soft); color: var(--bwa-success); border-color: var(--bwa-success-border); }
.bwa-pill.mono { font-family: 'JetBrains Mono', monospace; font-weight: 500; }

/* ---- Generic card ---- */
.bwa-card {
    border: 1px solid var(--bwa-accent-border);
    border-radius: var(--bwa-radius-md);
    padding: 1.1rem 1.2rem;
    background: #FFFFFF;
    box-shadow: var(--bwa-shadow-sm);
    margin-bottom: 0.9rem;
}
.bwa-card-flat {
    border: 1px solid var(--bwa-border-soft);
    border-radius: var(--bwa-radius-md);
    padding: 1rem 1.1rem;
    background: var(--bwa-surface);
    margin-bottom: 0.75rem;
}
.bwa-card-title {
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--bwa-accent);
    margin: 0 0 0.3rem 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.bwa-card-title svg { width: 15px; height: 15px; color: var(--bwa-accent); }

/* "Your thinking, drafted." motto card -- scoped to this one card
   (via its container key) rather than bumping every card title in
   the app, since this is the one spot meant to read as a tagline,
   not a section label. */
.st-key-bwa_new_blog_card .bwa-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    font-style: italic;
}

/* "Revise a draft" card title (main page) -- a bit bigger than the
   default card title so it reads as its own starting action, same
   scoped-container approach as the motto card above. */
.st-key-bwa_revise_card .bwa-card-title {
    font-size: 1.15rem;
}

/* ---- Empty states ---- */
.bwa-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 0.6rem;
    padding: 2.5rem 1.5rem;
    color: var(--bwa-text-muted);
    border: 1px dashed var(--bwa-border);
    border-radius: var(--bwa-radius-lg);
    background: var(--bwa-surface);
}
.bwa-empty-icon {
    width: 44px;
    height: 44px;
    border-radius: 999px;
    background: var(--bwa-accent-soft);
    color: var(--bwa-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.2rem;
}
.bwa-empty-icon svg { width: 20px; height: 20px; }
.bwa-empty-title { font-weight: 700; font-size: 1rem; color: var(--bwa-text); }
.bwa-empty-desc { font-size: 0.88rem; max-width: 30rem; line-height: 1.5; }
.bwa-empty.small { padding: 1.5rem 1rem; border-radius: var(--bwa-radius-md); }
.bwa-empty.small .bwa-empty-icon { width: 34px; height: 34px; }
.bwa-empty.small .bwa-empty-icon svg { width: 16px; height: 16px; }

/* ---- Pipeline step tracker ---- */
.bwa-step-track {
    display: flex;
    align-items: stretch;
    gap: 0.5rem;
    margin: 0.25rem 0 0.25rem 0;
    flex-wrap: wrap;
}
.bwa-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.85rem;
    border-radius: var(--bwa-radius-sm);
    border: 1px solid var(--bwa-border);
    background: #FFFFFF;
    font-size: 0.83rem;
    font-weight: 500;
    color: var(--bwa-text-faint);
}
.bwa-step .bwa-step-icon {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.bwa-step .bwa-step-icon svg { width: 14px; height: 14px; }
.bwa-step.pending { color: var(--bwa-text-faint); border-style: dashed; }
.bwa-step.active {
    color: var(--bwa-accent);
    border-color: var(--bwa-accent-border);
    background: var(--bwa-accent-soft);
}
.bwa-step.active .bwa-step-icon svg { animation: bwa-spin 0.9s linear infinite; }
.bwa-step.done { color: var(--bwa-success); border-color: var(--bwa-success-border); background: var(--bwa-success-soft); }
.bwa-step.skipped { color: var(--bwa-text-faint); background: var(--bwa-surface); border-style: dashed; }
.bwa-step .t { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; opacity: 0.85; margin-left: 0.1rem; }
@keyframes bwa-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ---- Article viewer ---- */
.bwa-article-shell {
    border: 1px solid var(--bwa-border);
    border-radius: var(--bwa-radius-lg);
    background: #FFFFFF;
    box-shadow: var(--bwa-shadow-md);
    padding: 2.75rem clamp(1.5rem, 6vw, 4.5rem);
    margin-bottom: 1rem;
}
.bwa-article {
    max-width: 720px;
    margin: 0 auto;
    color: var(--bwa-text);
    font-size: 1.02rem;
    line-height: 1.75;
}
.bwa-article h1 {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.2;
    margin: 0 0 1.4rem 0;
}
.bwa-article h2 {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 2.2rem 0 0.9rem 0;
    padding-top: 0.2rem;
}
.bwa-article h3 {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 1.8rem 0 0.7rem 0;
}
.bwa-article h4 { font-size: 1rem; font-weight: 700; margin: 1.4rem 0 0.5rem 0; }
.bwa-article p { margin: 0 0 1.1rem 0; }
.bwa-article ul, .bwa-article ol { margin: 0 0 1.1rem 0; padding-left: 1.4rem; }
.bwa-article li { margin: 0.35rem 0; }
.bwa-article li::marker { color: var(--bwa-accent); }
.bwa-article a { color: var(--bwa-accent); text-decoration: underline; text-decoration-color: var(--bwa-accent-border); text-underline-offset: 2px; }
.bwa-article a:hover { color: var(--bwa-accent-hover); }
.bwa-article strong { font-weight: 700; }
.bwa-article hr { border: none; border-top: 1px solid var(--bwa-border); margin: 2rem 0; }

.bwa-article blockquote {
    margin: 1.3rem 0;
    padding: 0.9rem 1.2rem;
    border-left: 3px solid var(--bwa-accent);
    background: var(--bwa-accent-soft);
    border-radius: 0 var(--bwa-radius-sm) var(--bwa-radius-sm) 0;
    color: var(--bwa-text);
    font-style: italic;
}
.bwa-article blockquote p { margin: 0.3rem 0; }
.bwa-article blockquote p:first-child { margin-top: 0; }
.bwa-article blockquote p:last-child { margin-bottom: 0; }

.bwa-article code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.86em;
    background: var(--bwa-surface-2);
    border: 1px solid var(--bwa-border);
    padding: 0.12em 0.4em;
    border-radius: 5px;
    color: #BE185D;
}
.bwa-article pre {
    background: #0F172A;
    color: #E2E8F0;
    border-radius: var(--bwa-radius-md);
    padding: 1.1rem 1.25rem;
    overflow-x: auto;
    margin: 1.3rem 0;
    box-shadow: var(--bwa-shadow-sm);
}
.bwa-article pre code {
    background: transparent;
    border: none;
    color: inherit;
    padding: 0;
    font-size: 0.86rem;
    line-height: 1.6;
}

.bwa-article img {
    max-width: 100%;
    border-radius: var(--bwa-radius-md);
    border: 1px solid var(--bwa-border);
    box-shadow: var(--bwa-shadow-sm);
    display: block;
    margin: 0.4rem auto 0.35rem auto;
}
.bwa-article p > em:only-child {
    display: block;
    text-align: center;
    font-style: normal;
    font-size: 0.82rem;
    color: var(--bwa-text-muted);
    margin: -0.5rem 0 1.3rem 0;
}

.bwa-article table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.3rem 0;
    font-size: 0.92rem;
}
.bwa-article th, .bwa-article td {
    border: 1px solid var(--bwa-border);
    padding: 0.5rem 0.75rem;
    text-align: left;
}
.bwa-article th { background: var(--bwa-surface); font-weight: 700; }

/* ---- Inline citation markers + References list (evidence-driven) ---- */
.bwa-article sup.bwa-cite {
    font-size: 0.72em;
    font-weight: 700;
    color: var(--bwa-accent);
    margin-left: 0.1em;
}
.bwa-references {
    margin-top: 2.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--bwa-border);
}
.bwa-references h2 {
    font-size: 1.05rem;
    font-weight: 700;
    margin: 0 0 0.9rem 0;
}
.bwa-references ol {
    padding-left: 1.3rem;
    margin: 0;
}
.bwa-references li {
    font-size: 0.86rem;
    color: var(--bwa-text-muted);
    margin: 0.4rem 0;
}
.bwa-references a {
    color: var(--bwa-accent);
    text-decoration: none;
}
.bwa-references a:hover { text-decoration: underline; }
.bwa-references .bwa-ref-meta { color: var(--bwa-text-faint); }

/* ---- Image-generation-failed callout (frontend-detected, styled) ---- */
.bwa-callout-warning {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
    margin: 1.3rem 0;
    padding: 1rem 1.15rem;
    border: 1px solid var(--bwa-warning-border);
    background: var(--bwa-warning-soft);
    border-radius: var(--bwa-radius-md);
}
.bwa-callout-warning .bwa-callout-icon { color: var(--bwa-warning); flex-shrink: 0; margin-top: 0.15rem; }
.bwa-callout-warning .bwa-callout-icon svg { width: 18px; height: 18px; }
.bwa-callout-warning .bwa-callout-title { font-weight: 700; font-size: 0.9rem; color: var(--bwa-text); margin-bottom: 0.2rem; }
.bwa-callout-warning .bwa-callout-body { font-size: 0.85rem; color: var(--bwa-text-muted); line-height: 1.55; }
.bwa-callout-warning details { margin-top: 0.4rem; }
.bwa-callout-warning summary { cursor: pointer; font-size: 0.78rem; color: var(--bwa-warning); font-weight: 600; }
.bwa-callout-warning pre.bwa-callout-pre {
    background: #FFFFFF;
    border: 1px solid var(--bwa-warning-border);
    border-radius: 6px;
    padding: 0.5rem 0.65rem;
    font-size: 0.76rem;
    margin-top: 0.4rem;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--bwa-text-muted);
}

/* ---- Saved posts list ---- */
.bwa-saved-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.55rem 0.7rem;
    border-radius: var(--bwa-radius-sm);
    border: 1px solid var(--bwa-border-soft);
    background: #FFFFFF;
    margin-bottom: 0.4rem;
}
.bwa-saved-title { font-size: 0.84rem; font-weight: 600; color: var(--bwa-text); }
.bwa-saved-meta {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.72rem;
    color: var(--bwa-text-faint);
}
.bwa-saved-meta svg { width: 13px; height: 13px; flex-shrink: 0; }

/* ---- Responsiveness ---- */
@media (max-width: 700px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    .bwa-article-shell { padding: 1.75rem 1.1rem; }
    .bwa-header { flex-direction: column; align-items: flex-start; }
}
</style>
"""


def inject() -> None:
    """Injects the shared stylesheet. Call once, near the top of the page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
