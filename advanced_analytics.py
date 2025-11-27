# -*- coding: utf-8 -*-
"""
Advanced Analytics - Métriques avancées pour le bot de trading
Calcule les performances, ratios et statistiques détaillées
"""
from typing import Dict, List, Optional
from datetime import datetime
from db_manager import db_manager


class AdvancedAnalytics:
    """Calcule les métriques avancées de trading"""

    def __init__(self):
        self.trades = []

    def add_trade(self, trader: str, entry: float, exit: float, profit: float):
        """Ajoute un trade à l'historique"""
        self.trades.append({
            'trader': trader,
            'entry': entry,
            'exit': exit,
            'profit': profit,
            'timestamp': datetime.now()
        })

    def calculate_win_rate(self, trader_name: str = None) -> float:
        """
        Calcule le win rate réel depuis la base de données

        Args:
            trader_name: Nom du trader (optionnel, None = tous)

        Returns:
            Win rate en pourcentage (0-100)
        """
        trades = db_manager.get_closed_trades(trader_name)
        if not trades:
            return 0.0

        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        total_trades = len(trades)

        return (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0

    def calculate_profit_factor(self, trader_name: str = None) -> float:
        """
        Calcule le Profit Factor (Total Gains / Total Pertes)

        Args:
            trader_name: Nom du trader (optionnel)

        Returns:
            Profit Factor (> 1 = profitable)
        """
        trades = db_manager.get_closed_trades(trader_name)
        if not trades:
            return 0.0

        gains = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        losses = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))

        return gains / losses if losses > 0 else (gains if gains > 0 else 0.0)

    def calculate_max_drawdown(self, trader_name: str = None) -> float:
        """
        Calcule le drawdown maximum depuis le pic

        Args:
            trader_name: Nom du trader (optionnel)

        Returns:
            Max Drawdown en pourcentage
        """
        trades = db_manager.get_closed_trades(trader_name)
        if not trades:
            return 0.0

        # Calculer la courbe d'équité (cumulative PnL)
        equity = []
        cumulative = 0
        for trade in trades:
            cumulative += trade.get('pnl', 0)
            equity.append(cumulative)

        if not equity or len(equity) == 0:
            return 0.0

        # Calculer le drawdown max
        peak = equity[0]
        max_dd = 0
        for value in equity:
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return round(max_dd, 2)

    def calculate_sharpe_ratio(self, trader_name: str = None, risk_free_rate: float = 0.0) -> float:
        """
        Calcule le Sharpe Ratio (rendement ajusté au risque)

        Sharpe Ratio = (Rendement moyen - Taux sans risque) / Écart-type des rendements

        Args:
            trader_name: Nom du trader (optionnel)
            risk_free_rate: Taux sans risque (défaut: 0)

        Returns:
            Sharpe Ratio (> 1 = bon, > 2 = très bon, > 3 = excellent)
        """
        trades = db_manager.get_closed_trades(trader_name)
        if len(trades) < 2:
            return 0.0

        returns = [t.get('pnl', 0) for t in trades]
        avg_return = sum(returns) / len(returns)

        # Calculer l'écart-type
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        sharpe = (avg_return - risk_free_rate) / std_dev

        return round(sharpe, 2)

    def get_avg_trade_duration(self, trader_name: str = None) -> float:
        """
        Calcule la durée moyenne des positions

        Args:
            trader_name: Nom du trader (optionnel)

        Returns:
            Durée moyenne en heures
        """
        trades = db_manager.get_closed_trades(trader_name)
        if not trades:
            return 0.0

        durations = []
        for trade in trades:
            try:
                opened_at = datetime.fromisoformat(trade.get('opened_at', ''))
                closed_at = datetime.fromisoformat(trade.get('closed_at', ''))
                duration = (closed_at - opened_at).total_seconds() / 3600  # en heures
                durations.append(duration)
            except:
                continue

        return round(sum(durations) / len(durations), 2) if durations else 0.0

    def get_total_pnl(self, trader_name: str = None) -> float:
        """
        Calcule le PnL total

        Args:
            trader_name: Nom du trader (optionnel)

        Returns:
            PnL total
        """
        trades = db_manager.get_closed_trades(trader_name)
        if not trades:
            return 0.0

        return round(sum(t.get('pnl', 0) for t in trades), 2)

    def get_comprehensive_metrics(self, trader_name: str = None) -> Dict:
        """
        Retourne toutes les métriques dans un seul dictionnaire

        Args:
            trader_name: Nom du trader (optionnel)

        Returns:
            Dictionnaire avec toutes les métriques
        """
        trades = db_manager.get_closed_trades(trader_name)

        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)

        return {
            'win_rate': self.calculate_win_rate(trader_name),
            'profit_factor': self.calculate_profit_factor(trader_name),
            'max_drawdown': self.calculate_max_drawdown(trader_name),
            'sharpe_ratio': self.calculate_sharpe_ratio(trader_name),
            'avg_trade_duration': self.get_avg_trade_duration(trader_name),
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_pnl': self.get_total_pnl(trader_name),
            'timestamp': datetime.now().isoformat()
        }

    def get_metrics(self) -> Dict:
        """
        Retourne les métriques pour tous les traders

        Returns:
            Métriques globales
        """
        return self.get_comprehensive_metrics(trader_name=None)


# Instance globale
analytics = AdvancedAnalytics()
