"""
🌾 Estrategias de Cobertura - Espartina S.A.
App Streamlit refactorizada: UI compacta, builder dinámico, A3, FAS y reporte.
"""

from __future__ import annotations

import base64
import html
import io
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculadora import calcular_exportacion_grano
from estrategias_engine import Leg, Strategy
from estrategias_presets import create_preset_strategies, get_strategy_alerts
from google_sheets import obtener_datos_a3
from scraper import obtener_datos_bolsa

# ═══════════════════════════════════════════════════════════════════════════════
# Configuración
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Estrategias de Cobertura - Espartina S.A.",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = ["#1A6B3C", "#2563eb", "#d97706", "#7c3aed", "#c43030", "#0d9488"]
CROP_LABELS = {"soja": "Soja", "maiz": "Maíz", "trigo": "Trigo", "girasol": "Girasol"}
CROP_CODES = {"SOJ": "soja", "MAI": "maiz", "TRI": "trigo", "GIR": "girasol"}
CROP_TO_FOB_KEY = {"soja": "soja", "maiz": "maiz", "trigo": "trigo", "girasol": "girasol"}
RET_DEFAULTS = {
    "soja": {"ret": 26.0, "fobbing": 12.0, "fas_obj": 323.0},
    "maiz": {"ret": 7.0, "fobbing": 11.0, "fas_obj": 185.0},
    "trigo": {"ret": 7.0, "fobbing": 13.0, "fas_obj": 216.0},
    "girasol": {"ret": 7.0, "fobbing": 14.0, "fas_obj": 475.0},
}

