"""
Módulo de integración con Google Sheets
Obtiene datos de A3 Info
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


def parsear_datos_a3(df):
    """
    Parsea y limpia los datos de A3
    
    Args:
        df (pd.DataFrame): DataFrame crudo de Google Sheets
        
    Returns:
        dict: Datos estructurados
    """
    
    # Aquí puedes agregar lógica de parseo específica
    # según la estructura de tu Google Sheet
    
    return {
        'dataframe': df,
        'resumen': {
            'filas': len(df),
            'columnas': len(df.columns),
            'columnas_list': df.columns.tolist()
        }
    }
