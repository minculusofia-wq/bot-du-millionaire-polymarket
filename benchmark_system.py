# -*- coding: utf-8 -*-
"""
Système de Benchmark
Compare les performances du bot vs chaque trader
"""
from typing import Dict, List, Optional
from datetime import datetime
from db_manager import db_manager

class BenchmarkSystem:
    """Compare bot vs traders"""
    
    def __init__(self):
        self.benchmarks = []
        
    def calculate_benchmark(self, bot_performance: Dict, traders_performances: List[Dict]) -> Dict:
        """Calcule le benchmark bot vs traders"""
        bot_pnl = bot_performance.get('pnl', 0)
        bot_win_rate = bot_performance.get('win_rate', 0)
        
        benchmark = {
            'bot_pnl': bot_pnl,
            'bot_win_rate': bot_win_rate,
            'traders_compared': [],
            'best_trader': None,
            'bot_rank': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        all_pnl = [bot_pnl]
        
        for trader in traders_performances:
            trader_pnl = trader.get('pnl', 0)
            trader_win_rate = trader.get('win_rate', 0)
            
            comparison = {
                'trader_address': trader.get('address', ''),
                'trader_name': trader.get('name', ''),
                'trader_pnl': trader_pnl,
                'trader_win_rate': trader_win_rate,
                'pnl_diff': bot_pnl - trader_pnl,
                'win_rate_diff': bot_win_rate - trader_win_rate,
                'bot_better': bot_pnl > trader_pnl
            }
            
            benchmark['traders_compared'].append(comparison)
            all_pnl.append(trader_pnl)
            
            # Sauvegarder dans la DB
            db_manager.save_benchmark({
                'bot_pnl': bot_pnl,
                'bot_win_rate': bot_win_rate,
                'trader_address': trader.get('address', ''),
                'trader_name': trader.get('name', ''),
                'trader_pnl': trader_pnl,
                'trader_win_rate': trader_win_rate
            })
        
        # Calculer le classement du bot
        sorted_pnl = sorted(all_pnl, reverse=True)
        benchmark['bot_rank'] = sorted_pnl.index(bot_pnl) + 1
        
        # Trader avec le meilleur PnL
        if benchmark['traders_compared']:
            best_trader = max(benchmark['traders_compared'], key=lambda x: x['trader_pnl'])
            benchmark['best_trader'] = best_trader
        
        self.benchmarks.append(benchmark)
        return benchmark
    
    def get_benchmark_summary(self) -> Dict:
        """Résumé du benchmark"""
        if not self.benchmarks:
            return {'error': 'No benchmarks available'}
        
        latest = self.benchmarks[-1]
        total_traders = len(latest['traders_compared'])
        
        traders_better = sum(1 for t in latest['traders_compared'] if not t['bot_better'])
        traders_worse = total_traders - traders_better
        
        return {
            'timestamp': latest['timestamp'],
            'bot_pnl': latest['bot_pnl'],
            'bot_win_rate': latest['bot_win_rate'],
            'bot_rank': latest['bot_rank'],
            'total_traders_compared': total_traders,
            'traders_outperforming_bot': traders_better,
            'traders_bot_outperforms': traders_worse,
            'best_trader': latest['best_trader']
        }
    
    def get_ranking(self) -> List[Dict]:
        """Retourne le classement complet"""
        if not self.benchmarks:
            return []
        
        latest = self.benchmarks[-1]
        ranking = [{'rank': 1, 'name': 'BOT', 'pnl': latest['bot_pnl'], 'win_rate': latest['bot_win_rate']}]
        
        sorted_traders = sorted(latest['traders_compared'], key=lambda x: x['trader_pnl'], reverse=True)
        
        for i, trader in enumerate(sorted_traders, 2):
            ranking.append({
                'rank': i,
                'name': trader['trader_name'],
                'pnl': trader['trader_pnl'],
                'win_rate': trader['trader_win_rate']
            })
        
        return ranking

benchmark_system = BenchmarkSystem()
