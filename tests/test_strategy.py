# -*- coding: utf-8 -*-
"""
Script de test pour valider Strategy Engine et Kelly Criterion sans impacter la DB réelle.
"""
import logging
from unittest.mock import MagicMock
from strategy_engine import StrategyEngine, strategy_engine
from polymarket_executor import PolymarketExecutor
from db_manager import db_manager

# Config logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestStrategy")

def test_strategy_logic():
    print("\n🧪 === TEST STRATEGY ENGINE & KELLY ===\n")

    # 1. Mock DB Manager pour retourner des stats simulées
    # Scénario A: Trader gagnant (Win Rate 60%, Profit Factor 2.0)
    winner_stats = {
        'total_trades': 20,
        'wins': 12,
        'losses': 8,
        'win_rate': 60.0,
        'profit_factor': 2.0,
        'total_pnl': 500.0,
        'total_invested': 1000.0
    }

    # Scénario B: Trader perdant (Win Rate 30%, Profit Factor 0.5)
    loser_stats = {
        'total_trades': 20,
        'wins': 6,
        'losses': 14,
        'win_rate': 30.0,
        'profit_factor': 0.5,
        'total_pnl': -400.0,
        'total_invested': 1000.0
    }

    # Scénario C: Nouveau trader (Pas assez de data)
    new_stats = {
        'total_trades': 2,
        'wins': 1,
        'losses': 1,
        'win_rate': 50.0,
        'profit_factor': 1.0,
        'total_pnl': 0.0,
        'total_invested': 100.0
    }

    # Mocking
    original_get_perf = db_manager.get_trader_performance
    db_manager.get_trader_performance = MagicMock(side_effect=lambda addr: 
        winner_stats if addr == 'winner' else 
        (loser_stats if addr == 'loser' else new_stats)
    )

    try:
        # --- TEST CALCUL KELLY ---
        print("🔎 Test 1: Calcul Kelly Criterion")
        
        # Test Gagnant
        size_winner = strategy_engine.calculate_kelly_size('winner', base_capital=100.0)
        print(f"   Shape Winner (Base $100): ${size_winner} (Attendu: >= $100)")
        assert size_winner >= 100.0, f"Le trader gagnant devrait avoir une mise standard ou augmentée (Reçu: {size_winner})"

        # Test Perdant
        size_loser = strategy_engine.calculate_kelly_size('loser', base_capital=100.0)
        print(f"   Shape Loser (Base $100): ${size_loser} (Attendu: $0 ou très faible)")
        assert size_loser == 0.0, "Le trader perdant ne devrait rien miser"

        # Test Nouveau
        size_new = strategy_engine.calculate_kelly_size('new', base_capital=100.0)
        print(f"   Shape New (Base $100): ${size_new} (Attendu: $100)")
        assert size_new == 100.0, "Le nouveau trader devrait garder la mise de base"
        
        print("✅ Test 1 PASSÉ\n")


        # --- TEST EXECUTOR INTEGRATION ---
        print("🔎 Test 2: Intégration Executor")
        executor = PolymarketExecutor()
        
        # Signal avec Kelly Activé
        signal_kelly = {
            'wallet': 'winner',
            'capital_allocated': 100,
            'percent_per_trade': 10, # Ignoré si Kelly actif
            'use_kelly': True
        }
        
        size = executor.calculate_position_size(signal_kelly, bot_capital=1000)
        print(f"   Executor Kelly (Winner): ${size}")
        assert size >= 100, "L'executor n'a pas appliqué le logic Kelly (devrait être >= 100)"

        # Signal SANS Kelly
        signal_fixed = {
            'wallet': 'winner',
            'capital_allocated': 1000,
            'percent_per_trade': 10, # 10% de 1000 = 100
            'use_kelly': False
        }
        size_fixed = executor.calculate_position_size(signal_fixed, bot_capital=1000)
        print(f"   Executor Fixed: ${size_fixed}")
        assert size_fixed == 100.0, "L'executor aurait dû utiliser le sizing fixe"

        print("✅ Test 2 PASSÉ\n")
        print("🎉 TOUS LES TESTS SONT VALIDES")

    finally:
        # Restaurer DB Manager
        db_manager.get_trader_performance = original_get_perf

if __name__ == "__main__":
    test_strategy_logic()
