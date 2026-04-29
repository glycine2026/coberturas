"""
Modulo de scraping de la Bolsa de Cereales.
Obtiene precios FOB desde https://preciosfob.bolsadecereales.com

Regla de datos: los FOB y subproductos se devuelven crudos, sin retenciones,
sin fobbing y sin ningun descuento aplicado. La cascada FAS debe aplicar esos
costos en app.py, nunca en el parser.
"""

from __future__ import annotations

import os
import re
import time
from typing import Dict

import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _parse_precio(texto: str) -> float:
    """Parsea valores de la tabla FOB sin aplicar transformaciones financieras."""
    s = str(texto or "").strip()
    if not s or s.upper() in {"S/C", "SC", "N/A", "-", "--"}:
        return 0.0
    # Normaliza posibles formatos: 1.191,50 / 1191,50 / 1191.50 / 1191
    s = re.sub(r"[^0-9,.-]", "", s)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalizar_mes(mes: str) -> str:
    return " ".join(str(mes or "").strip().upper().split())


@st.cache_data(ttl=3600)
def obtener_datos_bolsa() -> Dict[str, Dict[str, float]]:
    """
    Obtiene los datos de la Bolsa de Cereales usando Selenium.

    Returns:
        dict: posicion -> precios crudos.
        Ejemplo:
        {
            'ABR 2026': {
                'soja': 427.0,
                'maiz': 215.0,
                'trigo': 224.0,
                'harina': 357.0,
                'aceite': 1191.0,
                'aceiteGirasol': 1303.0,
            },
            ...
        }
    """
    print("Iniciando scraping de Bolsa de Cereales...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    if os.path.exists("/usr/bin/chromium"):
        chrome_options.binary_location = "/usr/bin/chromium"

    driver = None
    try:
        if os.path.exists("/usr/bin/chromedriver"):
            service = Service("/usr/bin/chromedriver")
        else:
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=chrome_options)
        url = "https://preciosfob.bolsadecereales.com"
        driver.get(url)
        print(f"Pagina cargada: {url}")

        wait = WebDriverWait(driver, 25)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
        time.sleep(3)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table", class_="tabla-cotizaciones") or soup.find("table")
        if not table:
            raise RuntimeError("No se encontro la tabla FOB en el HTML")

        tbody = table.find("tbody") or table
        rows = tbody.find_all("tr")
        print(f"Procesando {len(rows)} filas FOB...")

        datos: Dict[str, Dict[str, float]] = {}
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 7:
                continue

            mes = _normalizar_mes(cells[0].get_text(" ", strip=True))
            if not mes or "USD" in mes or "SOJA" in mes:
                continue

            # Columnas oficiales visibles:
            # 1 Soja, 2 Maiz, 3 Trigo, 4 Harina soja, 5 Aceite soja, 6 Aceite girasol.
            valores = [_parse_precio(cell.get_text(" ", strip=True)) for cell in cells[1:7]]
            if len(valores) < 6:
                continue

            datos[mes] = {
                "soja": valores[0],
                "maiz": valores[1],
                "trigo": valores[2],
                "harina": valores[3],
                "aceite": valores[4],
                "aceiteGirasol": valores[5],
            }

        if not datos:
            raise RuntimeError("No se pudieron extraer datos FOB de la tabla")

        print(f"Se extrajeron {len(datos)} posiciones FOB")
        return datos

    except Exception as exc:
        print(f"ERROR en scraping: {exc}")
        print("Usando datos de respaldo completos hasta ABR 2027")
        return obtener_datos_bolsa_mock()

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def obtener_datos_bolsa_mock() -> Dict[str, Dict[str, float]]:
    """
    Respaldo completo basado en la tabla visible de Bolsa de Cereales
    del 28/04/2026. Mantiene todos los datos crudos, sin descuentos.
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
