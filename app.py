"""
Estrategias de Cobertura - Espartina S.A.
Streamlit app refactorizada con separacion de fuentes:
- data_bolsa: FOB / Retenciones / FAS teorico.
- data_a3: Futuros / Calls / Puts para builder de estrategias.

Objetivo de arquitectura:
1) El FOB de Bolsa se conserva como dato fuente inmutable.
2) La cascada FAS usa ese FOB como punto de partida, sin descuentos previos.
3) El builder toma el FOB/FAS como linea base, pero A3 solo alimenta strikes/primas.
"""

from __future__ import annotations

import html
import io
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from estrategias_engine import Leg, Strategy
from estrategias_presets import create_preset_strategies, get_strategy_alerts
from google_sheets import obtener_datos_a3
from scraper import obtener_datos_bolsa

# -----------------------------------------------------------------------------
# Page config
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Estrategias de Cobertura - Espartina S.A.",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

COLORS = ["#1A6B3C", "#2563eb", "#d97706", "#7c3aed", "#c43030", "#0d9488"]
CROP_LABELS = {"soja": "Soja", "maiz": "Maiz", "trigo": "Trigo", "girasol": "Girasol"}
CROP_CODES = {"SOJ": "soja", "MAI": "maiz", "TRI": "trigo", "GIR": "girasol"}
CROP_TO_FOB_KEY = {"soja": "soja", "maiz": "maiz", "trigo": "trigo", "girasol": "girasol"}

RET_DEFAULTS = {
    "soja": {"ret": 26.0, "fobbing": 12.0, "fas_obj": 323.0},
    "maiz": {"ret": 7.0, "fobbing": 11.0, "fas_obj": 185.0},
    "trigo": {"ret": 7.0, "fobbing": 13.0, "fas_obj": 216.0},
    "girasol": {"ret": 7.0, "fobbing": 14.0, "fas_obj": 475.0},
}

FALLBACK_FOB = {"soja": 427.0, "maiz": 215.0, "trigo": 224.0, "girasol": 520.0}

