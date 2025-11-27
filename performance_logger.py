# -*- coding: utf-8 -*-
"""
Performance Logger - Logging détaillé des métriques de performance
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional

class PerformanceLogger:
    """Logger de performance avec export JSON"""
    
    def __init__(self, log_file: str = 'performance_metrics.jsonl'):
        self.log_file = log_file
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                pass
        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_latency_ms': 0
        }
        print(f"✅ Performance Logger initialisé")
    
    def _write_log(self, entry: Dict):
        """Écrit une entrée dans le fichier log"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            print(f"⚠️ Erreur écriture log: {e}")
    
    def log_trade_execution(self, trade_data: Dict):
        """Log l'exécution d'un trade"""
        self.stats['total_trades'] += 1
        if trade_data.get('success', False):
            self.stats['successful_trades'] += 1
        else:
            self.stats['failed_trades'] += 1
        
        latency = trade_data.get('latency_ms', 0)
        self.stats['total_latency_ms'] += latency
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'trade_execution',
            'trader': trade_data.get('trader'),
            'latency_ms': latency,
            'slippage_percent': trade_data.get('slippage_percent', 0),
            'success': trade_data.get('success', False)
        }
        self._write_log(entry)
    
    def log_error(self, error_data: Dict):
        """Log une erreur"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'error',
            'module': error_data.get('module'),
            'error_message': error_data.get('error_message')
        }
        self._write_log(entry)
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        avg_latency = 0
        if self.stats['successful_trades'] > 0:
            avg_latency = self.stats['total_latency_ms'] / self.stats['successful_trades']
        
        success_rate = 0
        if self.stats['total_trades'] > 0:
            success_rate = (self.stats['successful_trades'] / self.stats['total_trades']) * 100
        
        return {
            'total_trades': self.stats['total_trades'],
            'successful_trades': self.stats['successful_trades'],
            'success_rate_percent': round(success_rate, 2),
            'avg_latency_ms': round(avg_latency, 2)
        }

performance_logger = PerformanceLogger()
