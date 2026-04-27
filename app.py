"""
Estrategias de Cobertura - Espartina S.A.
Refactor con Separacion de Responsabilidades.

Panel A:
    Mercado & FAS Teorico (Bolsa de Cereales).
    Fuente unica para FOB, retenciones, fobbing y cascada FAS.

Panel B:
    Builder de Coberturas (A3).
    Fuente unica para futuros, calls, puts, strikes y primas.

Regla de datos:
    Los valores de mercado leidos desde Bolsa/A3 se almacenan crudos y no se
    modifican antes de mostrarse. Las retenciones, fobbing y gastos solo se
    aplican dentro de las cascadas y calculos derivados.
"""

from __future__ import annotations

import io
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from google_sheets import obtener_datos_a3
from scraper import obtener_datos_bolsa

# =============================================================================
# Configuracion general
# =============================================================================

st.set_page_config(
    page_title="Estrategias de Cobertura - Espartina S.A.",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Constantes de dominio
# =============================================================================

CROP_LABELS = {
    "soja": "Soja",
    "maiz": "Maíz",
    "trigo": "Trigo",
    "girasol": "Girasol",
}

CROP_TO_FOB_KEY = {
    "soja": "soja",
    "maiz": "maiz",
    "trigo": "trigo",
    "girasol": "girasol",
}

CROP_CODE_MAP = {
    "SOJ": "soja",
    "MAI": "maiz",
    "TRI": "trigo",
    "GIR": "girasol",
}

RET_DEFAULTS = {
    # Valores alineados al prototipo HTML original.
    "soja": {"ret_pct": 26.0, "fobbing": 12.0, "fas_obj": 323.0},
    "maiz": {"ret_pct": 7.0, "fobbing": 11.0, "fas_obj": 185.0},
    "trigo": {"ret_pct": 7.0, "fobbing": 13.0, "fas_obj": 216.0},
    "girasol": {"ret_pct": 7.0, "fobbing": 14.0, "fas_obj": 475.0},
}

COLORS = ["#1A6B3C", "#2563eb", "#d97706", "#7c3aed", "#c43030", "#0d9488"]

MONTH_LABELS = {
    "ENE": "Enero",
    "FEB": "Febrero",
    "MAR": "Marzo",
    "ABR": "Abril",
    "MAY": "Mayo",
    "JUN": "Junio",
    "JUL": "Julio",
    "AGO": "Agosto",
    "SEP": "Septiembre",
    "OCT": "Octubre",
    "NOV": "Noviembre",
    "DIC": "Diciembre",
    "DIS": "Diciembre",
}


# =============================================================================
# Estilos: sistema visual compacto y horizontal
# =============================================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --es-green: #1A6B3C;
  --es-green-dark: #145430;
  --es-green-light: #e8f5ec;
  --es-green-muted: #2d8a54;
  --es-gold: #C8A44A;
  --es-gold-light: #f9f3e3;
  --bg: #f4f5f0;
  --bg-card: #ffffff;
  --bg-input: #f0f1ec;
  --text: #1c2118;
  --text-2: #505845;
  --text-3: #7e8574;
  --border: #dde0d5;
  --border-2: #c8cbbe;
  --green: #1a854a;
  --red: #c43030;
  --blue: #2563eb;
  --orange: #d97706;
  --font: 'DM Sans', system-ui, sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --radius: 10px;
  --shadow: 0 1px 4px rgba(26,107,60,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow-lg: 0 4px 16px rgba(26,107,60,.08), 0 2px 6px rgba(0,0,0,.04);
}

html, body, [class*="css"] {
  font-family: var(--font) !important;
}

.stApp {
  background: var(--bg) !important;
  color: var(--text) !important;
}

.block-container {
  max-width: 1320px;
  padding-top: 16px;
  padding-bottom: 40px;
}

section[data-testid="stSidebar"] {
  background: #f7f8f3 !important;
  border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] * {
  color: var(--text) !important;
}

h1, h2, h3 {
  color: var(--text) !important;
  letter-spacing: -0.25px;
}

label, .stCaption, .stMarkdown p {
  color: var(--text-2) !important;
}

.main-header {
  background: linear-gradient(135deg, var(--es-green-dark) 0%, var(--es-green) 60%, var(--es-green-muted) 100%);
  padding: 16px 24px;
  border-radius: 12px;
  margin-bottom: 18px;
  box-shadow: 0 2px 12px rgba(20,84,48,.25);
  border-bottom: 3px solid var(--es-gold);
  display: flex;
  align-items: center;
  gap: 14px;
}

.main-header .logo {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,.15);
  border: 1px solid rgba(255,255,255,.12);
  font-size: 20px;
}

.main-header h1 {
  color: #fff !important;
  margin: 0;
  font-size: 22px;
  font-weight: 800;
}

.main-header p {
  color: rgba(255,255,255,.68) !important;
  margin: 1px 0 0;
  font-size: 12px;
}

.header-badge {
  margin-left: auto;
  background: rgba(200,164,74,.20);
  border: 1px solid rgba(200,164,74,.35);
  color: var(--es-gold);
  font-size: 10px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 20px;
  letter-spacing: .7px;
  text-transform: uppercase;
}

div.stButton > button {
  background: var(--es-green) !important;
  color: #fff !important;
  border: 1px solid var(--es-green) !important;
  border-radius: 8px !important;
  min-height: 36px !important;
  padding: 7px 12px !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
  line-height: 1.1 !important;
  box-shadow: 0 1px 3px rgba(26,107,60,.16) !important;
}

div.stButton > button:hover {
  background: var(--es-green-dark) !important;
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(26,107,60,.2) !important;
}

section[data-testid="stSidebar"] div.stButton > button {
  width: 100% !important;
  background: var(--es-gold) !important;
  border-color: var(--es-gold) !important;
  color: #fff !important;
  min-height: 42px !important;
  font-size: 13px !important;
}

div[data-baseweb="select"] > div,
input,
textarea {
  background: var(--bg-input) !important;
  border-color: var(--border) !important;
  border-radius: 7px !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
}

div[data-baseweb="select"] > div:focus-within,
input:focus,
textarea:focus {
  border-color: var(--es-green) !important;
  box-shadow: 0 0 0 3px rgba(26,107,60,.10) !important;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.panel-heading h2 {
  margin: 0 !important;
  font-size: 22px !important;
  color: var(--text) !important;
}

.panel-subtitle {
  margin: -6px 0 14px;
  font-size: 12px;
  color: var(--text-3);
}

.source-chip-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 8px 0 14px;
}

.source-chip {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 10px 13px;
  min-width: 160px;
}

.source-chip .lbl {
  display: block;
  color: var(--text-3);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .05em;
}

.source-chip .val {
  display: block;
  font-family: var(--mono);
  font-size: 16px;
  font-weight: 900;
  color: var(--text);
}

.cascade-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  box-shadow: var(--shadow);
  margin-bottom: 14px;
}

