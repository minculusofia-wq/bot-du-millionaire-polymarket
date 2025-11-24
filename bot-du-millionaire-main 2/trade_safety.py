"""
Sécurité des trades - TP/SL, protection, gestion des risques
"""
from typing import Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import json

class RiskLevel(Enum):
    """Niveaux de risque"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TradeSafety:
    """Gestion de la sécurité des trades"""
    
    def __init__(self):
        self.active_trades = {}
        self.closed_trades = []
        self.risk_limits = {
            RiskLevel.LOW: {'max_loss_percent': 2, 'tp_ratio': 2},
            RiskLevel.MEDIUM: {'max_loss_percent': 5, 'tp_ratio': 1.5},
            RiskLevel.HIGH: {'max_loss_percent': 10, 'tp_ratio': 1}
        }
        
    def create_trade_with_safety(self, 
                                 trade_id: str,
                                 entry_price: float,
                                 amount: float,
                                 risk_level: RiskLevel = RiskLevel.MEDIUM,
                                 tp_percent: float = None,
                                 sl_percent: float = None) -> Dict:
        """
        Crée un trade avec TP/SL automatiques
        """
        if trade_id in self.active_trades:
            return {'error': f'Trade {trade_id} already exists'}
        
        # Déterminer TP/SL si non fournis
        if tp_percent is None or sl_percent is None:
            limits = self.risk_limits[risk_level]
            sl_percent = limits['max_loss_percent']
            tp_ratio = limits['tp_ratio']
            tp_percent = sl_percent * tp_ratio
        
        # Calculer les prix
        sl_price = entry_price * (1 - sl_percent / 100)
        tp_price = entry_price * (1 + tp_percent / 100)
        
        trade = {
            'id': trade_id,
            'entry_price': entry_price,
            'amount': amount,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'sl_percent': sl_percent,
            'tp_percent': tp_percent,
            'risk_level': risk_level.value,
            'status': 'OPEN',
            'entry_time': datetime.now().isoformat(),
            'current_price': entry_price,
            'pnl': 0,
            'pnl_percent': 0
        }
        
        self.active_trades[trade_id] = trade
        return trade
    
    def update_trade_price(self, trade_id: str, current_price: float) -> Optional[Dict]:
        """
        Met à jour le prix du trade et vérifie les sorties
        """
        if trade_id not in self.active_trades:
            return None
        
        trade = self.active_trades[trade_id]
        
        # Calculer PnL (évite division par zéro)
        pnl = (current_price - trade['entry_price']) * trade['amount']
        pnl_percent = ((current_price - trade['entry_price']) / trade['entry_price'] * 100) if trade['entry_price'] != 0 else 0
        
        trade['current_price'] = current_price
        trade['pnl'] = pnl
        trade['pnl_percent'] = pnl_percent
        
        # Vérifier les sorties
        exit_reason = self._check_exit_conditions(trade, current_price)
        if exit_reason:
            return self._close_trade(trade_id, current_price, exit_reason)
        
        return trade
    
    def _check_exit_conditions(self, trade: Dict, current_price: float) -> Optional[str]:
        """Vérifie si le trade doit sortir"""
        if trade['status'] != 'OPEN':
            return None
        
        # Vérifier TP
        if current_price >= trade['tp_price']:
            return 'TP_HIT'
        
        # Vérifier SL
        if current_price <= trade['sl_price']:
            return 'SL_HIT'
        
        return None
    
    def _close_trade(self, trade_id: str, exit_price: float, exit_reason: str) -> Dict:
        """Ferme un trade"""
        trade = self.active_trades[trade_id]
        
        trade['status'] = exit_reason
        trade['exit_price'] = exit_price
        trade['exit_time'] = datetime.now().isoformat()
        
        # Calculer PnL final (protégé contre division par zéro)
        final_pnl = (exit_price - trade['entry_price']) * trade['amount']
        final_pnl_percent = ((exit_price - trade['entry_price']) / trade['entry_price'] * 100) if trade['entry_price'] != 0 else 0
        
        trade['final_pnl'] = final_pnl
        trade['final_pnl_percent'] = final_pnl_percent
        
        # Déplacer vers closed_trades
        del self.active_trades[trade_id]
        self.closed_trades.append(trade)
        
        return trade
    
    def get_active_trades(self) -> Dict:
        """Retourne les trades actifs"""
        return self.active_trades
    
    def get_closed_trades(self, limit: int = 50) -> list:
        """Retourne les trades fermés"""
        return self.closed_trades[-limit:]
    
    def get_portfolio_risk(self) -> Dict:
        """Calcule le risque du portefeuille"""
        if not self.active_trades:
            return {
                'total_exposure': 0,
                'total_pnl': 0,
                'max_loss_potential': 0,
                'active_trades_count': 0,
                'risk_level': 'LOW'
            }
        
        total_pnl = sum(t['pnl'] for t in self.active_trades.values())
        total_exposure = sum(t['entry_price'] * t['amount'] for t in self.active_trades.values())
        
        # Calculer la perte potentielle si tous les SL sont touchés
        max_loss = sum(
            (t['entry_price'] - t['sl_price']) * t['amount'] 
            for t in self.active_trades.values()
        )
        
        # Déterminer le niveau de risque
        if max_loss < total_exposure * 0.02:
            risk_level = 'LOW'
        elif max_loss < total_exposure * 0.05:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'
        
        return {
            'total_exposure': round(total_exposure, 2),
            'total_pnl': round(total_pnl, 2),
            'max_loss_potential': round(max_loss, 2),
            'active_trades_count': len(self.active_trades),
            'risk_level': risk_level
        }
    
    def get_trade_stats(self) -> Dict:
        """Retourne les statistiques de trading"""
        all_trades = self.closed_trades
        if not all_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'average_pnl': 0,
                'total_pnl': 0
            }
        
        winning_trades = [t for t in all_trades if t.get('final_pnl', 0) > 0]
        losing_trades = [t for t in all_trades if t.get('final_pnl', 0) < 0]
        
        total_pnl = sum(t.get('final_pnl', 0) for t in all_trades)
        average_pnl = total_pnl / len(all_trades) if all_trades else 0
        win_rate = (len(winning_trades) / len(all_trades) * 100) if all_trades else 0
        
        return {
            'total_trades': len(all_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'average_pnl': round(average_pnl, 2),
            'total_pnl': round(total_pnl, 2)
        }
    
    def emergency_close_all(self, current_price: float) -> list:
        """Ferme tous les trades en urgence"""
        closed = []
        for trade_id in list(self.active_trades.keys()):
            trade = self.active_trades[trade_id]
            final_pnl = (current_price - trade['entry_price']) * trade['amount']
            
            trade['status'] = 'EMERGENCY_CLOSED'
            trade['exit_price'] = current_price
            trade['exit_time'] = datetime.now().isoformat()
            trade['final_pnl'] = final_pnl
            
            del self.active_trades[trade_id]
            self.closed_trades.append(trade)
            closed.append(trade_id)
        
        return closed

# Instance globale
trade_safety = TradeSafety()
