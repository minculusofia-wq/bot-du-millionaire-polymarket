# -*- coding: utf-8 -*-
"""
Risk Manager - Gestion avancée du risque avec circuit breakers
✨ Phase 9 Optimization: Protection maximale du capital

Features:
- Circuit breakers (arrêt auto si pertes excessives)
- Position sizing dynamique
- Diversification automatique
- Monitoring des drawdowns
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time


class CircuitBreaker:
    """Circuit breaker pour arrêter le bot en cas de pertes excessives"""

    def __init__(self):
        self.breakers = {
            'hourly_loss': {'threshold': -10, 'window': 3600, 'enabled': True},      # -10% en 1h
            'daily_loss': {'threshold': -20, 'window': 86400, 'enabled': True},      # -20% en 24h
            'consecutive_sl': {'threshold': 5, 'count': 0, 'enabled': True},         # 5 SL consécutifs
            'max_drawdown': {'threshold': -30, 'current': 0, 'enabled': True}        # -30% drawdown max
        }

        self.pnl_history = []  # [(timestamp, pnl)]
        self.last_trades = []  # [(timestamp, 'TP'/'SL')]
        self.is_open = False
        self.open_reason = None

    def check_pnl_loss(self, current_pnl: float, window_seconds: int, threshold_percent: float) -> bool:
        """Vérifie la perte sur une période donnée"""
        now = time.time()
        cutoff = now - window_seconds

        # Filtrer les PnL dans la fenêtre
        recent_pnl = [pnl for ts, pnl in self.pnl_history if ts >= cutoff]

        if len(recent_pnl) < 2:
            return False

        # Calculer la variation
        start_pnl = recent_pnl[0]
        variation_percent = ((current_pnl - start_pnl) / abs(start_pnl) * 100) if start_pnl != 0 else 0

        return variation_percent <= threshold_percent

    def update(self, current_pnl: float, last_trade_result: Optional[str] = None) -> bool:
        """
        Met à jour le circuit breaker

        Args:
            current_pnl: PnL actuel
            last_trade_result: 'TP' ou 'SL' si trade vient de se terminer

        Returns:
            True si circuit breaker déclenché
        """
        now = time.time()

        # Ajouter PnL à l'historique
        self.pnl_history.append((now, current_pnl))
        # Garder max 1000 entrées
        if len(self.pnl_history) > 1000:
            self.pnl_history.pop(0)

        # 1. Vérifier perte horaire
        if self.breakers['hourly_loss']['enabled']:
            if self.check_pnl_loss(current_pnl, 3600, -10):
                self.is_open = True
                self.open_reason = "Perte > 10% en 1 heure"
                return True

        # 2. Vérifier perte journalière
        if self.breakers['daily_loss']['enabled']:
            if self.check_pnl_loss(current_pnl, 86400, -20):
                self.is_open = True
                self.open_reason = "Perte > 20% en 24 heures"
                return True

        # 3. Vérifier SL consécutifs
        if last_trade_result == 'SL':
            self.last_trades.append((now, 'SL'))
            self.breakers['consecutive_sl']['count'] += 1

            if self.breakers['consecutive_sl']['count'] >= 5:
                self.is_open = True
                self.open_reason = "5 Stop Loss consécutifs"
                return True
        elif last_trade_result == 'TP':
            self.last_trades.append((now, 'TP'))
            self.breakers['consecutive_sl']['count'] = 0  # Reset

        # 4. Vérifier drawdown max
        self.breakers['max_drawdown']['current'] = min(0, current_pnl)
        if self.breakers['max_drawdown']['current'] <= -30:
            self.is_open = True
            self.open_reason = "Drawdown maximum atteint (-30%)"
            return True

        return False

    def reset(self):
        """Reset le circuit breaker"""
        self.is_open = False
        self.open_reason = None
        self.breakers['consecutive_sl']['count'] = 0
        print("✅ Circuit breaker réinitialisé")


class PositionSizer:
    """Calcule la taille optimale des positions"""

    def __init__(self, total_capital: float):
        self.total_capital = total_capital
        self.max_position_percent = 15  # Max 15% du capital par position
        self.max_trader_percent = 30     # Max 30% du capital par trader

    def calculate_position_size(
        self,
        trader_win_rate: float,
        market_volatility: float,
        current_drawdown: float
    ) -> float:
        """
        Calcule la taille de position recommandée

        Args:
            trader_win_rate: Win rate du trader (0-1)
            market_volatility: Volatilité du marché (0-1)
            current_drawdown: Drawdown actuel (%)

        Returns:
            Taille de position en % du capital
        """
        base_size = 10  # 10% de base

        # Ajuster selon win rate
        if trader_win_rate >= 0.7:
            multiplier = 1.5
        elif trader_win_rate >= 0.6:
            multiplier = 1.2
        elif trader_win_rate >= 0.5:
            multiplier = 1.0
        else:
            multiplier = 0.7

        # Réduire si volatilité élevée
        if market_volatility > 0.15:
            multiplier *= 0.7
        elif market_volatility > 0.10:
            multiplier *= 0.85

        # Réduire si en drawdown
        if current_drawdown < -10:
            multiplier *= 0.6
        elif current_drawdown < -5:
            multiplier *= 0.8

        size = base_size * multiplier
        return min(size, self.max_position_percent)


# Instances globales
global_circuit_breaker = CircuitBreaker()
global_position_sizer = PositionSizer(total_capital=1000)