# -----------------------------------------------------------------------------
# CSS / Design system
# -----------------------------------------------------------------------------

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{
  --es-green:#1A6B3C;--es-green-dark:#145430;--es-green-light:#e8f5ec;--es-green-muted:#2d8a54;
  --es-gold:#C8A44A;--es-gold-light:#f9f3e3;--bg:#f4f5f0;--bg-card:#ffffff;--bg-input:#f0f1ec;
  --text:#1c2118;--text-2:#505845;--text-3:#7e8574;--border:#dde0d5;--border-2:#c8cbbe;
  --green:#1a854a;--red:#c43030;--blue:#2563eb;--orange:#d97706;
  --font:'DM Sans',system-ui,sans-serif;--mono:'JetBrains Mono',ui-monospace,monospace;
  --radius:10px;--shadow:0 1px 4px rgba(26,107,60,.06),0 1px 2px rgba(0,0,0,.04);
  --shadow-lg:0 4px 16px rgba(26,107,60,.08),0 2px 6px rgba(0,0,0,.04);
}
html,body,[class*="css"]{font-family:var(--font)!important;}
.stApp{background:var(--bg)!important;color:var(--text)!important;}
.block-container{max-width:1320px;padding-top:16px;padding-bottom:36px;}
section[data-testid="stSidebar"]{background:#f7f8f3!important;border-right:1px solid var(--border);}
section[data-testid="stSidebar"] *{color:var(--text)!important;}
h1,h2,h3{color:var(--text)!important;letter-spacing:-.25px;}
.stMarkdown p,.stCaption,label{color:var(--text-2)!important;}
.main-header{background:linear-gradient(135deg,var(--es-green-dark) 0%,var(--es-green) 60%,var(--es-green-muted) 100%);padding:16px 24px;border-radius:12px;margin-bottom:18px;box-shadow:0 2px 12px rgba(20,84,48,.25);border-bottom:3px solid var(--es-gold);display:flex;align-items:center;gap:14px;}
.main-header .logo{width:38px;height:38px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.12);font-size:20px;}
.main-header h1{color:#fff!important;margin:0;font-size:22px;font-weight:800;}
.main-header p{color:rgba(255,255,255,.68)!important;margin:1px 0 0;font-size:12px;}
.header-badge{margin-left:auto;background:rgba(200,164,74,.2);border:1px solid rgba(200,164,74,.35);color:var(--es-gold);font-size:10px;font-weight:800;padding:4px 10px;border-radius:20px;letter-spacing:.7px;text-transform:uppercase;}
div.stButton>button{background:var(--es-green)!important;color:#fff!important;border:1px solid var(--es-green)!important;border-radius:8px!important;min-height:36px!important;padding:7px 12px!important;font-size:12px!important;font-weight:800!important;white-space:nowrap!important;line-height:1.1!important;box-shadow:0 1px 3px rgba(26,107,60,.16)!important;}
div.stButton>button:hover{background:var(--es-green-dark)!important;transform:translateY(-1px);box-shadow:0 3px 8px rgba(26,107,60,.2)!important;}
section[data-testid="stSidebar"] div.stButton>button{width:100%!important;background:var(--es-gold)!important;border-color:var(--es-gold)!important;color:#fff!important;min-height:42px!important;font-size:13px!important;}
div[data-baseweb="select"]>div,input,textarea{background:var(--bg-input)!important;border-color:var(--border)!important;border-radius:7px!important;color:var(--text)!important;font-family:var(--mono)!important;}
div[data-baseweb="select"]>div:focus-within,input:focus,textarea:focus{border-color:var(--es-green)!important;box-shadow:0 0 0 3px rgba(26,107,60,.10)!important;}
.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:2px solid var(--border);padding-bottom:10px;overflow-x:auto;}
.stTabs [data-baseweb="tab"]{background:var(--bg-card);border:1px solid var(--border);color:var(--text-2);border-radius:8px;padding:9px 16px;font-size:13px;font-weight:800;box-shadow:var(--shadow);white-space:nowrap;}
.stTabs [aria-selected="true"]{background:var(--es-green)!important;color:#fff!important;border-color:var(--es-green)!important;}
.top-panel{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;margin-bottom:16px;box-shadow:var(--shadow);}
.compact-card{background:var(--bg-card);border:1px solid var(--border);border-left:4px solid var(--es-green);border-radius:var(--radius);padding:12px 14px;box-shadow:var(--shadow);margin-bottom:8px;}
.card-title{font-weight:800;font-size:14px;color:var(--text);margin-bottom:4px;}.card-desc{font-size:12px;color:var(--text-3);line-height:1.45;margin-bottom:8px;}.card-cost{font-family:var(--mono);font-size:12px;font-weight:800;}.debit{color:var(--red)}.credit{color:var(--green)}.zero{color:var(--text-3)}
.strategy-shell{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:14px 14px 10px;margin-bottom:14px;border-left:4px solid var(--es-green);}
.leg-header{display:grid;grid-template-columns:1.3fr 1.15fr .9fr 1fr 1fr .35fr;gap:8px;font-size:10px;color:var(--text-3);font-weight:900;letter-spacing:.04em;text-transform:uppercase;margin:4px 0 2px;padding:0 4px;}
.leg-wrap{background:var(--bg-input);border:1px solid transparent;border-radius:8px;padding:7px 8px;margin-bottom:7px;}
.kpi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;padding-top:10px;border-top:1px dashed var(--border);}.kpi-card{background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 7px;text-align:center;}.k-lbl{font-size:9px;text-transform:uppercase;color:var(--text-3);font-weight:900;letter-spacing:.05em;margin-bottom:3px;}.k-val{font-size:13px;font-weight:900;font-family:var(--mono);}
.fas-info-bar{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 16px;}.fas-chip{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:10px 14px;min-width:175px;}.fas-chip .lbl{color:var(--text-3);font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:.05em}.fas-chip .val{font-family:var(--mono);font-size:17px;font-weight:900;color:var(--text)}
.cascade-panel{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow);margin-bottom:14px;}.cascade-title{font-size:15px;font-weight:900;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}.bar-row{margin-bottom:8px}.bar-labels{display:flex;justify-content:space-between;margin-bottom:3px}.bar-name{font-size:12px;color:var(--text-2)}.bar-val{font-size:12px;font-family:var(--mono);font-weight:800}.bar{height:24px;border-radius:5px;display:flex;align-items:center;padding-left:8px;font-size:11px;font-family:var(--mono);font-weight:800}.result-row{margin-top:12px;padding-top:12px;border-top:2px solid var(--border);display:flex;justify-content:space-between;align-items:baseline}.result-lbl{font-size:13px;font-weight:900}.result-val{font-size:24px;font-weight:900;font-family:var(--mono)}.margin-row{background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;margin-top:10px}.tri-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.tri-chip{background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:8px 10px}.tri-lbl{font-size:10px;color:var(--text-3);font-weight:900;text-transform:uppercase;letter-spacing:.04em}.tri-val{font-size:14px;font-weight:900;font-family:var(--mono);margin-top:2px}.tri-sub{font-size:10px;color:var(--text-3)}
.winner-box{background:var(--bg-card);border:1px solid var(--border);border-left:4px solid var(--es-gold);border-radius:8px;padding:10px 12px;margin-bottom:8px;box-shadow:var(--shadow)}.winner-range{font-family:var(--mono);font-size:12px;color:var(--text-2);margin-bottom:3px}.winner-name{font-size:14px;font-weight:900}.section-title{font-size:13px;font-weight:900;color:var(--text-2);text-transform:uppercase;letter-spacing:.06em;margin:10px 0 12px;display:flex;align-items:center;gap:8px}.section-title::before{content:'';display:inline-block;width:4px;height:16px;background:var(--es-green);border-radius:2px}.note{background:var(--es-gold-light);border:1px solid var(--es-gold);border-radius:var(--radius);padding:12px 16px;font-size:12px;color:var(--text-2);line-height:1.6;margin-top:6px}.footer{text-align:center;padding:2rem;color:var(--text-3);font-size:.85rem;margin-top:2rem;border-top:1px solid var(--border)}
[data-testid="stDataFrame"]{border-radius:var(--radius);overflow:hidden;border:1px solid var(--border);box-shadow:var(--shadow)}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Session state and migration
# -----------------------------------------------------------------------------


def init_state() -> None:
    defaults = {
        "data_bolsa": {"cotizaciones": None, "last_update": None, "source": "Bolsa de Cereales"},
        "data_a3": {"raw_df": None, "market": None, "last_update": None, "source": "A3 Google Sheet"},
        "builder_strategies": [],
        "strategy_counter": 1,
        "force_sync_fob": False,
        "active_fob_signature": None,
        "fas_context": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Backward compatibility with earlier app versions.
    if st.session_state.get("datos_bolsa") is not None and not st.session_state.data_bolsa.get("cotizaciones"):
        st.session_state.data_bolsa = {
            "cotizaciones": st.session_state.get("datos_bolsa"),
            "last_update": st.session_state.get("ultima_actualizacion"),
            "source": "Bolsa de Cereales",
        }
    if st.session_state.get("datos_a3") is not None and st.session_state.data_a3.get("raw_df") is None:
        st.session_state.data_a3["raw_df"] = st.session_state.get("datos_a3")
        st.session_state.data_a3["market"] = st.session_state.get("a3_market")


init_state()

# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def html_block(markup: str) -> None:
    st.markdown(markup.strip(), unsafe_allow_html=True)


def slug_crop(label: str) -> str:
    s = label.lower().strip().replace("í", "i").replace("á", "a")
    return {"soja": "soja", "maiz": "maiz", "maíz": "maiz", "trigo": "trigo", "girasol": "girasol"}.get(s, "soja")


def money(value: float, digits: int = 1) -> str:
    return f"${value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_num(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    s = str(value).strip()
    if s in {"", "-", "N/A", "nan", "None"}:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def safe_style_map(styler: pd.io.formats.style.Styler, func, subset):
    # Pandas >= 2.1 uses Styler.map; older versions use applymap.
    if hasattr(styler, "map"):
        return styler.map(func, subset=subset)
    return styler.applymap(func, subset=subset)


# -----------------------------------------------------------------------------
# Bolsa data helpers - source A
# -----------------------------------------------------------------------------


def get_bolsa_quotes() -> Dict[str, Dict[str, float]]:
    return st.session_state.data_bolsa.get("cotizaciones") or {}


def get_bolsa_positions() -> List[str]:
    return list(get_bolsa_quotes().keys())


def get_source_fob(crop: str, position: Optional[str]) -> Optional[float]:
    if not position:
        return None
    quotes = get_bolsa_quotes().get(position)
    if not quotes:
        return None
    key = CROP_TO_FOB_KEY.get(crop, "soja")
    value = quotes.get(key)
    if value is None:
        return None
    return float(value)


def get_source_byproducts(position: Optional[str]) -> Dict[str, float]:
    if not position:
        return {}
    return get_bolsa_quotes().get(position, {}) or {}


def sync_fob_widget_with_source(crop: str, position: Optional[str], source_fob: float) -> None:
    """Keep the FOB widget aligned with source changes without resetting user edits.

    Reset only when source signature changes or when user explicitly refreshes FOB.
    """
    signature = f"{crop}|{position}|{source_fob:.6f}"
    should_sync = st.session_state.get("force_sync_fob") or st.session_state.get("active_fob_signature") != signature
    if should_sync:
        st.session_state["ret_fob_indice"] = float(source_fob)
        st.session_state["active_fob_signature"] = signature
        st.session_state["force_sync_fob"] = False


# -----------------------------------------------------------------------------
# A3 parser and market helpers - source B
# -----------------------------------------------------------------------------


def parse_contrato(contrato: str) -> Optional[Dict[str, Any]]:
    pattern = r"^([A-Z]{3})\.[A-Z.]+\/([A-Z0-9]+)(?:\s+(\d+(?:\.\d+)?)\s+([CP]))?$"
    match = re.match(pattern, contrato.strip().upper())
    if not match:
        return None
    crop = CROP_CODES.get(match.group(1))
    if not crop:
        return None
    result: Dict[str, Any] = {"crop": crop, "pos": match.group(2)}
    if match.group(3) and match.group(4):
        result["strike"] = float(match.group(3))
        result["type"] = "call" if match.group(4) == "C" else "put"
    return result


def col_find(cols: List[str], *needles: str) -> int:
    for index, column in enumerate(cols):
        if all(needle.lower() in column for needle in needles):
            return index
    return -1


def parse_a3_market(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    if df is None or df.empty:
        return None

    headers = [str(c).strip().lower() for c in df.columns]
    c_contrato = col_find(headers, "contrato")
    if c_contrato < 0:
        c_contrato = 0
    c_vto = col_find(headers, "vencimiento")
    c_moneda = col_find(headers, "moneda")
    c_tipo = col_find(headers, "tipo")
    c_pc = col_find(headers, "put")
    c_ajuste = col_find(headers, "ajuste")
    if c_ajuste < 0:
        c_ajuste = col_find(headers, "valor")
    if c_ajuste < 0:
        c_ajuste = col_find(headers, "precio")
    c_ia = col_find(headers, "inter", "abierto")
    c_fecha = col_find(headers, "fecha")

    futuros: Dict[str, List[Dict[str, Any]]] = {}
    opciones: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {}
    fecha = ""

    for _, row in df.iterrows():
        values = list(row.values)
        contrato = str(values[c_contrato]).strip() if c_contrato < len(values) else ""
        if not contrato or contrato.lower() == "nan":
            continue
        info = parse_contrato(contrato)
        if not info:
            continue
        moneda = str(values[c_moneda]).strip().upper() if 0 <= c_moneda < len(values) else "USD"
        if moneda and moneda != "USD":
            continue
        tipo = str(values[c_tipo]).strip().lower() if 0 <= c_tipo < len(values) else ""
        put_call = str(values[c_pc]).strip().upper() if 0 <= c_pc < len(values) else ""
        ajuste = parse_num(values[c_ajuste]) if 0 <= c_ajuste < len(values) else 0.0
        ia = parse_num(values[c_ia]) if 0 <= c_ia < len(values) else 0.0
        vto = str(values[c_vto]).strip() if 0 <= c_vto < len(values) else ""
        if not fecha and 0 <= c_fecha < len(values):
            fecha = str(values[c_fecha]).strip()

        crop = info["crop"]
        pos = info["pos"]
        if "futuro" in tipo or ("strike" not in info and "opci" not in tipo):
            futuros.setdefault(crop, []).append({"posicion": pos, "ajuste": ajuste, "vencimiento": vto, "ia": ia, "contrato": contrato})
        elif "opci" in tipo or "strike" in info:
            opt_type = info.get("type") or ("call" if put_call == "CALL" else "put")
            opciones.setdefault(crop, {}).setdefault(pos, {"calls": [], "puts": []})
            key = "calls" if opt_type == "call" else "puts"
            opciones[crop][pos][key].append({"strike": float(info.get("strike", 0)), "prima": ajuste, "contrato": contrato})

    for crop_opts in opciones.values():
        for pos_opts in crop_opts.values():
            pos_opts["calls"].sort(key=lambda item: item["strike"])
            pos_opts["puts"].sort(key=lambda item: item["strike"])

    if not futuros and not opciones:
        return None
    return {"futuros": futuros, "opciones": opciones, "metadata": {"fecha_datos": fecha or datetime.now().strftime("%d/%m/%Y")}}


def get_a3_market() -> Optional[Dict[str, Any]]:
    return st.session_state.data_a3.get("market")


def get_market_positions(crop: str) -> List[str]:
    market = get_a3_market()
    if not market:
        return []
    return [item["posicion"] for item in market.get("futuros", {}).get(crop, []) if float(item.get("ajuste", 0) or 0) > 0]


def get_market_future(crop: str, position: Optional[str]) -> Optional[float]:
    if not position:
        return None
    market = get_a3_market()
    if not market:
        return None
    for item in market.get("futuros", {}).get(crop, []):
        if item.get("posicion") == position:
            value = float(item.get("ajuste", 0) or 0)
            return value if value > 0 else None
    return None


def get_available_strikes(crop: str, position: Optional[str], option_type: str) -> List[float]:
    if not position or option_type == "futuro":
        return []
    market = get_a3_market()
    if not market:
        return []
    position_options = market.get("opciones", {}).get(crop, {}).get(position, {})
    key = "calls" if option_type == "call" else "puts"
    return [float(item["strike"]) for item in position_options.get(key, []) if item.get("strike")]


def lookup_prima(crop: str, position: Optional[str], option_type: str, strike: float) -> Optional[float]:
    if option_type == "futuro":
        return 0.0
    if not position:
        return None
    market = get_a3_market()
    if not market:
        return None
    position_options = market.get("opciones", {}).get(crop, {}).get(position, {})
    key = "calls" if option_type == "call" else "puts"
    for item in position_options.get(key, []):
        if abs(float(item.get("strike", 0)) - float(strike)) < 0.001:
            return float(item.get("prima", 0))
    return None


# -----------------------------------------------------------------------------
# Strategy model helpers
# -----------------------------------------------------------------------------


def leg_to_dict(leg: Leg) -> Dict[str, Any]:
    return {
        "direction": leg.direction,
        "type": leg.type,
        "ratio": float(leg.ratio),
        "strike": float(leg.strike),
        "prima": float(leg.prima),
    }


def new_strategy(name: Optional[str] = None, legs: Optional[List[Dict[str, Any]]] = None, color: Optional[str] = None) -> Dict[str, Any]:
    idx = int(st.session_state.strategy_counter)
    st.session_state.strategy_counter += 1
    return {
        "id": idx,
        "name": name or f"Estrategia {idx}",
        "color": color or COLORS[(idx - 1) % len(COLORS)],
        "legs": legs or [],
    }


def option_cost(strategy: Dict[str, Any]) -> float:
    cost = 0.0
    for leg in strategy.get("legs", []):
        if leg.get("type") == "futuro":
            continue
        qty = float(leg.get("ratio", 1) or 1)
        premium = float(leg.get("prima", 0) or 0)
        cost += premium * qty if leg.get("direction") == "buy" else -premium * qty
    return cost


def net_sale_value(strategy: Dict[str, Any], price: float) -> float:
    """HTML-compatible payoff: physical price + derivative payoff - net premium."""
    net_premium = 0.0
    derivative_payoff = 0.0
    for leg in strategy.get("legs", []):
        direction = leg.get("direction", "buy")
        leg_type = leg.get("type", "put")
        qty = float(leg.get("ratio", 1) or 1)
        strike = float(leg.get("strike", 0) or 0)
        premium = float(leg.get("prima", 0) or 0)

        if leg_type == "futuro":
            intrinsic = price - strike
            derivative_payoff += intrinsic * qty if direction == "buy" else -intrinsic * qty
            continue

        intrinsic = max(strike - price, 0) if leg_type == "put" else max(price - strike, 0)
        if direction == "buy":
            net_premium += premium * qty
            derivative_payoff += intrinsic * qty
        else:
            net_premium -= premium * qty
            derivative_payoff -= intrinsic * qty
    return price + derivative_payoff - net_premium


def strategy_kpis(strategy: Dict[str, Any], spot: float) -> Tuple[str, str, str]:
    values = [net_sale_value(strategy, p) for p in range(1, 1501)]
    floor = min(values)
    ceiling = max(values)
    floor_text = "Riesgo baja" if floor < spot * 0.5 else money(floor, 1)
    ceiling_text = "Ilimitado" if ceiling > 1400 else money(ceiling, 1)

    breakevens = []
    prev_diff = net_sale_value(strategy, 1) - 1
    for price in range(2, 801):
        diff = net_sale_value(strategy, price) - price
        if (prev_diff < 0 <= diff) or (prev_diff > 0 >= diff):
            breakevens.append(price)
        prev_diff = diff

    cost = option_cost(strategy)
    has_options = any(leg.get("type") != "futuro" for leg in strategy.get("legs", []))
    if abs(cost) < 1e-9 and has_options and not breakevens:
        be = "0 Costo"
    elif len(breakevens) == 1:
        be = money(float(breakevens[0]), 0)
    elif len(breakevens) > 1:
        be = "Multiples"
    else:
        be = "-"
    return floor_text, ceiling_text, be


# -----------------------------------------------------------------------------
# Visual helpers
# -----------------------------------------------------------------------------


def render_header() -> None:
    html_block(
        """
<div class="main-header"><div class="logo">🌾</div><div><h1>Estrategias Coberturas</h1><p>Espartina S.A. - Simulador de Coberturas & FAS</p></div><div class="header-badge">Builder de Opciones</div></div>
"""
    )


def render_cascade_bar(name: str, value: float, pct: float, background: str, color: str) -> str:
    width = max(min(abs(pct), 100), 3)
    value_color = "var(--red)" if value < 0 else "var(--text)"
    return (
        f'<div class="bar-row"><div class="bar-labels"><span class="bar-name">{html.escape(name)}</span>'
        f'<span class="bar-val" style="color:{value_color}">{value:,.2f}</span></div>'
        f'<div class="bar" style="width:{width:.1f}%;background:{background};color:{color};">{pct:.1f}%</div></div>'
    )


def render_grain_cascade(position: Optional[str], crop: str, fob: float, ret_pct: float, fobbing: float, fas_obj: float) -> Tuple[float, str]:
    ret_value = fob * ret_pct / 100
    fas_ctp = fob - ret_value - fobbing
    margin = fas_ctp - fas_obj
    fob_needed = (fas_obj + fobbing) / (1 - ret_pct / 100) if ret_pct < 100 else 0
    ret_impl = (1 - (fas_obj + fobbing) / fob) * 100 if fob else 0
    margin_color = "var(--green)" if margin >= 0 else "var(--red)"
    bars = "".join(
        [
            render_cascade_bar(f"FOB {CROP_LABELS[crop]}", fob, 100, "var(--es-gold-light)", "var(--es-gold)"),
            render_cascade_bar(f"Retencion {ret_pct:.1f}%", -ret_value, ret_pct, "#fde8e8", "var(--red)"),
            render_cascade_bar("Fobbing", -fobbing, (fobbing / fob * 100) if fob else 0, "var(--bg-input)", "var(--text-3)"),
        ]
    )
    panel = (
        f'<div class="cascade-panel"><div class="cascade-title" style="color:var(--es-green)">Exportacion grano {html.escape(str(position or ""))}</div>'
        f'{bars}'
        f'<div class="result-row"><span class="result-lbl">FAS Teorico (CTP)</span><span class="result-val" style="color:var(--es-green)">{fas_ctp:.2f}</span></div>'
        f'<div class="margin-row"><span>Margen export. vs obj {fas_obj:.1f}</span><strong style="color:{margin_color}">{margin:+.2f}</strong></div>'
        f'<div class="tri-grid"><div class="tri-chip"><div class="tri-lbl">FOB Necesario</div><div class="tri-val" style="color:var(--blue)">{fob_needed:.2f}</div><div class="tri-sub">Para pagar FAS obj {fas_obj:.1f}</div></div>'
        f'<div class="tri-chip"><div class="tri-lbl">Retencion Implicita</div><div class="tri-val" style="color:var(--orange)">{ret_impl:.2f}%</div><div class="tri-sub">Gap: {ret_impl-ret_pct:+.2f} pp</div></div></div></div>'
    )
    return fas_ctp, panel


def render_crushing_cascade(byproducts: Dict[str, float], fas_obj: float) -> Tuple[float, str]:
    ca = st.number_input("FOB Aceite", value=float(byproducts.get("aceite", 1191.0) or 1191.0), step=0.1, key="crush_aceite")
    ch = st.number_input("FOB Harina", value=float(byproducts.get("harina", 357.0) or 357.0), step=0.1, key="crush_harina")
    cols = st.columns(4)
    with cols[0]:
        coef_a = st.number_input("Coef. Aceite", value=0.19, step=0.01, key="coef_a")
    with cols[1]:
        coef_h = st.number_input("Coef. Harina", value=0.78, step=0.01, key="coef_h")
    with cols[2]:
        ret_sub = st.number_input("Ret Sub %", value=22.5, step=0.1, key="ret_sub")
    with cols[3]:
        gto_ind = st.number_input("Gto Ind.", value=29.0, step=1.0, key="gto_ind")
    fobbing_sub = st.number_input("Fobbing subprod", value=19.0, step=0.5, key="fobbing_sub")

    aceite_bruto = ca * coef_a
    harina_bruto = ch * coef_h
    bruto = aceite_bruto + harina_bruto
    ret_value = bruto * ret_sub / 100
    fas_crushing = bruto - ret_value - fobbing_sub - gto_ind
    margin = fas_crushing - fas_obj
    margin_color = "var(--green)" if margin >= 0 else "var(--red)"

    bars = "".join(
        [
            render_cascade_bar(f"Aceite ({ca:.1f} x {coef_a:.2f})", aceite_bruto, (aceite_bruto / bruto * 100) if bruto else 0, "var(--es-green-light)", "var(--es-green-dark)"),
            render_cascade_bar(f"Harina ({ch:.1f} x {coef_h:.2f})", harina_bruto, (harina_bruto / bruto * 100) if bruto else 0, "var(--es-green-light)", "var(--es-green-dark)"),
            render_cascade_bar(f"Ret subprod {ret_sub:.1f}%", -ret_value, ret_sub, "#fde8e8", "var(--red)"),
            render_cascade_bar("Fobbing subprod", -fobbing_sub, (fobbing_sub / bruto * 100) if bruto else 0, "var(--bg-input)", "var(--text-3)"),
            render_cascade_bar("Gasto industrial", -gto_ind, (gto_ind / bruto * 100) if bruto else 0, "var(--bg-input)", "var(--text-3)"),
        ]
    )
    panel = (
        f'<div class="cascade-panel"><div class="cascade-title" style="color:var(--es-gold)">Crushing subproductos</div>'
        f'{bars}'
        f'<div class="result-row"><span class="result-lbl">FAS Crushing</span><span class="result-val" style="color:var(--es-gold)">{fas_crushing:.2f}</span></div>'
        f'<div class="margin-row"><span>Margen crushing vs obj {fas_obj:.1f}</span><strong style="color:{margin_color}">{margin:+.2f}</strong></div></div>'
    )
    return fas_crushing, panel


def build_payoff_chart(strategies: List[Dict[str, Any]], spot: float, min_price: float, max_price: float) -> go.Figure:
    prices = list(range(int(min_price), int(max_price) + 1, 2)) or [int(spot)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=prices, mode="lines", name="Fisico sin cobertura", line=dict(color="#b0afa8", width=2, dash="dash")))
    for strategy in strategies:
        fig.add_trace(
            go.Scatter(
                x=prices,
                y=[net_sale_value(strategy, price) for price in prices],
                mode="lines",
                name=strategy["name"],
                line=dict(color=strategy.get("color", COLORS[0]), width=3),
                hovertemplate="<b>%{fullData.name}</b><br>Precio: $%{x:.1f}<br>Neto: $%{y:.2f}<extra></extra>",
            )
        )
    fig.add_vline(x=spot, line_dash="dot", line_color="#C8A44A", annotation_text=f"Spot {spot:.1f}", annotation_position="top")
    fig.update_layout(
        title="Precio Neto de Venta - Coberturas vs Fisico",
        height=520,
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1c2118", family="DM Sans"),
        xaxis=dict(title="Precio a vencimiento (USD/tn)", gridcolor="rgba(28,33,24,.08)"),
        yaxis=dict(title="Precio neto de venta (USD/tn)", gridcolor="rgba(28,33,24,.08)"),
        legend=dict(bgcolor="rgba(255,255,255,.85)", bordercolor="#dde0d5", borderwidth=1),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def scenario_rows(strategies: List[Dict[str, Any]], spot: float) -> pd.DataFrame:
    scenarios: List[Tuple[str, float]] = [
        ("Derrumbe (-30%)", spot * 0.70),
        ("Baja fuerte (-15%)", spot * 0.85),
        ("Spot", spot),
        ("Suba moderada (+15%)", spot * 1.15),
        ("Rally (+30%)", spot * 1.30),
    ]
    for strategy in strategies:
        for leg in strategy.get("legs", []):
            if leg.get("type") != "futuro" and leg.get("strike"):
                strike = float(leg["strike"])
                if not any(abs(item[1] - strike) < 0.5 for item in scenarios):
                    scenarios.append((f"Strike {leg.get('type','').upper()} {strike:.1f}", strike))
    scenarios.sort(key=lambda item: item[1])

    rows: List[Dict[str, Any]] = []
    for name, price in scenarios:
        row: Dict[str, Any] = {"Escenario": name, "Mercado": price, "Sin cobertura": price}
        for strategy in strategies:
            row[strategy["name"]] = net_sale_value(strategy, price)
        rows.append(row)
    return pd.DataFrame(rows)


def dominance_ranges(strategies: List[Dict[str, Any]], min_price: float, max_price: float) -> List[Dict[str, Any]]:
    ranges: List[Dict[str, Any]] = []
    current_name: Optional[str] = None
    current_color = "#b0afa8"
    start = int(min_price)
    for price in range(int(min_price), int(max_price) + 1):
        best_name = "Sin cobertura"
        best_value = float(price)
        best_color = "#b0afa8"
        for strategy in strategies:
            value = net_sale_value(strategy, float(price))
            if value > best_value + 0.05:
                best_value = value
                best_name = strategy["name"]
                best_color = strategy.get("color", COLORS[0])
        if current_name != best_name:
            if current_name is not None:
                ranges.append({"name": current_name, "start": start, "end": price - 1, "color": current_color})
            current_name = best_name
            current_color = best_color
            start = price
    if current_name is not None:
        ranges.append({"name": current_name, "start": start, "end": int(max_price), "color": current_color})
    return ranges


def style_number(value: Any) -> str:
    if isinstance(value, (int, float)):
        color = "#1a854a" if value > 0 else "#c43030" if value < 0 else "#7e8574"
        return f"color:{color};font-weight:800"
    return ""


def pdf_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_simple_pdf(title: str, lines: List[str]) -> bytes:
    content = ["BT", "/F1 18 Tf", "50 790 Td", f"({pdf_escape(title)}) Tj", "/F1 10 Tf", "0 -28 Td"]
    for line in lines[:42]:
        content.append(f"({pdf_escape(line)}) Tj")
        content.append("0 -16 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        b"5 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n" + stream + b"\nendstream endobj",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj + b"\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


# -----------------------------------------------------------------------------
# Header and sidebar
# -----------------------------------------------------------------------------

render_header()

with st.sidebar:
    st.header("Configuracion")

    update_cols = st.columns([3, 1])
    with update_cols[0]:
        if st.button("Actualizar FOB", use_container_width=True):
            with st.spinner("Obteniendo datos FOB desde Bolsa..."):
                try:
                    obtener_datos_bolsa.clear()
                except Exception:
                    pass
                data = obtener_datos_bolsa()
                if data:
                    st.session_state.data_bolsa = {"cotizaciones": data, "last_update": datetime.now(), "source": "Bolsa de Cereales"}
                    st.session_state.force_sync_fob = True
                    st.success("FOB actualizado")
                else:
                    st.error("No se obtuvieron datos FOB")
    with update_cols[1]:
        last = st.session_state.data_bolsa.get("last_update")
        st.caption(last.strftime("%H:%M") if last else "--")

    if st.button("Sincronizar A3", use_container_width=True):
        with st.spinner("Sincronizando A3..."):
            df = obtener_datos_a3()
            if df is not None and not df.empty:
                market = parse_a3_market(df)
                st.session_state.data_a3 = {"raw_df": df, "market": market, "last_update": datetime.now(), "source": "A3 Google Sheet"}
                if market:
                    futures_count = sum(len(v) for v in market.get("futuros", {}).values())
                    options_count = sum(
                        len(pos.get("calls", [])) + len(pos.get("puts", []))
                        for crop_data in market.get("opciones", {}).values()
                        for pos in crop_data.values()
                    )
                    st.success(f"A3 sincronizado: {futures_count} futuros, {options_count} opciones")
                else:
                    st.warning("A3 sincronizado, pero no se detecto estructura de futuros/opciones")
            else:
                st.warning("No se obtuvieron datos A3")

    st.divider()
    st.subheader("Parametros")
    crop_label = st.selectbox("Cultivo", list(CROP_LABELS.values()), index=0, key="ui_crop_selector")
    crop = slug_crop(crop_label)

    bolsa_positions = get_bolsa_positions()
    if bolsa_positions:
        selected_bolsa_pos = st.selectbox("Posicion FOB", bolsa_positions, key="ui_bolsa_position")
    else:
        selected_bolsa_pos = None
        st.info("Actualizar FOB para cargar posiciones")

    a3_positions = get_market_positions(crop)
    if a3_positions:
        selected_a3_pos = st.selectbox("Posicion A3 opciones", a3_positions, key="ui_a3_position")
    else:
        selected_a3_pos = None
        st.caption("Sin posiciones A3 de opciones")

    source_fob = get_source_fob(crop, selected_bolsa_pos)
    fob_source_label = "Bolsa de Cereales"
    if source_fob is None:
        source_fob = get_market_future(crop, selected_a3_pos)
        fob_source_label = "A3 futuro fallback" if source_fob is not None else "Default fallback"
    if source_fob is None:
        source_fob = FALLBACK_FOB[crop]

    sync_fob_widget_with_source(crop, selected_bolsa_pos, float(source_fob))
    active_fob_for_builder = float(st.session_state.get("ret_fob_indice", source_fob))

    st.divider()
    st.caption("Estado de fuentes")
    st.caption(f"Bolsa: {len(bolsa_positions)} posiciones" if bolsa_positions else "Bolsa: sin datos")
    if get_a3_market():
        st.caption("A3: mercado disponible")
    elif st.session_state.data_a3.get("raw_df") is not None:
        st.caption("A3: sheet cargado, sin parseo mercado")
    else:
        st.caption("A3: sin datos")

# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------

tab_builder, tab_manual, tab_fas = st.tabs(["Builder de Coberturas", "Manual Teorico", "Retenciones & FAS Teorico"])

# -----------------------------------------------------------------------------
# Tab 1 - Builder
# -----------------------------------------------------------------------------

with tab_builder:
    st.header("Builder de Estrategias")
    spot = float(active_fob_for_builder or source_fob or 0)
    min_x = max(1.0, spot * 0.70)
    max_x = max(spot * 1.30, min_x + 1)

    html_block(
        f'<div class="fas-info-bar"><div class="fas-chip"><div class="lbl">Cultivo</div><div class="val">{CROP_LABELS[crop]}</div></div>'
        f'<div class="fas-chip"><div class="lbl">FOB / Spot</div><div class="val">{spot:.1f} u$s</div></div>'
        f'<div class="fas-chip"><div class="lbl">Posicion FOB</div><div class="val">{html.escape(str(selected_bolsa_pos or "-"))}</div></div>'
        f'<div class="fas-chip"><div class="lbl">A3 opciones</div><div class="val">{html.escape(str(selected_a3_pos or "-"))}</div></div></div>'
    )

    left, right = st.columns([0.92, 1.58], gap="large")

    with left:
        html_block('<div class="top-panel">')
        st.subheader("Cargar plantilla")
        presets = create_preset_strategies(spot)
        flat_presets: List[Tuple[str, Dict[str, Any]]] = []
        for category, items in presets.items():
            for item in items:
                flat_presets.append((category, item))
        preset_names = [f"{item['name']} - {category.title()}" for category, item in flat_presets]
        selected_preset_idx = st.selectbox("Plantilla", range(len(preset_names)), format_func=lambda idx: preset_names[idx], label_visibility="collapsed")
        preset_category, preset_data = flat_presets[selected_preset_idx]
        preset_strategy = Strategy(preset_data["name"], preset_data["legs"], preset_data["color"])
        cost = preset_strategy.total_cost()
        cost_class = "debit" if cost < 0 else "credit" if cost > 0 else "zero"
        cost_text = f"Costo neto: ${abs(cost):.2f}" if cost < 0 else f"Credito: ${cost:.2f}" if cost > 0 else "Costo: ~$0"
        html_block(
            f'<div class="compact-card" style="border-left-color:{preset_data["color"]}"><div class="card-title">{html.escape(preset_data["name"])}</div><div class="card-desc">{html.escape(preset_data["desc"])}</div><div class="card-cost {cost_class}">{cost_text}</div></div>'
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Agregar plantilla", use_container_width=True):
                st.session_state.builder_strategies.append(new_strategy(preset_data["name"], [leg_to_dict(leg) for leg in preset_data["legs"]], preset_data["color"]))
                st.rerun()
        with col_b:
            if st.button("Nueva vacia", use_container_width=True):
                st.session_state.builder_strategies.append(
                    new_strategy(
                        "Estrategia de Cobertura",
                        [{"direction": "buy", "type": "put", "ratio": 1.0, "strike": round(spot * 0.97), "prima": 0.0}],
                    )
                )
                st.rerun()
        if preset_data.get("alert"):
            alerts = get_strategy_alerts()
            if preset_data["name"] in alerts:
                st.warning(alerts[preset_data["name"]]["mensaje"], icon="⚠")
        html_block("</div>")

        html_block('<div class="section-title">Estrategias activas</div>')
        if not st.session_state.builder_strategies:
            st.info("Agrega una plantilla o crea una estrategia nueva para empezar.")

        market_ready = bool(get_a3_market() and selected_a3_pos)
        if st.button("Actualizar primas A3", use_container_width=True, disabled=not market_ready):
            updated = 0
            for strategy in st.session_state.builder_strategies:
                for leg in strategy.get("legs", []):
                    if leg.get("type") == "futuro":
                        leg["prima"] = 0.0
                        continue
                    premium = lookup_prima(crop, selected_a3_pos, leg.get("type", "put"), float(leg.get("strike", 0)))
                    if premium is not None:
                        leg["prima"] = float(premium)
                        updated += 1
            st.success(f"{updated} primas actualizadas")
            st.rerun()

    with right:
        if st.session_state.builder_strategies:
            st.plotly_chart(build_payoff_chart(st.session_state.builder_strategies, spot, min_x, max_x), use_container_width=True)
        else:
            html_block(
                '<div class="top-panel" style="min-height:360px;display:flex;align-items:center;justify-content:center;text-align:center;"><div><h3 style="color:var(--es-gold)!important;">Selecciona estrategias para comenzar</h3><p>Usa el menu compacto de plantillas o crea una estrategia desde cero.</p></div></div>'
            )

    st.divider()
    st.subheader("Constructor editable")

    for s_idx, strategy in enumerate(list(st.session_state.builder_strategies)):
        html_block(f'<div class="strategy-shell" style="border-left-color:{strategy.get("color", COLORS[0])}">')
        top_cols = st.columns([2.6, 1, 0.6])
        with top_cols[0]:
            strategy["name"] = st.text_input("Nombre", value=strategy["name"], key=f"strat_name_{strategy['id']}", label_visibility="collapsed")
        with top_cols[1]:
            if st.button("Agregar pata", key=f"add_leg_{strategy['id']}", use_container_width=True):
                strategy.setdefault("legs", []).append({"direction": "buy", "type": "put", "ratio": 1.0, "strike": round(spot), "prima": 0.0})
                st.rerun()
        with top_cols[2]:
            if st.button("Borrar", key=f"del_strat_{strategy['id']}", use_container_width=True):
                st.session_state.builder_strategies.pop(s_idx)
                st.rerun()

        html_block('<div class="leg-header"><span>Operacion</span><span>Instrum.</span><span>Cant.</span><span>Strike</span><span>Prima</span><span></span></div>')
        for leg_idx, leg in enumerate(list(strategy.get("legs", []))):
            html_block('<div class="leg-wrap">')
            c_dir, c_type, c_ratio, c_strike, c_prima, c_del = st.columns([1.3, 1.15, 0.9, 1.0, 1.0, 0.35], gap="small")
            with c_dir:
                leg["direction"] = st.selectbox(
                    "Operacion",
                    ["buy", "sell"],
                    index=0 if leg.get("direction") == "buy" else 1,
                    format_func=lambda value: "Compra" if value == "buy" else "Venta",
                    key=f"dir_{strategy['id']}_{leg_idx}",
                    label_visibility="collapsed",
                )
            with c_type:
                type_options = ["put", "call", "futuro"]
                current_type = leg.get("type", "put") if leg.get("type", "put") in type_options else "put"
                leg["type"] = st.selectbox(
                    "Instrumento",
                    type_options,
                    index=type_options.index(current_type),
                    format_func=lambda value: value.capitalize(),
                    key=f"type_{strategy['id']}_{leg_idx}",
                    label_visibility="collapsed",
                )
            with c_ratio:
                leg["ratio"] = st.number_input("Ratio", min_value=0.0, value=float(leg.get("ratio", 1.0)), step=0.5, key=f"ratio_{strategy['id']}_{leg_idx}", label_visibility="collapsed")
            with c_strike:
                current_strike = float(leg.get("strike", round(spot)) or round(spot))
                strikes = get_available_strikes(crop, selected_a3_pos, leg.get("type", "put"))
                if strikes:
                    strike_options = strikes.copy()
                    if current_strike not in strike_options:
                        strike_options = [current_strike] + strike_options
                    selected_strike = st.selectbox("Strike", strike_options, index=strike_options.index(current_strike), key=f"strike_sel_{strategy['id']}_{leg_idx}", label_visibility="collapsed")
                    if float(selected_strike) != float(leg.get("_last_strike", current_strike)):
                        premium = lookup_prima(crop, selected_a3_pos, leg.get("type", "put"), float(selected_strike))
                        if premium is not None:
                            leg["prima"] = float(premium)
                    leg["strike"] = float(selected_strike)
                    leg["_last_strike"] = float(selected_strike)
                else:
                    leg["strike"] = st.number_input("Strike", value=current_strike, step=1.0, key=f"strike_{strategy['id']}_{leg_idx}", label_visibility="collapsed")
                    leg["_last_strike"] = float(leg["strike"])
            with c_prima:
                disabled = leg.get("type") == "futuro"
                if disabled:
                    leg["prima"] = 0.0
                leg["prima"] = st.number_input("Prima", value=float(leg.get("prima", 0.0)), step=0.1, disabled=disabled, key=f"prima_{strategy['id']}_{leg_idx}", label_visibility="collapsed")
            with c_del:
                if st.button("X", key=f"del_leg_{strategy['id']}_{leg_idx}", use_container_width=True):
                    strategy["legs"].pop(leg_idx)
                    st.rerun()
            html_block("</div>")

        floor_text, ceiling_text, be_text = strategy_kpis(strategy, spot)
        cost = option_cost(strategy)
        cost_label = f"Costo {money(cost,1)}" if cost > 0 else f"Credito {money(abs(cost),1)}" if cost < 0 else "Costo $0"
        html_block(
            f'<div class="kpi-grid"><div class="kpi-card"><div class="k-lbl">Costo neto</div><div class="k-val">{cost_label}</div></div><div class="kpi-card"><div class="k-lbl">Piso asegurado</div><div class="k-val">{floor_text}</div></div><div class="kpi-card"><div class="k-lbl">Empate B.E.</div><div class="k-val">{be_text}</div></div></div>'
        )
        html_block("</div>")

    if st.session_state.builder_strategies:
        st.subheader("Analisis de escenarios")
        df = scenario_rows(st.session_state.builder_strategies, spot)
        numeric_cols = [column for column in df.columns if column != "Escenario"]
        styler = df.style.format({column: "${:.2f}" for column in numeric_cols})
        styler = safe_style_map(styler, style_number, subset=numeric_cols)
        st.dataframe(styler, use_container_width=True, hide_index=True)

        st.subheader("Rango de dominancia")
        dom_cols = st.columns(2)
        for i, item in enumerate(dominance_ranges(st.session_state.builder_strategies, min_x, max_x)):
            with dom_cols[i % 2]:
                html_block(
                    f'<div class="winner-box" style="border-left-color:{item["color"]}"><div class="winner-range">Si el mercado cierra entre u$s {item["start"]:.1f} y u$s {item["end"]:.1f}</div><div class="winner-name" style="color:{item["color"]}">Conviene: {html.escape(item["name"])}</div></div>'
                )

        report_lines = [
            f"Cultivo: {CROP_LABELS[crop]}",
            f"Posicion FOB: {selected_bolsa_pos or '-'}",
            f"FOB/Spot: {spot:.2f}",
            "",
            "Estrategias:",
        ]
        for strategy in st.session_state.builder_strategies:
            report_lines.append(f"- {strategy['name']} | costo neto {option_cost(strategy):.2f} | patas {len(strategy.get('legs', []))}")
        st.download_button("Exportar PDF", data=make_simple_pdf("Reporte Coberturas Espartina", report_lines), file_name="reporte_coberturas.pdf", mime="application/pdf")

# -----------------------------------------------------------------------------
# Tab 2 - Manual
# -----------------------------------------------------------------------------

with tab_manual:
    st.header("Catalogo de Estructuras Comerciales")
    st.markdown(
        """
El diseno de una cobertura no busca predecir el mercado, sino administrar asimetrias de riesgo. Toda decision operativa implica un trade-off entre costo financiero, riesgo de cola y costo de oportunidad.

### Protecciones base
**Put seco:** seguro puro, maxima proteccion sin techo.  
**Put spread:** proteccion con franquicia, menor costo y piso limitado.  
**Collar:** tunel de rentabilidad, costo bajo/cero a cambio de resignar upside.

### Estructuras avanzadas
**Gaviota:** put spread financiado con venta de call.  
**Futuro + Call:** fijacion sintetica con opcionalidad alcista.  
**Ratio Put Spread 1x2:** costo bajo/cero con riesgo en baja extrema.
"""
    )

# -----------------------------------------------------------------------------
# Tab 3 - FAS / Retenciones
# -----------------------------------------------------------------------------

with tab_fas:
    st.header("Retenciones & FAS Teorico")
    defaults = RET_DEFAULTS[crop]

    top = st.columns([1, 1, 1, 1, 1])
    with top[0]:
        ret_crop = st.selectbox("Cultivo", list(CROP_LABELS.keys()), index=list(CROP_LABELS.keys()).index(crop), format_func=lambda item: CROP_LABELS[item], key="ret_crop")
    if ret_crop != crop:
        crop = ret_crop
        defaults = RET_DEFAULTS[crop]
        new_source_fob = get_source_fob(crop, selected_bolsa_pos) or get_market_future(crop, selected_a3_pos) or FALLBACK_FOB[crop]
        sync_fob_widget_with_source(crop, selected_bolsa_pos, float(new_source_fob))
        source_fob = float(new_source_fob)
        fob_source_label = "Bolsa de Cereales" if get_source_fob(crop, selected_bolsa_pos) is not None else "Fallback"

    source_fob_for_diag = float(source_fob or FALLBACK_FOB[crop])
    with top[1]:
        fob_indice = st.number_input("FOB Indice", value=source_fob_for_diag, step=0.1, key="ret_fob_indice")
    with top[2]:
        ret_pct = st.number_input("Ret %", value=float(defaults["ret"]), step=0.1, key="ret_pct")
    with top[3]:
        fobbing = st.number_input("Fobbing", value=float(defaults["fobbing"]), step=0.1, key="ret_fobbing")
    with top[4]:
        fas_obj = st.number_input("FAS Obj 1", value=float(defaults["fas_obj"]), step=0.1, key="ret_fas_obj")

    delta_fob = fob_indice - source_fob_for_diag
    status = "OK" if abs(delta_fob) < 0.01 else "REVISION"
    st.info(
        f"Diagnostico FOB [{status}]: fuente {fob_source_label} para {CROP_LABELS[crop]} / {selected_bolsa_pos or '-'} = {source_fob_for_diag:.2f}. "
        f"Valor usado en cascada = {fob_indice:.2f}. Diferencia = {delta_fob:+.2f}. "
        "El FOB fuente se almacena sin descuentos; retenciones y fobbing se aplican solo dentro de la cascada."
    )

    fas_ctp, grain_panel = render_grain_cascade(selected_bolsa_pos, crop, fob_indice, ret_pct, fobbing, fas_obj)
    st.session_state.fas_context = {
        "crop": crop,
        "position": selected_bolsa_pos,
        "source_fob": source_fob_for_diag,
        "active_fob": fob_indice,
        "fas_ctp": fas_ctp,
        "ret_pct": ret_pct,
        "fobbing": fobbing,
        "fas_obj": fas_obj,
    }

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        html_block(grain_panel)

    crush_fas: Optional[float] = None
    with c2:
        if crop == "soja":
            crush_fas, crush_panel = render_crushing_cascade(get_source_byproducts(selected_bolsa_pos), fas_obj)
            html_block(crush_panel)
        else:
            st.info("El crushing solo aplica para soja.")

    html_block('<div class="section-title">Simulador de escenario - Baja de retenciones</div>')
    reduction = st.slider("Reduccion de retenciones", min_value=0, max_value=100, value=25, step=5, format="-%d%%")
    new_ret = ret_pct * (1 - reduction / 100)
    new_fas = fob_indice * (1 - new_ret / 100) - fobbing
    comparison = pd.DataFrame(
        [
            {"Escenario": "Actual", "Retencion grano": ret_pct, "FAS teorico": fas_ctp, "FAS crushing": crush_fas},
            {"Escenario": "Con reduccion", "Retencion grano": new_ret, "FAS teorico": new_fas, "FAS crushing": None},
        ]
    )
    st.dataframe(comparison.style.format({"Retencion grano": "{:.1f}%", "FAS teorico": "${:.2f}", "FAS crushing": "${:.2f}"}), use_container_width=True, hide_index=True)
    html_block(
        f'<div class="note"><strong>Conexion con coberturas:</strong> si cubris a FOB <strong>{fob_indice:.1f}</strong> con un PUT, tu piso de FAS neto es <strong>{fas_ctp:.2f}</strong> u$s/tn menos la prima pagada.</div>'
    )

html_block(
    '<div class="footer"><strong>Espartina S.A.</strong> - Dashboard de Estrategias de Cobertura<br><span style="font-size:.75rem">Datos FOB desde Bolsa de Cereales - Datos A3 desde Google Sheets</span></div>'
)
