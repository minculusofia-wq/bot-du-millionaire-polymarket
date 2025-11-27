# -*- coding: utf-8 -*-
"""
Engine de Backtesting
Teste les paramètres TP/SL sur l'historique des traders
"""
from typing import Dict, List, Optional
from datetime import datetime
from db_manager import db_manager

class BacktestingEngine:
    """Simule les trades passés avec différents paramètres"""
    
    def __init__(self):
        self.backtest_results = []
        
    def run_backtest(self, trader_address: str, trades_history: List[Dict], 
                     tp_percent: float, sl_percent: float) -> Dict:
        """Lance un backtest sur l'historique des trades"""
        if not trades_history:
            return {'error': 'No trades to backtest'}
        
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        total_pnl = 0
        
        for trade in trades_history:
            if trade.get('status') != 'CLOSED' and trade.get('status') != 'TP_HIT' and trade.get('status') != 'SL_HIT':
                continue
                
            entry_price = trade.get('entry_price_usd', 0)
            exit_price = trade.get('exit_price_usd', 0)
            
            if entry_price == 0:
                continue
            
            # Calculer les prix avec TP/SL
            tp_price = entry_price * (1 + tp_percent / 100)
            sl_price = entry_price * (1 - sl_percent / 100)
            
            # Simuler l'exit
            if exit_price >= tp_price:
                simulated_exit = tp_price
            elif exit_price <= sl_price:
                simulated_exit = sl_price
            else:
                simulated_exit = exit_price
            
            trade_pnl = simulated_exit - entry_price
            amount = trade.get('output_amount', 1)
            
            total_trades += 1
            total_pnl += trade_pnl * amount
            
            if trade_pnl > 0:
                winning_trades += 1
            else:
                losing_trades += 1
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        # Calculer le PnL % sur le capital initial moyen (évite division par zéro)
        capital_per_trade = sum(t.get('input_amount', 1) for t in trades_history if t.get('entry_price_usd', 0) > 0)
        total_pnl_percent = (total_pnl / capital_per_trade * 100) if capital_per_trade > 0 else 0
        
        result = {
            'strategy_id': f"{trader_address}_{tp_percent}_{sl_percent}_{datetime.now().isoformat()}",
            'trader_address': trader_address,
            'tp_percent': tp_percent,
            'sl_percent': sl_percent,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_percent': round(total_pnl_percent, 2)
        }
        
        # Sauvegarder le résultat
        db_manager.save_backtest_result(result)
        self.backtest_results.append(result)
        
        return result
    
    def get_best_parameters(self, trader_address: str) -> Optional[Dict]:
        """Récupère les meilleurs paramètres TP/SL"""
        results = db_manager.get_backtest_results(trader_address)
        
        if not results:
            return None
        
        # Trier par win_rate descendant
        best = max(results, key=lambda x: x.get('win_rate', 0))
        return best
    
    def run_multiple_backtests(self, trader_address: str, trades_history: List[Dict]) -> List[Dict]:
        """Lance plusieurs backtests avec différents paramètres"""
        results = []
        
        # Tester différentes combinaisons TP/SL
        tp_values = [5, 10, 15, 20, 25, 50]
        sl_values = [2, 3, 5, 7, 10]
        
        for tp in tp_values:
            for sl in sl_values:
                result = self.run_backtest(trader_address, trades_history, tp, sl)
                if 'error' not in result:
                    results.append(result)
        
        return results

backtesting_engine = BacktestingEngine()