# ═══════════════════════════════════════════════════════════════════════════════
# CSS: replica estructura del HTML original, corrigiendo el vertical stacking
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root {
  --es-green:#1A6B3C; --es-green-dark:#145430; --es-green-light:#e8f5ec; --es-green-muted:#2d8a54;
  --es-gold:#C8A44A; --es-gold-light:#f9f3e3; --bg:#f4f5f0; --bg-card:#ffffff; --bg-input:#f0f1ec;
  --text:#1c2118; --text-2:#505845; --text-3:#7e8574; --border:#dde0d5; --border-2:#c8cbbe;
  --green:#1a854a; --red:#c43030; --blue:#2563eb; --orange:#d97706;
  --font:'DM Sans', system-ui, sans-serif; --mono:'JetBrains Mono', ui-monospace, monospace;
  --radius:10px; --shadow:0 1px 4px rgba(26,107,60,.06),0 1px 2px rgba(0,0,0,.04);
  --shadow-lg:0 4px 16px rgba(26,107,60,.08),0 2px 6px rgba(0,0,0,.04);
}
html, body, [class*="css"] { font-family:var(--font)!important; }
.stApp { background:var(--bg)!important; color:var(--text)!important; }
.block-container { max-width:1320px; padding-top:16px; padding-bottom:36px; }
section[data-testid="stSidebar"] { background:#f7f8f3!important; border-right:1px solid var(--border); }
section[data-testid="stSidebar"] * { color:var(--text)!important; }
h1,h2,h3 { color:var(--text)!important; letter-spacing:-.25px; }
.stMarkdown p, .stCaption, label { color:var(--text-2)!important; }

.main-header{background:linear-gradient(135deg,var(--es-green-dark) 0%,var(--es-green) 60%,var(--es-green-muted) 100%);padding:16px 24px;border-radius:12px;margin-bottom:18px;box-shadow:0 2px 12px rgba(20,84,48,.25);border-bottom:3px solid var(--es-gold);display:flex;align-items:center;gap:14px;}
.main-header .logo{width:38px;height:38px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.12);font-size:20px;}
.main-header h1{color:#fff!important;margin:0;font-size:22px;font-weight:800;}
.main-header p{color:rgba(255,255,255,.68)!important;margin:1px 0 0;font-size:12px;}
.header-badge{margin-left:auto;background:rgba(200,164,74,.2);border:1px solid rgba(200,164,74,.35);color:var(--es-gold);font-size:10px;font-weight:800;padding:4px 10px;border-radius:20px;letter-spacing:.7px;text-transform:uppercase;}

/* Botones compactos: evita que “Agregar/Usar” se rompa verticalmente */
div.stButton > button{background:var(--es-green)!important;color:#fff!important;border:1px solid var(--es-green)!important;border-radius:8px!important;min-height:36px!important;padding:7px 12px!important;font-size:12px!important;font-weight:800!important;white-space:nowrap!important;line-height:1.1!important;box-shadow:0 1px 3px rgba(26,107,60,.16)!important;}
div.stButton > button:hover{background:var(--es-green-dark)!important;transform:translateY(-1px);box-shadow:0 3px 8px rgba(26,107,60,.2)!important;}
section[data-testid="stSidebar"] div.stButton > button{width:100%!important;background:var(--es-gold)!important;border-color:var(--es-gold)!important;color:#fff!important;min-height:42px!important;font-size:13px!important;}

/* Inputs */
div[data-baseweb="select"] > div, input, textarea{background:var(--bg-input)!important;border-color:var(--border)!important;border-radius:7px!important;color:var(--text)!important;font-family:var(--mono)!important;}
div[data-baseweb="select"] > div:focus-within,input:focus,textarea:focus{border-color:var(--es-green)!important;box-shadow:0 0 0 3px rgba(26,107,60,.10)!important;}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:2px solid var(--border);padding-bottom:10px;overflow-x:auto;}
.stTabs [data-baseweb="tab"]{background:var(--bg-card);border:1px solid var(--border);color:var(--text-2);border-radius:8px;padding:9px 16px;font-size:13px;font-weight:800;box-shadow:var(--shadow);white-space:nowrap;}
.stTabs [aria-selected="true"]{background:var(--es-green)!important;color:#fff!important;border-color:var(--es-green)!important;}

/* Componentes custom */
.top-panel{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;margin-bottom:16px;box-shadow:var(--shadow);}
.compact-card{background:var(--bg-card);border:1px solid var(--border);border-left:4px solid var(--es-green);border-radius:var(--radius);padding:12px 14px;box-shadow:var(--shadow);margin-bottom:8px;}
.compact-card:hover{box-shadow:var(--shadow-lg);}
.card-title{font-weight:800;font-size:14px;color:var(--text);margin-bottom:4px;}
.card-desc{font-size:12px;color:var(--text-3);line-height:1.45;margin-bottom:8px;}
.card-cost{font-family:var(--mono);font-size:12px;font-weight:800;}.debit{color:var(--red)}.credit{color:var(--green)}.zero{color:var(--text-3)}
.strategy-shell{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:14px 14px 10px;margin-bottom:14px;border-left:4px solid var(--es-green);}
.leg-header{display:grid;grid-template-columns:1.3fr 1.15fr .9fr 1fr 1fr .35fr;gap:8px;font-size:10px;color:var(--text-3);font-weight:900;letter-spacing:.04em;text-transform:uppercase;margin:4px 0 2px;padding:0 4px;}
.leg-wrap{background:var(--bg-input);border:1px solid transparent;border-radius:8px;padding:7px 8px;margin-bottom:7px;}
.kpi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px;padding-top:10px;border-top:1px dashed var(--border);}
.kpi-card{background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:9px 7px;text-align:center;}
.k-lbl{font-size:9px;text-transform:uppercase;color:var(--text-3);font-weight:900;letter-spacing:.05em;margin-bottom:3px;}.k-val{font-size:13px;font-weight:900;font-family:var(--mono);}
.fas-info-bar{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 16px;}.fas-chip{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:10px 14px;min-width:175px;}.fas-chip .lbl{color:var(--text-3);font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:.05em}.fas-chip .val{font-family:var(--mono);font-size:17px;font-weight:900;color:var(--text)}
.cascade-panel{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow);margin-bottom:14px;}.cascade-title{font-size:15px;font-weight:900;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border)}.bar-row{margin-bottom:8px}.bar-labels{display:flex;justify-content:space-between;margin-bottom:3px}.bar-name{font-size:12px;color:var(--text-2)}.bar-val{font-size:12px;font-family:var(--mono);font-weight:800}.bar{height:24px;border-radius:5px;display:flex;align-items:center;padding-left:8px;font-size:11px;font-family:var(--mono);font-weight:800}.result-row{margin-top:12px;padding-top:12px;border-top:2px solid var(--border);display:flex;justify-content:space-between;align-items:baseline}.result-lbl{font-size:13px;font-weight:900}.result-val{font-size:24px;font-weight:900;font-family:var(--mono)}.margin-row{background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:10px 12px;display:flex;justify-content:space-between;margin-top:10px}.tri-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.tri-chip{background:var(--bg-input);border:1px solid var(--border);border-radius:8px;padding:8px 10px}.tri-lbl{font-size:10px;color:var(--text-3);font-weight:900;text-transform:uppercase;letter-spacing:.04em}.tri-val{font-size:14px;font-weight:900;font-family:var(--mono);margin-top:2px}.tri-sub{font-size:10px;color:var(--text-3)}
.winner-box{background:var(--bg-card);border:1px solid var(--border);border-left:4px solid var(--es-gold);border-radius:8px;padding:10px 12px;margin-bottom:8px;box-shadow:var(--shadow)}.winner-range{font-family:var(--mono);font-size:12px;color:var(--text-2);margin-bottom:3px}.winner-name{font-size:14px;font-weight:900}.section-title{font-size:13px;font-weight:900;color:var(--text-2);text-transform:uppercase;letter-spacing:.06em;margin:10px 0 12px;display:flex;align-items:center;gap:8px}.section-title::before{content:'';display:inline-block;width:4px;height:16px;background:var(--es-green);border-radius:2px}.note{background:var(--es-gold-light);border:1px solid var(--es-gold);border-radius:var(--radius);padding:12px 16px;font-size:12px;color:var(--text-2);line-height:1.6;margin-top:6px}.footer{text-align:center;padding:2rem;color:var(--text-3);font-size:.85rem;margin-top:2rem;border-top:1px solid var(--border)}
[data-testid="stDataFrame"]{border-radius:var(--radius);overflow:hidden;border:1px solid var(--border);box-shadow:var(--shadow)}
</style>
""",
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Estado y helpers
# ═══════════════════════════════════════════════════════════════════════════════


def init_state() -> None:
    defaults = {
        "datos_bolsa": None,
        "datos_a3": None,
        "a3_market": None,
        "ultima_actualizacion": None,
        "builder_strategies": [],
        "strategy_counter": 1,
        "fas_context": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


def slug_crop(label: str) -> str:
    s = label.lower().strip().replace("í", "i").replace("á", "a")
    return {"soja": "soja", "maiz": "maiz", "maíz": "maiz", "trigo": "trigo", "girasol": "girasol"}.get(s, "soja")


def money(v: float, digits: int = 1) -> str:
    return f"${v:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def leg_to_dict(leg: Leg) -> Dict[str, Any]:
    return {"direction": leg.direction, "type": leg.type, "ratio": float(leg.ratio), "strike": float(leg.strike), "prima": float(leg.prima)}


def dict_to_leg(d: Dict[str, Any]) -> Leg:
    return Leg(d.get("direction", "buy"), d.get("type", "put"), float(d.get("ratio", 1)), float(d.get("strike", 0)), float(d.get("prima", 0)))


def strategy_to_object(s: Dict[str, Any]) -> Strategy:
    return Strategy(s["name"], [dict_to_leg(l) for l in s.get("legs", [])], s.get("color", COLORS[0]))


def new_strategy(name: Optional[str] = None, legs: Optional[List[Dict[str, Any]]] = None, color: Optional[str] = None) -> Dict[str, Any]:
    idx = st.session_state.strategy_counter
    st.session_state.strategy_counter += 1
    return {
        "id": idx,
        "name": name or f"Estrategia {idx}",
        "color": color or COLORS[(idx - 1) % len(COLORS)],
        "legs": legs or [],
    }


def option_cost(strategy: Dict[str, Any]) -> float:
    cost = 0.0
    for l in strategy.get("legs", []):
        if l.get("type") == "futuro":
            continue
        q = float(l.get("ratio", 1))
        prima = float(l.get("prima", 0))
        cost += prima * q if l.get("direction") == "buy" else -prima * q
    return cost


def net_sale_value(strategy: Dict[str, Any], price: float) -> float:
    """Replica lógica del HTML: físico + payoff opciones/futuro - prima neta."""
    net_prima = 0.0
    options_payoff = 0.0
    for l in strategy.get("legs", []):
        direction = l.get("direction", "buy")
        typ = l.get("type", "put")
        q = float(l.get("ratio", 1))
        strike = float(l.get("strike", 0))
        prima = float(l.get("prima", 0))
        if typ == "futuro":
            intrinsic = price - strike
            options_payoff += intrinsic * q if direction == "buy" else -intrinsic * q
        else:
            intrinsic = max(strike - price, 0) if typ == "put" else max(price - strike, 0)
            if direction == "buy":
                net_prima += prima * q
                options_payoff += intrinsic * q
            else:
                net_prima -= prima * q
                options_payoff -= intrinsic * q
    return price + options_payoff - net_prima


def strategy_kpis(strategy: Dict[str, Any], spot: float) -> Tuple[str, str, str]:
    values = [net_sale_value(strategy, p) for p in range(1, 1501)]
    floor = min(values)
    ceiling = max(values)
    floor_text = "Riesgo baja" if floor < spot * 0.5 else money(floor, 1)
    ceiling_text = "Ilimitado" if ceiling > 1400 else money(ceiling, 1)
    bes = []
    prev = net_sale_value(strategy, 1) - 1
    for p in range(2, 801):
        diff = net_sale_value(strategy, p) - p
        if (prev < 0 <= diff) or (prev > 0 >= diff):
            bes.append(p)
        prev = diff
    cost = option_cost(strategy)
    has_options = any(l.get("type") != "futuro" for l in strategy.get("legs", []))
    if abs(cost) < 1e-9 and has_options and not bes:
        be = "0 Costo"
    elif len(bes) == 1:
        be = money(float(bes[0]), 0)
    elif len(bes) > 1:
        be = "Múltiples"
    else:
        be = "—"
    return floor_text, ceiling_text, be


# ═══════════════════════════════════════════════════════════════════════════════
# Parser A3 y datos de mercado
# ═══════════════════════════════════════════════════════════════════════════════


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


def parse_contrato(contrato: str) -> Optional[Dict[str, Any]]:
    m = re.match(r"^([A-Z]{3})\.[A-Z.]+\/([A-Z0-9]+)(?:\s+(\d+(?:\.\d+)?)\s+([CP]))?$", contrato.strip().upper())
    if not m:
        return None
    crop = CROP_CODES.get(m.group(1))
    if not crop:
        return None
    out: Dict[str, Any] = {"crop": crop, "pos": m.group(2)}
    if m.group(3) and m.group(4):
        out["strike"] = float(m.group(3))
        out["type"] = "call" if m.group(4) == "C" else "put"
    return out


def col_find(cols: List[str], *needles: str) -> int:
    for i, c in enumerate(cols):
        if all(n.lower() in c for n in needles):
            return i
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

        crop, pos = info["crop"], info["pos"]
        if "futuro" in tipo or ("strike" not in info and "opci" not in tipo):
            futuros.setdefault(crop, []).append({"posicion": pos, "ajuste": ajuste, "vencimiento": vto, "ia": ia, "contrato": contrato})
        elif "opci" in tipo or "strike" in info:
            typ = info.get("type") or ("call" if put_call == "CALL" else "put")
            opciones.setdefault(crop, {}).setdefault(pos, {"calls": [], "puts": []})
            key = "calls" if typ == "call" else "puts"
            opciones[crop][pos][key].append({"strike": float(info.get("strike", 0)), "prima": ajuste, "contrato": contrato})

    for crop_opts in opciones.values():
        for pos_opts in crop_opts.values():
            pos_opts["calls"].sort(key=lambda x: x["strike"])
            pos_opts["puts"].sort(key=lambda x: x["strike"])
    if not futuros and not opciones:
        return None
    return {"futuros": futuros, "opciones": opciones, "metadata": {"fecha_datos": fecha or datetime.now().strftime("%d/%m/%Y")}}


def get_market_positions(crop: str) -> List[str]:
    market = st.session_state.a3_market
    if not market:
        return []
    return [f["posicion"] for f in market.get("futuros", {}).get(crop, []) if f.get("ajuste", 0) > 0]


def get_market_future(crop: str, pos: str) -> Optional[float]:
    market = st.session_state.a3_market
    if not market:
        return None
    for f in market.get("futuros", {}).get(crop, []):
        if f.get("posicion") == pos:
            return float(f.get("ajuste", 0))
    return None


def get_available_strikes(crop: str, pos: str, typ: str) -> List[float]:
    market = st.session_state.a3_market
    if not market or typ == "futuro":
        return []
    pos_opts = market.get("opciones", {}).get(crop, {}).get(pos, {})
    key = "calls" if typ == "call" else "puts"
    return [float(o["strike"]) for o in pos_opts.get(key, []) if o.get("strike")]


def lookup_prima(crop: str, pos: str, typ: str, strike: float) -> Optional[float]:
    market = st.session_state.a3_market
    if not market or typ == "futuro":
        return 0.0 if typ == "futuro" else None
    pos_opts = market.get("opciones", {}).get(crop, {}).get(pos, {})
    key = "calls" if typ == "call" else "puts"
    for o in pos_opts.get(key, []):
        if abs(float(o.get("strike", 0)) - float(strike)) < 0.001:
            return float(o.get("prima", 0))
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Visual helpers
# ═══════════════════════════════════════════════════════════════════════════════


def render_header() -> None:
    st.markdown(
        """
        <div class="main-header">
          <div class="logo">🌾</div>
          <div><h1>Estrategias Coberturas</h1><p>Espartina S.A. — Simulador de Coberturas & FAS</p></div>
          <div class="header-badge">Builder de Opciones</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cascade_bar(name: str, val: float, pct: float, bg: str, color: str) -> str:
    width = max(min(abs(pct), 100), 3)
    val_color = "var(--red)" if val < 0 else "var(--text)"
    return f"""
    <div class="bar-row">
      <div class="bar-labels"><span class="bar-name">{html.escape(name)}</span><span class="bar-val" style="color:{val_color}">{val:,.2f}</span></div>
      <div class="bar" style="width:{width:.1f}%;background:{bg};color:{color};">{pct:.1f}%</div>
    </div>
    """


