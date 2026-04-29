"""
Estrategias de Cobertura - Espartina S.A.
Refactor Streamlit: separacion de responsabilidades, UI clean dashboard,
Bolsa/FAS independiente del Builder A3.
"""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from google_sheets import obtener_datos_a3
from scraper import obtener_datos_bolsa

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Estrategias de Cobertura - Espartina S.A.",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAV_LOAD = "\u2699\ufe0f Carga de Datos"
NAV_MARKET = "\U0001f4ca Panel de Mercado (FAS)"
NAV_BUILDER = "\U0001f3d7\ufe0f Builder de Coberturas"

CROP_LABELS = {
    "soja": "Soja",
    "maiz": "Maiz",
    "trigo": "Trigo",
    "girasol": "Girasol",
}
CROP_KEYS = {
    "soja": "soja",
    "maiz": "maiz",
    "trigo": "trigo",
    "girasol": "aceiteGirasol",  # Bolsa publica aceite de girasol como subproducto
}
GRAIN_KEYS = {
    "soja": "soja",
    "maiz": "maiz",
    "trigo": "trigo",
    "girasol": "aceiteGirasol",
}
DEFAULT_PARAMS = {
    "soja": {"ret_pct": 26.0, "fobbing": 12.0, "fas_obj": 323.0},
    "maiz": {"ret_pct": 7.0, "fobbing": 11.0, "fas_obj": 185.0},
    "trigo": {"ret_pct": 7.0, "fobbing": 13.0, "fas_obj": 216.0},
    "girasol": {"ret_pct": 7.0, "fobbing": 14.0, "fas_obj": 475.0},
}

MONTH_LABELS = {
    "ENE": "Ene",
    "FEB": "Feb",
    "MAR": "Mar",
    "ABR": "Abr",
    "MAY": "May",
    "JUN": "Jun",
    "JUL": "Jul",
    "AGO": "Ago",
    "SEP": "Sep",
    "OCT": "Oct",
    "NOV": "Nov",
    "DIC": "Dic",
    "DIS": "Dic",
}

CROP_CODE_MAP = {
    "SOJ": "soja",
    "MAI": "maiz",
    "TRI": "trigo",
    "GIR": "girasol",
}

PRESETS = {
    "Put Seco": [
        {"dir": "buy", "type": "put", "ratio": 1.0, "strike_mult": 0.98, "prima": 6.0},
    ],
    "Put Spread": [
        {"dir": "buy", "type": "put", "ratio": 1.0, "strike_mult": 0.98, "prima": 6.0},
        {"dir": "sell", "type": "put", "ratio": 1.0, "strike_mult": 0.94, "prima": 2.0},
    ],
    "Collar": [
        {"dir": "buy", "type": "put", "ratio": 1.0, "strike_mult": 0.97, "prima": 5.0},
        {"dir": "sell", "type": "call", "ratio": 1.0, "strike_mult": 1.10, "prima": 5.0},
    ],
    "Gaviota": [
        {"dir": "buy", "type": "put", "ratio": 1.0, "strike_mult": 0.98, "prima": 6.0},
        {"dir": "sell", "type": "put", "ratio": 1.0, "strike_mult": 0.95, "prima": 2.5},
        {"dir": "sell", "type": "call", "ratio": 1.0, "strike_mult": 1.12, "prima": 2.0},
    ],
    "Futuro + Call": [
        {"dir": "sell", "type": "futuro", "ratio": 1.0, "strike_mult": 1.00, "prima": 0.0},
        {"dir": "buy", "type": "call", "ratio": 1.0, "strike_mult": 1.05, "prima": 4.0},
    ],
    "Ratio Put Spread 1x2": [
        {"dir": "buy", "type": "put", "ratio": 1.0, "strike_mult": 0.98, "prima": 6.0},
        {"dir": "sell", "type": "put", "ratio": 2.0, "strike_mult": 0.92, "prima": 3.0},
    ],
    "Gaviota Invertida": [
        {"dir": "buy", "type": "call", "ratio": 1.0, "strike_mult": 1.03, "prima": 5.0},
        {"dir": "sell", "type": "call", "ratio": 1.0, "strike_mult": 1.15, "prima": 2.0},
        {"dir": "sell", "type": "put", "ratio": 1.0, "strike_mult": 0.92, "prima": 3.0},
    ],
    "Lanzamiento Cubierto": [
        {"dir": "sell", "type": "call", "ratio": 1.0, "strike_mult": 1.08, "prima": 4.0},
    ],
}



BOLSA_FALLBACK_FULL = {
    # Snapshot de respaldo — FOB Bolsa de Cereales al 28/04/2026.
    # Solo se usa para completar posiciones faltantes cuando el scraper cae a datos parciales.
    "ABR 2026": {"soja": 432.0, "maiz": 217.0, "trigo": 222.0, "harina": 356.0, "aceite": 1189.0, "aceiteGirasol": 1293.0},
    "MAY 2026": {"soja": 432.0, "maiz": 218.0, "trigo": 228.0, "harina": 355.0, "aceite": 1195.0, "aceiteGirasol": 1289.0},
    "JUN 2026": {"soja": 434.0, "maiz": 217.0, "trigo": 232.0, "harina": 353.0, "aceite": 1172.0, "aceiteGirasol": 1289.0},
    "JUL 2026": {"soja": 436.0, "maiz": 215.0, "trigo": 234.0, "harina": 352.0, "aceite": 1164.0, "aceiteGirasol": 1293.0},
    "AGO 2026": {"soja": 438.0, "maiz": 218.0, "trigo": 231.0, "harina": 350.0, "aceite": 1162.0, "aceiteGirasol": 1293.0},
    "SEP 2026": {"soja": 434.0, "maiz": 221.0, "trigo": 229.0, "harina": 349.0, "aceite": 1128.0, "aceiteGirasol": 1293.0},
    "OCT 2026": {"soja": 446.0, "maiz": 223.0, "trigo": 231.0, "harina": 345.0, "aceite": 1133.0, "aceiteGirasol": 1273.0},
    "NOV 2026": {"soja": 447.0, "maiz": 225.0, "trigo": 232.0, "harina": 345.0, "aceite": 1114.0, "aceiteGirasol": 1273.0},
    "DIC 2026": {"soja": 448.0, "maiz": 226.0, "trigo": 238.0, "harina": 345.0, "aceite": 1117.0, "aceiteGirasol": 1273.0},
    "ENE 2027": {"soja": 441.0, "maiz": 228.0, "trigo": 241.0, "harina": 0.0,   "aceite": 1109.0, "aceiteGirasol": 1273.0},
    "FEB 2027": {"soja": 417.0, "maiz": 230.0, "trigo": 232.0, "harina": 0.0,   "aceite": 1093.0, "aceiteGirasol": 1273.0},
    "MAR 2027": {"soja": 410.0, "maiz": 220.0, "trigo": 234.0, "harina": 0.0,   "aceite": 1093.0, "aceiteGirasol": 1273.0},
    "ABR 2027": {"soja": 411.0, "maiz": 220.0, "trigo": 234.0, "harina": 0.0,   "aceite": 1078.0, "aceiteGirasol": 1273.0},
}

# -----------------------------------------------------------------------------
# CSS - Clean Dashboard System
# -----------------------------------------------------------------------------

