"""
Motor de Estrategias de Cobertura
Cálculo de payoff, P&L y análisis de opciones
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple


class Leg:
    """
    Representa una pierna (leg) de la estrategia
    """
    def __init__(self, direction: str, option_type: str, ratio: float, 
                 strike: float, prima: float = 0):
        """
        Args:
            direction: 'buy' o 'sell'
            option_type: 'call', 'put', o 'futuro'
            ratio: Cantidad de contratos
            strike: Precio de ejercicio
            prima: Prima pagada/recibida
        """
        self.direction = direction  # buy o sell
        self.type = option_type     # call, put, futuro
        self.ratio = ratio          # Número de contratos
        self.strike = strike        # Strike price
        self.prima = prima          # Prima


    def payoff(self, spot_price: float) -> float:
        """
        Calcula el payoff de la pierna a un precio spot dado
        """
        if self.type == 'futuro':
            # Futuro: diferencia entre spot y strike
            intrinsic = (spot_price - self.strike) * self.ratio
            if self.direction == 'sell':
                intrinsic = -intrinsic
            return intrinsic
        
        elif self.type == 'call':
            # Call: max(spot - strike, 0)
            intrinsic = max(spot_price - self.strike, 0) * self.ratio
            if self.direction == 'sell':
                intrinsic = -intrinsic
            return intrinsic
        
        elif self.type == 'put':
            # Put: max(strike - spot, 0)
            intrinsic = max(self.strike - spot_price, 0) * self.ratio
            if self.direction == 'sell':
                intrinsic = -intrinsic
            return intrinsic
        
        return 0


    def net_cost(self) -> float:
        """
        Calcula el costo neto de la pierna (prima pagada - prima recibida)
        """
        if self.direction == 'buy':
            return -self.prima * self.ratio
        else:  # sell
            return self.prima * self.ratio


    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'direction': self.direction,
            'type': self.type,
            'ratio': self.ratio,
            'strike': self.strike,
            'prima': self.prima
        }


class Strategy:
    """
    Representa una estrategia completa de cobertura
    """
    def __init__(self, name: str, legs: List[Leg], color: str = '#1a5430'):
        """
        Args:
            name: Nombre de la estrategia
            legs: Lista de piernas
            color: Color para gráficos
        """
        self.name = name
        self.legs = legs
        self.color = color


    def total_payoff(self, spot_price: float) -> float:
        """
        Calcula el payoff total de la estrategia a un precio spot
        """
        return sum(leg.payoff(spot_price) for leg in self.legs)


    def total_cost(self) -> float:
        """
        Costo neto total de la estrategia (primas)
        """
        return sum(leg.net_cost() for leg in self.legs)


    def pnl(self, spot_price: float) -> float:
        """
        Profit & Loss total = payoff + costo
        """
        return self.total_payoff(spot_price) + self.total_cost()


    def payoff_curve(self, spot_range: np.ndarray) -> np.ndarray:
        """
        Genera curva de payoff para un rango de precios spot
        """
        return np.array([self.pnl(spot) for spot in spot_range])


    def max_profit(self, spot_range: np.ndarray) -> float:
        """
        Ganancia máxima posible
        """
        curve = self.payoff_curve(spot_range)
        return np.max(curve)


    def max_loss(self, spot_range: np.ndarray) -> float:
        """
        Pérdida máxima posible
        """
        curve = self.payoff_curve(spot_range)
        return np.min(curve)


    def breakeven_points(self, spot_range: np.ndarray) -> List[float]:
        """
        Encuentra los puntos de equilibrio (donde P&L = 0)
        """
        curve = self.payoff_curve(spot_range)
        breakevens = []
        
        for i in range(len(curve) - 1):
            # Detectar cruces por cero
            if curve[i] * curve[i+1] < 0:
                # Interpolación lineal para encontrar el punto exacto
                x1, y1 = spot_range[i], curve[i]
                x2, y2 = spot_range[i+1], curve[i+1]
                x_zero = x1 - y1 * (x2 - x1) / (y2 - y1)
                breakevens.append(x_zero)
        
        return breakevens


    def analyze_at_price(self, spot_price: float) -> dict:
        """
        Análisis completo en un precio específico
        """
        pnl = self.pnl(spot_price)
        cost = self.total_cost()
        payoff = self.total_payoff(spot_price)
        
        return {
            'spot': spot_price,
            'payoff_intrinseco': payoff,
            'costo_primas': cost,
            'pnl_total': pnl,
            'roi_pct': (pnl / abs(cost) * 100) if cost != 0 else 0
        }


    def to_dict(self) -> dict:
        """Convierte a diccionario"""
        return {
            'name': self.name,
            'legs': [leg.to_dict() for leg in self.legs],
            'color': self.color,
            'total_cost': self.total_cost()
        }


def create_spot_range(center: float, width_pct: float = 0.30, points: int = 200) -> np.ndarray:
    """
    Crea un rango de precios spot para graficar
    
    Args:
        center: Precio central (spot actual o strike ATM)
        width_pct: Ancho del rango como % del centro
        points: Número de puntos
    
    Returns:
        Array de precios
    """
    min_price = center * (1 - width_pct)
    max_price = center * (1 + width_pct)
    return np.linspace(min_price, max_price, points)


def compare_strategies(strategies: List[Strategy], spot_prices: List[float]) -> pd.DataFrame:
    """
    Compara múltiples estrategias en diferentes escenarios de precio
    
    Returns:
        DataFrame con comparación
    """
    data = []
    
    for spot in spot_prices:
        row = {'Precio Spot': spot}
        for strat in strategies:
            analysis = strat.analyze_at_price(spot)
            row[f'{strat.name} - P&L'] = analysis['pnl_total']
            row[f'{strat.name} - ROI%'] = analysis['roi_pct']
        data.append(row)
    
    return pd.DataFrame(data)


def calculate_greeks_simple(leg: Leg, spot: float, days_to_expiry: int = 90) -> dict:
    """
    Cálculo simplificado de Greeks (aproximación)
    Para producción usar Black-Scholes completo
    """
    # Simplificación: Delta aproximado
    if leg.type == 'futuro':
        delta = 1.0 if leg.direction == 'buy' else -1.0
    elif leg.type == 'call':
        # Call ITM tiene delta ~1, OTM ~0
        moneyness = spot / leg.strike
        delta = min(max((moneyness - 1) * 2 + 0.5, 0), 1)
        if leg.direction == 'sell':
            delta = -delta
    elif leg.type == 'put':
        # Put ITM tiene delta ~-1, OTM ~0
        moneyness = leg.strike / spot
        delta = -min(max((moneyness - 1) * 2 + 0.5, 0), 1)
        if leg.direction == 'sell':
            delta = -delta
    else:
        delta = 0
    
    # Theta (decay diario aproximado)
    theta = -leg.prima / days_to_expiry if leg.type != 'futuro' else 0
    
    return {
        'delta': delta * leg.ratio,
        'theta': theta * leg.ratio,
        'gamma': 0,  # Simplificado
        'vega': 0    # Simplificado
    }
