# -*- coding: utf-8 -*-
"""
Strategy Engine - Cerveau analytique du bot
Gère le scoring des traders et le sizing des positions (Kelly Criterion)
"""
import logging
from typing import Dict, Optional, Tuple
from db_manager import db_manager

logger = logging.getLogger("StrategyEngine")

class StrategyEngine:
    """
    Moteur de décision pour l'optimisation des trades.
    """
    
    def __init__(self):
        self.min_trades_for_scoring = 5
        logger.info("🧠 Strategy Engine initialisé")

    def calculate_trader_score(self, trader_address: str) -> Dict:
        """
        Calcule un score de qualité (0-100) pour un trader basé sur son historique.
        
        Critères:
        - Win Rate (40%)
        - Profit Factor (30%)
        - ROI Moyen (20%)
        - Activité (10%)
        """
        stats = db_manager.get_trader_performance(trader_address)
        
        if stats['total_trades'] < self.min_trades_for_scoring:
            return {
                'score': 50.0, # Score neutre par défaut
                'reason': 'Pas assez d\'historique',
                'stats': stats
            }

        # 1. Win Rate Score (0-40)
        # 50% WR = 20pts, 80% WR = 40pts
        wr_score = min(40, max(0, (stats['win_rate'] - 30) * 0.8))
        
        # 2. Profit Factor Score (0-30)
        # PF 1.0 = 10pts, PF 2.0 = 25pts, PF 3.0+ = 30pts
        # PF = (Gross Profit / Gross Loss)
        pf = stats['profit_factor']
        if pf < 1: pf_score = 0
        else: pf_score = min(30, (pf - 1) * 15)

        # 3. ROI Score (0-20)
        # ROI > 0 = points
        avg_roi = stats['total_pnl'] / (stats['total_invested'] + 1e-6) * 100
        roi_score = min(20, max(0, avg_roi * 2))

        # 4. Activity/Consistency (0-10)
        # Bonification pour nombre de trades
        activity_score = min(10, stats['total_trades'] / 5)

        total_score = wr_score + pf_score + roi_score + activity_score
        
        return {
            'score': round(total_score, 1),
            'win_rate': stats['win_rate'],
            'profit_factor': stats['profit_factor'],
            'stats': stats
        }

    def calculate_kelly_size(self, 
                           trader_address: str, 
                           base_capital: float, 
                           market_odds: float = 2.0) -> float:
        """
        Calcule la taille de position idéale selon le Kelly Criterion.
        
        Formula: f* = (bp - q) / b
        Utilise un "Half-Kelly" pour la sécurité.
        """
        stats = db_manager.get_trader_performance(trader_address)
        
        # Si pas assez de données, utiliser taille fixe par défaut
        if stats['total_trades'] < self.min_trades_for_scoring:
            return base_capital

        win_rate = stats['win_rate'] / 100.0
        
        # Sécurité: Si le trader est perdant (<50% WR sur cotes ~2.0), on réduit drastiquement
        if win_rate < 0.45:
            logger.warning(f"⚠️ Trader {trader_address[:6]} sous-performant (WR {win_rate*100:.1f}%), Kelly = 0")
            return 0.0

        # Paramètres Kelly
        p = win_rate
        q = 1 - p
        b = market_odds - 1 # Cotes nettes (ex: x2.0 => b=1)

        if b <= 0: return 0

        f_star = (b * p - q) / b
        
        # Half-Kelly pour réduire la volatilité (recommandé)
        safe_f = f_star * 0.5
        
        # Capping de sécurité (jamais plus de 20% du capital sur un trade)
        safe_f = min(0.20, max(0.0, safe_f))
        
        # Interprétation: "Base Capital" est le montant qu'on miserait pour un Kelly de 10% (safe_f=0.10)
        # Si Kelly dit 10% (0.10), on mise 100% du Base Capital (x1.0)
        # Si Kelly dit 5% (0.05), on mise 50% du Base Capital (x0.5)
        # Si Kelly dit 20% (0.20), on mise 200% du Base Capital (x2.0)
        multiplier = safe_f * 10.0
        
        adjusted_size = base_capital * multiplier
        
        logger.info(f"📐 Kelly Calc: p={p:.2f}, b={b:.2f} -> f*={f_star:.2f} -> safe_f={safe_f:.2f} -> Mult={multiplier:.2f} -> Size=${adjusted_size:.2f}")
        
        return round(adjusted_size, 2)

strategy_engine = StrategyEngine()
