"""
Interface de Usuario para Estrategias de Cobertura
Componentes visuales y interactivos para Streamlit
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from estrategias_engine import Strategy, Leg, create_spot_range, compare_strategies
from estrategias_presets import create_preset_strategies, get_strategy_alerts


def render_payoff_chart(strategies: list, spot_price: float, width: int = 800, height: int = 500):
    """
    Renderiza gráfico de payoff interactivo con Plotly
    
    Args:
        strategies: Lista de objetos Strategy
        spot_price: Precio FOB actual
        width, height: Dimensiones del gráfico
    """
    # Crear rango de precios
    spot_range = create_spot_range(spot_price, width_pct=0.35, points=300)
    
    # Crear figura
    fig = go.Figure()
    
    # Línea de referencia en cero
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
    
    # Línea vertical en precio actual
    fig.add_vline(
        x=spot_price, 
        line_dash="dot", 
        line_color="#c9a961", 
        line_width=2,
        annotation_text=f"FOB Actual: ${spot_price:.0f}",
        annotation_position="top"
    )
    
    # Agregar curva de cada estrategia
    for strategy in strategies:
        payoff_curve = strategy.payoff_curve(spot_range)
        
        fig.add_trace(go.Scatter(
            x=spot_range,
            y=payoff_curve,
            mode='lines',
            name=strategy.name,
            line=dict(color=strategy.color, width=3),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Precio: $%{x:.1f}<br>' +
                         'P&L: $%{y:.2f}<br>' +
                         '<extra></extra>'
        ))
    
    # Layout
    fig.update_layout(
        title={
            'text': '📊 Diagrama de Payoff - Estrategias de Cobertura',
            'font': {'size': 20, 'color': '#fff', 'family': 'DM Sans'}
        },
        xaxis_title='Precio FOB (USD/tn)',
        yaxis_title='P&L (USD/tn)',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#fff', family='DM Sans'),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True,
            zeroline=True,
            zerolinecolor='rgba(255,255,255,0.3)',
            zerolinewidth=2
        ),
        legend=dict(
            bgcolor='rgba(26,107,60,0.3)',
            bordercolor='rgba(255,255,255,0.2)',
            borderwidth=1
        ),
        width=width,
        height=height
    )
    
    return fig


def render_strategy_card(strategy_data: dict, spot_price: float, key_prefix: str):
    """
    Renderiza una tarjeta de estrategia predefinida
    
    Args:
        strategy_data: Dict con datos de la estrategia
        spot_price: Precio FOB actual
        key_prefix: Prefijo para keys únicos de Streamlit
    """
    strategy = Strategy(
        name=strategy_data['name'],
        legs=strategy_data['legs'],
        color=strategy_data['color']
    )
    
    # Crear columnas para la tarjeta
    col_info, col_btn = st.columns([4, 1])
    
    with col_info:
        st.markdown(f"**{strategy_data['name']}**")
        st.caption(strategy_data['desc'])
        
        # Mostrar costo
        cost = strategy.total_cost()
        cost_color = "green" if cost > 0 else "red" if cost < 0 else "gray"
        cost_text = f"Costo neto: ${abs(cost):.2f}" if cost < 0 else f"Crédito neto: ${cost:.2f}" if cost > 0 else "Costo: ~$0"
        st.markdown(f":{cost_color}[{cost_text}]")
    
    with col_btn:
        if st.button("Usar", key=f"{key_prefix}_{strategy_data['name']}", use_container_width=True):
            return strategy
    
    # Alerta si existe
    if strategy_data.get('alert'):
        alerts = get_strategy_alerts()
        if strategy_data['name'] in alerts:
            alert_data = alerts[strategy_data['name']]
            if alert_data['tipo'] == 'danger':
                st.error(alert_data['mensaje'], icon="⚠️")
            elif alert_data['tipo'] == 'warning':
                st.warning(alert_data['mensaje'], icon="⚡")
    
    return None


def render_comparison_table(strategies: list, spot_prices: list):
    """
    Renderiza tabla de comparación de estrategias en diferentes escenarios
    
    Args:
        strategies: Lista de Strategy objects
        spot_prices: Lista de precios para analizar
    """
    if not strategies:
        st.info("Agregá estrategias para ver la comparación")
        return
    
    # Crear DataFrame de comparación
    data = []
    
    for spot in spot_prices:
        row = {'Escenario': f'${spot:.0f}'}
        for strat in strategies:
            pnl = strat.pnl(spot)
            row[strat.name] = pnl
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Formatear como tabla
    st.dataframe(
        df.style.format({col: '${:.2f}' for col in df.columns if col != 'Escenario'})
              .background_gradient(cmap='RdYlGn', subset=[col for col in df.columns if col != 'Escenario']),
        use_container_width=True,
        hide_index=True
    )


def render_strategy_legs_editor(strategy: Strategy, key_prefix: str):
    """
    Editor de piernas (legs) de una estrategia
    
    Args:
        strategy: Objeto Strategy
        key_prefix: Prefijo para keys
    
    Returns:
        Strategy modificada o None
    """
    st.subheader(f"⚙️ {strategy.name}")
    
    modified_legs = []
    
    for idx, leg in enumerate(strategy.legs):
        with st.expander(f"Leg {idx + 1}: {leg.type.upper()} - {leg.direction.upper()}", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                direction = st.selectbox(
                    "Dirección",
                    ['buy', 'sell'],
                    index=0 if leg.direction == 'buy' else 1,
                    key=f"{key_prefix}_dir_{idx}"
                )
            
            with col2:
                option_type = st.selectbox(
                    "Tipo",
                    ['call', 'put', 'futuro'],
                    index=['call', 'put', 'futuro'].index(leg.type),
                    key=f"{key_prefix}_type_{idx}"
                )
            
            with col3:
                strike = st.number_input(
                    "Strike",
                    value=float(leg.strike),
                    step=1.0,
                    key=f"{key_prefix}_strike_{idx}"
                )
            
            with col4:
                prima = st.number_input(
                    "Prima",
                    value=float(leg.prima),
                    step=0.5,
                    key=f"{key_prefix}_prima_{idx}"
                )
            
            ratio = st.slider(
                "Ratio (contratos)",
                min_value=0.5,
                max_value=5.0,
                value=float(leg.ratio),
                step=0.5,
                key=f"{key_prefix}_ratio_{idx}"
            )
            
            modified_leg = Leg(direction, option_type, ratio, strike, prima)
            modified_legs.append(modified_leg)
    
    # Botón para agregar leg
    if st.button("➕ Agregar Leg", key=f"{key_prefix}_add_leg"):
        new_leg = Leg('buy', 'put', 1, 400, 5)
        modified_legs.append(new_leg)
    
    # Crear nueva estrategia con legs modificadas
    return Strategy(strategy.name, modified_legs, strategy.color)


def render_preset_selector(spot_price: float):
    """
    Selector de estrategias predefinidas organizado por categorías
    
    Returns:
        Strategy seleccionada o None
    """
    presets = create_preset_strategies(spot_price)
    
    st.subheader("📚 Estrategias Predefinidas")
    
    tabs = st.tabs(["🛡️ Protección", "⚡ Avanzadas", "📈 Alcistas"])
    
    selected_strategy = None
    
    with tabs[0]:
        st.caption("Estrategias conservadoras de cobertura")
        for strat_data in presets['proteccion']:
            result = render_strategy_card(strat_data, spot_price, "prot")
            if result:
                selected_strategy = result
    
    with tabs[1]:
        st.caption("Estrategias complejas con mejor costo-beneficio")
        for strat_data in presets['avanzadas']:
            result = render_strategy_card(strat_data, spot_price, "adv")
            if result:
                selected_strategy = result
    
    with tabs[2]:
        st.caption("⚠️ Solo para posiciones vendidas o generación de ingresos")
        for strat_data in presets['alcistas']:
            result = render_strategy_card(strat_data, spot_price, "alc")
            if result:
                selected_strategy = result
    
    return selected_strategy


def render_strategy_summary(strategy: Strategy, spot_price: float):
    """
    Muestra resumen de métricas de una estrategia
    """
    # Crear rango para análisis
    spot_range = create_spot_range(spot_price, width_pct=0.35, points=300)
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cost = strategy.total_cost()
        st.metric(
            "Costo Neto",
            f"${abs(cost):.2f}",
            delta="Crédito" if cost > 0 else "Débito" if cost < 0 else "Neutro",
            delta_color="normal" if cost >= 0 else "inverse"
        )
    
    with col2:
        max_profit = strategy.max_profit(spot_range)
        st.metric(
            "Ganancia Máxima",
            f"${max_profit:.2f}" if max_profit < 1000 else "Ilimitada"
        )
    
    with col3:
        max_loss = strategy.max_loss(spot_range)
        st.metric(
            "Pérdida Máxima",
            f"${abs(max_loss):.2f}" if max_loss > -1000 else "Ilimitada",
            delta_color="inverse"
        )
    
    with col4:
        breakevens = strategy.breakeven_points(spot_range)
        be_text = f"${breakevens[0]:.1f}" if len(breakevens) > 0 else "N/A"
        st.metric(
            "Break-even",
            be_text
        )
    
    # P&L al precio actual
    current_pnl = strategy.pnl(spot_price)
    st.metric(
        f"P&L al precio actual (${spot_price:.0f})",
        f"${current_pnl:.2f}",
        delta_color="normal" if current_pnl >= 0 else "inverse"
    )