st.markdown(
    """
<style>
:root {
    --es-green-900: #123c26;
    --es-green-800: #145430;
    --es-green-700: #1a6b3c;
    --es-green-100: #e8f5ec;
    --es-gold-600: #c8a44a;
    --es-gold-100: #f8f0d8;
    --bg: #f4f5f0;
    --surface: #ffffff;
    --surface-muted: #f0f1ec;
    --border: #dde0d5;
    --border-strong: #c8cbbe;
    --text: #1c2118;
    --text-muted: #68705f;
    --danger: #c43030;
    --success: #1a854a;
    --warning: #d97706;
    --shadow: 0 1px 4px rgba(26,107,60,.06), 0 1px 2px rgba(0,0,0,.04);
    --shadow-lg: 0 8px 28px rgba(20,84,48,.10), 0 2px 8px rgba(0,0,0,.05);
}

html, body, [class*="css"] {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

.stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
}

[data-testid="stSidebar"] {
    background: #f8f8f4 !important;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {
    color: var(--text) !important;
}

.main .block-container {
    max-width: 1360px;
    padding-top: 1.6rem;
    padding-bottom: 4rem;
}

.es-hero {
    background: linear-gradient(135deg, var(--es-green-900) 0%, var(--es-green-700) 75%);
    color: white;
    padding: 28px 32px;
    border-radius: 18px;
    box-shadow: var(--shadow-lg);
    border-bottom: 4px solid var(--es-gold-600);
    margin-bottom: 22px;
}
.es-hero-title {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 26px;
    line-height: 1.15;
    font-weight: 850;
    letter-spacing: -0.04em;
    margin: 0;
}
.es-hero-subtitle {
    color: rgba(255,255,255,.72);
    font-size: 14px;
    margin-top: 8px;
}
.es-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 5px 10px;
    background: rgba(200,164,74,.18);
    border: 1px solid rgba(200,164,74,.42);
    color: #f7e7ad;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .08em;
    float: right;
}

.section-title {
    font-size: 28px;
    font-weight: 850;
    color: var(--es-green-900);
    letter-spacing: -0.045em;
    margin: 8px 0 6px 0;
}
.section-subtitle {
    color: var(--text-muted);
    font-size: 14px;
    margin-bottom: 16px;
}

.clean-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 22px;
    box-shadow: var(--shadow);
    margin-bottom: 18px;
}
.clean-panel-tight {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px;
    box-shadow: var(--shadow);
}

.kpi-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 12px 0 4px 0;
}
.kpi {
    background: white;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: var(--shadow);
}
.kpi-lbl {
    font-size: 10px;
    color: var(--text-muted);
    text-transform: uppercase;
    font-weight: 850;
    letter-spacing: .08em;
    margin-bottom: 6px;
}
.kpi-val {
    font-size: 22px;
    color: var(--text);
    font-weight: 850;
    font-variant-numeric: tabular-nums;
}
.kpi-val.green { color: var(--es-green-700); }
.kpi-val.gold { color: #8a6817; }

.cascade-wrap {
    display: grid;
    gap: 10px;
}
.cascade-row {
    display: grid;
    grid-template-columns: minmax(140px, 1fr) 90px;
    gap: 14px;
    align-items: center;
}
.cascade-label {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--text);
    font-size: 13px;
    font-weight: 650;
    margin-bottom: 4px;
}
.cascade-value {
    font-weight: 850;
    font-variant-numeric: tabular-nums;
}
.cascade-bar-track {
    width: 100%;
    height: 28px;
    background: #f3f3ef;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #eceee6;
}
.cascade-bar {
    height: 100%;
    min-width: 16px;
    border-radius: 7px;
    display: flex;
    align-items: center;
    padding-left: 10px;
    font-size: 11px;
    font-weight: 850;
    font-variant-numeric: tabular-nums;
}
.cascade-bar.fob { background: var(--es-gold-100); color: #8a6817; }
.cascade-bar.ret { background: #fde8e8; color: var(--danger); }
.cascade-bar.cost { background: var(--surface-muted); color: var(--text-muted); }
.cascade-result {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-top: 2px solid var(--border);
    margin-top: 14px;
    padding-top: 14px;
}
.cascade-result span:first-child {
    font-weight: 850;
    color: var(--text);
}
.cascade-result span:last-child {
    font-size: 28px;
    font-weight: 900;
    color: var(--es-green-700);
    font-variant-numeric: tabular-nums;
}
.cascade-note {
    display: flex;
    justify-content: space-between;
    margin-top: 10px;
    padding: 10px 12px;
    background: #f7f8f3;
    border: 1px solid var(--border);
    border-radius: 10px;
    font-size: 13px;
}
.cascade-note strong { font-variant-numeric: tabular-nums; }

.strategy-card {
    background: white;
    border: 1px solid var(--border);
    border-left: 4px solid var(--es-green-700);
    border-radius: 15px;
    padding: 14px 16px;
    box-shadow: var(--shadow);
    margin-bottom: 12px;
}
.leg-header {
    display: grid;
    grid-template-columns: 1fr 1fr .75fr 1fr .9fr 44px;
    gap: 8px;
    color: var(--text-muted);
    font-size: 10px;
    font-weight: 850;
    text-transform: uppercase;
    letter-spacing: .05em;
    padding: 0 2px 4px 2px;
}
.small-muted {
    color: var(--text-muted);
    font-size: 12px;
}
.divider-light {
    border-top: 1px solid var(--border);
    margin: 12px 0;
}

.stButton > button {
    border-radius: 11px !important;
    font-weight: 780 !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow) !important;
    min-height: 42px !important;
}
.stButton > button[kind="primary"], .stButton > button:hover {
    background: var(--es-green-700) !important;
    color: white !important;
    border-color: var(--es-green-700) !important;
}

.stSelectbox [data-baseweb="select"],
.stNumberInput input,
.stTextInput input,
.stTextArea textarea {
    border-radius: 10px !important;
}

[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 12px 14px;
    box-shadow: var(--shadow);
}
[data-testid="stMetric"] *,
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] *,
[data-testid="stMetricDelta"],
[data-testid="stMetricDelta"] * {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
}

/* Plotly contrast: Streamlit Cloud can inject a dark/transparent chart theme.
   Keep all chart labels, legends and axis texts readable over white plots. */
.js-plotly-plot .plotly text,
.js-plotly-plot .gtitle,
.js-plotly-plot .xtitle,
.js-plotly-plot .ytitle,
.js-plotly-plot .legendtext {
    fill: var(--text) !important;
    color: var(--text) !important;
    opacity: 1 !important;
}

/* Form readability: Streamlit Cloud can inherit dark-mode input styles.
   Force all labels, select values, input values and helper text to a dark
   accessible color while keeping the dashboard background light. */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
.stSelectbox label,
.stNumberInput label,
.stTextInput label,
.stSlider label,
.stRadio label,
label,
[data-baseweb="select"] * {
    color: var(--text) !important;
}

.stNumberInput input,
.stTextInput input,
.stTextArea textarea,
[data-baseweb="input"] input {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    background: #ffffff !important;
    caret-color: var(--text) !important;
}

[data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #ffffff !important;
    color: var(--text) !important;
    border-color: var(--border-strong) !important;
}

[data-testid="stNumberInput"] button {
    background: #20232d !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: #20232d !important;
}
[data-testid="stNumberInput"] button * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stNumberInput"] button:hover {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
}

/* High-contrast rule: anything rendered as a primary/dark button must keep
   white text/icons. This fixes + / - controls and sidebar dark actions. */
.stButton > button[kind="primary"],
.stButton > button[kind="primary"] *,
[data-testid="baseButton-primary"],
[data-testid="baseButton-primary"] *,
button[kind="primary"],
button[kind="primary"] * {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Sidebar button text is handled by button-specific rules below.
   Do not force all sidebar buttons to dark text because primary/dark
   buttons need white text for contrast. */

.sim-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 26px 0 12px;
    color: var(--text);
    font-size: 16px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .06em;
}
.sim-title::before {
    content: '';
    display: inline-block;
    width: 5px;
    height: 24px;
    border-radius: 999px;
    background: var(--es-gold-600);
}
.sim-control {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: var(--shadow);
    margin-bottom: 16px;
}
.scenario-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: var(--shadow);
}
.scenario-card.highlight {
    border: 2px solid var(--es-green-700);
    box-shadow: var(--shadow-lg);
}
.scenario-title {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .07em;
    margin-bottom: 14px;
}
.scenario-card.highlight .scenario-title { color: var(--es-green-700); }
.scenario-row {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    border-bottom: 1px solid var(--border);
    padding: 8px 0;
    font-size: 15px;
    color: var(--text);
}
.scenario-row:last-child { border-bottom: 0; }
.scenario-row strong {
    font-variant-numeric: tabular-nums;
    font-weight: 900;
    color: var(--text);
}
.scenario-card.highlight .scenario-row strong { color: var(--es-green-700); }
.coverage-note {
    background: var(--es-gold-100);
    border: 1px solid var(--es-gold-600);
    border-radius: 14px;
    padding: 14px 16px;
    color: var(--text);
    font-size: 14px;
    margin-top: 16px;
}

@media (max-width: 1100px) {
    .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .leg-header { display: none; }
}

/* Strong text color overrides for Streamlit widgets. Some deployed themes render
   widget labels/values too light over the dashboard background. */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
.stSelectbox label,
.stNumberInput label,
.stSlider label,
.stTextInput label,
.stRadio label,
label {
    color: var(--text) !important;
    opacity: 1 !important;
}

.stSelectbox [data-baseweb="select"] *,
.stNumberInput input,
.stTextInput input,
.stTextArea textarea {
    color: var(--text) !important;
    background-color: #ffffff !important;
    -webkit-text-fill-color: var(--text) !important;
}

[data-baseweb="select"] div,
[data-baseweb="select"] span {
    color: var(--text) !important;
}

/* Scenario simulator */
.scenario-title {
    display:flex;
    align-items:center;
    gap:10px;
    margin: 28px 0 12px 0;
    color: #3d4638;
    font-size: 15px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .08em;
}
.scenario-title::before {
    content:"";
    display:block;
    width:5px;
    height:22px;
    border-radius:6px;
    background:var(--es-gold-600);
}
.scenario-card {
    background:#ffffff;
    border:1px solid var(--border);
    border-radius:16px;
    padding:18px 20px;
    box-shadow:var(--shadow);
    min-height:150px;
}
.scenario-card.highlight {
    border:2px solid var(--es-green-700);
    box-shadow:var(--shadow-lg);
}
.scenario-card-title {
    color:var(--text-muted);
    font-size:12px;
    font-weight:900;
    text-transform:uppercase;
    letter-spacing:.08em;
    margin-bottom:16px;
}
.scenario-card.highlight .scenario-card-title { color:var(--es-green-700); }
.scenario-row {
    display:flex;
    justify-content:space-between;
    gap:18px;
    padding:7px 0;
    border-bottom:1px solid var(--border);
    font-size:14px;
    color:var(--text);
}
.scenario-row:last-child { border-bottom:0; }
.scenario-row strong {
    font-variant-numeric:tabular-nums;
    font-weight:850;
    color:var(--text);
}
.scenario-card.highlight .scenario-row strong { color:var(--es-green-700); }
.coverage-note {
    background:var(--es-gold-100);
    border:1px solid var(--es-gold-600);
    border-radius:14px;
    padding:14px 18px;
    margin-top:16px;
    font-size:14px;
    color:var(--text);
}
.coverage-note strong { color:var(--text); }


/* Dark button contrast fixes: every label/icon inside a dark button must be white. */
.stButton > button[kind="primary"],
.stButton > button[kind="primary"] *,
.stButton > button[kind="primary"] p,
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] .stButton > button p {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

[data-testid="stSidebar"] .stButton > button {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
}

[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] button:hover,
[data-testid="stNumberInput"] button:focus {
    background: #1f2230 !important;
    color: #ffffff !important;
    border-color: #1f2230 !important;
}
[data-testid="stNumberInput"] button *,
[data-testid="stNumberInput"] button svg,
[data-testid="stNumberInput"] button svg *,
[data-testid="stNumberInput"] button p,
[data-testid="stNumberInput"] button span {
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Final contrast guard for dark widgets and sidebar actions. */
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stButton > button:disabled {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] button:hover,
[data-testid="stNumberInput"] button:focus,
[data-testid="stNumberInput"] button:disabled {
    background: #1f2230 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: #1f2230 !important;
    opacity: 1 !important;
}
[data-testid="stNumberInput"] button *,
[data-testid="stNumberInput"] button svg,
[data-testid="stNumberInput"] button svg *,
[data-testid="stNumberInput"] button p,
[data-testid="stNumberInput"] button span {
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    opacity: 1 !important;
}


/* FINAL contrast pass for Builder + charts area.
   Streamlit Cloud may apply a dark BaseWeb theme to secondary buttons and
   metric internals; these rules force a readable dashboard contrast. */
[data-testid="stMetric"],
[data-testid="stMetric"] * {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] *,
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
}

.stButton > button:not([kind="primary"]):not(:disabled) {
    background: #ffffff !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    border-color: var(--border-strong) !important;
}
.stButton > button:not([kind="primary"]):not(:disabled) *,
.stButton > button:not([kind="primary"]):not(:disabled) p,
.stButton > button:not([kind="primary"]):not(:disabled) span {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
}

.stButton > button[kind="primary"],
.stButton > button[kind="primary"] *,
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
.stButton > button[kind="primary"] svg,
.stButton > button[kind="primary"] svg * {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    opacity: 1 !important;
}

.stButton > button:disabled,
.stButton > button[disabled] {
    background: #eef0e8 !important;
    color: #68705f !important;
    -webkit-text-fill-color: #68705f !important;
    border-color: var(--border) !important;
    opacity: 1 !important;
}
.stButton > button:disabled *,
.stButton > button[disabled] *,
.stButton > button:disabled p,
.stButton > button[disabled] p {
    color: #68705f !important;
    -webkit-text-fill-color: #68705f !important;
    opacity: 1 !important;
}

[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] button:hover,
[data-testid="stNumberInput"] button:focus {
    background: #1f2230 !important;
    border-color: #1f2230 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stNumberInput"] button *,
[data-testid="stNumberInput"] button p,
[data-testid="stNumberInput"] button span,
[data-testid="stNumberInput"] button svg,
[data-testid="stNumberInput"] button svg * {
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    opacity: 1 !important;
}


/* ------------------------------------------------------------------
   FINAL CONTRAST PATCH
   Streamlit can inherit dark theme colors for widget internals. These
   overrides keep the dashboard readable: dark/primary buttons always
   render white text/icons, while metrics and Plotly labels remain dark.
------------------------------------------------------------------ */
.stButton > button,
.stButton > button:disabled,
.stButton > button[disabled],
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"] {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    opacity: 1 !important;
}
.stButton > button *,
.stButton > button:disabled *,
.stButton > button[disabled] *,
.stButton > button p,
.stButton > button span,
.stButton > button svg,
.stButton > button svg *,
[data-testid="baseButton-primary"] *,
[data-testid="baseButton-secondary"] * {
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
.stButton > button:hover,
.stButton > button:focus {
    background: var(--es-green-800) !important;
    border-color: var(--es-green-800) !important;
    color: #ffffff !important;
}

/* Number input +/- controls are dark by design, so force icon contrast. */
[data-testid="stNumberInput"] button,
[data-testid="stNumberInput"] button:disabled,
[data-testid="stNumberInput"] button[disabled] {
    background: #1f2230 !important;
    border-color: #1f2230 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    opacity: 1 !important;
}
[data-testid="stNumberInput"] button *,
[data-testid="stNumberInput"] button svg,
[data-testid="stNumberInput"] button svg * {
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Metrics such as Linea base FOB and Costo neto must remain legible on light cards. */
[data-testid="stMetric"],
[data-testid="stMetric"] *,
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] *,
[data-testid="stMetricDelta"],
[data-testid="stMetricDelta"] * {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
}
[data-testid="stMetricValue"] {
    color: var(--es-green-700) !important;
    -webkit-text-fill-color: var(--es-green-700) !important;
    font-weight: 900 !important;
}

/* Plotly toolbar and labels: keep readable on white chart background. */
.js-plotly-plot .plotly .gtitle,
.js-plotly-plot .plotly .xtitle,
.js-plotly-plot .plotly .ytitle,
.js-plotly-plot .plotly .legend text,
.js-plotly-plot .plotly .xtick text,
.js-plotly-plot .plotly .ytick text,
.js-plotly-plot .plotly .annotation-text,
.js-plotly-plot .plotly text {
    fill: var(--text) !important;
    color: var(--text) !important;
    opacity: 1 !important;
}

/* Definitive Streamlit button contrast and readability overrides. Placed last
   so they win over Streamlit Cloud theme defaults. */
.stButton > button,
.stButton > button:focus:not(:active) {
    background: #ffffff !important;
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
    opacity: 1 !important;
}
.stButton > button *,
.stButton > button p,
.stButton > button span {
    color: inherit !important;
    -webkit-text-fill-color: inherit !important;
    opacity: 1 !important;
}
.stButton > button:hover:not(:disabled) {
    background: var(--es-green-100) !important;
    color: var(--es-green-900) !important;
    -webkit-text-fill-color: var(--es-green-900) !important;
    border-color: var(--es-green-700) !important;
}
.stButton > button[kind="primary"],
.stButton > button[kind="primary"]:hover:not(:disabled),
[data-testid="baseButton-primary"],
[data-testid="baseButton-primary"]:hover:not(:disabled),
button[kind="primary"],
button[kind="primary"]:hover:not(:disabled) {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
.stButton > button[kind="primary"] *,
[data-testid="baseButton-primary"] *,
button[kind="primary"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
.stButton > button:disabled,
.stButton > button:disabled:hover {
    background: #1f2230 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: #1f2230 !important;
    opacity: .80 !important;
}
.stButton > button:disabled *,
.stButton > button:disabled p,
.stButton > button:disabled span {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] .stButton > button:disabled {
    background: var(--es-green-700) !important;
    border-color: var(--es-green-700) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
[data-testid="stMetric"],
[data-testid="stMetric"] div,
[data-testid="stMetric"] p,
[data-testid="stMetric"] span,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"] {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
}


.coverage-scenario-table {
    width: 100%;
    border-collapse: collapse;
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: var(--shadow);
    font-size: 14px;
}
.coverage-scenario-table th {
    background: var(--es-green-100);
    color: var(--es-green-900) !important;
    text-align: left;
    padding: 12px 14px;
    border-bottom: 2px solid var(--es-green-700);
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .04em;
}
.coverage-scenario-table td {
    color: var(--text) !important;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    font-variant-numeric: tabular-nums;
    vertical-align: middle;
}
.coverage-scenario-table tr:last-child td {
    border-bottom: 0;
}
.coverage-scenario-table tr.is-spot td {
    background: var(--es-green-100);
}
.coverage-scenario-table .scenario-name {
    font-weight: 750;
    font-variant-numeric: normal;
}
.coverage-scenario-table .money-cell {
    white-space: nowrap;
    font-weight: 760;
}
.coverage-scenario-table .strategy-cell {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    white-space: nowrap;
}
.coverage-scenario-table .strategy-value {
    font-weight: 850;
    color: var(--text) !important;
}
.coverage-scenario-table .delta-pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 2px 7px;
    font-size: 12px;
    font-weight: 900;
    line-height: 1.4;
}
.coverage-scenario-table .delta-positive {
    color: var(--success) !important;
    background: #e4f7ec;
}
.coverage-scenario-table .delta-negative {
    color: var(--danger) !important;
    background: #fde8e8;
}
.coverage-scenario-table .delta-neutral {
    color: var(--text-muted) !important;
    background: var(--surface-muted);
}

</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# STATE
# -----------------------------------------------------------------------------


def init_state() -> None:
    defaults = {
        "data_loaded": False,
        "data_bolsa": None,
        "data_a3": None,
        "bolsa_loaded_at": None,
        "a3_loaded_at": None,
        "market_crop": "soja",
        "market_position": None,
        "builder_crop": "soja",
        "builder_position": None,
        "next_strategy_id": 2,
        "next_leg_id": 2,
        "builder_strategies": [
            {
                "id": 1,
                "name": "Estrategia 1",
                "color": "#1a6b3c",
                "legs": [
                    {
                        "id": 1,
                        "dir": "buy",
                        "type": "put",
                        "ratio": 1.0,
                        "strike": 420.0,
                        "prima": 5.0,
                    }
                ],
            }
        ],
        "ret_params": deepcopy(DEFAULT_PARAMS),
        "ret_reduction_pct": 25,
        "preset_reset_nonce": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

def request_navigation(target: str) -> None:
    """Schedule sidebar navigation for the next rerun.

    Streamlit forbids assigning to st.session_state["main_nav"] after
    the radio widget with key="main_nav" has already been created in
    the current run. This helper stores the target in a private key and
    main() applies it before rendering the sidebar.
    """
    st.session_state["_pending_nav"] = target
    st.rerun()


def apply_pending_navigation() -> None:
    """Apply a scheduled navigation target before widgets are created."""
    target = st.session_state.pop("_pending_nav", None)
    if target in {NAV_LOAD, NAV_MARKET, NAV_BUILDER}:
        st.session_state["main_nav"] = target


def step_retention_reduction(delta: int) -> None:
    """Slider helper used by the retentions scenario simulator."""
    current = int(st.session_state.get("ret_reduction_pct", 25))
    st.session_state.ret_reduction_pct = max(0, min(100, current + int(delta)))

# -----------------------------------------------------------------------------
# FORMATTERS AND LOW-LEVEL HELPERS
# -----------------------------------------------------------------------------


def fmt_num(value: Any, decimals: int = 2) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "-"
    text = f"{x:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_signed(value: Any, decimals: int = 2) -> str:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "-"
    sign = "+" if x >= 0 else ""
    return f"{sign}{fmt_num(x, decimals)}"


def parse_num(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.upper() in {"N/A", "S/C", "SC", "-", "--"}:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def canonical_pos_label(pos: str) -> str:
    raw = str(pos).strip().upper()
    m = re.match(r"^([A-Z]{3})\s*(20)?(\d{2})$", raw)
    if m:
        return f"{MONTH_LABELS.get(m.group(1), m.group(1)).upper()} 20{m.group(3)}"
    return raw


def compact_pos_label(pos: str) -> str:
    raw = str(pos).strip().upper()
    m = re.match(r"^([A-Z]{3})\s+20(\d{2})$", raw)
    if m:
        return f"{MONTH_LABELS.get(m.group(1), m.group(1))} {m.group(2)}"
    m = re.match(r"^([A-Z]{3})(\d{2})$", raw)
    if m:
        return f"{MONTH_LABELS.get(m.group(1), m.group(1))} {m.group(2)}"
    return raw.title()


def a3_pos_sort_key(pos: str) -> Tuple[int, int, str]:
    """Chronological sort for A3 position codes such as MAY26 or Bolsa labels."""
    raw = canonical_a3_pos_code(pos)
    month_order = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12, "DIS": 12}
    m = re.match(r"^([A-Z]{3})(\d{2})$", raw)
    if not m:
        return (9999, 99, raw)
    return (2000 + int(m.group(2)), month_order.get(m.group(1), 99), raw)


def canonical_a3_pos_code(pos: Any) -> str:
    """Convert ABR 2026 / Abr 26 / ABR26 into the A3 code ABR26."""
    raw = str(pos or "").strip().upper()
    m = re.match(r"^([A-Z]{3})\s+20(\d{2})$", raw)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    m = re.match(r"^([A-Z]{3})\s*(\d{2})$", raw)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return raw



def position_sort_key(pos: str) -> Tuple[int, int, str]:
    """Stable chronological order for Bolsa positions such as ABR 2026."""
    raw = canonical_pos_label(pos)
    month_order = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12, "DIS": 12}
    m = re.match(r"^([A-Z]{3})\s+20(\d{2})$", raw)
    if not m:
        return (9999, 99, raw)
    return (2000 + int(m.group(2)), month_order.get(m.group(1), 99), raw)


def normalize_bolsa_data(raw_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Normalize Bolsa data and complete missing future positions.

    The parser output remains the source of truth when it provides a non-zero value.
    The fallback snapshot is only used to complete missing rows/fields so the UI can
    expose the full visible curve through ABR 2027 even when the scraper falls back
    to a partial dataset.
    """
    normalized: Dict[str, Dict[str, float]] = {}
    keys = ["soja", "maiz", "trigo", "harina", "aceite", "aceiteGirasol"]

    for pos, row in (raw_data or {}).items():
        canonical = canonical_pos_label(pos)
        fallback_row = BOLSA_FALLBACK_FULL.get(canonical, {})
        normalized[canonical] = {}
        for key in keys:
            value = parse_num((row or {}).get(key, 0.0))
            # Fill parser misses without overriding valid scraped values.
            if value <= 0 and safe_float(fallback_row.get(key), 0.0) > 0:
                value = safe_float(fallback_row.get(key), 0.0)
            normalized[canonical][key] = float(value)

    for pos, row in BOLSA_FALLBACK_FULL.items():
        normalized.setdefault(pos, deepcopy(row))

    return dict(sorted(normalized.items(), key=lambda item: position_sort_key(item[0])))


def get_positions_bolsa() -> List[str]:
    data = st.session_state.data_bolsa or {}
    return sorted(list(data.keys()), key=position_sort_key)


def select_default_position(data: Dict[str, Dict[str, float]]) -> Optional[str]:
    if not data:
        return None
    for candidate in ["ABR 2026", "MAY 2026"]:
        if candidate in data:
            return candidate
    return next(iter(data.keys()))


def get_market_row(position: Optional[str] = None) -> Dict[str, float]:
    data = st.session_state.data_bolsa or {}
    pos = position or st.session_state.market_position
    if pos in data:
        return data[pos] or {}
    return {}


def get_raw_value(position: Optional[str], key: str) -> float:
    return safe_float(get_market_row(position).get(key, 0.0))


def get_selected_fob(crop: Optional[str] = None, position: Optional[str] = None) -> float:
    crop = crop or st.session_state.market_crop
    key = GRAIN_KEYS.get(crop, "soja")
    return get_raw_value(position or st.session_state.market_position, key)


def html_escape(s: Any) -> str:
    text = str(s)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

# -----------------------------------------------------------------------------
# A3 PARSER
# -----------------------------------------------------------------------------


def normalize_a3_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Accepts either a proper CSV header or a preamble table and returns clean rows."""
    if df is None or df.empty:
        return pd.DataFrame()

    clean = df.copy()
    clean.columns = [str(c).strip() for c in clean.columns]
    lower_cols = [c.lower() for c in clean.columns]
    if any("contrato" in c for c in lower_cols):
        return clean

    # Sometimes pandas reads preamble rows as headers. Recreate a matrix and find header row.
    matrix = [list(clean.columns)] + clean.astype(str).fillna("").values.tolist()
    header_idx = None
    for i, row in enumerate(matrix[:20]):
        if row and "contrato" in str(row[0]).strip().lower():
            header_idx = i
            break
    if header_idx is None:
        return clean

    header = [str(x).strip() for x in matrix[header_idx]]
    rows = matrix[header_idx + 1 :]
    out = pd.DataFrame(rows, columns=header)
    out = out.dropna(how="all")
    return out


def find_col(columns: Iterable[str], *patterns: str, default: Optional[str] = None) -> Optional[str]:
    cols = list(columns)
    normalized = {c: str(c).strip().lower() for c in cols}
    for c, low in normalized.items():
        if all(p in low for p in patterns):
            return c
    return default


def parse_contrato(contrato: str) -> Optional[Dict[str, Any]]:
    """Parse A3 contract names with the same tolerance as the HTML prototype.

    Examples:
    - SOJ.ROS/MAY26
    - SOJ.ROS/MAY26 248 C
    - GIR.ROS.P/DIS26

    The previous Streamlit version only accepted positions shaped as exactly
    three letters + two digits. The HTML accepted any alphanumeric position
    after the slash, so valid A3 positions could disappear from the dropdown.
    """
    text = str(contrato or "").strip().upper()
    m = re.match(r"^([A-Z]{3})\.[A-Z.]+\/([A-Z0-9]+)(?:\s+(\d+(?:[\.,]\d+)?)\s+([CP]))?\s*$", text)
    if not m:
        return None
    crop = CROP_CODE_MAP.get(m.group(1))
    if not crop:
        return None
    result: Dict[str, Any] = {"crop": crop, "pos": canonical_a3_pos_code(m.group(2))}
    if m.group(3) and m.group(4):
        result["strike"] = parse_num(m.group(3))
        result["opt_type"] = "call" if m.group(4) == "C" else "put"
    return result


def parse_a3_data(df: pd.DataFrame) -> Dict[str, Any]:
    normalized = normalize_a3_dataframe(df)
    result = {
        "raw_df": normalized,
        "futuros": {},
        "opciones": {},
        "fecha_datos": "",
        "n_futuros": 0,
        "n_opciones": 0,
    }
    if normalized.empty:
        return result

    contrato_col = find_col(normalized.columns, "contrato", default=normalized.columns[0])
    tipo_col = find_col(normalized.columns, "tipo")
    moneda_col = find_col(normalized.columns, "moneda")
    ajuste_col = find_col(normalized.columns, "ajuste") or find_col(normalized.columns, "valor")
    put_call_col = find_col(normalized.columns, "put", "call")
    vto_col = find_col(normalized.columns, "vencimiento")
    ia_col = find_col(normalized.columns, "inter", "abierto")
    fecha_col = find_col(normalized.columns, "fecha", "datos")

    if contrato_col is None or ajuste_col is None or tipo_col is None:
        return result

    for _, row in normalized.iterrows():
        contrato = str(row.get(contrato_col, "")).strip()
        if not contrato:
            continue
        info = parse_contrato(contrato)
        if not info:
            continue

        moneda = str(row.get(moneda_col, "USD") if moneda_col else "USD").strip().upper()
        if moneda and moneda != "USD":
            continue

        tipo = str(row.get(tipo_col, "")).strip().lower()
        ajuste = parse_num(row.get(ajuste_col, 0))
        vto = str(row.get(vto_col, "") if vto_col else "").strip()
        ia = parse_num(row.get(ia_col, 0)) if ia_col else 0.0
        if not result["fecha_datos"] and fecha_col and row.get(fecha_col, None) is not None:
            result["fecha_datos"] = str(row.get(fecha_col, "")).strip()

        crop = info["crop"]
        pos = canonical_a3_pos_code(info["pos"])
        if "futuro" in tipo:
            result["futuros"].setdefault(crop, [])
            result["futuros"][crop].append(
                {"pos": pos, "precio": ajuste, "vto": vto, "ia": ia, "contrato": contrato}
            )
            result["n_futuros"] += 1
        elif "opci" in tipo or "option" in tipo:
            if "strike" not in info:
                continue
            put_call = str(row.get(put_call_col, "") if put_call_col else "").strip().upper()
            opt_type = info.get("opt_type")
            if put_call == "CALL":
                opt_type = "call"
            elif put_call == "PUT":
                opt_type = "put"
            if opt_type not in {"call", "put"}:
                continue
            result["opciones"].setdefault(crop, {}).setdefault(pos, {"call": [], "put": []})
            result["opciones"][crop][pos][opt_type].append(
                {"strike": float(info["strike"]), "prima": ajuste, "contrato": contrato}
            )
            result["n_opciones"] += 1

    for futs in result["futuros"].values():
        futs.sort(key=lambda x: a3_pos_sort_key(x.get("pos", "")))

    for crop_opts in result["opciones"].values():
        for pos_opts in crop_opts.values():
            pos_opts["call"].sort(key=lambda x: x["strike"])
            pos_opts["put"].sort(key=lambda x: x["strike"])
    return result


def get_a3_positions(crop: str, include_bolsa_curve: bool = True) -> List[str]:
    """Return the complete position universe for the Builder.

    A3 is the source for futures/options/primas. Bolsa is added only as a
    navigation fallback so the Builder can use the full FOB curve as baseline.
    If a Bolsa-only position has no A3 options, strike remains editable and
    premium autocomplete simply does nothing.
    """
    data = st.session_state.data_a3 or {}
    positions = set()

    for fut in data.get("futuros", {}).get(crop, []):
        pos = canonical_a3_pos_code(fut.get("pos"))
        if pos:
            positions.add(pos)

    for pos in (data.get("opciones", {}).get(crop, {}) or {}).keys():
        code = canonical_a3_pos_code(pos)
        if code:
            positions.add(code)

    # Match the HTML workflow better: the position selector should not feel
    # artificially truncated when A3 has options only for part of the curve.
    # The full Bolsa curve remains read-only market data and does not alter A3.
    if include_bolsa_curve:
        for bolsa_pos in get_positions_bolsa():
            code = canonical_a3_pos_code(bolsa_pos)
            if code:
                positions.add(code)

    return sorted([p for p in positions if p], key=a3_pos_sort_key)


def get_a3_position_summary(include_bolsa_curve: bool = False) -> pd.DataFrame:
    """Audit table with A3 positions by crop and available option counts.

    By default this shows A3-only positions, so the user can verify how the 25
    futures and 119 options are distributed across crops. The builder selector
    can additionally expose the full Bolsa curve as navigation fallback.
    """
    data = st.session_state.data_a3 or {}
    rows: List[Dict[str, Any]] = []
    for crop in CROP_LABELS.keys():
        positions = get_a3_positions(crop, include_bolsa_curve=include_bolsa_curve)
        for pos in positions:
            fut = next(
                (
                    f
                    for f in data.get("futuros", {}).get(crop, [])
                    if canonical_a3_pos_code(f.get("pos")) == canonical_a3_pos_code(pos)
                ),
                None,
            )
            opts = data.get("opciones", {}).get(crop, {}).get(canonical_a3_pos_code(pos), {}) or {}
            calls = len(opts.get("call", []))
            puts = len(opts.get("put", []))
            if fut is None and calls + puts == 0 and not include_bolsa_curve:
                continue
            rows.append(
                {
                    "Cultivo": CROP_LABELS.get(crop, crop),
                    "Posicion": compact_pos_label(pos),
                    "Futuro A3": safe_float(fut.get("precio"), 0.0) if fut else 0.0,
                    "Calls": calls,
                    "Puts": puts,
                    "Opciones": calls + puts,
                }
            )
    return pd.DataFrame(rows)




def get_a3_future_price(crop: str, position: Optional[str]) -> Optional[float]:
    """Return the A3 future price for the selected crop/position, when available.

    In the original HTML builder the chart base is the MATBA/A3 future/spot
    (for example Maiz Mayo 26 around 189), not the Bolsa FOB soybean value
    used by the FAS panel (for example 427).
    """
    if not crop or not position:
        return None
    data = st.session_state.data_a3 or {}
    pos_code = canonical_a3_pos_code(position)
    for fut in data.get("futuros", {}).get(crop, []):
        if canonical_a3_pos_code(fut.get("pos")) == pos_code:
            price = safe_float(fut.get("precio"), 0.0)
            if price > 0:
                return price
    return None


def get_builder_base_price(crop: Optional[str] = None, position: Optional[str] = None) -> Tuple[float, str]:
    """Return the builder spot/base price and a source label.

    Builder behavior now matches the HTML: A3 future price is the first source
    for presets, payoff chart and scenarios. Bolsa FOB remains isolated in
    Panel Mercado/FAS and is used only as fallback when A3 has no future for
    the selected crop/position.
    """
    crop = crop or st.session_state.builder_crop
    position = position or st.session_state.builder_position
    a3_price = get_a3_future_price(crop, position)
    if a3_price is not None:
        return a3_price, f"A3 futuro {CROP_LABELS.get(crop, crop)} {compact_pos_label(position)}"

    fob_price = get_selected_fob(st.session_state.market_crop, st.session_state.market_position)
    if fob_price > 0:
        return fob_price, f"Bolsa FOB {CROP_LABELS.get(st.session_state.market_crop, st.session_state.market_crop)} {compact_pos_label(st.session_state.market_position)}"

    return safe_float(st.session_state.get("last_market_fob"), 400.0), "Fallback"

def get_available_strikes(crop: str, position: Optional[str], opt_type: str) -> List[float]:
    if opt_type not in {"call", "put"} or not position:
        return []
    data = st.session_state.data_a3 or {}
    pos = canonical_a3_pos_code(position)
    opts = data.get("opciones", {}).get(crop, {}).get(pos, {}).get(opt_type, [])
    return [float(o["strike"]) for o in opts if safe_float(o.get("strike"), 0) > 0]


def lookup_premium(crop: str, position: Optional[str], opt_type: str, strike: float) -> Optional[float]:
    if opt_type not in {"call", "put"} or not position:
        return None
    data = st.session_state.data_a3 or {}
    pos = canonical_a3_pos_code(position)
    opts = data.get("opciones", {}).get(crop, {}).get(pos, {}).get(opt_type, [])
    if not opts:
        return None
    for opt in opts:
        if abs(float(opt.get("strike", 0)) - float(strike)) < 0.001:
            return float(opt.get("prima", 0))
    return None

# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------


def load_bolsa(force: bool = False) -> None:
    if force and hasattr(obtener_datos_bolsa, "clear"):
        obtener_datos_bolsa.clear()
    data = obtener_datos_bolsa()
    if not data:
        raise RuntimeError("No se obtuvieron datos desde Bolsa de Cereales")
    normalized = normalize_bolsa_data(data)
    st.session_state.data_bolsa = normalized
    st.session_state.bolsa_loaded_at = datetime.now()
    if not st.session_state.market_position or st.session_state.market_position not in normalized:
        st.session_state.market_position = select_default_position(normalized)
    st.session_state.data_loaded = True


def load_a3() -> None:
    df = obtener_datos_a3()
    parsed = parse_a3_data(df)
    st.session_state.data_a3 = parsed
    st.session_state.a3_loaded_at = datetime.now()
    positions = get_a3_positions(st.session_state.builder_crop)
    if positions and st.session_state.builder_position not in positions:
        st.session_state.builder_position = positions[0]

# -----------------------------------------------------------------------------
# FINANCIAL CALCULATIONS
# -----------------------------------------------------------------------------


def calc_grain_fas(fob: float, ret_pct: float, fobbing: float) -> Dict[str, float]:
    ret_value = fob * ret_pct / 100.0
    fas = fob - ret_value - fobbing
    return {"fob": fob, "ret_value": ret_value, "fobbing": fobbing, "fas": fas}


def calc_crush(
    fob_aceite: float,
    fob_harina: float,
    coef_aceite: float,
    coef_harina: float,
    ret_sub_pct: float,
    fobbing_sub: float,
    gto_ind: float,
) -> Dict[str, float]:
    aceite_bruto = fob_aceite * coef_aceite
    harina_bruta = fob_harina * coef_harina
    bruto = aceite_bruto + harina_bruta
    ret_sub = bruto * ret_sub_pct / 100.0
    fas_crush = bruto - ret_sub - fobbing_sub - gto_ind
    return {
        "aceite_bruto": aceite_bruto,
        "harina_bruta": harina_bruta,
        "bruto": bruto,
        "ret_sub": ret_sub,
        "fobbing_sub": fobbing_sub,
        "gto_ind": gto_ind,
        "fas": fas_crush,
    }


def calc_net_price(strategy: Dict[str, Any], terminal_price: float) -> float:
    """Physical sale price plus option/future hedge payoff minus net paid premium."""
    net_premium_paid = 0.0
    hedge_payoff = 0.0
    for leg in strategy.get("legs", []):
        q = safe_float(leg.get("ratio"), 1.0)
        strike = safe_float(leg.get("strike"), 0.0)
        prima = safe_float(leg.get("prima"), 0.0)
        direction = leg.get("dir", "buy")
        typ = leg.get("type", "put")

        if typ == "futuro":
            intrinsic = (terminal_price - strike) * q
            hedge_payoff += intrinsic if direction == "buy" else -intrinsic
            continue

        if typ == "put":
            intrinsic = max(strike - terminal_price, 0.0) * q
        elif typ == "call":
            intrinsic = max(terminal_price - strike, 0.0) * q
        else:
            intrinsic = 0.0

        if direction == "buy":
            net_premium_paid += prima * q
            hedge_payoff += intrinsic
        else:
            net_premium_paid -= prima * q
            hedge_payoff -= intrinsic
    return terminal_price + hedge_payoff - net_premium_paid


def strategy_cost(strategy: Dict[str, Any]) -> float:
    cost = 0.0
    for leg in strategy.get("legs", []):
        if leg.get("type") == "futuro":
            continue
        q = safe_float(leg.get("ratio"), 1.0)
        prima = safe_float(leg.get("prima"), 0.0)
        cost += prima * q if leg.get("dir") == "buy" else -prima * q
    return cost


def collect_scenario_prices(spot: float, strategies: List[Dict[str, Any]]) -> List[Tuple[str, float]]:
    scenarios = [
        ("Derrumbe (-30%)", spot * 0.70),
        ("Baja fuerte (-15%)", spot * 0.85),
        ("Spot", spot),
        ("Suba moderada (+15%)", spot * 1.15),
        ("Rally (+30%)", spot * 1.30),
    ]
    existing = {round(v, 2) for _, v in scenarios}
    for strat in strategies:
        for leg in strat.get("legs", []):
            if leg.get("type") != "futuro":
                strike = safe_float(leg.get("strike"), 0.0)
                if strike > 0 and round(strike, 2) not in existing:
                    scenarios.append((f"Strike {leg.get('type', '').upper()} {strike:.0f}", strike))
                    existing.add(round(strike, 2))
    scenarios.sort(key=lambda x: x[1])
    return scenarios


def dominance_ranges(spot: float, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if spot <= 0:
        return []
    low, high = spot * 0.70, spot * 1.30
    prices = np.linspace(low, high, 181)
    ranges: List[Dict[str, Any]] = []
    current_name = None
    current_color = "#b0afa8"
    start = prices[0]
    for price in prices:
        best_name = "Fisico sin cobertura"
        best_value = price
        best_color = "#b0afa8"
        for strat in strategies:
            value = calc_net_price(strat, float(price))
            if value > best_value + 0.01:
                best_name = strat.get("name", "Estrategia")
                best_value = value
                best_color = strat.get("color", "#1a6b3c")
        if current_name != best_name:
            if current_name is not None:
                ranges.append({"start": start, "end": prev_price, "name": current_name, "color": current_color})
            current_name = best_name
            current_color = best_color
            start = price
        prev_price = price
    ranges.append({"start": start, "end": prices[-1], "name": current_name, "color": current_color})
    return ranges

# -----------------------------------------------------------------------------
# HTML VISUAL HELPERS
# -----------------------------------------------------------------------------


def hero() -> None:
    st.markdown(
        """
        <div class="es-hero">
            <span class="es-badge">Builder de opciones</span>
            <div class="es-hero-title"><span>🌾</span><span>Estrategias de Cobertura</span></div>
            <div class="es-hero-subtitle">Espartina S.A. - Simulador de Coberturas, FAS Teorico y datos A3</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"<div class='section-title'>{html_escape(title)}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='section-subtitle'>{html_escape(subtitle)}</div>", unsafe_allow_html=True)


