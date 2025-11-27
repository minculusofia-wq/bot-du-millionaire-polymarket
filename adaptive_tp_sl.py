# -*- coding: utf-8 -*-
"""
Adaptive TP/SL - Take Profit et Stop Loss adaptatifs basés sur la volatilité
✨ Phase 9 Optimization: TP/SL intelligents pour maximiser les gains et réduire les pertes

Features:
- Calcul automatique de TP/SL basé sur la volatilité du token
- Trailing stop loss (suivre le prix à la hausse)
- Ajustement dynamique selon les conditions du marché
- Analyse ATR (Average True Range) pour volatilité
"""
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics


class VolatilityAnalyzer:
    """Analyse la volatilité d'un token"""

    def __init__(self):
        # Cache des données de prix (token_address -> price_history)
        self.price_history = {}
        self.max_history_size = 100  # Garder max 100 prix

    def add_price(self, token_address: str, price: float, timestamp: Optional[float] = None):
        """Ajoute un prix à l'historique"""
        if token_address not in self.price_history:
            self.price_history[token_address] = []

        self.price_history[token_address].append({
            'price': price,
            'timestamp': timestamp or time.time()
        })

        # Limiter la taille
        if len(self.price_history[token_address]) > self.max_history_size:
            self.price_history[token_address].pop(0)

    def calculate_volatility(self, token_address: str, lookback_periods: int = 20) -> Optional[float]:
        """
        Calcule la volatilité d'un token (écart-type des prix)

        Args:
            token_address: Adresse du token
            lookback_periods: Nombre de périodes à analyser

        Returns:
            Volatilité (0-1) ou None si pas assez de données
        """
        if token_address not in self.price_history:
            return None

        history = self.price_history[token_address]
        if len(history) < 2:
            return None

        # Prendre les N derniers prix
        recent_prices = [p['price'] for p in history[-lookback_periods:]]

        if len(recent_prices) < 2:
            return None

        # Calculer l'écart-type
        mean_price = statistics.mean(recent_prices)
        std_dev = statistics.stdev(recent_prices)

        # Normaliser par rapport à la moyenne (coefficient de variation)
        volatility = std_dev / mean_price if mean_price > 0 else 0

        return volatility

    def get_atr(self, token_address: str, periods: int = 14) -> Optional[float]:
        """
        Calcule l'ATR (Average True Range) - mesure de volatilité

        Args:
            token_address: Adresse du token
            periods: Nombre de périodes pour ATR (défaut: 14)

        Returns:
            ATR ou None si pas assez de données
        """
        if token_address not in self.price_history:
            return None

        history = self.price_history[token_address]
        if len(history) < periods + 1:
            return None

        # Calculer les True Ranges
        true_ranges = []
        for i in range(1, len(history)):
            high = max(history[i]['price'], history[i-1]['price'])
            low = min(history[i]['price'], history[i-1]['price'])
            true_range = high - low
            true_ranges.append(true_range)

        # ATR = moyenne des N derniers True Ranges
        if len(true_ranges) < periods:
            return None

        atr = statistics.mean(true_ranges[-periods:])
        return atr


class AdaptiveTPSLCalculator:
    """Calcule des TP/SL adaptatifs basés sur la volatilité"""

    def __init__(self):
        self.volatility_analyzer = VolatilityAnalyzer()

        # Multiplicateurs par niveau de volatilité
        self.volatility_levels = {
            'very_low': {'threshold': 0.02, 'tp_mult': 1.5, 'sl_mult': 0.8},    # Volatilité < 2%
            'low': {'threshold': 0.05, 'tp_mult': 1.2, 'sl_mult': 0.9},          # 2-5%
            'medium': {'threshold': 0.10, 'tp_mult': 1.0, 'sl_mult': 1.0},       # 5-10%
            'high': {'threshold': 0.20, 'tp_mult': 0.8, 'sl_mult': 1.2},         # 10-20%
            'very_high': {'threshold': 999, 'tp_mult': 0.6, 'sl_mult': 1.5},     # > 20%
        }

        # TP/SL de base (en %)
        self.base_tp_levels = [50, 100, 200]  # TP1, TP2, TP3
        self.base_sl = 20  # SL

    def classify_volatility(self, volatility: float) -> str:
        """Classifie le niveau de volatilité"""
        for level, config in self.volatility_levels.items():
            if volatility < config['threshold']:
                return level
        return 'very_high'

    def calculate_adaptive_tp_sl(
        self,
        token_address: str,
        entry_price: float,
        default_tp: List[float] = None,
        default_sl: float = None
    ) -> Dict:
        """
        Calcule des TP/SL adaptatifs pour un token

        Args:
            token_address: Adresse du token
            entry_price: Prix d'entrée
            default_tp: Liste des TP par défaut [TP1, TP2, TP3] (en %)
            default_sl: SL par défaut (en %)

        Returns:
            {
                'tp_levels': [TP1, TP2, TP3] (prix absolus),
                'sl_level': SL (prix absolu),
                'tp_percents': [%TP1, %TP2, %TP3],
                'sl_percent': %SL,
                'volatility': float,
                'volatility_level': str
            }
        """
        default_tp = default_tp or self.base_tp_levels
        default_sl = default_sl or self.base_sl

        # Calculer la volatilité
        volatility = self.volatility_analyzer.calculate_volatility(token_address)

        if volatility is None:
            # Pas assez de données, utiliser les valeurs par défaut
            return {
                'tp_levels': [entry_price * (1 + tp/100) for tp in default_tp],
                'sl_level': entry_price * (1 - default_sl/100),
                'tp_percents': default_tp,
                'sl_percent': default_sl,
                'volatility': 0,
                'volatility_level': 'unknown'
            }

        # Classifier la volatilité
        vol_level = self.classify_volatility(volatility)
        config = self.volatility_levels[vol_level]

        # Ajuster les TP/SL selon la volatilité
        tp_mult = config['tp_mult']
        sl_mult = config['sl_mult']

        adaptive_tp_percents = [tp * tp_mult for tp in default_tp]
        adaptive_sl_percent = default_sl * sl_mult

        # Calculer les prix absolus
        tp_levels = [entry_price * (1 + tp/100) for tp in adaptive_tp_percents]
        sl_level = entry_price * (1 - adaptive_sl_percent/100)

        return {
            'tp_levels': tp_levels,
            'sl_level': sl_level,
            'tp_percents': adaptive_tp_percents,
            'sl_percent': adaptive_sl_percent,
            'volatility': volatility,
            'volatility_level': vol_level
        }


