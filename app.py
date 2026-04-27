"""
🌾 Estrategias de Cobertura - Espartina S.A.
Dashboard completo para análisis de coberturas y FAS Teórico
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time

# Importar módulos locales
from scraper import obtener_datos_bolsa
from calculadora import (
    calcular_fas_teorico,
    calcular_retenciones,
    calcular_crushing,
    calcular_exportacion_grano
)
from google_sheets import obtener_datos_a3

# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Estrategias de Cobertura - Espartina S.A.",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════
# ESTILOS CSS (Respetando estética del HTML)
# ═══════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Variables de color Espartina */
    :root {
        --es-green: #1a5430;
        --es-gold: #c9a961;
        --bg-primary: #f8f9fa;
        --text-primary: #2d3748;
        --text-secondary: #718096;
    }
    
    /* Header personalizado */
    .main-header {
        background: linear-gradient(135deg, #1a5430 0%, #2d6b42 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
        font-weight: 600;
    }
    
    .main-header p {
        color: #c9a961;
        margin: 0.5rem 0 0 0;
        font-size: 0.95rem;
    }
    
    /* Métricas personalizadas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #c9a961;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #718096;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    .metric-value {
        font-size: 1.75rem;
        color: #2d3748;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    .metric-delta-positive {
        color: #1a5430;
        font-size: 0.9rem;
    }
    
    .metric-delta-negative {
        color: #dc2626;
        font-size: 0.9rem;
    }
    
    /* Botones */
    .stButton > button {
        background: #c9a961 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background: #b89851 !important;
        box-shadow: 0 4px 12px rgba(201, 169, 97, 0.3) !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        border-radius: 8px;
        border-color: #e2e8f0;
    }
    
    /* Tabs personalizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
        border: 2px solid #e2e8f0;
        border-bottom: none;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1a5430;
        color: white !important;
        border-color: #1a5430;
    }
    
    /* Tablas */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Alertas */
    .alert-success {
        background: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 8px;
        color: #065f46;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 8px;
        color: #92400e;
        margin: 1rem 0;
    }
    
    .alert-error {
        background: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 1rem;
        border-radius: 8px;
        color: #991b1b;
        margin: 1rem 0;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: #f8f9fa;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #718096;
        font-size: 0.85rem;
        margin-top: 3rem;
        border-top: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# INICIALIZACIÓN DE SESSION STATE
# ═══════════════════════════════════════════════════════════

if 'datos_bolsa' not in st.session_state:
    st.session_state.datos_bolsa = None
    
if 'datos_a3' not in st.session_state:
    st.session_state.datos_a3 = None
    
if 'ultima_actualizacion' not in st.session_state:
    st.session_state.ultima_actualizacion = None

# ═══════════════════════════════════════════════════════════
# HEADER PRINCIPAL
# ═══════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🌾 Estrategias de Cobertura</h1>
    <p>Espartina S.A. — Simulador de Coberturas & FAS Teórico</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# SIDEBAR - CONFIGURACIÓN Y CONTROLES
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Botón de actualización de FOB
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🌾 Actualizar FOB", use_container_width=True):
            with st.spinner("Obteniendo datos de la Bolsa de Cereales..."):
                try:
                    datos = obtener_datos_bolsa()
                    if datos and len(datos) > 0:
                        st.session_state.datos_bolsa = datos
                        st.session_state.ultima_actualizacion = datetime.now()
                        st.success("✓ Datos actualizados correctamente")
                    else:
                        st.error("✗ No se obtuvieron datos de la Bolsa")
                except Exception as e:
                    st.error(f"✗ Error al actualizar: {str(e)}")
    
    with col2:
        if st.session_state.ultima_actualizacion:
            hora = st.session_state.ultima_actualizacion.strftime("%H:%M")
            st.caption(f"✓ {hora}")
        else:
            st.caption("⏳")
    
    st.divider()
    
    # Botón de sincronización con Google Sheets
    if st.button("📡 Sincronizar A3", use_container_width=True):
        with st.spinner("Obteniendo datos de Google Sheets..."):
            try:
                datos_a3 = obtener_datos_a3()
                if datos_a3:
                    st.session_state.datos_a3 = datos_a3
                    st.success("✓ Datos A3 sincronizados")
                else:
                    st.warning("⚠ No se obtuvieron datos de A3")
            except Exception as e:
                st.error(f"✗ Error: {str(e)}")
    
    st.divider()
    
    # Selectores de configuración
    st.subheader("📊 Parámetros")
    
    # Selector de cultivo
    cultivo = st.selectbox(
        "Cultivo",
        ["Soja", "Maíz", "Trigo", "Girasol"],
        key="cultivo_selector"
    )
    
    # Selector de posición (se llena dinámicamente)
    if st.session_state.datos_bolsa:
        posiciones = list(st.session_state.datos_bolsa.keys())
        posicion = st.selectbox(
            "Posición 1",
            posiciones,
            key="posicion_selector"
        )
    else:
        st.info("👆 Presiona 'Actualizar FOB' para cargar posiciones")
        posicion = None
    
    # Precio FAS manual (opcional)
    st.divider()
    st.subheader("💰 Precios Manuales")
    
    usar_precio_manual = st.checkbox("Usar precio FAS manual")
    if usar_precio_manual:
        precio_fas_manual = st.number_input(
            "FAS Objetivo (U$S)",
            min_value=0.0,
            value=323.0,
            step=1.0
        )
    else:
        precio_fas_manual = None
    
    st.divider()
    
    # Información de estado
    st.caption("📅 Estado del sistema")
    if st.session_state.datos_bolsa:
        num_posiciones = len(st.session_state.datos_bolsa)
        st.caption(f"✓ {num_posiciones} posiciones cargadas")
    else:
        st.caption("⚠ Sin datos de FOB")
    
    if st.session_state.datos_a3:
        st.caption("✓ Datos A3 disponibles")
    else:
        st.caption("⚠ Sin datos A3")

# ═══════════════════════════════════════════════════════════
# CONTENIDO PRINCIPAL - TABS
# ═══════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs([
    "📈 Estrategias de Cobertura",
    "📚 Manual Teórico",
    "🧮 Retenciones & FAS Teórico"
])

# ──────────────────────────────────────────────────────────
# TAB 1: ESTRATEGIAS DE COBERTURA
# ──────────────────────────────────────────────────────────

with tab1:
    st.header("Estrategias de Cobertura")
    
    if not st.session_state.datos_bolsa:
        st.markdown("""
        <div class="alert-warning">
            <strong>⚠ No hay datos disponibles</strong><br>
            Presiona el botón "🌾 Actualizar FOB" en el sidebar para obtener los precios de la Bolsa de Cereales.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("🚧 Esta sección está en desarrollo. Próximamente incluirá el simulador completo de estrategias de cobertura.")

