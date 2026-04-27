"""
Módulo de scraping de la Bolsa de Cereales
Obtiene precios FOB de https://preciosfob.bolsadecereales.com
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import streamlit as st
import time
import os

@st.cache_data(ttl=3600)  # Cache por 1 hora
def obtener_datos_bolsa():
    """
    Obtiene los datos de la Bolsa de Cereales usando Selenium
    
    Returns:
        dict: Diccionario con los precios por mes
        Ejemplo: {
            'ABR 2026': {'soja': 427, 'maiz': 215, 'trigo': 224, ...},
            'MAY 2026': {'soja': 426, 'maiz': 215, 'trigo': 226, ...},
            ...
        }
    """
    
    print("🌐 Iniciando scraping de Bolsa de Cereales...")
    
    # Configurar Chrome en modo headless
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Detectar si estamos en Streamlit Cloud
    if os.path.exists('/usr/bin/chromium'):
        chrome_options.binary_location = '/usr/bin/chromium'
    
    try:
        # Iniciar Chrome
        if os.path.exists('/usr/bin/chromedriver'):
            # Streamlit Cloud
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            # Local con webdriver-manager
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navegar a la página
        url = "https://preciosfob.bolsadecereales.com"
        driver.get(url)
        print(f"✓ Página cargada: {url}")
        
        # Esperar a que la tabla esté presente
        wait = WebDriverWait(driver, 20)
        table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "tabla-cotizaciones")))
        
        # Dar tiempo extra para que cargue completamente
        time.sleep(3)
        
        print("✓ Tabla encontrada, extrayendo datos...")
        
        # Obtener el HTML
        html = driver.page_source
        driver.quit()
        
        # Parsear con BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='tabla-cotizaciones')
        
        if not table:
            raise Exception("No se encontró la tabla en el HTML")
        
        # Extraer datos
        datos = {}
        rows = table.find('tbody').find_all('tr')
        
        print(f"📊 Procesando {len(rows)} filas...")
        
        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) >= 7:
                # Primera celda: mes
                mes = cells[0].get_text(strip=True)
                
                # Buscar valores en los spans
                valores = []
                for cell in cells:
                    span = cell.find('span')
                    if span:
                        text = span.get_text(strip=True)
                        if text in ['s/c', 'S/C', 'N/A', '', '-']:
                            valores.append(0)
                        else:
                            try:
                                valores.append(float(text))
                            except:
                                valores.append(0)
                
                # Asignar valores (esperamos 6: soja, maíz, trigo, harina, aceite, aceite girasol)
                if len(valores) >= 6:
                    datos[mes] = {
                        'soja': valores[0],
                        'maiz': valores[1],
                        'trigo': valores[2],
                        'harina': valores[3],
                        'aceite': valores[4],
                        'aceiteGirasol': valores[5] if len(valores) > 5 else 0
                    }
        
        if not datos:
            raise Exception("No se pudieron extraer datos de la tabla")
        
        print(f"✓ Se extrajeron {len(datos)} meses correctamente")
        
        # Mostrar vista previa
        for i, (mes, precios) in enumerate(datos.items()):
            if i < 3:
                print(f"  {mes}: Soja ${precios['soja']}, Maíz ${precios['maiz']}, Trigo ${precios['trigo']}")
        
        return datos
        
    except Exception as e:
        print(f"✗ ERROR en scraping: {e}")
        # En caso de error, usar datos mock
        print("⚠️ Usando datos de respaldo (mock)")
        return obtener_datos_bolsa_mock()


def obtener_datos_bolsa_mock():
    """
    Datos de prueba para testing sin scraping real
    Útil para desarrollo y testing
    """
    return {
        'ABR 2026': {
            'soja': 427.0,
            'maiz': 215.0,
            'trigo': 224.0,
            'harina': 357.0,
            'aceite': 1191.0,
            'aceiteGirasol': 1303.0
        },
        'MAY 2026': {
            'soja': 426.0,
            'maiz': 215.0,
            'trigo': 226.0,
            'harina': 355.0,
            'aceite': 1195.0,
            'aceiteGirasol': 1298.0
        },
        'JUN 2026': {
            'soja': 428.0,
            'maiz': 213.0,
            'trigo': 230.0,
            'harina': 347.0,
            'aceite': 1154.0,
            'aceiteGirasol': 1298.0
        },
        'JUL 2026': {
            'soja': 426.0,
            'maiz': 211.0,
            'trigo': 229.0,
            'harina': 346.0,
            'aceite': 1151.0,
            'aceiteGirasol': 1303.0
        },
        'AGO 2026': {
            'soja': 419.0,
            'maiz': 215.0,
            'trigo': 228.0,
            'harina': 344.0,
            'aceite': 1146.0,
            'aceiteGirasol': 1303.0
        }
    }
