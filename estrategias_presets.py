"""
Estrategias Predefinidas de Cobertura
Basado en el HTML original de Espartina
"""

from estrategias_engine import Leg, Strategy


def create_preset_strategies(spot_price: float) -> dict:
    """
    Crea estrategias predefinidas basadas en el precio spot actual
    
    Args:
        spot_price: Precio FOB actual
    
    Returns:
        Dict con estrategias por categoría
    """
    
    strategies = {
        'proteccion': [
            {
                'name': 'Put Seco',
                'desc': 'Seguro puro. Máxima protección, sin techo.',
                'legs': [
                    Leg('buy', 'put', 1, round(spot_price * 0.98), 6)
                ],
                'color': '#1a854a',
                'alert': None
            },
            {
                'name': 'Put Spread',
                'desc': 'Protección con franquicia. Menor costo, piso limitado.',
                'legs': [
                    Leg('buy', 'put', 1, round(spot_price * 0.98), 6),
                    Leg('sell', 'put', 1, round(spot_price * 0.94), 2)
                ],
                'color': '#2d8a54',
                'alert': None
            },
            {
                'name': 'Collar',
                'desc': 'Túnel de rentabilidad. Costo ~cero, con techo.',
                'legs': [
                    Leg('buy', 'put', 1, round(spot_price * 0.97), 5),
                    Leg('sell', 'call', 1, round(spot_price * 1.10), 5)
                ],
                'color': '#3fa06d',
                'alert': None
            }
        ],
        'avanzadas': [
            {
                'name': 'Gaviota',
                'desc': 'Cobertura financiada. Put Spread + venta de Call.',
                'legs': [
                    Leg('buy', 'put', 1, round(spot_price * 0.98), 6),
                    Leg('sell', 'put', 1, round(spot_price * 0.95), 2.5),
                    Leg('sell', 'call', 1, round(spot_price * 1.12), 2)
                ],
                'color': '#c9a961',
                'alert': None
            },
            {
                'name': 'Futuro + Call',
                'desc': 'Fijación sintética con opcionalidad alcista.',
                'legs': [
                    Leg('sell', 'futuro', 1, round(spot_price), 0),
                    Leg('buy', 'call', 1, round(spot_price * 1.05), 4)
                ],
                'color': '#b89851',
                'alert': None
            },
            {
                'name': 'Ratio Put Spread 1x2',
                'desc': 'Costo ~cero, riesgo en baja extrema.',
                'legs': [
                    Leg('buy', 'put', 1, round(spot_price * 0.98), 6),
                    Leg('sell', 'put', 2, round(spot_price * 0.92), 3)
                ],
                'color': '#d4af37',
                'alert': 'warning'
            }
        ],
        'alcistas': [
            {
                'name': 'Gaviota Invertida',
                'desc': 'Recompra sintética alcista. Solo sobre ventas previas.',
                'legs': [
                    Leg('buy', 'call', 1, round(spot_price * 1.03), 5),
                    Leg('sell', 'call', 1, round(spot_price * 1.15), 2),
                    Leg('sell', 'put', 1, round(spot_price * 0.92), 3)
                ],
                'color': '#e67e22',
                'alert': 'danger'
            },
            {
                'name': 'Lanzamiento Cubierto',
                'desc': 'Generación de tasa. Sin protección a la baja.',
                'legs': [
                    Leg('sell', 'call', 1, round(spot_price * 1.08), 4)
                ],
                'color': '#e74c3c',
                'alert': 'danger'
            }
        ]
    }
    
    return strategies


def get_strategy_alerts() -> dict:
    """
    Mensajes de alerta para estrategias específicas
    """
    return {
        'Gaviota Invertida': {
            'tipo': 'danger',
            'mensaje': '<strong>Alerta Directorio:</strong> Armar esta estrategia teniendo el físico sin vender implica duplicar el riesgo bajista. Solo debe usarse calzada contra ventas preexistentes.'
        },
        'Lanzamiento Cubierto': {
            'tipo': 'danger',
            'mensaje': '<strong>Alerta Directorio:</strong> Esta estrategia NO ofrece protección a la baja. Solo genera ingresos por prima en mercados laterales o levemente alcistas.'
        },
        'Ratio Put Spread 1x2': {
            'tipo': 'warning',
            'mensaje': '<strong>Precaución:</strong> El riesgo aumenta exponencialmente en caídas extremas por la venta de 2 PUTs vs 1 comprado.'
        }
    }


def create_custom_strategy(name: str, legs_data: list, color: str = '#1a5430') -> Strategy:
    """
    Crea una estrategia personalizada desde datos
    
    Args:
        name: Nombre de la estrategia
        legs_data: Lista de dicts con datos de legs
        color: Color para gráficos
    
    Example:
        legs_data = [
            {'direction': 'buy', 'type': 'put', 'ratio': 1, 'strike': 400, 'prima': 6},
            {'direction': 'sell', 'type': 'call', 'ratio': 1, 'strike': 450, 'prima': 5}
        ]
    """
    legs = []
    for leg_data in legs_data:
        leg = Leg(
            direction=leg_data['direction'],
            option_type=leg_data['type'],
            ratio=leg_data['ratio'],
            strike=leg_data['strike'],
            prima=leg_data.get('prima', 0)
        )
        legs.append(leg)
    
    return Strategy(name, legs, color)


def get_strategy_by_name(name: str, spot_price: float) -> Strategy:
    """
    Obtiene una estrategia predefinida por nombre
    """
    all_strategies = create_preset_strategies(spot_price)
    
    for category in all_strategies.values():
        for strat_data in category:
            if strat_data['name'] == name:
                return Strategy(
                    name=strat_data['name'],
                    legs=strat_data['legs'],
                    color=strat_data['color']
                )
    
    return None


def get_all_preset_names() -> list:
    """
    Retorna lista de nombres de todas las estrategias predefinidas
    """
    # Usar precio temporal para generar lista
    temp_strategies = create_preset_strategies(400)
    names = []
    
    for category in temp_strategies.values():
        for strat in category:
            names.append(strat['name'])
    
    return names
