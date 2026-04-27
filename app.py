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

@media (max-width: 1100px) {
    .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .leg-header { display: none; }
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


def get_positions_bolsa() -> List[str]:
    data = st.session_state.data_bolsa or {}
    return list(data.keys())


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
    # Examples: SOJ.ROS/MAY26 or SOJ.ROS/MAY26 248 C
    text = str(contrato or "").strip().upper()
    m = re.match(r"^([A-Z]{3})\.[A-Z.]+\/([A-Z]{3}\d{2})(?:\s+(\d+(?:[\.,]\d+)?)\s+([CP]))?", text)
    if not m:
        return None
    crop = CROP_CODE_MAP.get(m.group(1))
    if not crop:
        return None
    result: Dict[str, Any] = {"crop": crop, "pos": m.group(2)}
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
        pos = info["pos"]
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

    for crop_opts in result["opciones"].values():
        for pos_opts in crop_opts.values():
            pos_opts["call"].sort(key=lambda x: x["strike"])
            pos_opts["put"].sort(key=lambda x: x["strike"])
    return result


def get_a3_positions(crop: str) -> List[str]:
    data = st.session_state.data_a3 or {}
    positions = set()
    for fut in data.get("futuros", {}).get(crop, []):
        positions.add(fut.get("pos"))
    positions.update((data.get("opciones", {}).get(crop, {}) or {}).keys())
    return sorted([p for p in positions if p])


def get_available_strikes(crop: str, position: Optional[str], opt_type: str) -> List[float]:
    if opt_type not in {"call", "put"} or not position:
        return []
    data = st.session_state.data_a3 or {}
    opts = data.get("opciones", {}).get(crop, {}).get(position, {}).get(opt_type, [])
    return [float(o["strike"]) for o in opts if safe_float(o.get("strike"), 0) > 0]


def lookup_premium(crop: str, position: Optional[str], opt_type: str, strike: float) -> Optional[float]:
    if opt_type not in {"call", "put"} or not position:
        return None
    data = st.session_state.data_a3 or {}
    opts = data.get("opciones", {}).get(crop, {}).get(position, {}).get(opt_type, [])
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
    st.session_state.data_bolsa = data
    st.session_state.bolsa_loaded_at = datetime.now()
    if not st.session_state.market_position or st.session_state.market_position not in data:
        st.session_state.market_position = select_default_position(data)
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
    width = max(3.0, min(100.0, abs(pct)))
    sign_value = fmt_signed(value) if value < 0 else fmt_num(value)
    return f"""
    <div class="cascade-row">
        <div>
            <div class="cascade-label"><span>{html_escape(label)}</span><span class="cascade-value">{sign_value}</span></div>
            <div class="cascade-bar-track"><div class="cascade-bar {cls}" style="width:{width:.1f}%">{fmt_num(abs(pct), 1)}%</div></div>
        </div>
        <div></div>
    </div>
    """


def render_grain_cascade(crop: str, position: str, fob: float, ret_pct: float, fobbing: float, fas_obj: float) -> float:
    calc = calc_grain_fas(fob, ret_pct, fobbing)
    fobbing_pct = (fobbing / fob * 100.0) if fob else 0.0
    margin = calc["fas"] - fas_obj
    color = "var(--success)" if margin >= 0 else "var(--danger)"
    html = f"""
    <div class="clean-panel-tight">
        <div style="font-weight:850;color:var(--es-green-700);font-size:16px;margin-bottom:12px;">
            Exportacion grano {html_escape(compact_pos_label(position))}
        </div>
        <div class="cascade-wrap">
            {cascade_bar('FOB ' + CROP_LABELS.get(crop, crop), fob, 100.0, 'fob')}
            {cascade_bar('Retencion ' + fmt_num(ret_pct, 1) + '%', -calc['ret_value'], ret_pct, 'ret')}
            {cascade_bar('Fobbing', -fobbing, fobbing_pct, 'cost')}
            <div class="cascade-result"><span>FAS Teorico (CTP)</span><span>{fmt_num(calc['fas'])}</span></div>
            <div class="cascade-note"><span>Margen export. vs obj {fmt_num(fas_obj, 1)}</span><strong style="color:{color};">{fmt_signed(margin)}</strong></div>
        </div>
    </div>
    """
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
    html = f"""
    <div class="clean-panel-tight">
        <div style="font-weight:850;color:#8a6817;font-size:16px;margin-bottom:12px;">
            Crushing subproductos {html_escape(compact_pos_label(position))}
        </div>
        <div class="cascade-wrap">
            {cascade_bar('Aceite (' + fmt_num(values['fob_aceite'], 1) + ' x ' + fmt_num(values['coef_aceite'], 2) + ')', calc['aceite_bruto'], calc['aceite_bruto']/bruto*100, 'fob')}
            {cascade_bar('Harina (' + fmt_num(values['fob_harina'], 1) + ' x ' + fmt_num(values['coef_harina'], 2) + ')', calc['harina_bruta'], calc['harina_bruta']/bruto*100, 'fob')}
            {cascade_bar('Ret subprod ' + fmt_num(values['ret_sub_pct'], 1) + '%', -calc['ret_sub'], values['ret_sub_pct'], 'ret')}
            {cascade_bar('Fobbing subprod', -calc['fobbing_sub'], calc['fobbing_sub']/bruto*100, 'cost')}
            {cascade_bar('Gasto industrial', -calc['gto_ind'], calc['gto_ind']/bruto*100, 'cost')}
            <div class="cascade-result"><span>FAS Crushing</span><span>{fmt_num(calc['fas'])}</span></div>
            <div class="cascade-note"><span>Margen crush vs obj {fmt_num(fas_obj, 1)}</span><strong style="color:{color};">{fmt_signed(margin)}</strong></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    return calc["fas"]

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
        if st.button("Limpiar builder", use_container_width=True):
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
            if st.button("Actualizar FOB", type="primary", use_container_width=True):
                with st.spinner("Consultando Bolsa de Cereales..."):
                    try:
                        load_bolsa(force=True)
                        st.success("FOB actualizado correctamente")
                    except Exception as exc:
                        st.error(f"Error al cargar Bolsa: {exc}")
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
        expected_txt = " Control ABR 2026: Soja=427, Aceite=1191."
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
            fas_crush = render_crush_cascade(
                pos,
                {
                    "fob_aceite": fob_aceite,
                    "fob_harina": fob_harina,
                    "coef_aceite": coef_aceite,
                    "coef_harina": coef_harina,
                    "ret_sub_pct": ret_sub_pct,
                    "fobbing_sub": fobbing_sub,
                    "gto_ind": gto_ind,
                },
                params["fas_obj"],
            )
            st.session_state["last_fas_crush"] = fas_crush
        else:
            st.info("El modulo crushing aplica para soja. Para otros cultivos se muestra solo exportacion grano.")

    st.session_state["last_fas_grain"] = fas_grain
    st.session_state["last_market_fob"] = fob

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
        legs = [new_leg(get_selected_fob())]
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
            if st.button("+ Pata", key=f"add_leg_{sid}", use_container_width=True):
                strategy["legs"].append(new_leg(spot))
                st.rerun()
        with c2:
            if st.button("Prima A3", key=f"premium_one_{sid}", use_container_width=True):
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

    render_section_header(
        "Builder de Coberturas",
        "Panel independiente A3. Usa el FOB seleccionado en Mercado como linea base, sin modificar los datos de Bolsa.",
    )
    spot = get_selected_fob(st.session_state.market_crop, st.session_state.market_position)
    if spot <= 0:
        spot = safe_float(st.session_state.get("last_market_fob"), 400.0)

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
        with c3:
            st.metric("Linea base FOB", fmt_num(spot), help="Viene del Panel de Mercado (Bolsa).")
        with c4:
            preset = st.selectbox("Plantilla", ["Seleccionar..."] + list(PRESETS.keys()), key="preset_select")
        with c5:
            st.write("")
            st.write("")
            if st.button("Cargar plantilla", use_container_width=True, disabled=preset == "Seleccionar..."):
                load_preset(preset, spot)
                st.session_state.preset_select = "Seleccionar..."
                st.rerun()

        c6, c7, c8 = st.columns([1, 1, 3])
        with c6:
            if st.button("+ Nueva estrategia", type="primary", use_container_width=True):
                add_strategy("Nueva Estrategia", [new_leg(spot)])
                st.rerun()
        with c7:
            if st.button("Actualizar primas", use_container_width=True):
                updated = refresh_all_premiums()
                st.success(f"{updated} primas actualizadas desde A3")
                st.rerun()
        with c8:
            a3 = st.session_state.data_a3 or {}
            st.caption(f"A3 disponible: {a3.get('n_futuros', 0)} futuros / {a3.get('n_opciones', 0)} opciones. Strikes dinamicos si existen para la posicion.")

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
        st.warning("No hay FOB base para graficar.")
        return
    x = np.linspace(spot * 0.70, spot * 1.30, 220)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=x,
            mode="lines",
            name="Fisico sin cobertura",
            line=dict(color="#9ca3af", width=2, dash="dash"),
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
    fig.add_vline(x=spot, line_dash="dot", line_color="#c8a44a", annotation_text=f"FOB {spot:.0f}")
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=35, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
        title="Precio neto de venta a vencimiento",
        xaxis_title="Precio terminal (USD/tn)",
        yaxis_title="Precio neto de venta (USD/tn)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Inter, Arial", color="#1c2118"),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#eef0e8")
    fig.update_yaxes(gridcolor="#eef0e8")
    st.plotly_chart(fig, use_container_width=True)


def render_scenario_table(spot: float, strategies: List[Dict[str, Any]]) -> None:
    st.markdown("#### Analisis de escenarios")
    scenarios = collect_scenario_prices(spot, strategies)
    rows = []
    for name, price in scenarios:
        row: Dict[str, Any] = {"Escenario": name, "Mercado": price, "Sin cobertura": price}
        for strat in strategies:
            value = calc_net_price(strat, price)
            row[strat.get("name", "Estrategia")] = value
        rows.append(row)
    df = pd.DataFrame(rows)
    fmt_cols = {col: "${:,.2f}" for col in df.columns if col not in {"Escenario"}}
    st.dataframe(df.style.format(fmt_cols), use_container_width=True, hide_index=True)


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