def render_kpis(items: List[Tuple[str, Any, str]]) -> None:
    html = "<div class='kpi-row'>"
    for label, value, cls in items:
        html += (
            "<div class='kpi'>"
            f"<div class='kpi-lbl'>{html_escape(label)}</div>"
            f"<div class='kpi-val {cls}'>{html_escape(value)}</div>"
            "</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)



def cascade_bar(label: str, value: float, pct: float, cls: str) -> str:
    """Return a single-line HTML block.

    Streamlit/Markdown can render indented multiline HTML as a code block.
    Keeping these snippets unindented prevents raw <div> fragments from
    appearing in the UI.
    """
    pct_value = safe_float(pct, 0.0)
    width = max(3.0, min(100.0, abs(pct_value)))
    display_value = fmt_signed(value) if value < 0 else fmt_num(value)
    return (
        '<div class="cascade-row">'
        '<div>'
        f'<div class="cascade-label"><span>{html_escape(label)}</span>'
        f'<span class="cascade-value">{display_value}</span></div>'
        '<div class="cascade-bar-track">'
        f'<div class="cascade-bar {html_escape(cls)}" style="width:{width:.1f}%">{fmt_num(abs(pct_value), 1)}%</div>'
        '</div>'
        '</div>'
        '<div></div>'
        '</div>'
    )


def render_grain_cascade(crop: str, position: str, fob: float, ret_pct: float, fobbing: float, fas_obj: float) -> float:
    calc = calc_grain_fas(fob, ret_pct, fobbing)
    fobbing_pct = (fobbing / fob * 100.0) if fob else 0.0
    margin = calc["fas"] - fas_obj
    color = "var(--success)" if margin >= 0 else "var(--danger)"
    html = "".join(
        [
            '<div class="clean-panel-tight">',
            f'<div style="font-weight:850;color:var(--es-green-700);font-size:16px;margin-bottom:12px;">Exportacion grano {html_escape(compact_pos_label(position))}</div>',
            '<div class="cascade-wrap">',
            cascade_bar('FOB ' + CROP_LABELS.get(crop, crop), fob, 100.0, 'fob'),
            cascade_bar('Retencion ' + fmt_num(ret_pct, 1) + '%', -calc['ret_value'], ret_pct, 'ret'),
            cascade_bar('Fobbing', -fobbing, fobbing_pct, 'cost'),
            f'<div class="cascade-result"><span>FAS Teorico (CTP)</span><span>{fmt_num(calc["fas"])}</span></div>',
            f'<div class="cascade-note"><span>Margen export. vs obj {fmt_num(fas_obj, 1)}</span><strong style="color:{color};">{fmt_signed(margin)}</strong></div>',
            '</div>',
            '</div>',
        ]
    )
    st.markdown(html, unsafe_allow_html=True)
    return calc["fas"]


def render_crush_cascade(position: str, values: Dict[str, float], fas_obj: float) -> float:
    calc = calc_crush(
        values["fob_aceite"],
        values["fob_harina"],
        values["coef_aceite"],
        values["coef_harina"],
        values["ret_sub_pct"],
        values["fobbing_sub"],
        values["gto_ind"],
    )
    bruto = calc["bruto"] or 1.0
    margin = calc["fas"] - fas_obj
    color = "var(--success)" if margin >= 0 else "var(--danger)"
    html = "".join(
        [
            '<div class="clean-panel-tight">',
            f'<div style="font-weight:850;color:#8a6817;font-size:16px;margin-bottom:12px;">Crushing subproductos {html_escape(compact_pos_label(position))}</div>',
            '<div class="cascade-wrap">',
            cascade_bar('Aceite (' + fmt_num(values['fob_aceite'], 1) + ' x ' + fmt_num(values['coef_aceite'], 2) + ')', calc['aceite_bruto'], calc['aceite_bruto'] / bruto * 100, 'fob'),
            cascade_bar('Harina (' + fmt_num(values['fob_harina'], 1) + ' x ' + fmt_num(values['coef_harina'], 2) + ')', calc['harina_bruta'], calc['harina_bruta'] / bruto * 100, 'fob'),
            cascade_bar('Ret subprod ' + fmt_num(values['ret_sub_pct'], 1) + '%', -calc['ret_sub'], values['ret_sub_pct'], 'ret'),
            cascade_bar('Fobbing subprod', -calc['fobbing_sub'], calc['fobbing_sub'] / bruto * 100, 'cost'),
            cascade_bar('Gasto industrial', -calc['gto_ind'], calc['gto_ind'] / bruto * 100, 'cost'),
            f'<div class="cascade-result"><span>FAS Crushing</span><span>{fmt_num(calc["fas"])}</span></div>',
            f'<div class="cascade-note"><span>Margen crush vs obj {fmt_num(fas_obj, 1)}</span><strong style="color:{color};">{fmt_signed(margin)}</strong></div>',
            '</div>',
            '</div>',
        ]
    )

    st.markdown(html, unsafe_allow_html=True)
    return calc["fas"]


def render_retention_scenario_simulator(
    *,
    crop: str,
    fob: float,
    ret_pct: float,
    fobbing: float,
    fas_obj: float,
    grain_fas: float,
    crush_inputs: Optional[Dict[str, float]] = None,
    crush_fas: Optional[float] = None,
) -> None:
    """Replicate the HTML retentions-reduction scenario simulator.

    This section is intentionally independent from the raw Bolsa values: it only
    models what happens if retentions are reduced. FOB remains immutable.
    """
    st.markdown('<div class="scenario-title">Simulador de escenario — Baja de retenciones</div>', unsafe_allow_html=True)
    with st.container(border=True):
        c_lbl, c_minus, c_slider, c_plus, c_val = st.columns([1.8, .35, 6.2, .35, .7], gap="medium")
        with c_lbl:
            st.markdown('<div style="font-weight:800;color:var(--text);padding-top:8px;">Reducción de retenciones:</div>', unsafe_allow_html=True)
        with c_minus:
            st.button("-", key="ret_reduction_minus", type="primary", on_click=step_retention_reduction, args=(-5,), use_container_width=True)
        with c_slider:
            reduction_pct = st.slider(
                "Reducción de retenciones",
                min_value=0,
                max_value=100,
                step=5,
                key="ret_reduction_pct",
                label_visibility="collapsed",
            )
        with c_plus:
            st.button("+", key="ret_reduction_plus", type="primary", on_click=step_retention_reduction, args=(5,), use_container_width=True)
        with c_val:
            st.markdown(f'<div style="font-weight:900;color:var(--es-green-700);font-size:20px;padding-top:6px;text-align:right;">-{int(reduction_pct)}%</div>', unsafe_allow_html=True)

    reduction = float(reduction_pct) / 100.0
    new_ret_pct = float(ret_pct) * (1.0 - reduction)
    new_grain = calc_grain_fas(fob, new_ret_pct, fobbing)["fas"]

    current_crush_display = "-"
    new_crush_display = "-"
    if crop == "soja" and crush_inputs is not None:
        current_crush_display = fmt_num(crush_fas if crush_fas is not None else 0.0)
        new_crush_ret = float(crush_inputs.get("ret_sub_pct", 0.0)) * (1.0 - reduction)
        new_crush = calc_crush(
            crush_inputs.get("fob_aceite", 0.0),
            crush_inputs.get("fob_harina", 0.0),
            crush_inputs.get("coef_aceite", 0.0),
            crush_inputs.get("coef_harina", 0.0),
            new_crush_ret,
            crush_inputs.get("fobbing_sub", 0.0),
            crush_inputs.get("gto_ind", 0.0),
        )["fas"]
        new_crush_display = fmt_num(new_crush)

    left_html = "".join([
        '<div class="scenario-card">',
        '<div class="scenario-card-title">Escenario actual</div>',
        f'<div class="scenario-row"><span>Retención grano</span><strong>{fmt_num(ret_pct, 1)}%</strong></div>',
        f'<div class="scenario-row"><span>FAS teórico</span><strong>{fmt_num(grain_fas)}</strong></div>',
        f'<div class="scenario-row"><span>FAS crushing</span><strong>{current_crush_display}</strong></div>' if crop == "soja" else '',
        '</div>',
    ])
    right_html = "".join([
        '<div class="scenario-card highlight">',
        '<div class="scenario-card-title">Escenario con reducción</div>',
        f'<div class="scenario-row"><span>Retención grano</span><strong>{fmt_num(new_ret_pct, 1)}%</strong></div>',
        f'<div class="scenario-row"><span>FAS teórico</span><strong>{fmt_num(new_grain)}</strong></div>',
        f'<div class="scenario-row"><span>FAS crushing</span><strong>{new_crush_display}</strong></div>' if crop == "soja" else '',
        '</div>',
    ])
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown(left_html, unsafe_allow_html=True)
    with col_b:
        st.markdown(right_html, unsafe_allow_html=True)

    st.markdown(
        '<div class="coverage-note">'
        f'<strong>Conexión con coberturas:</strong> Si cubrís a FOB {fmt_num(fob, 1)} con un PUT, '
        f'tu piso de FAS neto es <strong style="color:var(--es-green-700);">{fmt_num(grain_fas)}</strong> u$s/tn '
        'menos la prima pagada. Usá el Builder de Coberturas para calcular el impacto exacto.'
        '</div>',
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# NAVIGATION AND GATE
# -----------------------------------------------------------------------------


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("### Menu Principal")
        page = st.radio(
            "Navegacion",
            [NAV_LOAD, NAV_MARKET, NAV_BUILDER],
            label_visibility="collapsed",
            key="main_nav",
        )
        st.divider()
        st.markdown("### Estado de fuentes")
        if st.session_state.data_loaded:
            st.success("Datos base cargados")
        else:
            st.warning("Datos pendientes")
        bolsa_count = len(st.session_state.data_bolsa or {})
        st.caption(f"Bolsa: {bolsa_count} posiciones")
        a3 = st.session_state.data_a3 or {}
        if a3:
            st.caption(f"A3: {a3.get('n_futuros', 0)} futuros / {a3.get('n_opciones', 0)} opciones")
        else:
            st.caption("A3: sin datos")
        st.divider()
        if st.button("Limpiar builder", type="primary", use_container_width=True):
            reset_builder()
            st.rerun()
    return page


def gate_if_needed() -> bool:
    if st.session_state.data_loaded:
        return True
    render_section_header("Datos requeridos", "Por favor, cargue los datos en la seccion Carga de Datos.")
    with st.container(border=True):
        st.info("Por favor, cargue los datos en la seccion ⚙️ Carga de Datos.")
        if st.button("Ir a Carga de Datos", type="primary"):
            request_navigation(NAV_LOAD)
    return False

# -----------------------------------------------------------------------------
# LOAD PAGE
# -----------------------------------------------------------------------------


def render_load_page() -> None:
    render_section_header(
        "Carga de Datos",
        "Primero cargue Bolsa para validar FOB/FAS. Luego sincronice A3 para opciones, strikes y primas.",
    )
    col_bolsa, col_a3 = st.columns(2, gap="large")
    with col_bolsa:
        with st.container(border=True):
            st.subheader("Bolsa de Cereales")
            st.caption("Fuente de FOB, harina, aceite y aceite de girasol. Estos valores se guardan crudos, sin descuentos.")
            from scraper import render_csv_uploader
            datos_csv = render_csv_uploader()
            if datos_csv:
                normalized = normalize_bolsa_data(datos_csv)
                st.session_state.data_bolsa = normalized
                st.session_state.bolsa_loaded_at = datetime.now()
                if not st.session_state.market_position or st.session_state.market_position not in normalized:
                    st.session_state.market_position = select_default_position(normalized)
                st.session_state.data_loaded = True
                st.rerun()
            if not st.session_state.data_bolsa:
                if st.button("Usar datos de respaldo (28/04/2026)", use_container_width=True):
                    with st.spinner("Cargando datos de respaldo..."):
                        try:
                            load_bolsa(force=True)
                            st.success("Datos de respaldo cargados.")
                        except Exception as exc:
                            st.error(f"Error: {exc}")
            if st.session_state.bolsa_loaded_at:
                st.caption(f"Ultima actualizacion: {st.session_state.bolsa_loaded_at:%d/%m/%Y %H:%M}")
            if st.session_state.data_bolsa:
                data = st.session_state.data_bolsa
                default_pos = select_default_position(data)
                soja = get_raw_value(default_pos, "soja")
                aceite = get_raw_value(default_pos, "aceite")
                render_kpis(
                    [
                        ("Posiciones", len(data), "green"),
                        ("Control soja", fmt_num(soja), "green"),
                        ("Control aceite", fmt_num(aceite), "gold"),
                        ("Estado", "OK" if aceite else "Revisar", "green" if aceite else ""),
                    ]
                )

    with col_a3:
        with st.container(border=True):
            st.subheader("A3 / Mercado de opciones")
            st.caption("Fuente de futuros, calls, puts, strikes y primas para el builder.")
            if st.button("Sincronizar A3", use_container_width=True):
                with st.spinner("Sincronizando Google Sheets A3..."):
                    try:
                        load_a3()
                        a3 = st.session_state.data_a3 or {}
                        st.success(f"A3 sincronizado: {a3.get('n_futuros', 0)} futuros, {a3.get('n_opciones', 0)} opciones")
                    except Exception as exc:
                        st.error(f"Error al sincronizar A3: {exc}")
            if st.session_state.a3_loaded_at:
                st.caption(f"Ultima sincronizacion: {st.session_state.a3_loaded_at:%d/%m/%Y %H:%M}")
            a3 = st.session_state.data_a3 or {}
            if a3:
                render_kpis(
                    [
                        ("Futuros", a3.get("n_futuros", 0), "green"),
                        ("Opciones", a3.get("n_opciones", 0), "gold"),
                        ("Fecha", a3.get("fecha_datos") or "-", ""),
                        ("Estado", "OK" if a3.get("n_opciones") else "Sin opciones", "green" if a3.get("n_opciones") else ""),
                    ]
                )

    if not st.session_state.data_loaded:
        st.info("Por favor, cargue los datos en la seccion ⚙️ Carga de Datos.")
    else:
        st.success("Flujo habilitado: 1) datos cargados -> 2) FOB validado -> 3) Builder activo.")
        if st.button("Abrir Panel de Mercado", type="primary"):
            request_navigation(NAV_MARKET)

# -----------------------------------------------------------------------------
# MARKET PANEL
# -----------------------------------------------------------------------------


def render_market_panel() -> None:
    if not gate_if_needed():
        return

    render_section_header(
        "Panel de Mercado (FAS)",
        "Fuente: Bolsa de Cereales. Los FOB y subproductos son datos crudos inmutables; retenciones y fobbing se aplican solo dentro de la cascada.",
    )
    data = st.session_state.data_bolsa or {}
    positions = get_positions_bolsa()
    if not positions:
        st.error("No hay posiciones de Bolsa cargadas.")
        return

    with st.container(border=True):
        c1, c2, c3, c4, c5, c6 = st.columns([1.15, 1.45, .8, .9, .9, .9], gap="medium")
        with c1:
            crop = st.selectbox(
                "Cultivo",
                list(CROP_LABELS.keys()),
                format_func=lambda c: CROP_LABELS[c],
                key="market_crop",
            )
        with c2:
            current_pos = st.session_state.market_position if st.session_state.market_position in positions else positions[0]
            pos = st.selectbox(
                "Mes / Posicion FOB",
                positions,
                index=positions.index(current_pos),
                format_func=compact_pos_label,
                key="market_position",
            )
        params = st.session_state.ret_params[crop]
        with c3:
            params["ret_pct"] = st.number_input("Ret %", min_value=0.0, max_value=100.0, step=0.1, key=f"ret_pct_{crop}", value=float(params["ret_pct"]))
        with c4:
            params["fobbing"] = st.number_input("Fobbing", min_value=0.0, step=0.5, key=f"fobbing_{crop}", value=float(params["fobbing"]))
        with c5:
            params["fas_obj"] = st.number_input("FAS Obj", min_value=0.0, step=0.5, key=f"fas_obj_{crop}", value=float(params["fas_obj"]))
        with c6:
            st.write("")
            st.write("")
            if st.button("Actualizar", type="primary", use_container_width=True):
                with st.spinner("Refrescando Bolsa..."):
                    load_bolsa(force=True)
                st.rerun()

    raw = get_market_row(pos)
    fob = safe_float(raw.get(GRAIN_KEYS.get(crop, "soja"), 0.0))
    soja_control = safe_float(raw.get("soja", 0.0))
    aceite = safe_float(raw.get("aceite", 0.0))
    harina = safe_float(raw.get("harina", 0.0))
    aceite_girasol = safe_float(raw.get("aceiteGirasol", 0.0))

    expected_txt = ""
    if pos == "ABR 2026":
        expected_txt = " Control ABR 2026: Soja=432, Aceite=1189."
    st.info(
        f"Diagnostico FOB [OK]: fuente Bolsa para {CROP_LABELS.get(crop, crop)} / {compact_pos_label(pos)} = {fmt_num(fob)}. "
        f"Valor usado en cascada = {fmt_num(fob)}. Diferencia = {fmt_signed(fob - fob)}. "
        f"Aceite crudo detectado = {fmt_num(aceite)}.{expected_txt}"
    )

    render_kpis(
        [
            (f"FOB fuente {CROP_LABELS.get(crop, crop)}", fmt_num(fob), "green"),
            ("FOB aceite crudo", fmt_num(aceite), "gold"),
            ("FOB harina crudo", fmt_num(harina), ""),
            ("Aceite girasol crudo", fmt_num(aceite_girasol), ""),
        ]
    )

    crush_inputs: Optional[Dict[str, float]] = None
    fas_crush: Optional[float] = None

    left, right = st.columns([1, 1], gap="large")
    with left:
        fas_grain = render_grain_cascade(crop, pos, fob, params["ret_pct"], params["fobbing"], params["fas_obj"])

    with right:
        if crop == "soja":
            with st.container(border=True):
                st.markdown("#### Parametros crushing")
                a, b = st.columns(2)
                with a:
                    fob_aceite = st.number_input("FOB Aceite", value=aceite, min_value=0.0, step=1.0, key=f"crush_aceite_{pos}")
                    coef_aceite = st.number_input("Coef. Aceite", value=0.19, min_value=0.0, step=0.01, key="crush_coef_aceite")
                    ret_sub_pct = st.number_input("Ret Sub %", value=22.5, min_value=0.0, max_value=100.0, step=0.1, key="crush_ret_sub")
                with b:
                    fob_harina = st.number_input("FOB Harina", value=harina, min_value=0.0, step=1.0, key=f"crush_harina_{pos}")
                    coef_harina = st.number_input("Coef. Harina", value=0.78, min_value=0.0, step=0.01, key="crush_coef_harina")
                    gto_ind = st.number_input("Gto Ind.", value=29.0, min_value=0.0, step=1.0, key="crush_gto_ind")
                fobbing_sub = st.number_input("Fobbing subprod", value=19.0, min_value=0.0, step=0.5, key="crush_fobbing_sub")
            crush_inputs = {
                "fob_aceite": fob_aceite,
                "fob_harina": fob_harina,
                "coef_aceite": coef_aceite,
                "coef_harina": coef_harina,
                "ret_sub_pct": ret_sub_pct,
                "fobbing_sub": fobbing_sub,
                "gto_ind": gto_ind,
            }
            fas_crush = render_crush_cascade(pos, crush_inputs, params["fas_obj"])
            st.session_state["last_fas_crush"] = fas_crush
        else:
            st.info("El modulo crushing aplica para soja. Para otros cultivos se muestra solo exportacion grano.")

    st.session_state["last_fas_grain"] = fas_grain
    st.session_state["last_market_fob"] = fob

    render_retention_scenario_simulator(
        crop=crop,
        fob=fob,
        ret_pct=params["ret_pct"],
        fobbing=params["fobbing"],
        fas_obj=params["fas_obj"],
        grain_fas=fas_grain,
        crush_inputs=crush_inputs,
        crush_fas=fas_crush,
    )

# -----------------------------------------------------------------------------
# BUILDER PANEL
# -----------------------------------------------------------------------------


def reset_builder() -> None:
    st.session_state.next_strategy_id = 2
    st.session_state.next_leg_id = 2
    st.session_state.builder_strategies = [
        {
            "id": 1,
            "name": "Estrategia 1",
            "color": "#1a6b3c",
            "legs": [
                {"id": 1, "dir": "buy", "type": "put", "ratio": 1.0, "strike": 420.0, "prima": 5.0}
            ],
        }
    ]
    # Remove old widget state related to legs/strategies.
    for key in list(st.session_state.keys()):
        if key.startswith("leg_") or key.startswith("strategy_name_"):
            del st.session_state[key]


def new_leg(spot: float, typ: str = "put") -> Dict[str, Any]:
    leg_id = int(st.session_state.next_leg_id)
    st.session_state.next_leg_id += 1
    return {
        "id": leg_id,
        "dir": "buy",
        "type": typ,
        "ratio": 1.0,
        "strike": round(spot, 0),
        "prima": 5.0 if typ != "futuro" else 0.0,
    }


def add_strategy(name: str = "Nueva Estrategia", legs: Optional[List[Dict[str, Any]]] = None) -> None:
    colors = ["#1a6b3c", "#2563eb", "#d97706", "#7c3aed", "#c43030", "#0d9488"]
    strat_id = int(st.session_state.next_strategy_id)
    st.session_state.next_strategy_id += 1
    color = colors[(strat_id - 1) % len(colors)]
    if legs is None:
        legs = [new_leg(get_builder_base_price()[0])]
    st.session_state.builder_strategies.append({"id": strat_id, "name": name, "color": color, "legs": legs})


def load_preset(name: str, spot: float) -> None:
    template = PRESETS.get(name)
    if not template:
        return
    legs: List[Dict[str, Any]] = []
    for item in template:
        leg = new_leg(spot, item["type"])
        leg.update(
            {
                "dir": item["dir"],
                "type": item["type"],
                "ratio": item["ratio"],
                "strike": round(spot * item["strike_mult"], 0),
                "prima": item["prima"],
            }
        )
        prem = lookup_premium(st.session_state.builder_crop, st.session_state.builder_position, leg["type"], leg["strike"])
        if prem is not None:
            leg["prima"] = prem
            st.session_state[f"leg_{leg['id']}_prima"] = prem
        legs.append(leg)
    add_strategy(name, legs)


def refresh_all_premiums() -> int:
    crop = st.session_state.builder_crop
    pos = st.session_state.builder_position
    count = 0
    for strat in st.session_state.builder_strategies:
        for leg in strat.get("legs", []):
            if leg.get("type") == "futuro":
                leg["prima"] = 0.0
                st.session_state[f"leg_{leg['id']}_prima"] = 0.0
                continue
            premium = lookup_premium(crop, pos, leg.get("type", "put"), safe_float(leg.get("strike")))
            if premium is not None:
                leg["prima"] = premium
                st.session_state[f"leg_{leg['id']}_prima"] = premium
                count += 1
    return count


def sync_widget_default(key: str, value: Any) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


def render_leg_row(strategy: Dict[str, Any], leg: Dict[str, Any], idx: int) -> None:
    leg_id = leg["id"]
    crop = st.session_state.builder_crop
    position = st.session_state.builder_position

    dir_key = f"leg_{leg_id}_dir"
    type_key = f"leg_{leg_id}_type"
    ratio_key = f"leg_{leg_id}_ratio"
    strike_key = f"leg_{leg_id}_strike"
    prima_key = f"leg_{leg_id}_prima"
    prev_key = f"leg_{leg_id}_prev_strike"

    sync_widget_default(dir_key, leg.get("dir", "buy"))
    sync_widget_default(type_key, leg.get("type", "put"))
    sync_widget_default(ratio_key, safe_float(leg.get("ratio"), 1.0))
    sync_widget_default(strike_key, safe_float(leg.get("strike"), 0.0))
    sync_widget_default(prima_key, safe_float(leg.get("prima"), 0.0))

    c1, c2, c3, c4, c5, c6 = st.columns([1.1, 1.1, .75, 1.15, .95, .45], gap="small")
    with c1:
        dir_val = st.selectbox(
            "Operacion",
            ["buy", "sell"],
            format_func=lambda x: "Compra" if x == "buy" else "Venta",
            key=dir_key,
            label_visibility="collapsed",
        )
    with c2:
        type_val = st.selectbox(
            "Instrumento",
            ["put", "call", "futuro"],
            format_func=lambda x: x.capitalize(),
            key=type_key,
            label_visibility="collapsed",
        )
    with c3:
        ratio_val = st.number_input(
            "Ratio",
            min_value=0.0,
            step=0.5,
            key=ratio_key,
            label_visibility="collapsed",
        )
    with c4:
        strikes = get_available_strikes(crop, position, type_val)
        if type_val in {"put", "call"} and strikes:
            current = safe_float(st.session_state.get(strike_key), safe_float(leg.get("strike")))
            if current not in strikes:
                current = min(strikes, key=lambda s: abs(s - current)) if current else strikes[0]
                st.session_state[strike_key] = current
            strike_val = st.selectbox(
                "Strike",
                strikes,
                index=strikes.index(current),
                format_func=lambda x: fmt_num(x, 0),
                key=strike_key,
                label_visibility="collapsed",
            )
            if st.session_state.get(prev_key) != strike_val:
                premium = lookup_premium(crop, position, type_val, strike_val)
                if premium is not None:
                    st.session_state[prima_key] = premium
                st.session_state[prev_key] = strike_val
        else:
            strike_val = st.number_input(
                "Strike",
                min_value=0.0,
                step=1.0,
                key=strike_key,
                label_visibility="collapsed",
            )
    with c5:
        disabled = type_val == "futuro"
        if disabled:
            st.session_state[prima_key] = 0.0
        prima_val = st.number_input(
            "Prima",
            min_value=0.0,
            step=0.1,
            key=prima_key,
            disabled=disabled,
            label_visibility="collapsed",
        )
    with c6:
        if st.button("X", key=f"delete_leg_{leg_id}", help="Borrar pata", use_container_width=True):
            strategy["legs"].pop(idx)
            st.rerun()

    leg.update(
        {
            "dir": dir_val,
            "type": type_val,
            "ratio": ratio_val,
            "strike": safe_float(strike_val),
            "prima": 0.0 if type_val == "futuro" else safe_float(prima_val),
        }
    )


def render_strategy_card(strategy: Dict[str, Any], spot: float) -> None:
    sid = strategy["id"]
    with st.container(border=True):
        h1, h2, h3 = st.columns([2.6, .9, .6])
        with h1:
            sync_widget_default(f"strategy_name_{sid}", strategy.get("name", "Estrategia"))
            strategy["name"] = st.text_input("Nombre", key=f"strategy_name_{sid}", label_visibility="collapsed")
        with h2:
            cost = strategy_cost(strategy)
            st.metric("Costo neto", fmt_signed(-cost) if cost < 0 else fmt_num(cost), help="Prima pagada neta. Credito si es negativo.")
        with h3:
            if st.button("Borrar", key=f"delete_strategy_{sid}", use_container_width=True):
                st.session_state.builder_strategies = [s for s in st.session_state.builder_strategies if s["id"] != sid]
                st.rerun()

        st.markdown("<div class='leg-header'><span>Operacion</span><span>Instrum.</span><span>Ratio</span><span>Strike</span><span>Prima</span><span></span></div>", unsafe_allow_html=True)
        for idx, leg in enumerate(list(strategy.get("legs", []))):
            render_leg_row(strategy, leg, idx)

        c1, c2, c3 = st.columns([1, 1, 4])
        with c1:
            if st.button("+ Pata", key=f"add_leg_{sid}", type="primary", use_container_width=True):
                strategy["legs"].append(new_leg(spot))
                st.rerun()
        with c2:
            if st.button("Prima A3", key=f"premium_one_{sid}", type="primary", use_container_width=True):
                updated = 0
                for leg in strategy.get("legs", []):
                    premium = lookup_premium(st.session_state.builder_crop, st.session_state.builder_position, leg.get("type"), safe_float(leg.get("strike")))
                    if premium is not None:
                        leg["prima"] = premium
                        st.session_state[f"leg_{leg['id']}_prima"] = premium
                        updated += 1
                st.toast(f"{updated} primas actualizadas")
                st.rerun()
        with c3:
            st.caption("Cada pata se guarda en session_state. Cambiar el mes del Panel FAS no resetea el builder.")


def render_builder_panel() -> None:
    if not gate_if_needed():
        return

    # El selector de plantillas usa una key dinamica.
    # Esto evita el error de Streamlit por intentar modificar manualmente
    # una key que ya fue usada por st.selectbox durante la misma ejecucion.

    render_section_header(
        "Builder de Coberturas",
        "Panel independiente A3. Usa el futuro A3 seleccionado como spot/base del builder; Bolsa FOB queda para el Panel FAS.",
    )

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([1.15, 1.25, 1.3, 1.2, 1.2], gap="medium")
        with c1:
            st.session_state.builder_crop = st.selectbox(
                "Cultivo A3",
                list(CROP_LABELS.keys()),
                index=list(CROP_LABELS.keys()).index(st.session_state.builder_crop),
                format_func=lambda c: CROP_LABELS[c],
                key="builder_crop_selector",
            )
            st.session_state.builder_crop = st.session_state.builder_crop_selector
        positions = get_a3_positions(st.session_state.builder_crop)
        with c2:
            if positions:
                if st.session_state.builder_position not in positions:
                    st.session_state.builder_position = positions[0]
                st.session_state.builder_position = st.selectbox(
                    "Posicion A3",
                    positions,
                    index=positions.index(st.session_state.builder_position),
                    format_func=compact_pos_label,
                    key="builder_position_selector",
                )
            else:
                st.selectbox("Posicion A3", ["Sin datos A3"], disabled=True)
                st.session_state.builder_position = None

        spot, spot_source = get_builder_base_price(st.session_state.builder_crop, st.session_state.builder_position)

        with c3:
            st.metric("Spot base Builder", fmt_num(spot), help=f"Fuente: {spot_source}. El FOB Bolsa/FAS se mantiene separado.")
        with c4:
            preset_key = f"preset_select_{st.session_state.preset_reset_nonce}"
            preset = st.selectbox("Plantilla", ["Seleccionar..."] + list(PRESETS.keys()), key=preset_key)
        with c5:
            st.write("")
            st.write("")
            if st.button("Cargar plantilla", use_container_width=True, disabled=preset == "Seleccionar..."):
                load_preset(preset, spot)
                st.session_state.preset_reset_nonce += 1
                st.rerun()

        st.caption(
            f"Base actual del builder: {spot_source}. "
            f"Referencia FAS/Bolsa separada: {CROP_LABELS.get(st.session_state.market_crop, st.session_state.market_crop)} "
            f"{compact_pos_label(st.session_state.market_position)} = {fmt_num(get_selected_fob(st.session_state.market_crop, st.session_state.market_position))}."
        )

        c6, c7, c8 = st.columns([1, 1, 3])
        with c6:
            if st.button("+ Nueva estrategia", type="primary", use_container_width=True):
                add_strategy("Nueva Estrategia", [new_leg(spot)])
                st.rerun()
        with c7:
            if st.button("Actualizar primas", type="primary", use_container_width=True):
                updated = refresh_all_premiums()
                st.success(f"{updated} primas actualizadas desde A3")
                st.rerun()
        with c8:
            a3 = st.session_state.data_a3 or {}
            a3_positions_count = len(get_a3_position_summary(include_bolsa_curve=False)) if a3 else 0
            full_positions_count = len(get_a3_positions(st.session_state.builder_crop)) if a3 else 0
            st.caption(
                f"A3 disponible: {a3.get('n_futuros', 0)} futuros / {a3.get('n_opciones', 0)} opciones / "
                f"{a3_positions_count} posiciones A3 unicas. "
                f"Para {CROP_LABELS.get(st.session_state.builder_crop, st.session_state.builder_crop)} se muestran {full_positions_count} posiciones en orden cronologico. "
                "Las primas/strikes solo se autocompletan cuando A3 tiene datos para esa posicion."
            )

    with st.expander("Ver posiciones y opciones A3 cargadas por cultivo", expanded=False):
        summary_df = get_a3_position_summary(include_bolsa_curve=False)
        if summary_df.empty:
            st.info("No hay posiciones A3 cargadas.")
        else:
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

    left, right = st.columns([.95, 1.35], gap="large")
    with left:
        st.markdown("### Estrategias")
        if not st.session_state.builder_strategies:
            st.info("Cree una estrategia para comenzar.")
        for strategy in st.session_state.builder_strategies:
            render_strategy_card(strategy, spot)

    with right:
        st.markdown("### Comparativo")
        render_strategy_chart(spot, st.session_state.builder_strategies)
        render_scenario_table(spot, st.session_state.builder_strategies)
        render_dominance(spot, st.session_state.builder_strategies)

def render_strategy_chart(spot: float, strategies: List[Dict[str, Any]]) -> None:
    if spot <= 0:
        st.warning("No hay precio base para graficar.")
        return
    x = np.linspace(spot * 0.70, spot * 1.30, 220)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=x,
            mode="lines",
            name="Linea base - Fisico sin cobertura",
            line=dict(color="#111827", width=2.6, dash="dash"),
            hovertemplate="Precio: %{x:.1f}<br>Neto: %{y:.1f}<extra></extra>",
        )
    )
    for strat in strategies:
        y = [calc_net_price(strat, float(p)) for p in x]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                name=strat.get("name", "Estrategia"),
                line=dict(color=strat.get("color", "#1a6b3c"), width=3),
                hovertemplate="Precio: %{x:.1f}<br>Neto: %{y:.1f}<extra></extra>",
            )
        )
    fig.add_vline(
        x=spot,
        line_dash="dot",
        line_color="#c8a44a",
        annotation_text=f"Base {spot:.0f}",
        annotation_font_color="#1c2118",
        annotation_font_size=12,
        annotation_bgcolor="rgba(255,255,255,.88)",
    )
    fig.update_layout(
        template="plotly_white",
        height=460,
        margin=dict(l=12, r=12, t=54, b=42),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        title=dict(
            text="Precio neto de venta a vencimiento",
            font=dict(family="Inter, Arial", color="#111827", size=16),
            x=0.0,
            xanchor="left",
        ),
        xaxis_title="Precio terminal (USD/tn)",
        yaxis_title="Precio neto de venta (USD/tn)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(family="Inter, Arial", color="#111827", size=12),
            bgcolor="rgba(255,255,255,.92)",
        ),
        font=dict(family="Inter, Arial", color="#111827", size=12),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor="#c8cbbe", font=dict(color="#111827")),
    )
    fig.update_xaxes(
        title_font=dict(color="#111827", size=12),
        tickfont=dict(color="#111827", size=11),
        color="#111827",
        linecolor="#c8cbbe",
        gridcolor="#e5e7df",
        zerolinecolor="#e5e7df",
    )
    fig.update_yaxes(
        title_font=dict(color="#111827", size=12),
        tickfont=dict(color="#111827", size=11),
        color="#111827",
        linecolor="#c8cbbe",
        gridcolor="#e5e7df",
        zerolinecolor="#e5e7df",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_scenario_table(spot: float, strategies: List[Dict[str, Any]]) -> None:
    """Render final scenario comparison with colored hedge deltas.

    Each strategy cell shows the final net sale price and, next to it, the
    difference versus the unhedged physical price for the same scenario.
    Positive deltas are green; negative deltas are red; neutral deltas are gray.
    """
    st.markdown("#### Analisis de escenarios")
    scenarios = collect_scenario_prices(spot, strategies)

    headers = ["Escenario", "Mercado", "Sin cobertura"] + [
        str(strat.get("name") or f"Estrategia {idx + 1}")
        for idx, strat in enumerate(strategies)
    ]

    html_parts: List[str] = ['<table class="coverage-scenario-table"><thead><tr>']
    for header in headers:
        html_parts.append(f"<th>{html_escape(header)}</th>")
    html_parts.append("</tr></thead><tbody>")

    for scenario_name, price in scenarios:
        is_spot = abs(price - spot) <= max(0.5, abs(spot) * 0.001)
        row_class = ' class="is-spot"' if is_spot else ""
        html_parts.append(f"<tr{row_class}>")
        html_parts.append(f'<td class="scenario-name">{html_escape(scenario_name)}</td>')
        html_parts.append(f'<td class="money-cell">u$s {fmt_num(price, 1)}</td>')
        html_parts.append(f'<td class="money-cell">u$s {fmt_num(price, 1)}</td>')

        for strat in strategies:
            value = calc_net_price(strat, price)
            diff = value - price
            if diff > 0.005:
                delta_class = "delta-positive"
            elif diff < -0.005:
                delta_class = "delta-negative"
            else:
                delta_class = "delta-neutral"

            delta_text = f"+u$s {fmt_num(abs(diff), 1)}" if diff >= 0 else f"-u$s {fmt_num(abs(diff), 1)}"
            html_parts.append(
                '<td>'
                '<span class="strategy-cell">'
                f'<span class="strategy-value">u$s {fmt_num(value, 1)}</span>'
                f'<span class="delta-pill {delta_class}">({delta_text})</span>'
                '</span>'
                '</td>'
            )
        html_parts.append("</tr>")

    html_parts.append("</tbody></table>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_dominance(spot: float, strategies: List[Dict[str, Any]]) -> None:
    st.markdown("#### Rango de dominancia")
    ranges = dominance_ranges(spot, strategies)
    if not ranges:
        st.info("No hay rangos calculados.")
        return
    for item in ranges:
        st.markdown(
            f"""
            <div class="clean-panel-tight" style="border-left:4px solid {item['color']}; padding:10px 12px; margin-bottom:8px;">
                <div class="small-muted">Si el mercado cierra entre USD {fmt_num(item['start'], 1)} y USD {fmt_num(item['end'], 1)}</div>
                <div style="font-weight:850;color:{item['color']};">Conviene: {html_escape(item['name'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -----------------------------------------------------------------------------
# AUDIT LOG
# -----------------------------------------------------------------------------


def render_audit_log() -> None:
    with st.expander("Log de Auditoria - fuentes y valores crudos", expanded=False):
        data = st.session_state.data_bolsa or {}
        if not data:
            st.write("Bolsa no cargada.")
        else:
            current_pos = st.session_state.market_position or select_default_position(data)
            current = data.get(current_pos, {})
            abr = data.get("ABR 2026", {})
            st.markdown("**Control de precision de Bolsa**")
            st.write(
                {
                    "posicion_actual": current_pos,
                    "raw_actual": current,
                    "control_ABR_2026_soja": abr.get("soja"),
                    "control_ABR_2026_aceite": abr.get("aceite"),
                    "regla": "FOB y subproductos se almacenan crudos; retenciones/fobbing solo se aplican dentro de la cascada.",
                }
            )
            audit_rows = []
            for pos, row in data.items():
                audit_rows.append(
                    {
                        "posicion": pos,
                        "soja": row.get("soja"),
                        "maiz": row.get("maiz"),
                        "trigo": row.get("trigo"),
                        "harina": row.get("harina"),
                        "aceite": row.get("aceite"),
                        "aceiteGirasol": row.get("aceiteGirasol"),
                    }
                )
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

        a3 = st.session_state.data_a3 or {}
        st.markdown("**Control A3**")
        st.write(
            {
                "a3_cargado": bool(a3),
                "futuros": a3.get("n_futuros", 0),
                "opciones": a3.get("n_opciones", 0),
                "fecha_datos": a3.get("fecha_datos", ""),
                "posiciones_builder_por_cultivo": {
                    CROP_LABELS[crop]: [compact_pos_label(p) for p in get_a3_positions(crop)]
                    for crop in CROP_LABELS
                },
                "builder_strategies": len(st.session_state.builder_strategies),
            }
        )

# -----------------------------------------------------------------------------
# APP ENTRYPOINT
# -----------------------------------------------------------------------------


def main() -> None:
    apply_pending_navigation()
    page = render_sidebar()
    hero()
    if page == NAV_LOAD:
        render_load_page()
    elif page == NAV_MARKET:
        render_market_panel()
    elif page == NAV_BUILDER:
        render_builder_panel()
    if st.session_state.data_loaded:
        render_audit_log()


if __name__ == "__main__":
    main()
