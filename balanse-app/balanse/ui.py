"""Shared pieces for the Streamlit screens: data loading, the status language, number formats and styling.

The look: light and neutral, hairline rules for lists, white cards for side figures. The whole
palette is built from the navy brand colour (#0F1B2D): the sidebar, primary buttons, one highlight
card per screen, and the status colours, which are navy and slate shades. Rust is the only warm
colour and is kept for Stockout, so the one thing that needs action now stands out. Every status
is shown as a small square (hollow for No sales) plus its name, and the coverage bar uses tints of
the same colours, so one legend explains all.
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from html import escape

import streamlit as st

from . import demo_data, services
from .engine import OPTIMAL, NO_SALES, OVERSTOCK, STOCKOUT, UNDERSTOCK, fmt
from .repository import Repository, StorageError, get_repository

DECISION_NOTE = "Balanse supports your decision. It does not place orders or change stock."

STATUS_MEANING = {
    STOCKOUT: "May run out before the next delivery arrives",
    UNDERSTOCK: "Covers the delivery time, but not your buffer days",
    NO_SALES: "Nothing sold in the sales period while stock remains",
    OVERSTOCK: "More days of stock than your maximum",
    OPTIMAL: "Within your stock coverage limits",
}

# colour = the marker and tile colour; symbol = used where only text fits (tables).
# Navy palette: shades of the brand navy, with rust as the only warm colour, kept for Stockout.
# Every colour holds white text (the dashboard tiles) at 4.5:1 or better.
STATUS_STYLE = {
    STOCKOUT:   {"symbol": "▲", "color": "#B5452F", "short": "Stockout"},
    UNDERSTOCK: {"symbol": "◆", "color": "#2A3B57", "short": "Understock"},
    OPTIMAL:    {"symbol": "●", "color": "#7DBF9A", "short": "Optimal"},
    OVERSTOCK:  {"symbol": "■", "color": "#62769A", "short": "Overstock"},
    NO_SALES:   {"symbol": "○", "color": "#6B7588", "short": "No sales"},
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap');
:root { --bg:#F4F6F4; --panel:#FFFFFF; --panel2:#EEF2EF; --line:#DFE5E1; --line2:#C5CEC8; --text:#111A15; --text2:#445049;
        --muted:#68756D; --accent:#4E6283; --stockout:#B5452F; --under:#2A3B57; --optimal:#5B7A86; --over:#62769A; --none:#6B7588;
        --z1:#E0877A; --z2:#5E6F91; --z3:#7DBF9A; --z4:#5F86C9;
        --mono:'Outfit','DM Sans',system-ui,-apple-system,'Segoe UI',sans-serif;
        --proxima:'Proxima Nova','ProximaNova','Outfit','DM Sans',system-ui,-apple-system,'Segoe UI',sans-serif; }
.stApp, .stApp button, .stApp input, .stApp textarea, .stApp select, .stApp h1, [data-testid="stSidebarNav"]::before { font-family:'Outfit','DM Sans',system-ui,-apple-system,'Segoe UI',sans-serif !important; }
/* Proxima Nova is deliberately limited to the sidebar and Dashboard. The existing Outfit stack remains the app default. */
[data-testid="stSidebar"], [data-testid="stSidebar"] button, [data-testid="stSidebar"] input, [data-testid="stSidebar"] select,
[data-testid="stSidebar"] textarea, [data-testid="stSidebar"] [data-testid="stSidebarNav"]::before,
[data-testid="stAppViewContainer"]:has(h1[id="dashboard"]) [data-testid="stMain"],
[data-testid="stAppViewContainer"]:has(h1[id="dashboard"]) [data-testid="stMain"] button,
[data-testid="stAppViewContainer"]:has(h1[id="dashboard"]) [data-testid="stMain"] input,
[data-testid="stAppViewContainer"]:has(h1[id="dashboard"]) [data-testid="stMain"] select,
[data-testid="stAppViewContainer"]:has(h1[id="dashboard"]) [data-testid="stMain"] textarea {
  font-family:var(--proxima) !important;
}
.bal-mono, .fig .v, .stat .v, .bal-key .n, .kv span, .ticks, table.bal td.r, table.bal th.r { font-variant-numeric:tabular-nums; }
.block-container { max-width:1120px; padding-top:1rem; padding-bottom:3rem; }
header[data-testid="stHeader"] { background:transparent; }
[data-testid="stVerticalBlock"] { gap:.6rem; }
h1 { font-size:40px !important; font-weight:700 !important; letter-spacing:-.02em; line-height:1.15 !important; padding:0 0 .5rem !important; margin:0; color:#0F1B2D; position:relative; }
h1::after { content:""; display:block; width:150px; height:5px; margin-top:8px; background:linear-gradient(90deg,#2F6FE0,#5B7A86); }
h2, h3 { font-weight:600 !important; letter-spacing:0; }
h3 { font-size:18px !important; }
p, li, label { color:var(--text); }
a { color:var(--accent); }

/* sidebar: white, brand on top, Product Details reached by clicking a product */
[data-testid="stSidebar"] { background:#0F1B2D; border-right:0; }
/* brand and store switcher sit above the page menu */
[data-testid="stSidebarContent"] { display:flex; flex-direction:column; }
[data-testid="stSidebarUserContent"] { order:-1; padding:1.5rem 0 .9rem; }
/* the empty header row only holds the collapse button: float it into the corner so it leaves no gap above the menu */
[data-testid="stSidebarHeader"] { position:absolute; top:.45rem; right:.45rem; width:auto; height:auto; padding:0; margin:0; z-index:5; }
/* fixed sidebar width: no drag handle; the collapse button at the top right is always visible and white */
[data-testid="stSidebar"] { width:260px !important; min-width:260px !important; max-width:260px !important; }
[data-testid="stSidebarResizeHandle"], [data-testid="stSidebar"] [role="separator"] { display:none !important; }
[data-testid="stSidebarHeader"], [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapseButton"] button { display:flex !important; visibility:visible !important; opacity:1 !important; }
[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"] button *, [data-testid="stSidebarHeader"] button, [data-testid="stSidebarHeader"] button * { color:#FFFFFF !important; fill:#FFFFFF !important; stroke:#FFFFFF !important; opacity:1 !important; }
[data-testid="stSidebarCollapseButton"] svg { width:20px !important; height:20px !important; }
/* no resize cursor on the sidebar edge: the sidebar keeps a fixed width */
[data-testid="stSidebar"], [data-testid="stSidebar"] *, [role="separator"][aria-orientation="vertical"] { cursor:default !important; }
[data-testid="stSidebarNav"] { padding-top:.2rem; }
[data-testid="stSidebarNav"] { order:0; }
.bal-brand { display:flex; align-items:center; gap:10px; margin:0 0 1.3rem 0; color:#FFFFFF; font-weight:700; font-size:23px; letter-spacing:.01em; line-height:1; white-space:nowrap; }
.bal-brand .mark { width:42px; height:37px; flex:none; }
.bal-store-label { color:#8FA3C0; font-size:11px; font-weight:600; letter-spacing:.09em; text-transform:uppercase; margin:0 0 .35rem 0; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div { margin-bottom:0; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"], [data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stSidebar"] [data-testid="stTextInput"] [data-baseweb="base-input"], [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {
  background:#17273F !important; border:1px solid #2B4263 !important; border-radius:9px !important; box-shadow:none !important; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"]:hover, [data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"]:focus-within { border-color:#2F6FE0 !important; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] input, [data-testid="stSidebar"] [data-testid="stTextInput"] input { color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF; font-weight:600; }
[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder { color:#8FA3C0 !important; -webkit-text-fill-color:#8FA3C0; font-weight:400; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] button, [data-testid="stSidebar"] [data-testid="stSelectbox"] svg { color:#C9D3E0 !important; fill:#C9D3E0 !important; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] .stButton > button[kind="primary"] { background:#2F6FE0; border-color:#2F6FE0; }
.bal-store-error { color:#FFB4A6; font-size:13px; margin-top:.3rem; }
[data-testid="stSidebarNav"] a, [data-testid="stSidebarNav"] a * { color:#C9D3E0 !important; fill:#C9D3E0 !important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background:#2F6FE0 !important; border-radius:6px; }
[data-testid="stSidebarNav"] a[aria-current="page"], [data-testid="stSidebarNav"] a[aria-current="page"] * { color:#FFFFFF !important; fill:#FFFFFF !important; }
[data-testid="stSidebarNav"] span[data-testid="stSidebarNavSeparator"], [data-testid="stSidebarNav"] li div:not(:has(a)), [data-testid="stSidebarNav"] li div:not(:has(a)) * { color:#FFFFFF !important; }
[data-testid="stSidebarNav"] a[href$="/product"] { display:none; }
[data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * { color:#FFFFFF !important; fill:#FFFFFF !important; }
[data-testid="stSidebarNav"] span[data-testid="stSidebarNavSeparator"], [data-testid="stSidebarNav"] li > div[class*="Header"] { text-transform:uppercase; font-size:11px; letter-spacing:.08em; color:var(--muted); }

/* buttons and inputs */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { border-radius:5px; border:1px solid var(--line2); background:#fff; color:var(--text); font-weight:500; min-height:2.1rem; padding:.25rem .8rem; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--muted); color:var(--text); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] { background:#0F1B2D; border-color:#0F1B2D; color:#fff; }
.stButton > button[kind="primary"] *, .stFormSubmitButton > button[kind="primary"] * { color:#FFFFFF !important; }
.stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primaryFormSubmit"] p { color:#FFFFFF !important; }
.stButton > button[kind="tertiary"] { border:0; background:none; color:var(--accent); padding:0; min-height:0; justify-content:flex-end; white-space:nowrap; }
.stButton:has(> button[kind="tertiary"]) { display:flex; justify-content:flex-end; }
.stButton > button[kind="tertiary"]:hover { text-decoration:underline; }
[data-testid="stPopover"] button svg { display:none !important; }   /* the Delete store popover: no dropdown arrow */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] { border-radius:5px !important; }
[data-testid="stTabs"] [role="tab"] { font-weight:500; }
[data-testid="stExpander"] { border:0; border-top:1px solid var(--line); border-radius:0; }
[data-testid="stExpander"] summary { padding-left:0; }
.stDataFrame, [data-testid="stTable"] table { font-size:13px; }

/* demo banner and footer */
.bal-demo { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#0F1B2D; padding:6px 0; margin-bottom:.4rem; }
.bal-foot { margin-top:2rem; padding-top:.7rem; border-top:1px solid var(--line); color:var(--muted); font-size:12px; }
.bal-sub { color:#0F1B2D; font-weight:500; margin:-.2rem 0 .5rem; }

/* cards: a white panel for each block of a page, as on the dashboard. ui.card() adds a hidden
   .bal-card marker as the first child of a container; the container with that marker becomes the card. */
.stVerticalBlock:has(> .stElementContainer .bal-card) { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px 18px; gap:.6rem; margin-top:.4rem; }
.stElementContainer:has(> .stMarkdown .bal-card) { display:none; }
/* table cards: no white panel or border round a table, the table's own grid is the frame */
.stVerticalBlock.st-key-card-inventory-table, .stVerticalBlock.st-key-card-reorder-table, .stVerticalBlock.st-key-card-sales-records { background:none !important; border:0 !important; padding:0 !important; }
.stVerticalBlock:has(> .stElementContainer .bal-card) .bal-sec-line, .stVerticalBlock:has(> .stElementContainer .bal-card) .stHorizontalBlock:has(> .stElementContainer .bal-sec) { padding-top:.1rem; }
[data-testid="stForm"] { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px 18px; }
.stVerticalBlock:has(> .stElementContainer .bal-card) [data-testid="stForm"] { border:0; padding:0; }
.stVerticalBlock:has(> .stElementContainer .bal-card) .stat { border-bottom:0; padding:0; }
.stVerticalBlock:has(> .stElementContainer .bal-card) .stat p + p { margin-top:8px; }
.card .l { font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--text2); }
.card .v { font:600 28px/1.2 var(--mono); margin:6px 0 2px; font-variant-numeric:tabular-nums; }
.card p { margin:0; color:var(--text2); font-size:13px; }
.bal-note { color:var(--muted); font-size:12px; margin:.3rem 0 0; }

/* section headers: small caps, one hairline */
.bal-sec { font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--text2); white-space:nowrap; }
.bal-sec-line { padding:1rem 0 .4rem; border-bottom:1px solid var(--line); margin-bottom:.2rem; }
/* (no asterisks in this stylesheet past this point: st.markdown pairs them up as italics and breaks the rules) */
.stHorizontalBlock:has(> .stElementContainer .bal-sec) { padding:1rem 0 .4rem; border-bottom:1px solid var(--line); margin-bottom:.2rem; flex-wrap:nowrap; }
.stHorizontalBlock:has(> .stElementContainer .bal-sec) .stButton > button[kind="tertiary"] { font-size:13px; font-weight:500; }
.bal-grp { font-size:12px; font-weight:600; color:var(--text2); padding:0 0 .35rem; }
.bal-grp span { font-weight:400; color:var(--muted); margin-left:6px; }

/* dashboard: alert groups, one row = status · name · days · link */
.st-key-grp-now, .st-key-grp-soon { gap:0; margin-top:1.1rem; }
.st-key-grp-now .stHorizontalBlock, .st-key-grp-soon .stHorizontalBlock { border-bottom:1px solid var(--line); padding:9px 0; flex-wrap:nowrap; }
.st-key-grp-now .stElementContainer:last-child .stHorizontalBlock, .st-key-grp-soon .stElementContainer:last-child .stHorizontalBlock { border-bottom:0; }
.st-key-grp-now .stHorizontalBlock > .stElementContainer:first-child, .st-key-grp-soon .stHorizontalBlock > .stElementContainer:first-child { flex:1 1 auto; min-width:0; }
.st-key-grp-now .stHorizontalBlock [data-testid="stMarkdownContainer"], .st-key-grp-soon .stHorizontalBlock [data-testid="stMarkdownContainer"] { margin-bottom:0; }
.bal-row { display:grid; grid-template-columns:118px minmax(0,1fr) 108px; gap:14px; align-items:center; }
.bal-row .st { font-weight:400; color:var(--text2); font-size:14px; }
.bal-row .nm { font-weight:500; }
.bal-row .d { text-align:right; font-variant-numeric:tabular-nums; color:var(--text2); white-space:nowrap; }

/* dashboard side column: one navy highlight card, then white cards */
.st-key-hero-reorder { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px 18px 14px; gap:.5rem; }
.st-key-hero-reorder p, .st-key-hero-reorder div, .st-key-hero-reorder span { color:#000000; }
.hero .l { font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:#000000; }
.hero .v { font:600 28px/1.2 var(--mono); color:#000000; margin:6px 0 2px; font-variant-numeric:tabular-nums; }
.hero p { margin:0 0 10px; color:#000000; font-size:13px; }
.hero .it { display:flex; justify-content:space-between; gap:12px; padding:7px 0; border-top:1px solid var(--line); font-size:13px; }
.hero .it b { font-weight:500; font-variant-numeric:tabular-nums; white-space:nowrap; color:#000000; }
.hero .it .nm { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#000000; }
.hero .it.more .nm { color:#000000; }
.st-key-hero-reorder .stButton > button[kind="tertiary"], .st-key-hero-reorder .stButton > button[kind="tertiary"] p { color:#000000 !important; font-weight:500; }
.st-key-card-excess, .st-key-card-sales, .st-key-hero-reorder { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px 18px; gap:.3rem; margin-top:.4rem; }
.st-key-card-sales .stHorizontalBlock:has(> .stElementContainer .bal-sec) { padding-top:0; }
.st-key-card-excess .card p { margin-bottom:8px; }
/* dashboard collage: the two right-hand cards share the height of the sales chart card, so the edges line up */
div:has(> .st-key-card-excess) { display:flex; flex-direction:column; height:100%; }
.st-key-card-excess, .st-key-hero-reorder { flex:1 1 0; }
.card .l { font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--text2); }
.card .v { font:600 28px/1.2 var(--mono); margin:6px 0 2px; font-variant-numeric:tabular-nums; }
.card p { margin:0; color:var(--text2); font-size:13px; }

/* status: a small square plus the name (hollow for No sales), matching the square status tiles */
.st { display:inline-flex; align-items:center; gap:7px; white-space:nowrap; font-weight:500; }
.st .dot { width:9px; height:9px; border-radius:2px; background:var(--c); flex:none; }
.st.ring .dot { background:none; box-shadow:inset 0 0 0 1.5px var(--c); }

/* status key: legend, counts and meaning in one strip */
.bal-key { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin:.5rem 0 1.25rem; }
.bal-key > div { min-width:0; }
.bal-key > div { padding:12px 22px 12px 14px; border-radius:8px; background:var(--c); color:#FFFFFF; min-width:120px; }
.bal-key .n { font:600 26px/1.15 var(--mono); color:#FFFFFF; margin-bottom:4px; }
.bal-key .t { font-weight:500; color:#FFFFFF; }
.bal-key > div.empty { background:var(--panel2); }
.bal-key > div.empty .n, .bal-key > div.empty .t { color:var(--muted); }
.bal-key > div.light, .bal-key > div.light .n, .bal-key > div.light .t { color:#0F1B2D; }

/* rows in lists */
.bal-nm { font-weight:500; }
.bal-why { color:var(--text2); font-size:13px; line-height:1.4; }
.bal-act { color:var(--text2); font-size:13px; margin-top:3px; }
.bal-mono { font-family:var(--mono); font-variant-numeric:tabular-nums; white-space:nowrap; }
.bal-hr { border-bottom:1px solid var(--line); margin:.15rem 0 .35rem; }

/* coverage bar: where days of supply sits against lead time, buffer and maximum */
.gauge { position:relative; display:flex; height:8px; border-radius:4px; background:var(--panel2); min-width:90px; }
.gauge i { height:100%; display:block; }
.gauge i:first-child { border-radius:4px 0 0 4px; } .gauge i.z4 { border-radius:0 4px 4px 0; }
.z1 { background:var(--z1); } .z2 { background:var(--z2); } .z3 { background:var(--z3); } .z4 { background:var(--z4); }
.gauge b { position:absolute; top:-5px; bottom:-5px; width:4px; margin-left:-2px; border-radius:2px; background:var(--text); }
.gauge.none { background:repeating-linear-gradient(90deg,var(--line2) 0 4px,transparent 4px 8px); }
.gauge.big { height:14px; border-radius:7px; } .gauge.big b { top:-6px; bottom:-6px; width:5px; margin-left:-2.5px; }
.ticks { position:relative; height:18px; margin-top:8px; font:11px var(--mono); color:var(--muted); }
.ticks span { position:absolute; transform:translateX(-50%); }
.zones { display:flex; flex-wrap:wrap; gap:4px 18px; margin:8px 0 14px; font-size:12px; color:var(--text2); }
.zones i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }

/* figures */
.figs { display:grid; grid-template-columns:repeat(var(--n,4),minmax(0,1fr)); gap:10px; margin:.5rem 0; }
.fig { padding:14px 16px; min-width:0; background:var(--panel); border:1px solid var(--line); border-radius:10px; }
.fig .l { font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--text2); } .fig .v { font:600 20px/1.35 var(--mono); overflow-wrap:anywhere; } .fig .n2 { font-size:12px; color:var(--muted); }
.fig .v.plain { font:600 16px/2 var(--mono); }
.stat { padding:10px 0 12px; border-bottom:1px solid var(--line); }
.stat .v { font:600 22px/1.25 var(--mono); } .stat p { margin:2px 0 0; color:var(--text2); font-size:13px; }
.kv { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); margin:.4rem 0 0; }
.kv span { padding:7px 0; border-bottom:1px solid var(--line); } .kv span:nth-child(even) { text-align:right; font-family:var(--mono); } .kv span:nth-child(odd) { color:var(--text2); }

/* tables */
.bal-tablewrap { overflow-x:auto; }
[data-testid="stMarkdownContainer"] table.bal, [data-testid="stMarkdownContainer"] table.bal th, [data-testid="stMarkdownContainer"] table.bal td { border:0; }
[data-testid="stMarkdownContainer"] table.bal th { background:none; border-bottom:1px solid var(--line2); }
[data-testid="stMarkdownContainer"] table.bal td { border-bottom:1px solid var(--line); }
[data-testid="stMarkdownContainer"] table.bal tr.grp td { border-bottom:1px solid var(--line2); }
[data-testid="stMarkdownContainer"] table.bal tr:nth-child(even) td, [data-testid="stMarkdownContainer"] table.bal tr:nth-child(even) { background:none; }
table.bal { width:100%; border-collapse:collapse; font-size:14px; }
table.bal th { text-align:left; font-size:11px; font-weight:500; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); padding:9px 12px 9px 0; border-bottom:1px solid var(--line2); white-space:nowrap; }
table.bal td { padding:10px 12px 10px 0; border-bottom:1px solid var(--line); vertical-align:middle; background:none; }
table.bal th.r, table.bal td.r { text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums; }
table.bal td small { display:block; color:var(--muted); font-size:12px; }
table.bal tr.grp td { padding:18px 0 8px; border-bottom:1px solid var(--line2); }
[data-testid="stMarkdownContainer"] table.bal tr.grp td, table.bal tr.grp td, table.bal tr.grp { background:#FFFFFF !important; }
table.bal tr.grp .c { font:500 12px var(--mono); color:var(--muted); margin-left:6px; }
table.bal tr.grp .m { color:var(--muted); font-size:13px; margin-left:12px; }
table.bal tr.grp .a { float:right; color:var(--text2); font-size:13px; }
/* opt-in grid for one table (class bal-grid): a border round every cell */
table.bal.bal-grid { border:1px solid var(--line2); border-collapse:collapse; }
table.bal.bal-grid th, table.bal.bal-grid td { border:1px solid var(--line2); padding:10px 12px; }
table.bal.bal-grid th { background:var(--panel2); }
/* compact grid (Inventory): tighter cells and a shorter gauge so the grid fits without squeezing the text */
table.bal.bal-compact th, table.bal.bal-compact td { padding:8px 10px; }
table.bal.bal-compact th { font-size:10.5px; letter-spacing:.04em; }
table.bal.bal-compact td { font-size:13.5px; white-space:nowrap; }
table.bal.bal-compact td:first-child { white-space:normal; min-width:200px; }
table.bal.bal-compact tr.grp td { padding:10px 10px; white-space:normal; }
table.bal.bal-compact .dos { grid-template-columns:54px minmax(70px,1fr); gap:8px; min-width:140px; max-width:240px; }
.dos { display:grid; grid-template-columns:62px minmax(90px,1fr); gap:10px; align-items:center; min-width:170px; max-width:420px; }

/* smooth motion: short fades on anything clickable, a soft rise when a page opens. Switched off for "reduce motion". */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  transition:background-color .18s ease, border-color .18s ease, color .18s ease, box-shadow .2s ease, transform .15s ease; }
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover { transform:translateY(-1px); box-shadow:0 4px 12px rgba(15,27,45,.14); }
.stButton > button:active, .stDownloadButton > button:active, .stFormSubmitButton > button:active { transform:translateY(0) scale(.98); box-shadow:none; }
.stButton > button[kind="tertiary"]:hover { transform:none; box-shadow:none; }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover { background:#1B2D4A; border-color:#1B2D4A; }
[data-testid="stSidebarNav"] a { transition:background-color .2s ease, transform .2s ease; }
[data-testid="stSidebarNav"] a:not([aria-current="page"]):hover { background:rgba(255,255,255,.08) !important; border-radius:6px; transform:translateX(2px); }
.bal-key > div { transition:transform .2s ease, box-shadow .2s ease, filter .2s ease; }
.bal-key > div:hover { transform:translateY(-2px); box-shadow:0 8px 18px rgba(15,27,45,.18); filter:brightness(1.05); }
.st-key-card-excess, .st-key-card-sales, .st-key-hero-reorder { transition:box-shadow .22s ease, transform .22s ease, border-color .22s ease; }
.st-key-card-excess:hover, .st-key-card-sales:hover, .st-key-hero-reorder:hover { box-shadow:0 8px 22px rgba(15,27,45,.09); border-color:var(--line2); transform:translateY(-1px); }
table.bal tbody tr { transition:background-color .15s ease; }
table.bal tbody tr:not(.grp):hover td { background:#F1F5F2; }
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"], [data-baseweb="input"], [data-testid="stNumberInput"] > div > div,
[data-testid="stTextInput"] > div > div { transition:border-color .18s ease, box-shadow .2s ease, background-color .18s ease; }
[data-testid="stExpander"] summary, [data-testid="stCheckbox"] label, [data-testid="stTabs"] [role="tab"] { transition:color .18s ease, background-color .18s ease; }
/* collapsed sidebar: give its space back to the page so the content re-centres, and show the re-open button as a tab on the screen edge */
[data-testid="stSidebar"][data-collapsed="true"] { width:0 !important; min-width:0 !important; max-width:0 !important; margin:0 !important; }
/* slide the sidebar and the page together, both when it closes and when it opens (width has to be animated too, or opening snaps) */
[data-testid="stSidebar"] { overflow:hidden; transition:width .32s cubic-bezier(.4,0,.2,1), min-width .32s cubic-bezier(.4,0,.2,1), max-width .32s cubic-bezier(.4,0,.2,1), transform .32s cubic-bezier(.4,0,.2,1) !important; }
[data-testid="stSidebarContent"] { min-width:250px; }
[data-testid="stExpandSidebarButton"] { position:fixed !important; left:0 !important; top:1.15rem !important; z-index:1000; width:30px; height:46px; margin:0 !important; padding:0;
  display:flex; align-items:center; justify-content:center; background:#0F1B2D; border-radius:0 12px 12px 0; box-shadow:3px 3px 12px rgba(15,27,45,.28);
  transition:width .18s ease, background-color .18s ease; }
[data-testid="stExpandSidebarButton"]:hover { width:38px; background:#2F6FE0; }
[data-testid="stExpandSidebarButton"], [data-testid="stExpandSidebarButton"] * { color:#FFFFFF !important; fill:#FFFFFF !important; }
@keyframes balRise { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
[data-testid="stMain"] .block-container > [data-testid="stVerticalBlock"] > * { animation:balRise .35s ease both; }
/* "reduce motion": switch off only OUR effects. Never touch Streamlit's own sidebar, whose slide needs its transition to finish. */
@media (prefers-reduced-motion: reduce) {
  .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stSidebarNav"] a, .bal-key > div,
  .st-key-card-excess, .st-key-card-sales, .st-key-hero-reorder, table.bal tbody tr, [data-testid="stSelectbox"] [role="group"],
  [data-testid="stMultiSelect"] [role="group"], [data-baseweb="input"], [data-testid="stNumberInput"] > div > div, [data-testid="stTextInput"] > div > div,
  [data-testid="stExpander"] summary, [data-testid="stCheckbox"] label, [data-testid="stTabs"] [role="tab"] { transition:none !important; transform:none !important; }
  [data-testid="stMain"] .block-container > [data-testid="stVerticalBlock"] > * { animation:none !important; }
}

@media (max-width:760px) { .figs { grid-template-columns:repeat(2,minmax(0,1fr)); } }
</style>
"""


