"""
Monitoring & Statistics en temps réel
Suivi des performances, métriques, alertes internes
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
from collections import deque

class AlertLevel(Enum):
    """Niveaux d'alerte"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class PerformanceMonitor:
    """Monitore les performances en temps réel"""
    
    def __init__(self):
        self.alerts = deque(maxlen=100)  # Garder 100 alertes
        self.performance_metrics = {}
        self.hourly_stats = deque(maxlen=24)  # 24 heures
        self.daily_stats = deque(maxlen=30)   # 30 jours
        self.current_hour_start = datetime.now()
        self.current_day_start = datetime.now()
        
    def add_alert(self, level: AlertLevel, message: str, data: Dict = None) -> Dict:
        """Ajoute une alerte"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level.value,
            'message': message,
            'data': data or {}
        }
        self.alerts.append(alert)
        return alert
    
    def record_trade(self, trade_data: Dict, status: str, pnl: float = 0) -> None:
        """Enregistre une trade pour les statistiques"""
        if 'trade_count' not in self.performance_metrics:
            self.performance_metrics['trade_count'] = 0
            self.performance_metrics['total_pnl'] = 0
            self.performance_metrics['winning_trades'] = 0
            self.performance_metrics['losing_trades'] = 0
            self.performance_metrics['trades_this_hour'] = 0
        
        self.performance_metrics['trade_count'] += 1
        self.performance_metrics['total_pnl'] += pnl
        self.performance_metrics['trades_this_hour'] += 1
        
        if pnl > 0:
            self.performance_metrics['winning_trades'] += 1
        elif pnl < 0:
            self.performance_metrics['losing_trades'] += 1
        
        # Alerte si trop de trades perdants
        total_trades = self.performance_metrics['winning_trades'] + self.performance_metrics['losing_trades']
        if total_trades >= 5:
            win_rate = (self.performance_metrics['winning_trades'] / total_trades) * 100
            if win_rate < 30:
                self.add_alert(
                    AlertLevel.WARNING,
                    f"🚨 Win rate faible: {win_rate:.1f}% (< 30%)",
                    {'win_rate': win_rate, 'total_trades': total_trades}
                )
    
    def get_win_rate(self) -> float:
        """Calcule le win rate"""
        winning = self.performance_metrics.get('winning_trades', 0)
        losing = self.performance_metrics.get('losing_trades', 0)
        total = winning + losing
        
        if total == 0:
            return 0
        return (winning / total) * 100
    
    def get_average_pnl_per_trade(self) -> float:
        """Calcule le PnL moyen par trade"""
        count = self.performance_metrics.get('trade_count', 0)
        if count == 0:
            return 0
        
        total_pnl = self.performance_metrics.get('total_pnl', 0)
        return total_pnl / count
    
    def get_rpc_health(self, success_count: int, error_count: int) -> Dict:
        """Évalue la santé du RPC"""
        total = success_count + error_count
        if total == 0:
            return {'status': 'UNKNOWN', 'success_rate': 100, 'latency': 'N/A'}
        
        success_rate = (success_count / total) * 100
        
        if success_rate >= 95:
            status = 'HEALTHY'
        elif success_rate >= 80:
            status = 'DEGRADED'
        else:
            status = 'CRITICAL'
            self.add_alert(
                AlertLevel.CRITICAL,
                f"🔴 RPC Health Critical: {success_rate:.1f}% success rate",
                {'success_rate': success_rate, 'errors': error_count}
            )
        
        return {
            'status': status,
            'success_rate': round(success_rate, 2),
            'total_calls': total,
            'successes': success_count,
            'errors': error_count
        }
    
    def get_performance_summary(self) -> Dict:
        """Résumé des performances"""
        return {
            'total_trades': self.performance_metrics.get('trade_count', 0),
            'total_pnl': round(self.performance_metrics.get('total_pnl', 0), 2),
            'winning_trades': self.performance_metrics.get('winning_trades', 0),
            'losing_trades': self.performance_metrics.get('losing_trades', 0),
            'win_rate': round(self.get_win_rate(), 2),
            'avg_pnl_per_trade': round(self.get_average_pnl_per_trade(), 2),
            'trades_this_hour': self.performance_metrics.get('trades_this_hour', 0)
        }
    
    def get_alerts(self, limit: int = 50) -> List[Dict]:
        """Récupère les alertes récentes"""
        return list(self.alerts)[-limit:]
    
    def get_critical_alerts(self) -> List[Dict]:
        """Récupère seulement les alertes critiques"""
        return [a for a in self.alerts if a['level'] == AlertLevel.CRITICAL.value]
    
    def reset_hourly(self) -> None:
        """Réinitialise les stats horaires"""
        self.performance_metrics['trades_this_hour'] = 0
        self.current_hour_start = datetime.now()

class ExecutionMonitor:
    """Monitore l'exécution des trades"""
    
    def __init__(self):
        self.execution_times = deque(maxlen=100)
        self.dex_usage = {}  # Compteur par DEX
        self.slippage_stats = []
        
    def record_execution(self, dex: str, execution_time_ms: float, slippage_bps: int) -> None:
        """Enregistre l'exécution d'une trade"""
        self.execution_times.append(execution_time_ms)
        
        if dex not in self.dex_usage:
            self.dex_usage[dex] = 0
        self.dex_usage[dex] += 1
        
        self.slippage_stats.append({
            'dex': dex,
            'slippage_bps': slippage_bps,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_average_execution_time(self) -> float:
        """Temps moyen d'exécution"""
        if not self.execution_times:
            return 0
        return sum(self.execution_times) / len(self.execution_times)
    
    def get_dex_statistics(self) -> Dict:
        """Statistiques par DEX"""
        total = sum(self.dex_usage.values())
        if total == 0:
            return {}
        
        return {
            dex: {'count': count, 'percentage': round((count/total)*100, 2)}
            for dex, count in self.dex_usage.items()
        }
    
    def get_average_slippage(self) -> Dict:
        """Slippage moyen par DEX"""
        if not self.slippage_stats:
            return {}
        
        dex_slippages = {}
        for stat in self.slippage_stats:
            dex = stat['dex']
            if dex not in dex_slippages:
                dex_slippages[dex] = []
            dex_slippages[dex].append(stat['slippage_bps'])
        
        return {
            dex: round(sum(slippages) / len(slippages), 2)
            for dex, slippages in dex_slippages.items()
        }

class SystemMonitor:
    """Monitore la santé du système"""
    
    def __init__(self):
        self.rpc_success = 0
        self.rpc_errors = 0
        self.wallet_balance_history = deque(maxlen=100)
        self.portfolio_value_history = deque(maxlen=100)
        self.last_health_check = None
        
    def record_rpc_call(self, success: bool) -> None:
        """Enregistre un appel RPC"""
        if success:
            self.rpc_success += 1
        else:
            self.rpc_errors += 1
    
    def record_wallet_balance(self, balance: float) -> None:
        """Enregistre le solde du wallet"""
        self.wallet_balance_history.append({
            'timestamp': datetime.now().isoformat(),
            'balance': balance
        })
    
    def record_portfolio_value(self, value: float) -> None:
        """Enregistre la valeur du portefeuille"""
        self.portfolio_value_history.append({
            'timestamp': datetime.now().isoformat(),
            'value': value
        })
    
    def get_health_status(self) -> Dict:
        """État de santé du système"""
        performance = PerformanceMonitor()
        rpc_health = performance.get_rpc_health(self.rpc_success, self.rpc_errors)
        
        return {
            'rpc': rpc_health,
            'wallet_balance_latest': self.wallet_balance_history[-1] if self.wallet_balance_history else None,
            'portfolio_value_latest': self.portfolio_value_history[-1] if self.portfolio_value_history else None,
            'uptime_minutes': self._get_uptime(),
            'last_check': datetime.now().isoformat()
        }
    
    def _get_uptime(self) -> int:
        """Obtient le temps de fonctionnement en minutes"""
        if not self.wallet_balance_history:
            return 0
        first_time = datetime.fromisoformat(self.wallet_balance_history[0]['timestamp'])
        return int((datetime.now() - first_time).total_seconds() / 60)
    
    def get_balance_trend(self, hours: int = 24) -> List[Dict]:
        """Tendance du solde sur les N dernières heures"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            b for b in self.wallet_balance_history
            if datetime.fromisoformat(b['timestamp']) > cutoff_time
        ]
    
    def get_portfolio_trend(self, hours: int = 24) -> List[Dict]:
        """Tendance du portefeuille sur les N dernières heures"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            p for p in self.portfolio_value_history
            if datetime.fromisoformat(p['timestamp']) > cutoff_time
        ]

class MetricsCollector:
    """Collecteur central de métriques"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.execution_monitor = ExecutionMonitor()
        self.system_monitor = SystemMonitor()
    
    def get_all_metrics(self) -> Dict:
        """Récupère toutes les métriques"""
        return {
            'performance': self.performance_monitor.get_performance_summary(),
            'execution': {
                'avg_execution_time_ms': self.execution_monitor.get_average_execution_time(),
                'dex_statistics': self.execution_monitor.get_dex_statistics(),
                'avg_slippage': self.execution_monitor.get_average_slippage()
            },
            'system': self.system_monitor.get_health_status(),
            'alerts': {
                'total': len(list(self.performance_monitor.alerts)),
                'critical': len(self.performance_monitor.get_critical_alerts()),
                'recent': self.performance_monitor.get_alerts(10)
            }
        }

# Instance globale
metrics_collector = MetricsCollector()
