"""
Módulo de integración con Google Sheets.
Lee datos de A3 (opciones/futuros) y FOB_Bolsa (precios FOB diarios).

La pestaña FOB_Bolsa es actualizada desde la PC local con actualizar_fob.py.
La app lee esa pestaña automáticamente — sin scraping desde el servidor.
"""

import re
from datetime import datetime
from typing import Dict, Optional

import pandas as pd
import streamlit as st

# Sheet de A3 (no se toca)
SHEET_ID = "2PACX-1vTYR1G5tN0wEOnBhbHOEElP5gF0UWctmCSOSLmjb8_Zw38dLkGMfTTOW51iCQqwROmkUOLsMShcLwnn"

# Sheet separado para FOB Bolsa (actualizado por actualizar_fob.py desde la PC)
FOB_SHEET_ID = "1Fmvsn0o2OpTD8BXnqw8sDTG_4Kr9zu_tWvcy7R7Zjjo"


# ── A3 ────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def obtener_datos_a3() -> pd.DataFrame:
    """Obtiene datos de A3 desde Google Sheets (pestaña principal)."""
    try:
        url = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?output=csv"
        print(f"📡 Conectando a Google Sheets A3: {SHEET_ID}")
        df = pd.read_csv(url)
        print(f"✓ A3: {len(df)} filas")
        return df
    except Exception as e:
        print(f"✗ Error A3: {e}")
        return obtener_datos_a3_mock()


def obtener_datos_a3_mock() -> pd.DataFrame:
    return pd.DataFrame({
        "Producto": ["Soja", "Maíz", "Trigo"],
        "Precio":   [323, 180, 225],
        "Volumen":  [1000, 500, 300],
    })


# ── FOB Bolsa ─────────────────────────────────────────────────────────────────

def _normalizar_mes(mes: str) -> str:
    raw = str(mes or "").strip().upper()
    m = re.match(r"([A-Z]{3})[\s\-]*(20)?(\d{2})", raw)
    if m:
        full_year = 2000 + int(m.group(3))
        return f"{m.group(1)} {full_year}"
    return " ".join(raw.split())


def _parse_num(valor) -> float:
    s = str(valor or "").strip()
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


@st.cache_data(ttl=1800)
def obtener_datos_fob_bolsa() -> Dict[str, Dict[str, float]]:
    """
    Lee la pestaña FOB_Bolsa del Google Sheet (subida por actualizar_fob.py)
    y devuelve el mismo formato que usaba el scraper:
        { "ABR 2026": { "soja": 432, "maiz": 217, ... }, ... }

    Si la pestaña no existe o falla, devuelve un dict vacío para que
    normalize_bolsa_data() use el fallback interno de app.py.
    """
    try:
        # Leer el Sheet FOB directamente como CSV exportado
        url = f"https://docs.google.com/spreadsheets/d/{FOB_SHEET_ID}/export?format=csv&gid=0"
        print("📡 Leyendo FOB_Bolsa desde Google Sheets...")
        df = pd.read_csv(url)

        if df.empty or "Posicion" not in df.columns:
            print("⚠️  Pestaña FOB_Bolsa vacía o sin columna 'Posicion'")
            return {}

        datos: Dict[str, Dict[str, float]] = {}
        for _, row in df.iterrows():
            mes = _normalizar_mes(str(row.get("Posicion", "")))
            if not mes or len(mes) < 7:
                continue
            datos[mes] = {
                "soja":          _parse_num(row.get("Soja", 0)),
                "maiz":          _parse_num(row.get("Maiz", 0)),
                "trigo":         _parse_num(row.get("Trigo", 0)),
                "harina":        _parse_num(row.get("Harina", 0)),
                "aceite":        _parse_num(row.get("Aceite", 0)),
                "aceiteGirasol": _parse_num(row.get("AceiteGirasol", 0)),
            }

        if datos:
            primera = next(iter(datos))
            print(f"✅ FOB Bolsa: {len(datos)} posiciones. "
                  f"Primera: {primera} — Soja: {datos[primera]['soja']:.0f}")

            # Guardar timestamp de última actualización si está en el CSV
            try:
                ts = str(df.iloc[0].get("Actualizado", ""))
                if ts:
                    st.session_state["fob_sheet_actualizado"] = ts
            except Exception:
                pass

        return datos

    except Exception as e:
        print(f"✗ Error leyendo FOB_Bolsa: {e}")
        return {}


def fob_sheet_timestamp() -> Optional[str]:
    """Retorna el timestamp de la última actualización del sheet FOB."""
    return st.session_state.get("fob_sheet_actualizado")


# ── Helpers legacy (compatibilidad con el resto de la app) ────────────────────

def obtener_datos_mercado_opciones() -> dict:
    try:
        obtener_datos_a3()
        return obtener_datos_mercado_mock()
    except Exception:
        return obtener_datos_mercado_mock()


def obtener_datos_mercado_mock() -> dict:
    return {
        "posicion": "MAY 2026",
        "calls": [
            {"strike": 440, "prima": 8.5},
            {"strike": 450, "prima": 6.2},
            {"strike": 460, "prima": 4.8},
            {"strike": 470, "prima": 3.5},
            {"strike": 480, "prima": 2.3},
        ],
        "puts": [
            {"strike": 420, "prima": 9.2},
            {"strike": 410, "prima": 6.8},
            {"strike": 400, "prima": 4.5},
            {"strike": 390, "prima": 3.0},
            {"strike": 380, "prima": 1.8},
        ],
    }


def parsear_datos_a3(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"dataframe": None, "resumen": {"filas": 0, "columnas": 0, "columnas_list": []}}
    return {
        "dataframe": df,
        "resumen": {
            "filas": len(df),
            "columnas": len(df.columns),
            "columnas_list": df.columns.tolist(),
        },
    }


def buscar_prima(tipo_opcion: str, strike: float, datos_mercado: dict = None) -> float:
    if datos_mercado is None:
        datos_mercado = obtener_datos_mercado_mock()
    opciones = datos_mercado.get("calls" if tipo_opcion == "call" else "puts", [])
    for op in opciones:
        if abs(op["strike"] - strike) < 0.5:
            return op["prima"]
    if len(opciones) >= 2:
        opciones_sorted = sorted(opciones, key=lambda x: x["strike"])
        for i in range(len(opciones_sorted) - 1):
            if opciones_sorted[i]["strike"] <= strike <= opciones_sorted[i + 1]["strike"]:
                s1, p1 = opciones_sorted[i]["strike"], opciones_sorted[i]["prima"]
                s2, p2 = opciones_sorted[i + 1]["strike"], opciones_sorted[i + 1]["prima"]
                return round(p1 + (strike - s1) * (p2 - p1) / (s2 - s1), 2)
    return 5.0