# ---------------------------------------------------------------- data
@st.cache_resource(show_spinner=False)
def _repo_resource() -> Repository:
    return get_repository()


# ---------------------------------------------------------------- stores
NEW_STORE = -1


def stores() -> list[dict]:
    """All stores, kept for the session. Call stores_changed() after adding, renaming or deleting one."""
    if "_stores" not in st.session_state:
        st.session_state["_stores"] = _repo_resource().list_stores()
    return st.session_state["_stores"]


def stores_changed() -> None:
    st.session_state.pop("_stores", None)


def current_store() -> dict:
    by_id = {s["id"]: s for s in stores()}
    chosen = st.session_state.get("store_id")
    if chosen not in by_id:
        last = _repo_resource().store_id
        chosen = last if last in by_id else next(iter(by_id))
        st.session_state["store_id"] = chosen
    return by_id[chosen]


def repo() -> Repository:
    """The storage, pointed at the store chosen in the sidebar."""
    resource, store = _repo_resource(), current_store()
    if resource.store_id != store["id"]:
        resource.use_store(store["id"])
    return resource


repo.clear = _repo_resource.clear      # app.py calls ui.repo.clear() on "Try again"


def switch_store(store_id: int) -> None:
    st.session_state["store_id"] = store_id
    st.session_state.pop("product_id", None)
    changed()


