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
from estrategias_ui import (
    render_payoff_chart,
    render_preset_selector,
    render_strategy_summary
)
from estrategias_engine import Strategy

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
                    if hasattr(obtener_datos_bolsa, "clear"):
                        obtener_datos_bolsa.clear()
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
                # Validar correctamente si es un DataFrame válido
                if datos_a3 is not None and not datos_a3.empty:
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
    if st.session_state.datos_bolsa is not None and len(st.session_state.datos_bolsa) > 0:
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
    if st.session_state.datos_bolsa is not None and len(st.session_state.datos_bolsa) > 0:
        num_posiciones = len(st.session_state.datos_bolsa)
        st.caption(f"✓ {num_posiciones} posiciones cargadas")
    else:
        st.caption("⚠ Sin datos de FOB")
    
    if st.session_state.datos_a3 is not None and not st.session_state.datos_a3.empty:
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
    st.header("📈 Estrategias de Cobertura")
    
    if st.session_state.datos_bolsa is None or len(st.session_state.datos_bolsa) == 0 or not posicion:
        st.markdown("""
        <div class="alert-warning">
            <strong>⚠ No hay datos disponibles</strong><br>
            Presiona "🌾 Actualizar FOB" en el sidebar para cargar los precios de la Bolsa.
        </div>
        """, unsafe_allow_html=True)
    else:
        # Obtener precio FOB actual
        precios = st.session_state.datos_bolsa[posicion]
        cultivo_lower = cultivo.lower()
        
        fob_keys = {
            'soja': 'soja',
            'maíz': 'maiz',
            'trigo': 'trigo',
            'girasol': 'girasol'
        }
        
        fob_precio = precios.get(fob_keys.get(cultivo_lower, 'soja'), 427)
        
        # Inicializar estrategias en session_state
        if 'estrategias_activas' not in st.session_state:
            st.session_state.estrategias_activas = []
        
        # Layout principal
        col_selector, col_grafico = st.columns([1, 2])
        
        with col_selector:
            # Selector de estrategias predefinidas
            selected = render_preset_selector(fob_precio)
            if selected:
                # Agregar a estrategias activas si no existe
                if selected.name not in [s.name for s in st.session_state.estrategias_activas]:
                    st.session_state.estrategias_activas.append(selected)
                    st.rerun()
            
            # Mostrar estrategias activas
            if st.session_state.estrategias_activas:
                st.divider()
                st.subheader("📊 Activas")
                
                for idx, strat in enumerate(st.session_state.estrategias_activas):
                    col_name, col_remove = st.columns([4, 1])
                    with col_name:
                        cost = strat.total_cost()
                        cost_icon = "💰" if cost > 0 else "💸" if cost < 0 else "⚖️"
                        st.write(f"{cost_icon} **{strat.name}**")
                        st.caption(f"Costo: ${abs(cost):.2f}")
                    with col_remove:
                        if st.button("🗑️", key=f"remove_{idx}"):
                            st.session_state.estrategias_activas.pop(idx)
                            st.rerun()
                
                # Botón para limpiar todas
                if st.button("🗑️ Limpiar Todas", use_container_width=True):
                    st.session_state.estrategias_activas = []
                    st.rerun()
        
        with col_grafico:
            if st.session_state.estrategias_activas:
                # Mostrar precio de referencia
                st.info(f"📍 **{cultivo} - {posicion}:** FOB ${fob_precio:.2f}/tn")
                
                # Renderizar gráfico de payoff
                try:
                    fig = render_payoff_chart(
                        st.session_state.estrategias_activas,
                        fob_precio,
                        width=750,
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error al generar gráfico: {str(e)}")
                
                # Análisis de escenarios
                st.subheader("🎯 Análisis de Escenarios")
                
                # Escenarios: -20%, -10%, actual, +10%, +20%
                escenarios = [
                    fob_precio * 0.80,
                    fob_precio * 0.90,
                    fob_precio,
                    fob_precio * 1.10,
                    fob_precio * 1.20
                ]
                
                # Tabla comparativa
                data = []
                for precio in escenarios:
                    row = {'Escenario': f'${precio:.0f}'}
                    variacion = ((precio / fob_precio) - 1) * 100
                    row['Variación'] = f'{variacion:+.0f}%'
                    
                    for strat in st.session_state.estrategias_activas:
                        pnl = strat.pnl(precio)
                        row[strat.name] = pnl
                    
                    data.append(row)
                
                df = pd.DataFrame(data)
                
                # Formatear y mostrar
                def color_pnl(val):
                    if isinstance(val, (int, float)):
                        color = '#1a854a' if val > 0 else '#c43030' if val < 0 else 'gray'
                        return f'color: {color}; font-weight: 600'
                    return ''
                
                st.dataframe(
                    df.style.format({
                        col: '${:.2f}' 
                        for col in df.columns 
                        if col not in ['Escenario', 'Variación']
                    }).map(
                        color_pnl,
                        subset=[col for col in df.columns if col not in ['Escenario', 'Variación']]
                    ),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Resumen de cada estrategia
                st.divider()
                for strat in st.session_state.estrategias_activas:
                    with st.expander(f"📊 {strat.name} - Métricas Detalladas"):
                        render_strategy_summary(strat, fob_precio)
            else:
                st.markdown("""
                <div style="text-align: center; padding: 4rem 2rem;">
                    <h3 style="color: #c9a961;">👈 Seleccioná estrategias para comenzar</h3>
                    <p style="color: #7e8574; margin-top: 1rem;">
                        Elegí una o más estrategias predefinidas del menú lateral.<br>
                        Podrás comparar gráficamente su performance en diferentes escenarios.
                    </p>
                </div>
                """, unsafe_allow_html=True)

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
    
    if st.session_state.datos_bolsa is None or len(st.session_state.datos_bolsa) == 0 or not posicion:
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
                
        st.markdown("### Simulador de escenario — Baja de retenciones")
        reduccion_ret = st.slider("Reducción de retenciones", 0, 100, 25, 5, format="-%d%%")

        # COLUMNAS PRINCIPALES
        col1, col2 = st.columns(2)
        
        # ──── COLUMNA 1: Exportación grano ────
        with col1:
            st.subheader(f"📈 Exportación grano - {posicion}")
            
            # Inputs editables
            with st.expander("⚙️ Ajustar parámetros", expanded=False):
                fob_indice = st.number_input(
                    "FOB ÍNDICE",
                    min_value=0.0,
                    value=float(fob_precio),
                    step=1.0,
                    key=f"fob_indice_input_{cultivo_lower}_{posicion}"
                )
                ret_porcentaje = st.number_input(
                    "RET %",
                    value=(26.0 if cultivo_lower == 'soja' else 7.0),
                    step=0.1,
                    key=f"ret_porcentaje_input_{cultivo_lower}_{posicion}"
                )
                fobbing = st.number_input(
                    "FOBBING",
                    value=(12.0 if cultivo_lower == 'soja' else 11.0 if cultivo_lower in ['maíz', 'maiz'] else 13.0 if cultivo_lower == 'trigo' else 14.0),
                    step=0.5,
                    key=f"fobbing_input_{cultivo_lower}_{posicion}"
                )
                precio_fas_objetivo = st.number_input(
                    "FAS OBJETIVO (U$S)",
                    min_value=0.0,
                    value=float(precio_fas_manual) if precio_fas_manual is not None else (323.0 if cultivo_lower == 'soja' else 185.0 if cultivo_lower in ['maíz', 'maiz'] else 216.0 if cultivo_lower == 'trigo' else 475.0),
                    step=1.0,
                    key=f"fas_objetivo_input_{cultivo_lower}_{posicion}"
                )
            
            # Calcular métricas con los inputs editables
            resultado_grano = calcular_exportacion_grano(
                fob=fob_indice,
                cultivo=cultivo_lower,
                precio_fas_manual=precio_fas_objetivo
            )

            # Mostrar métricas
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">FOB {cultivo}</div>
                <div class="metric-value">${fob_indice:.2f}</div>
                <div class="metric-delta-positive">100.0%</div>
            </div>
            """, unsafe_allow_html=True)
            
            retencion_valor = fob_indice * (ret_porcentaje / 100)
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
            fas_teorico = fob_indice - retencion_valor - fobbing
            st.markdown("---")
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #1a5430; background: #f0f9f4;">
                <div class="metric-label">FAS Teórico (CTP)</div>
                <div class="metric-value" style="color: #1a5430;">${fas_teorico:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #c9a961;">
                <div class="metric-label">FAS Objetivo</div>
                <div class="metric-value">${precio_fas_objetivo:.2f}</div>
                <div class="metric-delta-positive">Spread CTP vs objetivo: ${fas_teorico - precio_fas_objetivo:+.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            fob_necesario = (precio_fas_objetivo + fobbing) / (1 - ret_porcentaje / 100) if ret_porcentaje < 100 else 0
            ret_implicita = (1 - (precio_fas_objetivo + fobbing) / fob_indice) * 100 if fob_indice > 0 else 0
            st.markdown(f"""
            <div class="metric-card" style="border-left-color:#2563eb;">
                <div class="metric-label">FOB Necesario para FAS Objetivo</div>
                <div class="metric-value">${fob_necesario:.2f}</div>
                <div class="metric-delta-positive">Retención implícita: {ret_implicita:.2f}% | Gap: {ret_implicita - ret_porcentaje:+.2f} pp</div>
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

        st.divider()
        st.subheader("📉 Escenario con reducción de retenciones")
        ret_nueva = (ret_porcentaje / 100) * (1 - reduccion_ret / 100)
        fas_nuevo = fob_indice * (1 - ret_nueva) - fobbing
        col_act, col_red = st.columns(2)
        with col_act:
            st.metric("Escenario actual - FAS teórico", f"${fas_teorico:.2f}", f"Retención {ret_porcentaje:.1f}%")
        with col_red:
            st.metric("Escenario con reducción - FAS teórico", f"${fas_nuevo:.2f}", f"Mejora ${fas_nuevo - fas_teorico:+.2f} | Ret. {ret_nueva*100:.1f}%")
        st.info(f"Conexión con coberturas: si cubrís a FOB ${fob_indice:.1f} con un PUT, el piso de FAS neto estimado es ${fas_teorico:.2f}/tn menos la prima pagada.")

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