.cascade-title {
  font-size: 15px;
  font-weight: 900;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.bar-row {
  margin-bottom: 9px;
}

.bar-labels {
  display: flex;
  justify-content: space-between;
  margin-bottom: 3px;
}

.bar-name {
  font-size: 12px;
  color: var(--text-2);
}

.bar-val {
  font-size: 12px;
  font-family: var(--mono);
  font-weight: 800;
}

.bar {
  height: 24px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  padding-left: 8px;
  font-size: 11px;
  font-family: var(--mono);
  font-weight: 800;
  transition: width .2s ease;
}

.result-row {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 2px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.result-lbl {
  font-size: 13px;
  font-weight: 900;
}

.result-val {
  font-size: 24px;
  font-weight: 900;
  font-family: var(--mono);
}

.margin-row {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

.tri-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 10px;
}

.tri-chip {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
}

.tri-lbl {
  font-size: 10px;
  color: var(--text-3);
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .04em;
}

.tri-val {
  font-size: 14px;
  font-weight: 900;
  font-family: var(--mono);
  margin-top: 2px;
}

.tri-sub {
  font-size: 10px;
  color: var(--text-3);
}

.strategy-shell {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 4px solid var(--es-green);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px 14px 10px;
  margin-bottom: 14px;
}

.leg-label-row {
  display: grid;
  grid-template-columns: 1.35fr 1.15fr .75fr 1.35fr 1fr .35fr;
  gap: 8px;
  font-size: 10px;
  color: var(--text-3);
  font-weight: 900;
  letter-spacing: .04em;
  text-transform: uppercase;
  margin: 4px 0 2px;
  padding: 0 4px;
}

.leg-row-shell {
  background: var(--bg-input);
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 7px 8px;
  margin-bottom: 7px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
}

.kpi-card {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 7px;
  text-align: center;
}

.k-lbl {
  font-size: 9px;
  text-transform: uppercase;
  color: var(--text-3);
  font-weight: 900;
  letter-spacing: .05em;
  margin-bottom: 3px;
}

.k-val {
  font-size: 13px;
  font-weight: 900;
  font-family: var(--mono);
}

.winner-box {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 4px solid var(--es-gold);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  box-shadow: var(--shadow);
}

.winner-range {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-2);
  margin-bottom: 3px;
}

.winner-name {
  font-size: 14px;
  font-weight: 900;
}

.small-muted {
  font-size: 12px;
  color: var(--text-3);
}

[data-testid="stDataFrame"] {
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# Inicializacion de estado
# =============================================================================

def init_state() -> None:
    defaults = {
        "data_bolsa": {
            "cotizaciones": None,
            "last_update": None,
            "source": "Bolsa de Cereales",
        },
        "data_a3": {
            "raw_df": None,
            "market": None,
            "last_update": None,
            "source": "A3 Google Sheet",
        },
        "fas_context": None,
        "builder_strategies": [],
        "next_strategy_id": 1,
        "next_leg_id": 1,
        "audit_events": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Compatibilidad con versiones anteriores del repositorio.
    if "datos_bolsa" in st.session_state and st.session_state.get("datos_bolsa") and not st.session_state.data_bolsa["cotizaciones"]:
        st.session_state.data_bolsa["cotizaciones"] = st.session_state.get("datos_bolsa")
        st.session_state.data_bolsa["last_update"] = st.session_state.get("ultima_actualizacion")

    if "datos_a3" in st.session_state and st.session_state.get("datos_a3") is not None and st.session_state.data_a3["raw_df"] is None:
        st.session_state.data_a3["raw_df"] = st.session_state.get("datos_a3")


init_state()


# =============================================================================
# Helpers generales
# =============================================================================

def add_audit(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.audit_events.append(f"{timestamp} - {message}")
    st.session_state.audit_events = st.session_state.audit_events[-30:]


def fmt_num(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_money(value: float, digits: int = 2) -> str:
    return f"${fmt_num(value, digits)}"


def parse_num(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, float) and math.isnan(value):
        return 0.0
    s = str(value).strip()
    if s in {"", "-", "N/A", "nan", "None", "s/c", "S/C"}:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def normalize_position_code(label: str) -> str:
    """Convierte 'ABR 2026' o 'ABR2026' a 'ABR26' para matchear A3."""
    raw = str(label).upper().strip().replace(" ", "")
    match = re.match(r"([A-Z]{3})(\d{2,4})", raw)
    if not match:
        return raw
    month, year = match.groups()
    return f"{month}{year[-2:]}"


def position_label_from_code(code: str) -> str:
    """Convierte 'MAY26' a 'Mayo 26' para labels legibles."""
    raw = str(code).upper().strip()
    month = re.sub(r"\d", "", raw)
    year = re.sub(r"[A-Z]", "", raw)
    return f"{MONTH_LABELS.get(month, month)} {year}" if year else raw


def get_quotes() -> Dict[str, Dict[str, float]]:
    return st.session_state.data_bolsa.get("cotizaciones") or {}


def get_positions() -> List[str]:
    return list(get_quotes().keys())


def raw_quote(position: str) -> Dict[str, float]:
    return get_quotes().get(position, {}) or {}


def get_market_fob(crop: str, position: str) -> float:
    """Devuelve el FOB crudo de Bolsa. No descuenta retenciones ni gastos."""
    key = CROP_TO_FOB_KEY.get(crop, "soja")
    value = raw_quote(position).get(key, 0.0)
    return float(value or 0.0)


def get_market_byproduct(position: str, key: str) -> float:
    """Devuelve subproductos crudos de Bolsa. Sin gastos ni transformaciones."""
    return float(raw_quote(position).get(key, 0.0) or 0.0)


def safe_styler_map(styler: pd.io.formats.style.Styler, func, subset: List[str]):
    if hasattr(styler, "map"):
        return styler.map(func, subset=subset)
    return styler.applymap(func, subset=subset)


def color_delta(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if value > 0:
        return "color:#1a854a;font-weight:700"
    if value < 0:
        return "color:#c43030;font-weight:700"
    return "color:#7e8574;font-weight:700"


# =============================================================================
# Parser A3: futuros, calls y puts
# =============================================================================

def parse_contract(contract: str) -> Optional[Dict[str, Any]]:
    """
    Parse robusto del contrato A3:
    - SOJ.ROS/MAY26 -> futuro soja mayo 26
    - SOJ.ROS/MAY26 248 C -> call soja mayo 26 strike 248
    """
    text = str(contract).strip().upper()
    pattern = r"^([A-Z]{3})\.[A-Z.]+\/([A-Z0-9]+)(?:\s+(\d+(?:[\.,]\d+)?)\s+([CP]))?$"
    match = re.match(pattern, text)
    if not match:
        return None

    crop_code, pos, strike_raw, opt_code = match.groups()
    crop = CROP_CODE_MAP.get(crop_code)
    if not crop:
        return None

    parsed: Dict[str, Any] = {"crop": crop, "pos": pos}
    if strike_raw and opt_code:
        parsed["strike"] = parse_num(strike_raw)
        parsed["opt_type"] = "call" if opt_code == "C" else "put"
    return parsed


def find_column(headers: List[str], *needles: str) -> int:
    for idx, header in enumerate(headers):
        normalized = str(header).strip().lower()
        if all(needle in normalized for needle in needles):
            return idx
    return -1


def dataframe_to_rows_and_headers(df: pd.DataFrame) -> Tuple[List[str], List[List[Any]]]:
    """
    El CSV de A3 puede venir con header real en columns o dentro de las primeras filas.
    Esta funcion normaliza ambos casos.
    """
    if df is None or df.empty:
        return [], []

    headers = [str(c).strip() for c in df.columns]
    if any("contrato" in h.lower() for h in headers):
        return headers, df.astype(object).values.tolist()

    rows = df.astype(object).values.tolist()
    for idx, row in enumerate(rows[:10]):
        first_cell = str(row[0]).strip().lower() if row else ""
        if "contrato" in first_cell:
            clean_headers = [str(x).strip() for x in row]
            return clean_headers, rows[idx + 1 :]

    return headers, rows


def parse_a3_market(df: pd.DataFrame) -> Dict[str, Any]:
    headers, rows = dataframe_to_rows_and_headers(df)
    normalized_headers = [h.lower().strip() for h in headers]

    idx_contrato = find_column(normalized_headers, "contrato")
    if idx_contrato < 0:
        idx_contrato = 0

    idx_vto = find_column(normalized_headers, "vencimiento")
    idx_moneda = find_column(normalized_headers, "moneda")
    idx_tipo = find_column(normalized_headers, "tipo")
    idx_put_call = find_column(normalized_headers, "put", "call")
    idx_ajuste = find_column(normalized_headers, "ajuste")
    if idx_ajuste < 0:
        idx_ajuste = find_column(normalized_headers, "valor")
    idx_ia = find_column(normalized_headers, "inter", "abierto")
    idx_fecha = find_column(normalized_headers, "fecha", "dato")

    market = {
        "futuros": {},
        "opciones": {},
        "fecha_datos": "",
        "stats": {"futuros": 0, "opciones": 0},
    }

    for row in rows:
        if idx_contrato >= len(row):
            continue

        contrato = str(row[idx_contrato]).strip()
        if not contrato or contrato.lower() == "nan":
            continue

        moneda = str(row[idx_moneda]).strip().upper() if 0 <= idx_moneda < len(row) else ""
        if moneda and moneda != "USD":
            continue

        tipo = str(row[idx_tipo]).strip().lower() if 0 <= idx_tipo < len(row) else ""
        put_call_raw = str(row[idx_put_call]).strip().upper() if 0 <= idx_put_call < len(row) else ""
        ajuste = parse_num(row[idx_ajuste]) if 0 <= idx_ajuste < len(row) else 0.0
        ia = parse_num(row[idx_ia]) if 0 <= idx_ia < len(row) else 0.0
        vto = str(row[idx_vto]).strip() if 0 <= idx_vto < len(row) else ""

        if not market["fecha_datos"] and 0 <= idx_fecha < len(row):
            market["fecha_datos"] = str(row[idx_fecha]).strip()

        info = parse_contract(contrato)
        if not info:
            continue

        crop = info["crop"]
        pos = info["pos"]

        is_future = "futuro" in tipo or ("strike" not in info and "opci" not in tipo)
        is_option = "opci" in tipo or "strike" in info

        if is_future:
            market["futuros"].setdefault(crop, [])
            market["futuros"][crop].append(
                {
                    "pos": pos,
                    "precio": ajuste,
                    "vto": vto,
                    "ia": ia,
                    "contrato": contrato,
                }
            )
            market["stats"]["futuros"] += 1

        elif is_option:
            opt_type = info.get("opt_type")
            if not opt_type:
                opt_type = "call" if put_call_raw == "CALL" else "put" if put_call_raw == "PUT" else ""
            if opt_type not in {"call", "put"}:
                continue

            market["opciones"].setdefault(crop, {})
            market["opciones"][crop].setdefault(pos, {"calls": [], "puts": []})

            target = "calls" if opt_type == "call" else "puts"
            market["opciones"][crop][pos][target].append(
                {
                    "strike": float(info.get("strike", 0.0)),
                    "prima": ajuste,
                    "contrato": contrato,
                }
            )
            market["stats"]["opciones"] += 1

    for crop_opts in market["opciones"].values():
        for pos_opts in crop_opts.values():
            pos_opts["calls"].sort(key=lambda x: x["strike"])
            pos_opts["puts"].sort(key=lambda x: x["strike"])

    return market


def get_a3_market() -> Optional[Dict[str, Any]]:
    return st.session_state.data_a3.get("market")


def get_a3_positions(crop: str) -> List[str]:
    market = get_a3_market()
    if not market:
        return []

    pos_set = set()
    for fut in market.get("futuros", {}).get(crop, []):
        pos_set.add(fut["pos"])

    for pos in market.get("opciones", {}).get(crop, {}).keys():
        pos_set.add(pos)

    return sorted(pos_set)


def get_a3_option_list(crop: str, position_code: str, option_type: str) -> List[Dict[str, float]]:
    market = get_a3_market()
    if not market or not crop or not position_code:
        return []

    pos_data = market.get("opciones", {}).get(crop, {}).get(position_code, {})
    return pos_data.get("calls" if option_type == "call" else "puts", [])


def get_available_strikes(crop: str, position_code: str, option_type: str) -> List[float]:
    return [float(item["strike"]) for item in get_a3_option_list(crop, position_code, option_type)]


def lookup_market_premium(crop: str, position_code: str, option_type: str, strike: float) -> Optional[float]:
    if option_type == "futuro":
        return 0.0

    options = get_a3_option_list(crop, position_code, option_type)
    for item in options:
        if abs(float(item["strike"]) - float(strike)) < 0.0001:
            return float(item["prima"])

    return None


# =============================================================================
# Operaciones de carga
# =============================================================================

def update_bolsa_data() -> None:
    with st.spinner("Consultando FOB Bolsa de Cereales..."):
        if hasattr(obtener_datos_bolsa, "clear"):
            obtener_datos_bolsa.clear()

        datos = obtener_datos_bolsa()
        if not datos:
            st.error("No se obtuvieron cotizaciones de Bolsa.")
            return

        # Se guarda crudo. No se aplican retenciones/gastos en esta capa.
        st.session_state.data_bolsa = {
            "cotizaciones": datos,
            "last_update": datetime.now(),
            "source": "Bolsa de Cereales",
        }
        add_audit(f"Bolsa actualizada: {len(datos)} posiciones.")
        st.success("FOB actualizado desde Bolsa de Cereales.")


def update_a3_data() -> None:
    with st.spinner("Sincronizando A3..."):
        if hasattr(obtener_datos_a3, "clear"):
            obtener_datos_a3.clear()

        df = obtener_datos_a3()
        if df is None or df.empty:
            st.warning("A3 no devolvió datos.")
            return

        market = parse_a3_market(df)
        st.session_state.data_a3 = {
            "raw_df": df,
            "market": market,
            "last_update": datetime.now(),
            "source": "A3 Google Sheet",
        }

        st.success(
            f"A3 sincronizado: {market['stats']['futuros']} futuros, "
            f"{market['stats']['opciones']} opciones."
        )
        add_audit(
            f"A3 sincronizado: {market['stats']['futuros']} futuros / "
            f"{market['stats']['opciones']} opciones."
        )


# =============================================================================
# Cascadas de FAS
# =============================================================================

def cascade_bar(name: str, value: float, pct: float, bg: str, color: str) -> str:
    width = max(min(float(pct), 100.0), 3.0)
    sign_color = "var(--red)" if value < 0 else "var(--text)"
    return f"""
    <div class="bar-row">
      <div class="bar-labels">
        <span class="bar-name">{name}</span>
        <span class="bar-val" style="color:{sign_color};">{fmt_num(value, 2)}</span>
      </div>
      <div class="bar" style="width:{width:.1f}%; background:{bg}; color:{color};">{pct:.1f}%</div>
    </div>
    """


def render_grain_cascade(
    crop: str,
    position: str,
    fob_source: float,
    ret_pct: float,
    fobbing: float,
    fas_obj: float,
) -> Dict[str, float]:
    ret_value = fob_source * ret_pct / 100
    fas_ctp = fob_source - ret_value - fobbing
    margin = fas_ctp - fas_obj
    fob_needed = (fas_obj + fobbing) / (1 - ret_pct / 100) if ret_pct < 100 else 0.0
    ret_impl = (1 - ((fas_obj + fobbing) / fob_source)) * 100 if fob_source else 0.0
    gap_pp = ret_impl - ret_pct

    bars = ""
    bars += cascade_bar(f"FOB {CROP_LABELS[crop]}", fob_source, 100, "var(--es-gold-light)", "var(--es-gold)")
    bars += cascade_bar(f"Retención {ret_pct:.1f}%", -ret_value, ret_pct, "#fde8e8", "var(--red)")
    bars += cascade_bar("Fobbing", -fobbing, (fobbing / fob_source * 100) if fob_source else 0, "var(--bg-input)", "var(--text-3)")

    margin_color = "var(--green)" if margin >= 0 else "var(--red)"
    html = f"""
    <div class="cascade-panel">
      <div class="cascade-title" style="color:var(--es-green);">Exportación grano {position}</div>
      {bars}
      <div class="result-row">
        <span class="result-lbl">FAS Teórico (CTP)</span>
        <span class="result-val" style="color:var(--es-green);">{fmt_num(fas_ctp, 2)}</span>
      </div>
      <div class="margin-row">
        <span>Margen export. vs obj {fmt_num(fas_obj, 1)}</span>
        <strong style="color:{margin_color};">{'+' if margin >= 0 else ''}{fmt_num(margin, 2)}</strong>
      </div>
      <div class="tri-grid">
        <div class="tri-chip">
          <div class="tri-lbl">FOB Necesario</div>
          <div class="tri-val" style="color:var(--blue);">{fmt_num(fob_needed, 2)}</div>
          <div class="tri-sub">Para pagar FAS obj {fmt_num(fas_obj, 1)}</div>
        </div>
        <div class="tri-chip">
          <div class="tri-lbl">Retención Implícita</div>
          <div class="tri-val" style="color:var(--orange);">{fmt_num(ret_impl, 2)}%</div>
          <div class="tri-sub">Gap: {'+' if gap_pp >= 0 else ''}{fmt_num(gap_pp, 2)} pp</div>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    return {
        "ret_value": ret_value,
        "fas_ctp": fas_ctp,
        "margin": margin,
        "fob_needed": fob_needed,
        "ret_impl": ret_impl,
        "gap_pp": gap_pp,
    }


def render_crushing_cascade(
    position: str,
    fob_aceite: float,
    coef_aceite: float,
    fob_harina: float,
    coef_harina: float,
    ret_sub_pct: float,
    fobbing_sub: float,
    gto_ind: float,
    fas_obj: float,
) -> Dict[str, float]:
    aceite_bruto = fob_aceite * coef_aceite
    harina_bruto = fob_harina * coef_harina
    bruto_total = aceite_bruto + harina_bruto
    ret_sub_value = bruto_total * ret_sub_pct / 100
    fas_crushing = bruto_total - ret_sub_value - fobbing_sub - gto_ind
    margin = fas_crushing - fas_obj

    bars = ""
    bars += cascade_bar(
        f"Aceite ({fmt_num(fob_aceite, 1)} × {coef_aceite:.2f})",
        aceite_bruto,
        (aceite_bruto / bruto_total * 100) if bruto_total else 0,
        "var(--es-green-light)",
        "var(--es-green-dark)",
    )
    bars += cascade_bar(
        f"Harina ({fmt_num(fob_harina, 1)} × {coef_harina:.2f})",
        harina_bruto,
        (harina_bruto / bruto_total * 100) if bruto_total else 0,
        "var(--es-green-light)",
        "var(--es-green-dark)",
    )
    bars += cascade_bar(f"Ret subprod {ret_sub_pct:.1f}%", -ret_sub_value, ret_sub_pct, "#fde8e8", "var(--red)")
    bars += cascade_bar("Fobbing subprod", -fobbing_sub, (fobbing_sub / bruto_total * 100) if bruto_total else 0, "var(--bg-input)", "var(--text-3)")
    bars += cascade_bar("Gasto industrial", -gto_ind, (gto_ind / bruto_total * 100) if bruto_total else 0, "var(--bg-input)", "var(--text-3)")

    margin_color = "var(--green)" if margin >= 0 else "var(--red)"
    html = f"""
    <div class="cascade-panel">
      <div class="cascade-title" style="color:var(--es-gold);">Crushing subproductos {position}</div>
      {bars}
      <div class="result-row">
        <span class="result-lbl">FAS Crushing</span>
        <span class="result-val" style="color:var(--es-gold);">{fmt_num(fas_crushing, 2)}</span>
      </div>
      <div class="margin-row">
        <span>Margen crushing vs obj {fmt_num(fas_obj, 1)}</span>
        <strong style="color:{margin_color};">{'+' if margin >= 0 else ''}{fmt_num(margin, 2)}</strong>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    return {
        "aceite_bruto": aceite_bruto,
        "harina_bruto": harina_bruto,
        "bruto_total": bruto_total,
        "ret_sub_value": ret_sub_value,
        "fas_crushing": fas_crushing,
        "margin": margin,
    }


# =============================================================================
# Builder de estrategias
# =============================================================================

def new_leg(spot: float, option_type: str = "put") -> Dict[str, Any]:
    leg_id = st.session_state.next_leg_id
    st.session_state.next_leg_id += 1
    return {
        "id": leg_id,
        "direction": "buy",
        "type": option_type,
        "ratio": 1.0,
        "strike": round(spot),
        "prima": 0.0 if option_type == "futuro" else 5.0,
    }


def new_strategy(name: Optional[str], spot: float) -> Dict[str, Any]:
    sid = st.session_state.next_strategy_id
    st.session_state.next_strategy_id += 1
    color = COLORS[(sid - 1) % len(COLORS)]
    return {
        "id": sid,
        "name": name or f"Estrategia {sid}",
        "color": color,
        "legs": [new_leg(spot, "put")],
    }


def preset_legs(preset_name: str, spot: float) -> List[Dict[str, Any]]:
    def leg(direction: str, option_type: str, ratio: float, strike: float, prima: float) -> Dict[str, Any]:
        item = new_leg(spot, option_type)
        item.update(
            {
                "direction": direction,
                "type": option_type,
                "ratio": ratio,
                "strike": round(strike),
                "prima": prima,
            }
        )
        return item

    presets = {
        "Put Seco": [
            leg("buy", "put", 1, spot * 0.98, 6),
        ],
        "Put Spread": [
            leg("buy", "put", 1, spot * 0.98, 6),
            leg("sell", "put", 1, spot * 0.94, 2),
        ],
        "Collar": [
            leg("buy", "put", 1, spot * 0.97, 5),
            leg("sell", "call", 1, spot * 1.10, 5),
        ],
        "Gaviota": [
            leg("buy", "put", 1, spot * 0.98, 6),
            leg("sell", "put", 1, spot * 0.95, 2.5),
            leg("sell", "call", 1, spot * 1.12, 2),
        ],
        "Futuro + Call": [
            leg("sell", "futuro", 1, spot, 0),
            leg("buy", "call", 1, spot * 1.05, 4),
        ],
        "Ratio Put Spread 1x2": [
            leg("buy", "put", 1, spot * 0.98, 6),
            leg("sell", "put", 2, spot * 0.92, 3),
        ],
        "Gaviota Invertida": [
            leg("buy", "call", 1, spot * 1.03, 5),
            leg("sell", "call", 1, spot * 1.15, 2),
            leg("sell", "put", 1, spot * 0.92, 3),
        ],
        "Lanzamiento Cubierto": [
            leg("sell", "call", 1, spot * 1.08, 4),
        ],
    }
    return presets[preset_name]


def add_strategy_from_preset(preset_name: str, spot: float, crop: str, a3_pos: Optional[str]) -> None:
    strategy = new_strategy(preset_name, spot)
    strategy["legs"] = preset_legs(preset_name, spot)

    # Si A3 esta disponible, intentamos completar primas de la posición actual.
    if a3_pos:
        for leg in strategy["legs"]:
            premium = lookup_market_premium(crop, a3_pos, leg["type"], leg["strike"])
            if premium is not None:
                leg["prima"] = premium

    st.session_state.builder_strategies.append(strategy)
    add_audit(f"Builder: plantilla agregada '{preset_name}'.")


def option_intrinsic(leg: Dict[str, Any], terminal_price: float) -> float:
    ratio = float(leg.get("ratio", 1.0) or 1.0)
    strike = float(leg.get("strike", 0.0) or 0.0)
    option_type = leg.get("type", "put")
    direction = leg.get("direction", "buy")

    if option_type == "futuro":
        intrinsic = (terminal_price - strike) * ratio
        return intrinsic if direction == "buy" else -intrinsic

    if option_type == "call":
        intrinsic = max(terminal_price - strike, 0.0) * ratio
    elif option_type == "put":
        intrinsic = max(strike - terminal_price, 0.0) * ratio
    else:
        intrinsic = 0.0

    return intrinsic if direction == "buy" else -intrinsic


def net_premium_cost(strategy: Dict[str, Any]) -> float:
    """Costo de prima positivo = debito; negativo = credito."""
    total = 0.0
    for leg in strategy.get("legs", []):
        if leg.get("type") == "futuro":
            continue
        ratio = float(leg.get("ratio", 1.0) or 1.0)
        prima = float(leg.get("prima", 0.0) or 0.0)
        if leg.get("direction") == "buy":
            total += prima * ratio
        else:
            total -= prima * ratio
    return total


def calc_net_sale_price(strategy: Dict[str, Any], terminal_price: float) -> float:
    """Precio neto de venta = fisico + payoff opciones/futuros - costo neto de primas."""
    payoff = sum(option_intrinsic(leg, terminal_price) for leg in strategy.get("legs", []))
    return terminal_price + payoff - net_premium_cost(strategy)


def calc_diff_vs_unhedged(strategy: Dict[str, Any], terminal_price: float) -> float:
    return calc_net_sale_price(strategy, terminal_price) - terminal_price


def update_all_premiums_from_a3(crop: str, a3_position: Optional[str]) -> int:
    if not a3_position:
        return 0

    updated = 0
    for strategy in st.session_state.builder_strategies:
        for leg in strategy.get("legs", []):
            if leg.get("type") == "futuro":
                leg["prima"] = 0.0
                key = f"leg_{strategy['id']}_{leg['id']}_prima"
                st.session_state[key] = 0.0
                continue

            premium = lookup_market_premium(crop, a3_position, leg.get("type", "put"), leg.get("strike", 0.0))
            if premium is not None:
                leg["prima"] = premium
                key = f"leg_{strategy['id']}_{leg['id']}_prima"
                st.session_state[key] = premium
                updated += 1

    add_audit(f"Builder: {updated} primas actualizadas desde A3.")
    return updated


def strategy_kpis(strategy: Dict[str, Any], spot: float) -> Tuple[str, str, str]:
    prices = [spot * 0.5 + i * (spot * 1.0 / 160) for i in range(161)]
    values = [calc_net_sale_price(strategy, p) for p in prices]
    min_val = min(values) if values else 0
    max_val = max(values) if values else 0

    floor_txt = "Riesgo a la baja" if min_val < spot * 0.5 else fmt_money(min_val, 1)
    ceil_txt = "Ilimitado" if max_val > spot * 1.45 else fmt_money(max_val, 1)

    # Breakeven contra fisico sin cobertura.
    breakevens: List[float] = []
    prev_p = prices[0]
    prev_diff = calc_diff_vs_unhedged(strategy, prev_p)
    for p in prices[1:]:
        diff = calc_diff_vs_unhedged(strategy, p)
        if prev_diff == 0 or diff == 0 or (prev_diff < 0 < diff) or (prev_diff > 0 > diff):
            breakevens.append(p)
        prev_diff = diff
        prev_p = p

    if len(breakevens) == 0:
        be_txt = "0 costo" if abs(net_premium_cost(strategy)) < 0.01 else "-"
    elif len(breakevens) == 1:
        be_txt = fmt_money(breakevens[0], 1)
    else:
        be_txt = "Múltiples"

    return floor_txt, ceil_txt, be_txt


def render_strategy_editor(
    strategy: Dict[str, Any],
    spot: float,
    crop: str,
    a3_position: Optional[str],
) -> None:
    """Editor compacto de una estrategia.

    Importante: no usa HTML abierto alrededor de widgets de Streamlit. Cada
    estrategia vive en su propio st.container(border=True), evitando DOM roto y
    manteniendo layout horizontal estable.
    """
    sid = strategy["id"]
    color = strategy["color"]

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="border-left:4px solid {color};padding-left:10px;margin-bottom:8px;">
              <strong style="font-size:14px;color:{color};">Estrategia editable</strong>
              <span style="font-size:12px;color:var(--text-3);margin-left:8px;">ID {sid}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        header_cols = st.columns([3.0, 1.2, 1.0, 0.7])
        with header_cols[0]:
            strategy["name"] = st.text_input(
                "Nombre de estrategia",
                value=strategy.get("name", f"Estrategia {sid}"),
                key=f"strategy_{sid}_name",
                label_visibility="collapsed",
            )
        with header_cols[1]:
            cost = net_premium_cost(strategy)
            cost_label = "Débito" if cost > 0 else "Crédito" if cost < 0 else "Costo"
            st.metric(cost_label, fmt_money(abs(cost), 2))
        with header_cols[2]:
            if st.button("+ Pata", key=f"strategy_{sid}_add_leg", use_container_width=True):
                strategy["legs"].append(new_leg(spot, "put"))
                st.rerun()
        with header_cols[3]:
            if st.button("Borrar", key=f"strategy_{sid}_delete", use_container_width=True):
                st.session_state.builder_strategies = [s for s in st.session_state.builder_strategies if s["id"] != sid]
                st.rerun()

        st.markdown(
            """
            <div class="leg-label-row">
              <span>Operación</span><span>Instrumento</span><span>Cant.</span>
              <span>Strike</span><span>Prima</span><span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for idx, leg in enumerate(list(strategy.get("legs", []))):
            lid = leg["id"]

            # Separador sutil de filas: horizontal, sin cards verticales largas.
            st.markdown(
                '<div style="height:1px;background:#dde0d5;margin:4px 0 6px;"></div>',
                unsafe_allow_html=True,
            )
            cols = st.columns([1.35, 1.15, 0.75, 1.35, 1.0, 0.35])

            with cols[0]:
                direction = st.selectbox(
                    "Operación",
                    ["buy", "sell"],
                    format_func=lambda x: "Compra" if x == "buy" else "Venta",
                    index=0 if leg.get("direction") == "buy" else 1,
                    key=f"leg_{sid}_{lid}_direction",
                    label_visibility="collapsed",
                )
                leg["direction"] = direction

            with cols[1]:
                previous_type = leg.get("type", "put")
                option_type = st.selectbox(
                    "Instrumento",
                    ["put", "call", "futuro"],
                    format_func=lambda x: {"put": "Put", "call": "Call", "futuro": "Futuro"}[x],
                    index=["put", "call", "futuro"].index(previous_type) if previous_type in ["put", "call", "futuro"] else 0,
                    key=f"leg_{sid}_{lid}_type",
                    label_visibility="collapsed",
                )
                if option_type != previous_type:
                    leg["type"] = option_type
                    if option_type == "futuro":
                        leg["prima"] = 0.0
                        st.session_state[f"leg_{sid}_{lid}_prima"] = 0.0
                else:
                    leg["type"] = option_type

            with cols[2]:
                leg["ratio"] = st.number_input(
                    "Ratio",
                    min_value=0.0,
                    value=float(leg.get("ratio", 1.0)),
                    step=0.5,
                    key=f"leg_{sid}_{lid}_ratio",
                    label_visibility="collapsed",
                )

            with cols[3]:
                strike_key = f"leg_{sid}_{lid}_strike_{leg['type']}"
                if leg["type"] == "futuro":
                    leg["strike"] = st.number_input(
                        "Strike",
                        min_value=0.0,
                        value=float(leg.get("strike", round(spot))),
                        step=1.0,
                        key=strike_key,
                        label_visibility="collapsed",
                    )
                else:
                    strikes = get_available_strikes(crop, a3_position or "", leg["type"])
                    current_strike = float(leg.get("strike", round(spot)))

                    if strikes:
                        options = sorted(set([current_strike] + [float(s) for s in strikes]))
                        selected_strike = st.selectbox(
                            "Strike",
                            options,
                            index=options.index(current_strike) if current_strike in options else 0,
                            format_func=lambda x: fmt_num(float(x), 1),
                            key=strike_key,
                            label_visibility="collapsed",
                        )
                        if float(selected_strike) != current_strike:
                            leg["strike"] = float(selected_strike)
                            premium = lookup_market_premium(crop, a3_position or "", leg["type"], leg["strike"])
                            if premium is not None:
                                leg["prima"] = premium
                                st.session_state[f"leg_{sid}_{lid}_prima"] = premium
                        else:
                            leg["strike"] = float(selected_strike)
                    else:
                        leg["strike"] = st.number_input(
                            "Strike",
                            min_value=0.0,
                            value=current_strike,
                            step=1.0,
                            key=strike_key,
                            label_visibility="collapsed",
                        )

            with cols[4]:
                leg["prima"] = st.number_input(
                    "Prima",
                    min_value=0.0,
                    value=float(leg.get("prima", 0.0)),
                    step=0.5,
                    key=f"leg_{sid}_{lid}_prima",
                    disabled=leg["type"] == "futuro",
                    label_visibility="collapsed",
                )

            with cols[5]:
                if st.button("×", key=f"leg_{sid}_{lid}_delete", use_container_width=True):
                    strategy["legs"] = [l for l in strategy["legs"] if l["id"] != lid]
                    st.rerun()

        floor_txt, ceil_txt, be_txt = strategy_kpis(strategy, spot)
        st.markdown(
            f"""
            <div class="kpi-grid">
              <div class="kpi-card"><div class="k-lbl">Piso Asegurado</div><div class="k-val">{floor_txt}</div></div>
              <div class="kpi-card"><div class="k-lbl">Techo Máximo</div><div class="k-val">{ceil_txt}</div></div>
              <div class="kpi-card"><div class="k-lbl">Empate B.E.</div><div class="k-val">{be_txt}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

def build_scenario_prices(spot: float, strategies: List[Dict[str, Any]]) -> List[Tuple[str, float]]:
    scenarios = [
        ("Derrumbe (-30%)", spot * 0.70),
        ("Baja fuerte (-15%)", spot * 0.85),
        ("Spot / actual", spot),
        ("Suba moderada (+15%)", spot * 1.15),
        ("Rally (+30%)", spot * 1.30),
    ]

    seen = {round(v, 4) for _, v in scenarios}
    for strategy in strategies:
        for leg in strategy.get("legs", []):
            if leg.get("type") != "futuro":
                strike = float(leg.get("strike", 0.0) or 0.0)
                if strike > 0 and round(strike, 4) not in seen:
                    scenarios.append((f"Strike {leg['type'].upper()} {fmt_num(strike, 1)}", strike))
                    seen.add(round(strike, 4))

    return sorted(scenarios, key=lambda x: x[1])


def render_strategy_chart(spot: float, strategies: List[Dict[str, Any]]) -> None:
    min_price = max(1.0, spot * 0.70)
    max_price = spot * 1.30
    step = (max_price - min_price) / 160
    prices = [min_price + i * step for i in range(161)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=prices,
            y=prices,
            mode="lines",
            name="Físico sin cobertura",
            line=dict(color="#b0afa8", width=2, dash="dash"),
            hovertemplate="Mercado: $%{x:.1f}<br>Neto: $%{y:.1f}<extra></extra>",
        )
    )

    for strategy in strategies:
        fig.add_trace(
            go.Scatter(
                x=prices,
                y=[calc_net_sale_price(strategy, p) for p in prices],
                mode="lines",
                name=strategy["name"],
                line=dict(color=strategy["color"], width=3),
                hovertemplate="Mercado: $%{x:.1f}<br>Neto: $%{y:.1f}<extra></extra>",
            )
        )

    fig.add_vline(
        x=spot,
        line_dash="dot",
        line_color="#1A6B3C",
        line_width=1,
        annotation_text=f"FOB: {spot:.0f}",
    )

    fig.update_layout(
        height=470,
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1c2118", family="DM Sans"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis_title="Precio a vencimiento (u$s/tn)",
        yaxis_title="Precio neto de venta (u$s/tn)",
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="rgba(0,0,0,.06)")
    fig.update_yaxes(gridcolor="rgba(0,0,0,.06)")
    st.plotly_chart(fig, use_container_width=True)


def render_scenario_table(spot: float, strategies: List[Dict[str, Any]]) -> None:
    rows = []
    for name, price in build_scenario_prices(spot, strategies):
        row: Dict[str, Any] = {
            "Escenario": name,
            "Mercado": price,
            "Sin cobertura": price,
        }
        for strategy in strategies:
            net_price = calc_net_sale_price(strategy, price)
            row[strategy["name"]] = net_price
            row[f"{strategy['name']} Δ"] = net_price - price
        rows.append(row)

    df = pd.DataFrame(rows)
    money_cols = [c for c in df.columns if c not in ["Escenario"]]

    styler = df.style.format({col: "${:.2f}" for col in money_cols})
    delta_cols = [c for c in df.columns if c.endswith(" Δ")]
    if delta_cols:
        styler = safe_styler_map(styler, color_delta, delta_cols)

    st.dataframe(styler, use_container_width=True, hide_index=True)


def render_dominance_ranges(spot: float, strategies: List[Dict[str, Any]]) -> None:
    if not strategies:
        st.info("Agregá estrategias para calcular dominancia.")
        return

    min_price = round(spot * 0.70)
    max_price = round(spot * 1.30)
    ranges = []
    current_name = None
    current_color = "#b0afa8"
    start = min_price

    for price in range(min_price, max_price + 1):
        best_name = "Sin cobertura"
        best_value = float(price)
        best_color = "#b0afa8"

        for strategy in strategies:
            value = calc_net_sale_price(strategy, price)
            if value > best_value + 0.05:
                best_value = value
                best_name = strategy["name"]
                best_color = strategy["color"]

        if best_name != current_name:
            if current_name is not None:
                ranges.append((start, price - 1, current_name, current_color))
            start = price
            current_name = best_name
            current_color = best_color

    if current_name is not None:
        ranges.append((start, max_price, current_name, current_color))

    for start, end, winner, color in ranges:
        st.markdown(
            f"""
            <div class="winner-box" style="border-left-color:{color};">
              <div class="winner-range">Si el mercado cierra entre u$s {start:.1f} y u$s {end:.1f}</div>
              <div class="winner-name" style="color:{color};">Conviene: {winner}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def export_builder_report_html(context: Dict[str, Any], strategies: List[Dict[str, Any]]) -> bytes:
    rows = []
    for strategy in strategies:
        legs = "".join(
            f"<li>{leg['direction']} {leg['type']} x{leg['ratio']} strike {leg['strike']} prima {leg['prima']}</li>"
            for leg in strategy.get("legs", [])
        )
        rows.append(f"<h3>{strategy['name']}</h3><ul>{legs}</ul>")

    html_doc = f"""
    <html><head><meta charset="utf-8"><title>Reporte Coberturas</title></head>
    <body style="font-family:Arial,sans-serif;">
      <h1>Reporte de Coberturas - Espartina S.A.</h1>
      <h2>Contexto FAS</h2>
      <p>Cultivo: {CROP_LABELS.get(context.get('crop', ''), '')}</p>
      <p>Posición: {context.get('position', '')}</p>
      <p>FOB fuente: {fmt_money(context.get('fob_source', 0), 2)}</p>
      <p>FAS CTP: {fmt_money(context.get('fas_ctp', 0), 2)}</p>
      <h2>Estrategias</h2>
      {''.join(rows) if rows else '<p>Sin estrategias cargadas.</p>'}
    </body></html>
    """
    return html_doc.encode("utf-8")


# =============================================================================
# Panel A: Mercado & FAS Teorico
# =============================================================================

def render_panel_a_mercado_fas() -> Optional[Dict[str, Any]]:
    with st.container(border=True):
        st.markdown(
            """
            <div class="panel-heading">
              <span style="font-size:28px;">🧮</span>
              <h2>Panel A — Mercado & FAS Teórico</h2>
            </div>
            <div class="panel-subtitle">
              Fuente: Bolsa de Cereales. El FOB y subproductos se tratan como datos crudos inmutables.
            </div>
            """,
            unsafe_allow_html=True,
        )

        quotes = get_quotes()
        if not quotes:
            st.warning("Primero cargá los datos de Bolsa con el botón 'Actualizar FOB'.")
            return None

        positions = get_positions()
        if "fas_crop" not in st.session_state:
            st.session_state.fas_crop = "soja"
        if "fas_position" not in st.session_state or st.session_state.fas_position not in positions:
            st.session_state.fas_position = positions[0]

        control_cols = st.columns([1.15, 1.15, 0.8, 0.8, 0.9, 1.0])
        with control_cols[0]:
            crop = st.selectbox(
                "Cultivo",
                list(CROP_LABELS.keys()),
                format_func=lambda x: CROP_LABELS[x],
                key="fas_crop",
            )
        with control_cols[1]:
            position = st.selectbox(
                "Mes / Posición FOB",
                positions,
                key="fas_position",
            )

        defaults = RET_DEFAULTS[crop]
        with control_cols[2]:
            ret_pct = st.number_input(
                "Ret %",
                min_value=0.0,
                max_value=100.0,
                value=float(defaults["ret_pct"]),
                step=0.1,
                key=f"fas_ret_pct_{crop}",
            )
        with control_cols[3]:
            fobbing = st.number_input(
                "Fobbing",
                min_value=0.0,
                value=float(defaults["fobbing"]),
                step=0.1,
                key=f"fas_fobbing_{crop}",
            )
        with control_cols[4]:
            fas_obj = st.number_input(
                "FAS Obj",
                min_value=0.0,
                value=float(defaults["fas_obj"]),
                step=0.1,
                key=f"fas_obj_{crop}",
            )
        with control_cols[5]:
            st.write("")
            if st.button("Actualizar precios Bolsa", use_container_width=True):
                update_bolsa_data()
                st.rerun()

        fob_source = get_market_fob(crop, position)
        aceite_source = get_market_byproduct(position, "aceite")
        harina_source = get_market_byproduct(position, "harina")
        girasol_oil_source = get_market_byproduct(position, "aceiteGirasol")

        # Diagnostico visible: confirma que el FOB fuente no fue descontado.
        abr_key = next((p for p in positions if normalize_position_code(p).startswith("ABR")), None)
        abr_soja = get_market_fob("soja", abr_key) if abr_key else None
        abr_aceite = get_market_byproduct(abr_key, "aceite") if abr_key else None

        status = "OK" if fob_source > 0 else "REVISAR"
        st.info(
            f"Diagnóstico FOB [{status}]: fuente Bolsa para {CROP_LABELS[crop]} / {position} = "
            f"{fob_source:.2f}. Valor usado en cascada = {fob_source:.2f}. Diferencia = +0.00. "
            f"Control ABR 2026: Soja={abr_soja if abr_soja is not None else 's/d'}, "
            f"Aceite={abr_aceite if abr_aceite is not None else 's/d'}."
        )

        st.markdown(
            f"""
            <div class="source-chip-row">
              <div class="source-chip"><span class="lbl">FOB fuente {CROP_LABELS[crop]}</span><span class="val">{fmt_num(fob_source, 2)}</span></div>
              <div class="source-chip"><span class="lbl">FOB Aceite crudo</span><span class="val">{fmt_num(aceite_source, 2)}</span></div>
              <div class="source-chip"><span class="lbl">FOB Harina crudo</span><span class="val">{fmt_num(harina_source, 2)}</span></div>
              <div class="source-chip"><span class="lbl">Aceite Girasol crudo</span><span class="val">{fmt_num(girasol_oil_source, 2)}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        left, right = st.columns([1, 1], gap="large")
        with left:
            grain = render_grain_cascade(crop, position, fob_source, ret_pct, fobbing, fas_obj)

        crush = None
        with right:
            if crop == "soja":
                input_cols = st.columns(4)
                with input_cols[0]:
                    coef_aceite = st.number_input("Coef. Aceite", 0.0, 1.0, 0.19, 0.01, key="coef_aceite")
                with input_cols[1]:
                    coef_harina = st.number_input("Coef. Harina", 0.0, 1.0, 0.78, 0.01, key="coef_harina")
                with input_cols[2]:
                    ret_sub_pct = st.number_input("Ret Sub %", 0.0, 100.0, 22.5, 0.1, key="ret_sub_pct")
                with input_cols[3]:
                    gto_ind = st.number_input("Gto Ind.", 0.0, 200.0, 29.0, 1.0, key="gto_ind")

                fobbing_sub = st.number_input("Fobbing subprod", 0.0, 200.0, 19.0, 0.1, key="fobbing_sub")

                crush = render_crushing_cascade(
                    position,
                    aceite_source,
                    coef_aceite,
                    harina_source,
                    coef_harina,
                    ret_sub_pct,
                    fobbing_sub,
                    gto_ind,
                    fas_obj,
                )
            else:
                st.info("El panel de crushing aplica únicamente para soja.")

        context = {
            "crop": crop,
            "position": position,
            "position_code": normalize_position_code(position),
            "raw_quote": raw_quote(position),
            "fob_source": fob_source,
            "ret_pct": ret_pct,
            "fobbing": fobbing,
            "fas_obj": fas_obj,
            "fas_ctp": grain["fas_ctp"],
            "grain": grain,
            "crush": crush,
            "aceite_source": aceite_source,
            "harina_source": harina_source,
            "girasol_oil_source": girasol_oil_source,
        }

        st.session_state.fas_context = context
        return context


# =============================================================================
# Panel B: Builder de Coberturas
# =============================================================================

def render_panel_b_builder(context: Optional[Dict[str, Any]]) -> None:
    with st.container(border=True):
        st.markdown(
            """
            <div class="panel-heading">
              <span style="font-size:28px;">📈</span>
              <h2>Panel B — Builder de Coberturas</h2>
            </div>
            <div class="panel-subtitle">
              Fuente: A3 para futuros/opciones. El Panel B consume la línea base del Panel A, pero no modifica el FOB/FAS.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not context:
            st.warning("Cargá y validá primero el Panel A para activar el builder.")
            return

        crop = context["crop"]
        spot = float(context["fob_source"])
        position_code_a = context["position_code"]

        a3_positions = get_a3_positions(crop)
        if a3_positions:
            default_idx = a3_positions.index(position_code_a) if position_code_a in a3_positions else 0
        else:
            default_idx = 0

        top_cols = st.columns([1.2, 1.1, 1.2, 1.2, 1.0])
        with top_cols[0]:
            st.metric("Base Panel A", f"{CROP_LABELS[crop]} {context['position']}")
        with top_cols[1]:
            st.metric("FOB base", fmt_money(spot, 2))
        with top_cols[2]:
            if a3_positions:
                a3_position = st.selectbox(
                    "Posición A3",
                    a3_positions,
                    index=default_idx,
                    format_func=position_label_from_code,
                    key="builder_a3_position",
                )
            else:
                a3_position = None
                st.text_input("Posición A3", value="Sin datos A3", disabled=True)
        with top_cols[3]:
            preset_name = st.selectbox(
                "Cargar plantilla",
                [
                    "Put Seco",
                    "Put Spread",
                    "Collar",
                    "Gaviota",
                    "Futuro + Call",
                    "Ratio Put Spread 1x2",
                    "Gaviota Invertida",
                    "Lanzamiento Cubierto",
                ],
                key="builder_preset_name",
            )
        with top_cols[4]:
            st.write("")
            if st.button("Agregar plantilla", use_container_width=True):
                add_strategy_from_preset(preset_name, spot, crop, a3_position)
                st.rerun()

        action_cols = st.columns([1, 1, 1, 3])
        with action_cols[0]:
            if st.button("+ Estrategia nueva", use_container_width=True):
                st.session_state.builder_strategies.append(new_strategy(None, spot))
                add_audit("Builder: estrategia nueva creada.")
                st.rerun()
        with action_cols[1]:
            if st.button("Actualizar primas A3", use_container_width=True):
                updated = update_all_premiums_from_a3(crop, a3_position)
                st.success(f"{updated} primas actualizadas desde A3.")
        with action_cols[2]:
            report = export_builder_report_html(context, st.session_state.builder_strategies)
            st.download_button(
                "Exportar reporte",
                data=report,
                file_name="reporte_coberturas.html",
                mime="text/html",
                use_container_width=True,
            )
        with action_cols[3]:
            if get_a3_market():
                market = get_a3_market()
                st.caption(
                    f"A3 activo: {market['stats']['futuros']} futuros, "
                    f"{market['stats']['opciones']} opciones."
                )
            else:
                st.caption("A3 sin datos: los strikes quedan como inputs manuales.")

        st.divider()

        if not st.session_state.builder_strategies:
            st.info("Agregá una estrategia nueva o cargá una plantilla para comenzar.")
            return

        editor_col, chart_col = st.columns([1.05, 1.25], gap="large")
        with editor_col:
            for strategy in st.session_state.builder_strategies:
                render_strategy_editor(strategy, spot, crop, a3_position)

        with chart_col:
            render_strategy_chart(spot, st.session_state.builder_strategies)

        st.subheader("Análisis de escenarios")
        render_scenario_table(spot, st.session_state.builder_strategies)

        st.subheader("Rango de dominancia")
        render_dominance_ranges(spot, st.session_state.builder_strategies)


# =============================================================================
# Auditoria
# =============================================================================

def render_audit_log() -> None:
    with st.expander("Log de Auditoría — Datos crudos y validaciones", expanded=False):
        quotes = get_quotes()
        if quotes:
            rows = []
            for pos, values in quotes.items():
                rows.append(
                    {
                        "Posición": pos,
                        "Soja crudo": values.get("soja"),
                        "Maíz crudo": values.get("maiz"),
                        "Trigo crudo": values.get("trigo"),
                        "Harina soja crudo": values.get("harina"),
                        "Aceite soja crudo": values.get("aceite"),
                        "Aceite girasol crudo": values.get("aceiteGirasol"),
                    }
                )
            audit_df = pd.DataFrame(rows)
            st.dataframe(audit_df, use_container_width=True, hide_index=True)

            abr_key = next((p for p in quotes if normalize_position_code(p).startswith("ABR")), None)
            if abr_key:
                soja_abr = quotes[abr_key].get("soja")
                aceite_abr = quotes[abr_key].get("aceite")
                aceite_ok = "OK" if float(aceite_abr or 0) == 1191.0 else "REVISAR"
                soja_ok = "OK" if float(soja_abr or 0) == 427.0 else "REVISAR"
                st.info(
                    f"Control crítico ABR 2026: Soja crudo={soja_abr} [{soja_ok}], "
                    f"Aceite soja crudo={aceite_abr} [{aceite_ok}]. "
                    "Estos valores vienen directo del parser y no tienen fobbing ni gastos aplicados."
                )
        else:
            st.warning("No hay datos crudos de Bolsa cargados.")

        market = get_a3_market()
        if market:
            st.write("Resumen A3 parseado")
            st.json(
                {
                    "fecha_datos": market.get("fecha_datos"),
                    "stats": market.get("stats"),
                    "cultivos_futuros": list(market.get("futuros", {}).keys()),
                    "cultivos_opciones": list(market.get("opciones", {}).keys()),
                }
            )
        else:
            st.caption("A3 no sincronizado.")

        if st.session_state.audit_events:
            st.write("Eventos")
            for event in reversed(st.session_state.audit_events):
                st.caption(event)


# =============================================================================
# Sidebar
# =============================================================================

def render_sidebar() -> None:
    with st.sidebar:
        st.header("Configuración")

        if st.button("Actualizar FOB", use_container_width=True):
            update_bolsa_data()
            st.rerun()

        if st.session_state.data_bolsa.get("last_update"):
            st.caption(f"Bolsa: {st.session_state.data_bolsa['last_update'].strftime('%H:%M')}")
        else:
            st.caption("Bolsa: sin cargar")

        st.divider()

        if st.button("Sincronizar A3", use_container_width=True):
            update_a3_data()
            st.rerun()

        if st.session_state.data_a3.get("last_update"):
            market = get_a3_market()
            if market:
                st.success(
                    f"A3 sincronizado: {market['stats']['futuros']} futuros, "
                    f"{market['stats']['opciones']} opciones"
                )
        else:
            st.caption("A3: sin datos")

        st.divider()

        st.subheader("Estado de fuentes")
        quotes = get_quotes()
        st.caption(f"Bolsa: {len(quotes)} posiciones" if quotes else "Bolsa: sin datos")
        market = get_a3_market()
        if market:
            st.caption(
                f"A3: {market['stats']['futuros']} futuros / "
                f"{market['stats']['opciones']} opciones"
            )
        else:
            st.caption("A3: sin datos")

        st.divider()

        if st.button("Limpiar builder", use_container_width=True):
            st.session_state.builder_strategies = []
            add_audit("Builder limpiado por usuario.")
            st.rerun()


# =============================================================================
# Main
# =============================================================================

render_sidebar()

st.markdown(
    """
    <div class="main-header">
      <div class="logo">🌾</div>
      <div>
        <h1>Estrategias de Cobertura</h1>
        <p>Espartina S.A. — Simulador de Coberturas & FAS</p>
      </div>
      <div class="header-badge">Separación de fuentes</div>
    </div>
    """,
    unsafe_allow_html=True,
)

context = render_panel_a_mercado_fas()
st.write("")
render_panel_b_builder(context)
render_audit_log()

st.markdown(
    """
    <div style="text-align:center;padding:2rem;color:#7e8574;font-size:.85rem;margin-top:2rem;border-top:1px solid #dde0d5;">
      🌾 <strong>Espartina S.A.</strong> — Dashboard de Estrategias de Cobertura
    </div>
    """,
    unsafe_allow_html=True,
)