def _on_store_pick() -> None:
    pick = st.session_state.get("store_pick")
    if pick is not None and pick != NEW_STORE:
        switch_store(pick)


def _on_create_store() -> None:
    name = st.session_state.get("new_store_name", "")
    try:
        made = _repo_resource().create_store(name)
    except StorageError as problem:
        st.session_state["_store_error"] = str(problem)
        return
    stores_changed()
    st.session_state["new_store_name"] = ""
    st.session_state.pop("_store_error", None)
    switch_store(made["id"])
    st.session_state["store_pick"] = made["id"]
    flash(f"Store '{made['name']}' created. It is empty, so add products or import a CSV file in Data Input.")


BRAND_SVG = ('<svg class="mark" viewBox="0 0 64 56" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
             '<g fill="none" stroke="#D9D4C5" stroke-width="2.4" stroke-linecap="round">'
             '<path d="M6 14H58"/><path d="M32 8V50"/><path d="M18 51H46"/>'
             '<path d="M6 14L2 33M6 14L22 33M58 14L42 33M58 14L62 33"/><path d="M2 33Q12 45 22 33M42 33Q52 45 62 33"/></g>'
             '<g fill="#7FB2F5" stroke="#2F6FE0" stroke-width="1.6"><rect x="4" y="24" width="8" height="8" rx="1.6"/>'
             '<rect x="13" y="24" width="8" height="8" rx="1.6"/><rect x="43" y="24" width="8" height="8" rx="1.6"/>'
             '<rect x="52" y="24" width="8" height="8" rx="1.6"/></g><circle cx="32" cy="8" r="5" fill="#2F6FE0"/></svg>')


