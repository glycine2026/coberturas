"""
Modulo de datos FOB - Bolsa de Cereales.

ARQUITECTURA:
  1. CSV oficial  — el usuario sube el archivo descargado desde
                    preciosfob.bolsadecereales.com ("Descargar Cotización del Día").
                    Es la fuente más precisa y siempre actualizada.
  2. Mock interno — snapshot de respaldo usado solo si no hay CSV cargado.
                    Debe actualizarse manualmente cuando los precios cambien.

NOTA: preciosfob.bolsadecereales.com bloquea todas las peticiones HTTP
provenientes de servidores externos (Cloudflare allowlist). El scraping
automático via Selenium o requests no funciona en Streamlit Cloud ni en
ningún servidor de terceros; por eso se eliminó esa dependencia.

Regla de datos: los FOB y subproductos se devuelven CRUDOS — sin retenciones,
sin fobbing y sin ningún descuento aplicado. La cascada FAS aplica esos costos
en app.py, nunca aquí.
"""

from __future__ import annotations

import io
import re
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_precio(texto: str) -> float:
    """Parsea un valor de precio sin aplicar transformaciones financieras."""
    s = str(texto or "").strip()
    if not s or s.upper() in {"S/C", "SC", "N/A", "-", "--"}:
        return 0.0
    s = re.sub(r"[^0-9,.\-]", "", s)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalizar_mes(mes: str) -> str:
    """Normaliza etiqueta de mes: 'ABR2026', 'abr-26', etc. → 'ABR 2026'."""
    raw = str(mes or "").strip().upper()
    m = re.match(r"([A-Z]{3})[\s\-]*(20)?(\d{2})", raw)
    if m:
        year = int(m.group(3))
        full_year = 2000 + year if year < 100 else year
        return f"{m.group(1)} {full_year}"
    return " ".join(raw.split())


# Aliases de columnas esperadas en el CSV de la Bolsa
_COL_ALIASES = {
    "soja":          ["soja"],
    "maiz":          ["maiz", "maíz"],
    "trigo":         ["trigo"],
    "harina":        ["harina de soja", "harina soja", "harina"],
    "aceite":        ["aceite de soja", "aceite soja", "aceite"],
    "aceiteGirasol": ["aceite de girasol", "aceite girasol"],
}


def _find_col(columns: List[str], aliases: List[str]) -> Optional[str]:
    for col in columns:
        low = col.lower()
        for alias in aliases:
            if alias in low:
                return col
    return None


def _parse_csv(file_bytes: bytes) -> Dict[str, Dict[str, float]]:
    """
    Parsea el CSV oficial de la Bolsa de Cereales.
    Estructura esperada:
        ,SOJA (USD/TON),MAIZ (USD/TON),TRIGO 11.5% (USD/TON),...
        ABR 2026,432,217,222,...
    """
    for sep in [",", ";"]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, header=0)
            if len(df.columns) >= 4:
                break
        except Exception:
            continue

    mes_col = df.columns[0]
    cols = list(df.columns)

    mapping = {}
    for key, aliases in _COL_ALIASES.items():
        col = _find_col(cols, aliases)
        if col:
            mapping[key] = col

    datos: Dict[str, Dict[str, float]] = {}
    for _, row in df.iterrows():
        mes = _normalizar_mes(str(row[mes_col]))
        if not mes or len(mes) < 7:
            continue
        entry: Dict[str, float] = {}
        for key, col in mapping.items():
            entry[key] = _parse_precio(str(row.get(col, 0)))
        if any(v > 0 for v in entry.values()):
            datos[mes] = entry

    return datos


# ---------------------------------------------------------------------------
# Widget de carga CSV — se llama desde app.py en la sección "Carga de Datos"
# ---------------------------------------------------------------------------

def render_csv_uploader() -> Optional[Dict[str, Dict[str, float]]]:
    """
    Muestra el widget de carga del CSV de la Bolsa y retorna los datos
    parseados si se sube un archivo válido. Retorna None si no hay archivo.

    Uso en app.py (dentro de render_load_page):
        from scraper import render_csv_uploader
        datos_csv = render_csv_uploader()
        if datos_csv:
            normalized = normalize_bolsa_data(datos_csv)
            st.session_state.data_bolsa = normalized
            st.session_state.bolsa_loaded_at = datetime.now()
            st.session_state.data_loaded = True
    """
    st.markdown(
        """
        <div style="background:#f0f7f4;border:1px solid #b2d8c8;border-radius:12px;
                    padding:16px 20px;margin-bottom:16px;">
            <div style="font-weight:800;color:#145430;font-size:15px;margin-bottom:8px;">
                📥 Actualizar precios FOB desde la Bolsa de Cereales
            </div>
            <div style="color:#3d5a47;font-size:13px;line-height:1.8;">
                1. Ingresá a
                <a href="https://preciosfob.bolsadecereales.com" target="_blank"
                   style="color:#1a6b3c;font-weight:700;">preciosfob.bolsadecereales.com</a><br>
                2. Hacé clic en <strong>"Descargar Cotización del Día"</strong><br>
                3. Subí el archivo CSV aquí abajo — los precios se actualizan al instante
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "CSV de cotizaciones FOB (Bolsa de Cereales)",
        type=["csv"],
        key="bolsa_csv_upload",
        help="Archivo CSV descargado desde preciosfob.bolsadecereales.com",
    )

    if uploaded is not None:
        try:
            datos = _parse_csv(uploaded.read())
            if datos:
                n = len(datos)
                primera = next(iter(datos))
                muestra = datos[primera]
                st.success(
                    f"✅ CSV cargado correctamente: **{n} posiciones** detectadas. "
                    f"Primera posición: **{primera}** — "
                    f"Soja: **{muestra.get('soja', 0):.0f}**, "
                    f"Aceite: **{muestra.get('aceite', 0):.0f}**"
                )
                return datos
            else:
                st.error(
                    "No se pudieron leer posiciones del CSV. "
                    "Verificá que sea el archivo descargado desde la Bolsa."
                )
        except Exception as exc:
            st.error(f"Error al leer el CSV: {exc}")

    return None


# ---------------------------------------------------------------------------
# Función principal — compatibilidad con app.py
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1800)
def obtener_datos_bolsa() -> Dict[str, Dict[str, float]]:
    """
    Fuente primaria: pestaña FOB_Bolsa del Google Sheet (actualizada desde PC local).
    Fallback: snapshot hardcodeado si el Sheet no tiene datos.
    """
    try:
        from google_sheets import obtener_datos_fob_bolsa
        datos = obtener_datos_fob_bolsa()
        if datos:
            return datos
        print("⚠️  Sheet FOB vacío, usando mock interno.")
    except Exception as e:
        print(f"⚠️  No se pudo leer FOB desde Sheets: {e}")
    return obtener_datos_bolsa_mock()


def obtener_datos_bolsa_mock() -> Dict[str, Dict[str, float]]:
    """
    Snapshot de respaldo — FOB Bolsa de Cereales al 28/04/2026.
    Se usa SOLO cuando no hay CSV cargado por el usuario.
    Actualizar manualmente al comienzo de cada semana operativa.
    """
    return {
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