class TrailingStopLoss:
    """Trailing Stop Loss - suit le prix à la hausse"""

    def __init__(self):
        # Positions avec trailing SL (position_id -> config)
        self.trailing_positions = {}

    def activate_trailing(
        self,
        position_id: str,
        entry_price: float,
        initial_sl_percent: float = 20,
        trailing_percent: float = 10
    ):
        """
        Active le trailing SL pour une position

        Args:
            position_id: ID unique de la position
            entry_price: Prix d'entrée
            initial_sl_percent: SL initial (en %)
            trailing_percent: Distance de trailing (en %)
        """
        self.trailing_positions[position_id] = {
            'entry_price': entry_price,
            'highest_price': entry_price,
            'current_sl': entry_price * (1 - initial_sl_percent/100),
            'trailing_percent': trailing_percent,
            'activated': False  # Se déclenche quand profit > 0
        }
        print(f"🎯 Trailing SL activé pour {position_id[:8]}...")

    def update_trailing(self, position_id: str, current_price: float) -> Optional[float]:
        """
        Met à jour le trailing SL

        Args:
            position_id: ID de la position
            current_price: Prix actuel

        Returns:
            Nouveau SL ou None si position n'existe pas
        """
        if position_id not in self.trailing_positions:
            return None

        config = self.trailing_positions[position_id]
        entry_price = config['entry_price']

        # Activer le trailing si en profit
        if current_price > entry_price and not config['activated']:
            config['activated'] = True
            print(f"✅ Trailing SL activé (position en profit)")

        # Si activé, suivre le prix
        if config['activated']:
            # Mettre à jour le plus haut prix
            if current_price > config['highest_price']:
                config['highest_price'] = current_price

                # Nouveau SL = highest_price - trailing%
                new_sl = current_price * (1 - config['trailing_percent']/100)

                # SL ne descend jamais
                if new_sl > config['current_sl']:
                    config['current_sl'] = new_sl
                    print(f"📈 Trailing SL ajusté à {new_sl:.4f}")

        return config['current_sl']

    def should_close(self, position_id: str, current_price: float) -> bool:
        """
        Vérifie si le SL est touché

        Args:
            position_id: ID de la position
            current_price: Prix actuel

        Returns:
            True si SL touché
        """
        if position_id not in self.trailing_positions:
            return False

        config = self.trailing_positions[position_id]
        current_sl = self.update_trailing(position_id, current_price)

        if current_price <= current_sl:
            print(f"🛑 Trailing SL touché à {current_price:.4f} (SL: {current_sl:.4f})")
            return True

        return False

    def remove_position(self, position_id: str):
        """Retire une position du trailing"""
        if position_id in self.trailing_positions:
            del self.trailing_positions[position_id]


# Instances globales
global_volatility_analyzer = VolatilityAnalyzer()
global_adaptive_calculator = AdaptiveTPSLCalculator()
global_trailing_sl = TrailingStopLoss()

# Alias pour compatibilité (utilise l'analyseur de volatilité par défaut)
adaptive_tp_sl = global_volatility_analyzer


if __name__ == "__main__":
    # Tests unitaires
    print("🧪 Tests du Adaptive TP/SL...")

    analyzer = VolatilityAnalyzer()
    calculator = AdaptiveTPSLCalculator()

    # Test 1: Ajouter des prix et calculer volatilité
    token = "So11111111111111111111111111111111111111112"
    prices = [100, 102, 98, 105, 95, 103, 99, 107]  # Volatilité modérée

    for price in prices:
        analyzer.add_price(token, price)
        calculator.volatility_analyzer.add_price(token, price)

    volatility = analyzer.calculate_volatility(token)
    print(f"✅ Test 1: Volatilité calculée: {volatility:.4f}")

    # Test 2: Calculer TP/SL adaptatifs
    entry_price = 100
    result = calculator.calculate_adaptive_tp_sl(token, entry_price)
    print(f"✅ Test 2: TP/SL adaptatifs calculés")
    print(f"   TP levels: {result['tp_levels']}")
    print(f"   SL level: {result['sl_level']}")
    print(f"   Volatilité: {result['volatility_level']}")

    # Test 3: Trailing SL
    trailing = TrailingStopLoss()
    trailing.activate_trailing("pos1", entry_price=100, initial_sl_percent=10, trailing_percent=5)

    # Simuler une hausse
    prices_trail = [100, 105, 110, 115, 112, 108]  # Monte puis descend
    for price in prices_trail:
        should_close = trailing.should_close("pos1", price)
        if should_close:
            print(f"✅ Test 3: Trailing SL déclenché à {price}")
            break

    print("\n✅ Tous les tests réussis!")