def sidebar() -> None:
    """Brand and store switcher at the top of the sidebar (the page menu is placed under them by CSS)."""
    st.markdown(CSS, unsafe_allow_html=True)
    here = current_store()
    names = {s["id"]: s["name"] for s in stores()}
    options = [*names, NEW_STORE]
    if st.session_state.get("store_pick") not in options:
        st.session_state["store_pick"] = here["id"]
    with st.sidebar:
        st.markdown(f'<div class="bal-brand">{BRAND_SVG}<span>BALANSE</span></div>'
                    '<div class="bal-store-label">Store</div>', unsafe_allow_html=True)
        picked = st.selectbox("Store", options, key="store_pick", on_change=_on_store_pick, label_visibility="collapsed",
                              format_func=lambda i: "+  Add a store" if i == NEW_STORE else names[i])
        if picked == NEW_STORE:
            st.text_input("New store name", key="new_store_name", placeholder="e.g. Branch 2", max_chars=60, label_visibility="collapsed")
            st.button("Create store", key="create-store", type="primary", use_container_width=True, on_click=_on_create_store)
            if st.session_state.get("_store_error"):
                st.markdown(f'<div class="bal-store-error">{escape(st.session_state["_store_error"])}</div>', unsafe_allow_html=True)


def load() -> dict:
    """All saved data plus the analysis. Kept for the session and recalculated after every change."""
    if "data" not in st.session_state:
        with st.spinner("Calculating…"):
            st.session_state["data"] = services.load_everything(repo())
    return st.session_state["data"]