def style_number(val: Any) -> str:
    if isinstance(val, (int, float)):
        color = "#1a854a" if val > 0 else "#c43030" if val < 0 else "#7e8574"
        return f"color:{color};font-weight:800"
    return ""


def build_payoff_chart(strategies: List[Dict[str, Any]], spot: float, min_price: float, max_price: float) -> go.Figure:
    prices = list(range(int(min_price), int(max_price) + 1, 2))
    if not prices:
        prices = [int(spot)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=prices, mode="lines", name="Físico sin cobertura", line=dict(color="#b0afa8", width=2, dash="dash")))
    for s in strategies:
        fig.add_trace(
            go.Scatter(
                x=prices,
                y=[net_sale_value(s, p) for p in prices],
                mode="lines",
                name=s["name"],
                line=dict(color=s.get("color", COLORS[0]), width=3),
                hovertemplate="<b>%{fullData.name}</b><br>Precio: $%{x:.1f}<br>Neto: $%{y:.2f}<extra></extra>",
            )
        )
    fig.add_vline(x=spot, line_dash="dot", line_color="#C8A44A", annotation_text=f"Spot {spot:.1f}", annotation_position="top")
    fig.update_layout(
        title="📊 Precio Neto de Venta — Coberturas vs Físico",
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
    scenarios = [
        ("Derrumbe (-30%)", spot * 0.70),
        ("Baja fuerte (-15%)", spot * 0.85),
        ("Spot", spot),
        ("Suba moderada (+15%)", spot * 1.15),
        ("Rally (+30%)", spot * 1.30),
    ]
    for s in strategies:
        for l in s.get("legs", []):
            if l.get("type") != "futuro" and l.get("strike"):
                strike = float(l["strike"])
                if not any(abs(x[1] - strike) < 0.5 for x in scenarios):
                    scenarios.append((f"Strike {l.get('type','').upper()} {strike:.1f}", strike))
    scenarios.sort(key=lambda x: x[1])
    rows = []
    for name, price in scenarios:
        row: Dict[str, Any] = {"Escenario": name, "Mercado": price, "Sin cobertura": price}
        for s in strategies:
            row[s["name"]] = net_sale_value(s, price)
        rows.append(row)
    return pd.DataFrame(rows)


def dominance_ranges(strategies: List[Dict[str, Any]], min_price: float, max_price: float) -> List[Dict[str, Any]]:
    ranges: List[Dict[str, Any]] = []
    current_name: Optional[str] = None
    current_color = "#b0afa8"
    start = int(min_price)
    for p in range(int(min_price), int(max_price) + 1):
        best_name = "Sin cobertura"
        best_val = float(p)
        best_color = "#b0afa8"
        for s in strategies:
            val = net_sale_value(s, float(p))
            if val > best_val + 0.05:
                best_val = val
                best_name = s["name"]
                best_color = s.get("color", COLORS[0])
        if current_name != best_name:
            if current_name is not None:
                ranges.append({"name": current_name, "start": start, "end": p - 1, "color": current_color})
            current_name = best_name
            current_color = best_color
            start = p
    if current_name is not None:
        ranges.append({"name": current_name, "start": start, "end": int(max_price), "color": current_color})
    return ranges


def make_simple_pdf(title: str, lines: List[str]) -> bytes:
    """PDF minimalista sin dependencias externas."""
    content = ["BT", "/F1 18 Tf", "50 790 Td", f"({pdf_escape(title)}) Tj", "/F1 10 Tf", "0 -28 Td"]
    for line in lines[:42]:
        content.append(f"({pdf_escape(line)}) Tj")
        content.append("0 -16 Td")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj")
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")
    objects.append(b"5 0 obj << /Length " + str(len(stream)).encode() + b" >> stream\n" + stream + b"\nendstream endobj")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj + b"\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


def pdf_escape(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════════════

render_header()

with st.sidebar:
    st.header("⚙️ Configuración")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        if st.button("🌾 Actualizar FOB", use_container_width=True):
            with st.spinner("Obteniendo datos FOB..."):
                try:
                    obtener_datos_bolsa.clear()
                except Exception:
                    pass
                datos = obtener_datos_bolsa()
                if datos:
                    st.session_state.datos_bolsa = datos
                    st.session_state.ultima_actualizacion = datetime.now()
                    st.success("✓ FOB actualizado")
                else:
                    st.error("No se obtuvieron datos")
    with col_b:
        st.caption(st.session_state.ultima_actualizacion.strftime("✓ %H:%M") if st.session_state.ultima_actualizacion else "⏳")

    if st.button("📡 Sincronizar A3", use_container_width=True):
        with st.spinner("Sincronizando A3..."):
            df = obtener_datos_a3()
            if df is not None and not df.empty:
                st.session_state.datos_a3 = df
                st.session_state.a3_market = parse_a3_market(df)
                if st.session_state.a3_market:
                    futs = sum(len(v) for v in st.session_state.a3_market.get("futuros", {}).values())
                    opts = sum(len(p.get("calls", [])) + len(p.get("puts", [])) for crop in st.session_state.a3_market.get("opciones", {}).values() for p in crop.values())
                    st.success(f"✓ A3 sincronizado: {futs} futuros, {opts} opciones")
                else:
                    st.warning("A3 sincronizado, pero no se detectó formato de futuros/opciones")
            else:
                st.warning("No se obtuvieron datos A3")

    st.divider()
    st.subheader("📊 Parámetros")
    cultivo_label = st.selectbox("Cultivo", list(CROP_LABELS.values()), index=0, key="cultivo_selector")
    cultivo = slug_crop(cultivo_label)

    # Posiciones: A3 tiene prioridad para estrategias; Bolsa para FOB/FAS.
    bolsa_positions = list(st.session_state.datos_bolsa.keys()) if st.session_state.datos_bolsa else []
    if bolsa_positions:
        posicion = st.selectbox("Posición FOB", bolsa_positions, key="posicion_selector")
    else:
        st.info("Actualizá FOB para cargar posiciones")
        posicion = None

    a3_positions = get_market_positions(cultivo)
    if a3_positions:
        market_pos = st.selectbox("Posición A3 opciones", a3_positions, key="market_pos_selector")
    else:
        market_pos = None
        st.caption("Sin posiciones A3 de opciones")

    if st.session_state.datos_bolsa and posicion:
        raw_fob = float(st.session_state.datos_bolsa[posicion].get(CROP_TO_FOB_KEY[cultivo], 0))
    else:
        raw_fob = get_market_future(cultivo, market_pos) if market_pos else 0
        raw_fob = raw_fob or {"soja": 417.0, "maiz": 208.0, "trigo": 234.0, "girasol": 520.0}[cultivo]

    st.divider()
    st.caption("Estado")
    st.caption(f"✓ {len(bolsa_positions)} posiciones FOB" if bolsa_positions else "⚠ Sin FOB")
    if st.session_state.a3_market:
        st.caption("✓ A3 mercado disponible")
    elif st.session_state.datos_a3 is not None:
        st.caption("⚠ A3 sin parseo de opciones")
    else:
        st.caption("⚠ Sin A3")

# ═══════════════════════════════════════════════════════════════════════════════
# Tabs principales
# ═══════════════════════════════════════════════════════════════════════════════

tab_builder, tab_manual, tab_fas = st.tabs(["📈 Builder de Coberturas", "📚 Manual Teórico", "🧮 Retenciones & FAS Teórico"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 Builder
# ═══════════════════════════════════════════════════════════════════════════════

with tab_builder:
    st.header("📈 Builder de Estrategias")
    spot = float(raw_fob or 0)
    min_x = max(1.0, spot * 0.70)
    max_x = spot * 1.30

    st.markdown(
        f"""
        <div class="fas-info-bar">
          <div class="fas-chip"><div class="lbl">Cultivo</div><div class="val">{CROP_LABELS[cultivo]}</div></div>
          <div class="fas-chip"><div class="lbl">FOB / Spot</div><div class="val">{spot:.1f} u$s</div></div>
          <div class="fas-chip"><div class="lbl">Posición FOB</div><div class="val">{html.escape(str(posicion or '—'))}</div></div>
          <div class="fas-chip"><div class="lbl">A3 opciones</div><div class="val">{html.escape(str(market_pos or '—'))}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.92, 1.58], gap="large")

    with left:
        st.markdown('<div class="top-panel">', unsafe_allow_html=True)
        st.subheader("📋 Cargar plantilla")
        presets = create_preset_strategies(spot)
        flat_presets: List[Tuple[str, Dict[str, Any]]] = []
        for cat_name, cat_items in presets.items():
            for item in cat_items:
                flat_presets.append((cat_name, item))
        preset_names = [f"{item['name']} · {cat.title()}" for cat, item in flat_presets]
        selected_preset_idx = st.selectbox("Plantilla", range(len(preset_names)), format_func=lambda i: preset_names[i], label_visibility="collapsed")
        pcat, pdata = flat_presets[selected_preset_idx]
        pstrategy = Strategy(pdata["name"], pdata["legs"], pdata["color"])
        cost = pstrategy.total_cost()
        cost_class = "debit" if cost < 0 else "credit" if cost > 0 else "zero"
        cost_text = f"Costo neto: ${abs(cost):.2f}" if cost < 0 else f"Crédito: ${cost:.2f}" if cost > 0 else "Costo: ~$0"
        st.markdown(
            f"""
            <div class="compact-card" style="border-left-color:{pdata['color']}">
              <div class="card-title">{html.escape(pdata['name'])}</div>
              <div class="card-desc">{html.escape(pdata['desc'])}</div>
              <div class="card-cost {cost_class}">{cost_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Agregar plantilla", use_container_width=True):
                st.session_state.builder_strategies.append(new_strategy(pdata["name"], [leg_to_dict(l) for l in pdata["legs"]], pdata["color"]))
                st.rerun()
        with c2:
            if st.button("+ Nueva vacía", use_container_width=True):
                st.session_state.builder_strategies.append(
                    new_strategy(
                        "Estrategia de Cobertura",
                        [{"direction": "buy", "type": "put", "ratio": 1.0, "strike": round(spot * 0.97), "prima": 0.0}],
                    )
                )
                st.rerun()
        if pdata.get("alert"):
            alerts = get_strategy_alerts()
            if pdata["name"] in alerts:
                st.warning(alerts[pdata["name"]]["mensaje"], icon="⚡")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-title">Estrategias activas</div>', unsafe_allow_html=True)
        if not st.session_state.builder_strategies:
            st.info("Agregá una plantilla o creá una estrategia nueva para empezar.")

        if st.button("🔄 Actualizar primas A3", use_container_width=True, disabled=not bool(st.session_state.a3_market and market_pos)):
            updated = 0
            for strat in st.session_state.builder_strategies:
                for leg in strat.get("legs", []):
                    if leg.get("type") == "futuro":
                        leg["prima"] = 0.0
                        continue
                    prima = lookup_prima(cultivo, market_pos or "", leg.get("type", "put"), float(leg.get("strike", 0)))
                    if prima is not None:
                        leg["prima"] = float(prima)
                        updated += 1
            st.success(f"{updated} primas actualizadas")
            st.rerun()

    with right:
        if st.session_state.builder_strategies:
            st.plotly_chart(build_payoff_chart(st.session_state.builder_strategies, spot, min_x, max_x), use_container_width=True)
        else:
            st.markdown(
                """
                <div class="top-panel" style="min-height:360px;display:flex;align-items:center;justify-content:center;text-align:center;">
                  <div><h3 style="color:var(--es-gold)!important;">👈 Seleccioná estrategias para comenzar</h3>
                  <p>Usá el menú compacto de plantillas o creá una estrategia desde cero.</p></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("⚙️ Constructor editable")

    for s_idx, strat in enumerate(list(st.session_state.builder_strategies)):
        st.markdown(f'<div class="strategy-shell" style="border-left-color:{strat.get("color", COLORS[0])}">', unsafe_allow_html=True)
        top_cols = st.columns([2.6, 1, 0.6])
        with top_cols[0]:
            strat["name"] = st.text_input("Nombre", value=strat["name"], key=f"strat_name_{strat['id']}", label_visibility="collapsed")
        with top_cols[1]:
            if st.button("+ Agregar pata", key=f"add_leg_{strat['id']}", use_container_width=True):
                strat.setdefault("legs", []).append({"direction": "buy", "type": "put", "ratio": 1.0, "strike": round(spot), "prima": 0.0})
                st.rerun()
        with top_cols[2]:
            if st.button("Borrar", key=f"del_strat_{strat['id']}", use_container_width=True):
                st.session_state.builder_strategies.pop(s_idx)
                st.rerun()

        st.markdown('<div class="leg-header"><span>Operación</span><span>Instrum.</span><span>Cant.</span><span>Strike</span><span>Prima</span><span></span></div>', unsafe_allow_html=True)
        for l_idx, leg in enumerate(list(strat.get("legs", []))):
            st.markdown('<div class="leg-wrap">', unsafe_allow_html=True)
            c_dir, c_type, c_ratio, c_strike, c_prima, c_del = st.columns([1.3, 1.15, 0.9, 1.0, 1.0, 0.35], gap="small")
            with c_dir:
                leg["direction"] = st.selectbox("Operación", ["buy", "sell"], index=0 if leg.get("direction") == "buy" else 1, format_func=lambda x: "Compra" if x == "buy" else "Venta", key=f"dir_{strat['id']}_{l_idx}", label_visibility="collapsed")
            with c_type:
                typ_options = ["put", "call", "futuro"]
                leg["type"] = st.selectbox("Instrumento", typ_options, index=typ_options.index(leg.get("type", "put")), format_func=lambda x: x.capitalize(), key=f"type_{strat['id']}_{l_idx}", label_visibility="collapsed")
            with c_ratio:
                leg["ratio"] = st.number_input("Ratio", min_value=0.0, value=float(leg.get("ratio", 1.0)), step=0.5, key=f"ratio_{strat['id']}_{l_idx}", label_visibility="collapsed")
            with c_strike:
                strikes = get_available_strikes(cultivo, market_pos or "", leg.get("type", "put"))
                current_strike = float(leg.get("strike", round(spot)))
                if strikes:
                    opts = strikes.copy()
                    if current_strike not in opts:
                        opts = [current_strike] + opts
                    selected = st.selectbox("Strike", opts, index=opts.index(current_strike), key=f"strike_sel_{strat['id']}_{l_idx}", label_visibility="collapsed")
                    leg["strike"] = float(selected)
                    prima = lookup_prima(cultivo, market_pos or "", leg.get("type", "put"), float(selected))
                    if prima is not None and st.session_state.get(f"autofill_{strat['id']}_{l_idx}", True):
                        leg["prima"] = float(prima)
                else:
                    leg["strike"] = st.number_input("Strike", value=current_strike, step=1.0, key=f"strike_{strat['id']}_{l_idx}", label_visibility="collapsed")
            with c_prima:
                disabled = leg.get("type") == "futuro"
                leg["prima"] = st.number_input("Prima", value=0.0 if disabled else float(leg.get("prima", 0.0)), step=0.1, disabled=disabled, key=f"prima_{strat['id']}_{l_idx}", label_visibility="collapsed")
            with c_del:
                if st.button("✕", key=f"del_leg_{strat['id']}_{l_idx}", use_container_width=True):
                    strat["legs"].pop(l_idx)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        floor_text, ceiling_text, be_text = strategy_kpis(strat, spot)
        cost = option_cost(strat)
        cost_label = f"Costo {money(cost,1)}" if cost > 0 else f"Crédito {money(abs(cost),1)}" if cost < 0 else "Costo $0"
        st.markdown(
            f"""
            <div class="kpi-grid">
              <div class="kpi-card"><div class="k-lbl">Costo neto</div><div class="k-val">{cost_label}</div></div>
              <div class="kpi-card"><div class="k-lbl">Piso asegurado</div><div class="k-val">{floor_text}</div></div>
              <div class="kpi-card"><div class="k-lbl">Empate B.E.</div><div class="k-val">{be_text}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.builder_strategies:
        st.subheader("🎯 Análisis de escenarios")
        df = scenario_rows(st.session_state.builder_strategies, spot)
        num_cols = [c for c in df.columns if c not in ["Escenario"]]
        st.dataframe(df.style.format({c: "${:.2f}" for c in num_cols}).map(style_number, subset=num_cols), use_container_width=True, hide_index=True)

        st.subheader("🏁 Rango de dominancia")
        dom_cols = st.columns(2)
        ranges = dominance_ranges(st.session_state.builder_strategies, min_x, max_x)
        for i, r in enumerate(ranges):
            with dom_cols[i % 2]:
                st.markdown(
                    f"""
                    <div class="winner-box" style="border-left-color:{r['color']}">
                      <div class="winner-range">Si el mercado cierra entre u$s {r['start']:.1f} y u$s {r['end']:.1f}</div>
                      <div class="winner-name" style="color:{r['color']}">Conviene: {html.escape(r['name'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        report_lines = [
            f"Cultivo: {CROP_LABELS[cultivo]}",
            f"Posición FOB: {posicion or '-'}",
            f"Spot: {spot:.2f}",
            "",
            "Estrategias:",
        ]
        for s in st.session_state.builder_strategies:
            report_lines.append(f"- {s['name']} | costo neto {option_cost(s):.2f} | patas {len(s.get('legs', []))}")
        pdf = make_simple_pdf("Reporte Coberturas Espartina", report_lines)
        st.download_button("📄 Exportar PDF", data=pdf, file_name="reporte_coberturas.pdf", mime="application/pdf")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 Manual
# ═══════════════════════════════════════════════════════════════════════════════

with tab_manual:
    st.header("📚 Catálogo de Estructuras Comerciales")
    st.markdown(
        """
El diseño de una cobertura no busca predecir el mercado, sino administrar asimetrías de riesgo. Toda decisión operativa implica un **trade-off** entre costo financiero, riesgo de cola y costo de oportunidad.

### Protecciones base
**Put seco:** seguro puro, máxima protección sin techo.  
**Put spread:** protección con franquicia, menor costo y piso limitado.  
**Collar:** túnel de rentabilidad, costo bajo/cero a cambio de resignar upside.

### Estructuras avanzadas
**Gaviota:** put spread financiado con venta de call.  
**Futuro + Call:** fijación sintética con opcionalidad alcista.  
**Ratio Put Spread 1x2:** costo bajo/cero con riesgo en baja extrema.
        """
    )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 FAS / Retenciones
# ═══════════════════════════════════════════════════════════════════════════════

with tab_fas:
    st.header("🧮 Retenciones & FAS Teórico")
    defaults = RET_DEFAULTS[cultivo]

    fob_default = float(raw_fob or {"soja": 417, "maiz": 208, "trigo": 234, "girasol": 520}[cultivo])
    top = st.columns([1, 1, 1, 1, 1])
    with top[0]:
        ret_cultivo = st.selectbox("Cultivo", list(CROP_LABELS.keys()), index=list(CROP_LABELS.keys()).index(cultivo), format_func=lambda x: CROP_LABELS[x], key="ret_cultivo")
    if ret_cultivo != cultivo:
        cultivo = ret_cultivo
        defaults = RET_DEFAULTS[cultivo]
    with top[1]:
        fob_indice = st.number_input("FOB Índice", value=fob_default, step=0.1, key="ret_fob_indice")
    with top[2]:
        ret_pct = st.number_input("Ret %", value=float(defaults["ret"]), step=0.1, key="ret_pct")
    with top[3]:
        fobbing = st.number_input("Fobbing", value=float(defaults["fobbing"]), step=0.1, key="ret_fobbing")
    with top[4]:
        fas_obj = st.number_input("FAS Obj 1", value=float(defaults["fas_obj"]), step=0.1, key="ret_fas_obj")

    fas_ctp = fob_indice * (1 - ret_pct / 100) - fobbing
    ret_amount = fob_indice * (ret_pct / 100)
    margin = fas_ctp - fas_obj
    fob_needed = (fas_obj + fobbing) / (1 - ret_pct / 100) if ret_pct < 100 else 0
    ret_impl = (1 - (fas_obj + fobbing) / fob_indice) * 100 if fob_indice else 0

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        bars = ""
        bars += render_cascade_bar(f"FOB {CROP_LABELS[cultivo]}", fob_indice, 100, "var(--es-gold-light)", "var(--es-gold)")
        bars += render_cascade_bar(f"Retención {ret_pct:.1f}%", -ret_amount, ret_pct, "#fde8e8", "var(--red)")
        bars += render_cascade_bar("Fobbing", -fobbing, (fobbing / fob_indice * 100) if fob_indice else 0, "var(--bg-input)", "var(--text-3)")
        margin_color = "var(--green)" if margin >= 0 else "var(--red)"
        st.markdown(
            f"""
            <div class="cascade-panel">
              <div class="cascade-title" style="color:var(--es-green)">Exportación grano {html.escape(str(posicion or ''))}</div>
              {bars}
              <div class="result-row"><span class="result-lbl">FAS Teórico (CTP)</span><span class="result-val" style="color:var(--es-green)">{fas_ctp:.2f}</span></div>
              <div class="margin-row"><span>Margen export. vs obj {fas_obj:.1f}</span><strong style="color:{margin_color}">{margin:+.2f}</strong></div>
              <div class="tri-grid">
                <div class="tri-chip"><div class="tri-lbl">FOB Necesario</div><div class="tri-val" style="color:var(--blue)">{fob_needed:.2f}</div><div class="tri-sub">Para pagar FAS obj {fas_obj:.1f}</div></div>
                <div class="tri-chip"><div class="tri-lbl">Retención Implícita</div><div class="tri-val" style="color:var(--orange)">{ret_impl:.2f}%</div><div class="tri-sub">Gap: {ret_impl-ret_pct:+.2f} pp</div></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    crush_fas = None
    with c2:
        if cultivo == "soja":
            precios = st.session_state.datos_bolsa.get(posicion, {}) if st.session_state.datos_bolsa and posicion else {}
            ca = st.number_input("FOB Aceite", value=float(precios.get("aceite", 1200.0)), step=0.1, key="crush_aceite")
            cha = st.number_input("FOB Harina", value=float(precios.get("harina", 353.0)), step=0.1, key="crush_harina")
            coef_cols = st.columns(4)
            with coef_cols[0]:
                coef_a = st.number_input("Coef. Aceite", value=0.19, step=0.01, key="coef_a")
            with coef_cols[1]:
                coef_h = st.number_input("Coef. Harina", value=0.78, step=0.01, key="coef_h")
            with coef_cols[2]:
                ret_sub = st.number_input("Ret Sub %", value=22.5, step=0.1, key="ret_sub")
            with coef_cols[3]:
                gto_ind = st.number_input("Gto Ind.", value=29.0, step=1.0, key="gto_ind")
            fobbing_sub = st.number_input("Fobbing subprod", value=19.0, step=0.5, key="fobbing_sub")
            aceite_bruto = ca * coef_a
            harina_bruto = cha * coef_h
            bruto = aceite_bruto + harina_bruto
            ret_sub_val = bruto * ret_sub / 100
            crush_fas = bruto - ret_sub_val - fobbing_sub - gto_ind
            crush_margin = crush_fas - fas_obj
            bars2 = ""
            bars2 += render_cascade_bar(f"Aceite ({ca:.1f} × {coef_a:.2f})", aceite_bruto, (aceite_bruto / bruto * 100) if bruto else 0, "var(--es-green-light)", "var(--es-green-dark)")
            bars2 += render_cascade_bar(f"Harina ({cha:.1f} × {coef_h:.2f})", harina_bruto, (harina_bruto / bruto * 100) if bruto else 0, "var(--es-green-light)", "var(--es-green-dark)")
            bars2 += render_cascade_bar(f"Ret subprod {ret_sub:.1f}%", -ret_sub_val, ret_sub, "#fde8e8", "var(--red)")
            bars2 += render_cascade_bar("Fobbing subprod", -fobbing_sub, (fobbing_sub / bruto * 100) if bruto else 0, "var(--bg-input)", "var(--text-3)")
            bars2 += render_cascade_bar("Gasto industrialización", -gto_ind, (gto_ind / bruto * 100) if bruto else 0, "var(--bg-input)", "var(--text-3)")
            cm_color = "var(--green)" if crush_margin >= 0 else "var(--red)"
            st.markdown(
                f"""
                <div class="cascade-panel">
                  <div class="cascade-title" style="color:var(--es-gold)">Crushing subproductos</div>
                  {bars2}
                  <div class="result-row"><span class="result-lbl">FAS Crushing</span><span class="result-val" style="color:var(--es-gold)">{crush_fas:.2f}</span></div>
                  <div class="margin-row"><span>Margen crushing vs obj {fas_obj:.1f}</span><strong style="color:{cm_color}">{crush_margin:+.2f}</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("El crushing solo aplica para soja.")

    st.markdown('<div class="section-title">Simulador de escenario — Baja de retenciones</div>', unsafe_allow_html=True)
    reduction = st.slider("Reducción de retenciones", min_value=0, max_value=100, value=25, step=5, format="-%d%%")
    new_ret = ret_pct * (1 - reduction / 100)
    new_fas = fob_indice * (1 - new_ret / 100) - fobbing
    comp = pd.DataFrame([
        {"Escenario": "Actual", "Retención grano": ret_pct, "FAS teórico": fas_ctp, "FAS crushing": crush_fas if crush_fas is not None else None},
        {"Escenario": "Con reducción", "Retención grano": new_ret, "FAS teórico": new_fas, "FAS crushing": None},
    ])
    st.dataframe(comp.style.format({"Retención grano": "{:.1f}%", "FAS teórico": "${:.2f}", "FAS crushing": "${:.2f}"}), use_container_width=True, hide_index=True)
    st.markdown(f"""<div class="note"><strong>Conexión con coberturas:</strong> si cubrís a FOB <strong>{fob_indice:.1f}</strong> con un PUT, tu piso de FAS neto es <strong>{fas_ctp:.2f}</strong> u$s/tn menos la prima pagada.</div>""", unsafe_allow_html=True)

st.markdown(
    """
<div class="footer">
  🌾 <strong>Espartina S.A.</strong> — Dashboard de Estrategias de Cobertura<br>
  <span style="font-size:.75rem">Datos FOB desde Bolsa de Cereales · Datos A3 desde Google Sheets</span>
</div>
""",
    unsafe_allow_html=True,
)
