"""
Módulo de integración con Google Sheets
Obtiene datos de A3 Info y datos de mercado de opciones
"""

import pandas as pd
import streamlit as st
import requests

# ID del Google Sheet (extráelo de la URL de tu sheet)
SHEET_ID = "2PACX-1vTYR1G5tN0wEOnBhbHOEElP5gF0UWctmCSOSLmjb8_Zw38dLkGMfTTOW51iCQqwROmkUOLsMShcLwnn"

@st.cache_data(ttl=1800)  # Cache por 30 minutos
def obtener_datos_a3():
    """
    Obtiene datos de Google Sheets (A3 Info)
    
    Returns:
        pd.DataFrame: DataFrame con los datos del sheet
    """
    
    try:
        # URL pública del Google Sheet en formato CSV
        url = f"https://docs.google.com/spreadsheets/d/e/{SHEET_ID}/pub?output=csv"
        
        print(f"📡 Conectando a Google Sheets: {SHEET_ID}")
        
        # Leer CSV
        df = pd.read_csv(url)
        
        print(f"✓ Datos obtenidos: {len(df)} filas")
        
        return df
        
    except Exception as e:
        print(f"✗ Error al obtener datos de Google Sheets: {e}")
        
        # Retornar datos mock si falla
        return obtener_datos_a3_mock()


def obtener_datos_a3_mock():
    """
    Datos mock de A3 para testing
    """
    data = {
        'Producto': ['Soja', 'Maíz', 'Trigo'],
        'Precio': [323, 180, 225],
        'Volumen': [1000, 500, 300]
    }
    
    return pd.DataFrame(data)


def obtener_datos_mercado_opciones():
    """
    Obtiene datos de mercado de opciones (primas y strikes disponibles)
    desde Google Sheets
    
    Returns:
        dict: Datos de mercado estructurados
    """
    try:
        df = obtener_datos_a3()
        
        # Intentar parsear datos de opciones del sheet
        # Esto depende de cómo tu compañero estructuró los datos
        
        # Por ahora retornar mock si no hay estructura definida
        return obtener_datos_mercado_mock()
        
    except Exception as e:
        print(f"Error al obtener datos de mercado: {e}")
        return obtener_datos_mercado_mock()


def obtener_datos_mercado_mock():
    """
    Datos mock de mercado de opciones
    Estructura: posición -> tipo -> [lista de {strike, prima}]
    """
    return {
        'posicion': 'MAY 2026',  # Posición actual
        'calls': [
            {'strike': 440, 'prima': 8.5},
            {'strike': 450, 'prima': 6.2},
            {'strike': 460, 'prima': 4.8},
            {'strike': 470, 'prima': 3.5},
            {'strike': 480, 'prima': 2.3}
        ],
        'puts': [
            {'strike': 420, 'prima': 9.2},
            {'strike': 410, 'prima': 6.8},
            {'strike': 400, 'prima': 4.5},
            {'strike': 390, 'prima': 3.0},
            {'strike': 380, 'prima': 1.8}
        ]
    }


def parsear_datos_a3(df):
    """
    Parsea y limpia los datos de A3
    
    Args:
        df (pd.DataFrame): DataFrame crudo de Google Sheets
        
    Returns:
        dict: Datos estructurados
    """
    
    # Verificar si el DataFrame está vacío usando .empty
    if df is None or df.empty:
        return {
            'dataframe': None,
            'resumen': {
                'filas': 0,
                'columnas': 0,
                'columnas_list': []
            }
        }
    
    return {
        'dataframe': df,
        'resumen': {
            'filas': len(df),
            'columnas': len(df.columns),
            'columnas_list': df.columns.tolist()
        }
    }


def buscar_prima(tipo_opcion: str, strike: float, datos_mercado: dict = None) -> float:
    """
    Busca la prima de una opción en los datos de mercado
    
    Args:
        tipo_opcion: 'call' o 'put'
        strike: Precio de ejercicio
        datos_mercado: Dict con datos de mercado (opcional)
    
    Returns:
        Prima encontrada o estimación
    """
    if datos_mercado is None:
        datos_mercado = obtener_datos_mercado_mock()
    
    opciones = datos_mercado.get('calls' if tipo_opcion == 'call' else 'puts', [])
    
    # Buscar strike exacto
    for opcion in opciones:
        if abs(opcion['strike'] - strike) < 0.5:
            return opcion['prima']
    
    # Si no encuentra, interpolar o retornar estimación
    if len(opciones) >= 2:
        # Interpolación lineal simple
        opciones_sorted = sorted(opciones, key=lambda x: x['strike'])
        
        for i in range(len(opciones_sorted) - 1):
            if opciones_sorted[i]['strike'] <= strike <= opciones_sorted[i+1]['strike']:
                # Interpolación
                s1, p1 = opciones_sorted[i]['strike'], opciones_sorted[i]['prima']
                s2, p2 = opciones_sorted[i+1]['strike'], opciones_sorted[i+1]['prima']
                
                prima = p1 + (strike - s1) * (p2 - p1) / (s2 - s1)
                return round(prima, 2)
    
    # Default: estimación básica
    return 5.0