def changed() -> None:
    """Call after saving anything, so every screen recalculates."""
    st.session_state.pop("data", None)


def flash(message: str, kind: str = "success") -> None:
    st.session_state.setdefault("_flash", []).append((kind, message))


def show_flashes() -> None:
    for kind, message in st.session_state.pop("_flash", []):
        getattr(st, kind)(message)


def go(page_key: str, product_id=None) -> None:
    if product_id is not None:
        st.session_state["product_id"] = product_id
    pages = st.session_state.get("_pages", {})
    if page_key in pages:
        st.switch_page(pages[page_key])


# ---------------------------------------------------------------- formats
def currency() -> str:
    return os.environ.get("CURRENCY_SYMBOL", "₱")


def money(value) -> str:
    return "n/a" if value is None else f"{currency()}{value:,.2f}"


def peso0(value) -> str:
    return "n/a" if value is None else f"{currency()}{value:,.0f}"


def units(value) -> str:
    return fmt(value)


def days(value) -> str:
    return "Cannot be calculated" if value is None else f"{fmt(value)} days"


def status_text(status: str) -> str:
    """Plain status name. The coloured square comes from status_option_css, since a dropdown can only hold text."""
    return status


def status_option_css(statuses: list, label: str) -> None:
    """Put the legend's coloured square (hollow for No sales) in front of each option of a status dropdown.
    statuses is the exact option list given to the widget; options are matched by their position."""
    rules = ""
    for i, s in enumerate(statuses):
        c = STATUS_STYLE[s]["color"]
        fill = f"box-shadow:inset 0 0 0 1.5px {c};" if s == NO_SALES else f"background:{c};"
        rules += (f'[role="listbox"][aria-label="{label}"] [role="option"][data-key="{i}"] [data-item-hl]::before{{content:"";display:inline-block;width:9px;height:9px;'
                  f'border-radius:2px;margin-right:9px;vertical-align:baseline;{fill}}}')
    st.markdown(f"<style>{rules}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------- the status language
def status_html(status: str, short: bool = False) -> str:
    style = STATUS_STYLE[status]
    ring = " ring" if status == NO_SALES else ""
    return f'<span class="st{ring}" style="--c:{style["color"]}"><span class="dot"></span>{escape(style["short"] if short else status)}</span>'


def why_text(r: dict, s) -> str:
    """One short line saying why, with the numbers. The full wording is on Product Details."""
    lead, dos, status = r["lead_time_days"], r["days_of_supply"], r["status"]
    if status == STOCKOUT and r["current_stock"] <= 0:
        return f"Out of stock. Delivery takes {lead} days."
    if status == STOCKOUT:
        return f"Lasts about {fmt(dos)} days. Delivery takes {lead}. About {fmt(lead - dos)} days short."
    if status == UNDERSTOCK:
        return f"Lasts about {fmt(dos)} days. Covers the {lead}-day delivery, but not the {s.buffer_days}-day buffer."
    if status == OVERSTOCK:
        return f"Lasts about {fmt(dos)} days. Your maximum is {s.max_days_of_supply}. About {fmt(r['excess_units'])} units above it."
    if status == NO_SALES:
        return f"No sales in the last {s.sales_period_days} days. {fmt(r['current_stock'])} units in stock."
    return f"Lasts about {fmt(dos)} days. Within {lead + s.buffer_days} to {s.max_days_of_supply} days."


def gauge_html(lead: int, buffer_days: int, max_days: int, dos, status: str | None, big: bool = False, zones_only: bool = False) -> str:
    """The coverage bar. Zones: before delivery arrives, inside buffer days, optimal range, above maximum."""
    size = " big" if big else ""
    if dos is None and not zones_only:
        return f'<div class="gauge none{size}" title="No sales rate, so days of supply cannot be calculated"></div>'
    scale = max_days * 1.5

    def pc(x):
        return max(0.0, min(100.0, x / scale * 100))
    a, b, c = pc(lead), pc(lead + buffer_days), pc(max_days)
    marker = f'<b style="left:{pc(dos):.1f}%"></b>' if status and dos is not None else ""
    return (f'<div class="gauge{size}" title="{"" if dos is None else fmt(dos)} days of supply"><i class="z1" style="width:{a:.1f}%"></i>'
            f'<i class="z2" style="width:{b - a:.1f}%"></i><i class="z3" style="width:{c - b:.1f}%"></i>'
            f'<i class="z4" style="width:{100 - c:.1f}%"></i>{marker}</div>')


def result_gauge(r: dict, s, big: bool = False) -> str:
    return gauge_html(r["lead_time_days"], s.buffer_days, s.max_days_of_supply, r["days_of_supply"], r["status"], big)


def ticks_html(lead: int, buffer_days: int, max_days: int) -> str:
    scale = max_days * 1.5
    pc = lambda x: min(100.0, x / scale * 100)   # noqa: E731
    return (f'<div class="ticks"><span style="left:0;transform:none">0</span><span style="left:{pc(lead):.1f}%">{lead}</span>'
            f'<span style="left:{pc(lead + buffer_days):.1f}%">{lead + buffer_days}</span><span style="left:{pc(max_days):.1f}%">{max_days} days</span></div>')


def zone_legend() -> str:
    return ('<div class="zones"><span><i class="z1"></i>Before delivery arrives</span><span><i class="z2"></i>Inside buffer days</span>'
            '<span><i class="z3"></i>Optimal range</span><span><i class="z4"></i>Above maximum</span></div>')


def key_strip(results: list) -> str:
    """The five statuses with their counts, in one strip. It is the legend for the whole app."""
    counts = {s: sum(1 for r in results if r["status"] == s) for s in STATUS_STYLE}
    order = [STOCKOUT, UNDERSTOCK, NO_SALES, OPTIMAL, OVERSTOCK]
    # Each tile is filled with its status colour; the colour is the indicator, so no dot.
    # A status with no products goes neutral, so an empty "0 Stockout" tile does not shout.
    def tile(s: str) -> str:
        empty = "empty" if counts[s] == 0 else ""
        light = "light" if s == OPTIMAL else ""   # pale tile: dark text, so it stays readable
        return (f'<div class="{empty} {light}" style="--c:{STATUS_STYLE[s]["color"]}" title="{escape(STATUS_MEANING[s])}">'
                f'<div class="n">{counts[s]}</div><div class="t">{escape(s)}</div></div>')
    return '<div class="bal-key">' + "".join(tile(s) for s in order) + '</div>'


def figs(items: list[tuple]) -> str:
    """Figures in one strip of small cards. items: (label, value_html, small_note)."""
    return f'<div class="figs" style="--n:{len(items)}">' + "".join(
        f'<div class="fig"><div class="l">{label}</div><div class="v{" plain" if value.startswith("<span class=\"st") else ""}">{value}</div>' + (f'<div class="n2">{escape(note)}</div>' if note else "") + '</div>'
        for label, value, note in items) + '</div>'


def section(title: str, link: tuple | None = None) -> None:
    """Small-caps section header with an optional link-style button flush right, on one baseline."""
    if link:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center", gap="small", key=f"sechead-{slug}"):
            st.markdown(f'<div class="bal-sec">{escape(title)}</div>', unsafe_allow_html=True, width="content")
            if st.button(f"{link[0]} ›", key=f"sec-{slug}-{link[1]}", type="tertiary", width="content"):
                go(link[1])
    else:
        st.markdown(f'<div class="bal-sec bal-sec-line">{escape(title)}</div>', unsafe_allow_html=True)


@contextmanager
def card(key: str, title: str | None = None, link: tuple | None = None):
    """A white card around one block of a page, as on the dashboard. Optional section header inside."""
    with st.container(key=f"card-{key}") as box:
        st.markdown('<div class="bal-card"></div>', unsafe_allow_html=True)
        if title:
            section(title, link)
        yield box


BAR_SOFT = "#A9B6C9"     # bars that are context
BAR_NAVY = "#0F1B2D"     # the bar or line that matters (the latest day, stock on hand)


def soft_bars(count: int) -> list:
    """Bar colours for a time series: every day soft, the latest day in navy, as on the dashboard chart."""
    return [BAR_SOFT] * max(count - 1, 0) + [BAR_NAVY] * min(count, 1)


def chart_style(figure, height: int, **extra) -> None:
    """The dashboard chart look: no background, light grid, few ticks, short dates."""
    figure.update_layout(height=height, bargap=.3, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(size=11, color="#68756D"), **extra)
    figure.update_xaxes(showgrid=False, tickformat="%b %d")
    figure.update_yaxes(gridcolor="#E8ECE9", zeroline=False, nticks=5)


def review_row(r: dict, s, key: str, *, buttons: bool = True) -> None:
    """One product in a list: status, name and reason, coverage bar, days, and a Details button."""
    columns = st.columns([1.7, 3.3, 1.9, .9, 1.25], vertical_alignment="center", gap="small")
    columns[0].markdown(status_html(r["status"], True), unsafe_allow_html=True)
    columns[1].markdown(f'<div class="bal-nm">{escape(r["name"])}</div><div class="bal-why">{escape(why_text(r, s))}</div><div class="bal-act">Suggested: {escape(r["suggested_action"])}</div>', unsafe_allow_html=True)
    columns[2].markdown(result_gauge(r, s), unsafe_allow_html=True)
    columns[3].markdown(f'<span class="bal-mono">{"n/a" if r["days_of_supply"] is None else fmt(r["days_of_supply"]) + " d"}</span>', unsafe_allow_html=True)
    if buttons and columns[4].button("Details", key=key):
        go("product_details", r["product_id"])
    st.markdown('<div class="bal-hr"></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- page furniture
def page_header(title: str | None, caption: str = "", actions: list | None = None) -> dict:
    """Styles, demo banner, title and pending messages. Returns the loaded data.
    actions: [(label, page_key, primary)] shown as buttons on the right of the title."""
    st.markdown(CSS, unsafe_allow_html=True)
    data = load()
    label = current_store()["name"]
    if services.has_demo_data(data["products"]):
        label += f" {demo_data.LABEL}"
    st.markdown(f'<div class="bal-demo">{escape(label)}</div>', unsafe_allow_html=True)
    if title:
        if actions:
            columns = st.columns([5] + [1.4] * len(actions), vertical_alignment="center")
            columns[0].title(title)
            for column, (label, page, primary) in zip(columns[1:], actions):
                if column.button(label, key=f"act-{page}-{label}", type="primary" if primary else "secondary", use_container_width=True):
                    go(page)
        else:
            st.title(title)
    if caption:
        st.markdown(f'<div class="bal-sub">{escape(caption)}</div>', unsafe_allow_html=True)
    show_flashes()
    return data


def decision_note() -> None:
    st.markdown(f'<div class="bal-foot">{DECISION_NOTE}</div>', unsafe_allow_html=True)


def empty_state() -> None:
    st.info("No products yet. Go to **Data Input** to add a product, import a CSV file, or load the demonstration data.")
    if st.button("Open Data Input", type="primary"):
        go("data_input")