# ──────────────────────────────────────────────────────────
# TAB 2: MANUAL TEÓRICO
# ──────────────────────────────────────────────────────────

with tab2:
    st.header("Manual Teórico")
    st.info("🚧 Esta sección contendrá el manual teórico sobre coberturas y estrategias.")

# ──────────────────────────────────────────────────────────
# TAB 3: RETENCIONES & FAS TEÓRICO
# ──────────────────────────────────────────────────────────

with tab3:
    st.header("🧮 Retenciones & FAS Teórico")
    
    if not st.session_state.datos_bolsa or not posicion:
        st.markdown("""
        <div class="alert-warning">
            <strong>⚠ No hay datos disponibles</strong><br>
            Presiona "🌾 Actualizar FOB" y selecciona una posición para ver los cálculos.
        </div>
        """, unsafe_allow_html=True)
    else:
        # Obtener precios de la posición seleccionada
        precios = st.session_state.datos_bolsa[posicion]
        cultivo_lower = cultivo.lower()
        
        # Obtener precio FOB según cultivo
        fob_keys = {
            'soja': 'soja',
            'maíz': 'maiz',
            'trigo': 'trigo',
            'girasol': 'girasol'
        }
        
        fob_precio = precios.get(fob_keys.get(cultivo_lower, 'soja'), 0)
        
        # Calcular métricas
        resultado_grano = calcular_exportacion_grano(
            fob=fob_precio,
            cultivo=cultivo_lower,
            precio_fas_manual=precio_fas_manual
        )
        
        # COLUMNAS PRINCIPALES
        col1, col2 = st.columns(2)
        
        # ──── COLUMNA 1: Exportación grano ────
        with col1:
            st.subheader(f"📈 Exportación grano - {posicion}")
            
            # Inputs editables
            with st.expander("⚙️ Ajustar parámetros", expanded=False):
                fob_indice = st.number_input(
                    "FOB ÍNDICE",
                    value=float(fob_precio),
                    key="fob_indice_input"
                )
                ret_porcentaje = st.number_input(
                    "RET %",
                    value=24.0 if cultivo_lower == 'soja' else 12.0,
                    step=0.1,
                    key="ret_porcentaje_input"
                )
                fobbing = st.number_input(
                    "FOBBING",
                    value=12.0,
                    step=0.5,
                    key="fobbing_input"
                )
            
            # Mostrar métricas
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">FOB {cultivo}</div>
                <div class="metric-value">${fob_precio:.2f}</div>
                <div class="metric-delta-positive">100.0%</div>
            </div>
            """, unsafe_allow_html=True)
            
            retencion_valor = fob_precio * (ret_porcentaje / 100)
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Retención {ret_porcentaje}%</div>
                <div class="metric-value">-${retencion_valor:.2f}</div>
                <div class="metric-delta-negative">{ret_porcentaje}%</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Fobbing</div>
                <div class="metric-value">-${fobbing:.2f}</div>
                <div class="metric-delta-negative">2.9%</div>
            </div>
            """, unsafe_allow_html=True)
            
            # FAS Teórico (CTP)
            fas_teorico = fob_precio - retencion_valor - fobbing
            st.markdown("---")
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #1a5430; background: #f0f9f4;">
                <div class="metric-label">FAS Teórico (CTP)</div>
                <div class="metric-value" style="color: #1a5430;">${fas_teorico:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # ──── COLUMNA 2: Crushing subproductos ────
        with col2:
            if cultivo_lower == 'soja':
                st.subheader("🔄 Crushing subproductos")
                
                # Inputs crushing
                with st.expander("⚙️ Ajustar parámetros crushing", expanded=False):
                    fob_aceite = st.number_input(
                        "FOB ACEITE",
                        value=float(precios.get('aceite', 1191)),
                        key="fob_aceite_input"
                    )
                    coef_aceite = st.number_input(
                        "COEF. Aceite",
                        value=0.19,
                        step=0.01,
                        key="coef_aceite_input"
                    )
                    fob_harina = st.number_input(
                        "FOB HARINA",
                        value=float(precios.get('harina', 357)),
                        key="fob_harina_input"
                    )
                    coef_harina = st.number_input(
                        "COEF. Harina",
                        value=0.78,
                        step=0.01,
                        key="coef_harina_input"
                    )
                    ret_sub_porcentaje = st.number_input(
                        "RET SUB %",
                        value=22.5,
                        step=0.1,
                        key="ret_sub_input"
                    )
                    fobbing_sub = st.number_input(
                        "FOBBING Subprod",
                        value=19.0,
                        step=0.5,
                        key="fobbing_sub_input"
                    )
                    gto_ind = st.number_input(
                        "GTO IND.",
                        value=29.0,
                        step=1.0,
                        key="gto_ind_input"
                    )
                
                # Cálculos crushing
                aceite_bruto = fob_aceite * coef_aceite
                harina_bruta = fob_harina * coef_harina
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Aceite ({fob_aceite:.0f} × {coef_aceite})</div>
                    <div class="metric-value">${aceite_bruto:.2f}</div>
                    <div class="metric-delta-positive">45.3%</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Harina ({fob_harina:.0f} × {coef_harina})</div>
                    <div class="metric-value">${harina_bruta:.2f}</div>
                    <div class="metric-delta-positive">55.2%</div>
                </div>
                """, unsafe_allow_html=True)
                
                ret_subprod = (aceite_bruto + harina_bruta) * (ret_sub_porcentaje / 100)
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Ret subprod {ret_sub_porcentaje}%</div>
                    <div class="metric-value">-${ret_subprod:.2f}</div>
                    <div class="metric-delta-negative">{ret_sub_porcentaje}%</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Fobbing subprod</div>
                    <div class="metric-value">-${fobbing_sub:.2f}</div>
                    <div class="metric-delta-negative">3.8%</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Gto Ind.</div>
                    <div class="metric-value">-${gto_ind:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # FAS Crushing
                fas_crushing = aceite_bruto + harina_bruta - ret_subprod - fobbing_sub - gto_ind
                st.markdown("---")
                st.markdown(f"""
                <div class="metric-card" style="border-left-color: #1a5430; background: #f0f9f4;">
                    <div class="metric-label">FAS Crushing</div>
                    <div class="metric-value" style="color: #1a5430;">${fas_crushing:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Spread
                spread = fas_crushing - fas_teorico
                spread_color = "#1a5430" if spread > 0 else "#dc2626"
                st.markdown(f"""
                <div class="metric-card" style="border-left-color: {spread_color};">
                    <div class="metric-label">Spread Crushing vs Teórico</div>
                    <div class="metric-value" style="color: {spread_color};">${spread:+.2f}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"💡 El crushing solo aplica para Soja. Actualmente seleccionado: {cultivo}")

# ═══════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════

st.markdown("""
<div class="footer">
    <p>🌾 <strong>Espartina S.A.</strong> — Dashboard de Estrategias de Cobertura</p>
    <p style="font-size: 0.75rem; margin-top: 0.5rem;">
        Datos actualizados desde <a href="https://preciosfob.bolsadecereales.com" target="_blank">Bolsa de Cereales</a>
    </p>
</div>
""", unsafe_allow_html=True)
