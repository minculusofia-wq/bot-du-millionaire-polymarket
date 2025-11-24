"""
Validation des trades - Filtres de sécurité
Vérification avant exécution des transactions
"""
from typing import Dict, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging

class TradeValidationLevel(Enum):
    """Niveaux de validation"""
    STRICT = "strict"      # Maximum de vérifications
    NORMAL = "normal"      # Vérifications standard
    RELAXED = "relaxed"    # Vérifications minimales

class TradeValidator:
    """Valide les trades avant exécution"""
    
    def __init__(self, validation_level: TradeValidationLevel = TradeValidationLevel.NORMAL):
        self.validation_level = validation_level
        self.validation_history = []
        self.rejected_trades = []
        
        # Limites par défaut
        self.min_trade_amount_usd = 1.0
        self.max_trade_amount_usd = 10000.0
        self.max_slippage_bps = 500  # 5%
        self.max_trades_per_hour = 10
        self.max_concurrent_trades = 5
        
    def set_limits(self, 
                   min_usd: float = None,
                   max_usd: float = None,
                   max_slippage_bps: int = None,
                   max_trades_per_hour: int = None,
                   max_concurrent: int = None):
        """Configure les limites de sécurité"""
        if min_usd is not None:
            self.min_trade_amount_usd = min_usd
        if max_usd is not None:
            self.max_trade_amount_usd = max_usd
        if max_slippage_bps is not None:
            self.max_slippage_bps = max_slippage_bps
        if max_trades_per_hour is not None:
            self.max_trades_per_hour = max_trades_per_hour
        if max_concurrent is not None:
            self.max_concurrent_trades = max_concurrent
    
    def validate_trade(self, trade_data: Dict) -> Tuple[bool, str]:
        """
        Valide un trade complet
        Retourne (is_valid, reason)
        """
        trade_data['validation_timestamp'] = datetime.now().isoformat()
        
        # Vérifications basiques
        checks = [
            self._check_required_fields(trade_data),
            self._check_amount_limits(trade_data),
            self._check_slippage(trade_data),
            self._check_mint_addresses(trade_data),
            self._check_rate_limits(trade_data),
        ]
        
        if self.validation_level == TradeValidationLevel.STRICT:
            checks.append(self._check_capital_allocation(trade_data))
            checks.append(self._check_trader_performance(trade_data))
        
        for is_valid, reason in checks:
            if not is_valid:
                self.rejected_trades.append({
                    'trade': trade_data,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                })
                return False, reason
        
        # Trade validé
        self.validation_history.append({
            'trade': trade_data,
            'status': 'APPROVED',
            'timestamp': datetime.now().isoformat()
        })
        return True, "APPROVED"
    
    def _check_required_fields(self, trade_data: Dict) -> Tuple[bool, str]:
        """Vérifie les champs obligatoires"""
        required_fields = [
            'input_mint',
            'output_mint',
            'input_amount',
            'slippage_bps',
            'trader_address',
            'trade_amount_usd'
        ]
        
        for field in required_fields:
            if field not in trade_data:
                return False, f"❌ Champ obligatoire manquant: {field}"
        
        return True, ""
    
    def _check_amount_limits(self, trade_data: Dict) -> Tuple[bool, str]:
        """Vérifie les montants min/max"""
        amount_usd = float(trade_data.get('trade_amount_usd', 0))
        
        if amount_usd < self.min_trade_amount_usd:
            return False, f"❌ Montant trop petit: ${amount_usd} < ${self.min_trade_amount_usd}"
        
        if amount_usd > self.max_trade_amount_usd:
            return False, f"❌ Montant trop grand: ${amount_usd} > ${self.max_trade_amount_usd}"
        
        return True, ""
    
    def _check_slippage(self, trade_data: Dict) -> Tuple[bool, str]:
        """Vérifie le slippage"""
        slippage_bps = int(trade_data.get('slippage_bps', 0))
        
        if slippage_bps > self.max_slippage_bps:
            return False, f"❌ Slippage trop élevé: {slippage_bps} bps > {self.max_slippage_bps} bps"
        
        if slippage_bps < 0:
            return False, f"❌ Slippage invalide: {slippage_bps} bps"
        
        return True, ""
    
    def _check_mint_addresses(self, trade_data: Dict) -> Tuple[bool, str]:
        """Vérifie les addresses de tokens"""
        input_mint = str(trade_data.get('input_mint', ''))
        output_mint = str(trade_data.get('output_mint', ''))
        
        if input_mint == output_mint:
            return False, "❌ Input et output mint identiques"
        
        if len(input_mint) < 32 or len(output_mint) < 32:
            return False, "❌ Adresse de mint invalide"
        
        return True, ""
    
    def _check_rate_limits(self, trade_data: Dict) -> Tuple[bool, str]:
        """Vérifie la fréquence des trades"""
        # Compter les trades de cette heure
        now = datetime.now()
        trades_this_hour = sum(
            1 for t in self.validation_history
            if (now - datetime.fromisoformat(t['timestamp'])).total_seconds() < 3600
        )
        
        if trades_this_hour >= self.max_trades_per_hour:
            return False, f"❌ Limite horaire atteinte: {trades_this_hour}/{self.max_trades_per_hour}"
        
        return True, ""
    
    def _check_capital_allocation(self, trade_data: Dict) -> Tuple[bool, str]:
        """Vérifie l'allocation du capital (STRICT mode)"""
        capital_allocated = float(trade_data.get('trader_capital', 0))
        trade_amount = float(trade_data.get('trade_amount_usd', 0))
        
        if trade_amount > capital_allocated:
            return False, f"❌ Trade > capital: ${trade_amount} > ${capital_allocated}"
        
        # Max 30% du capital par trade
        if trade_amount > capital_allocated * 0.3:
            return False, f"❌ Trade trop grand par rapport au capital: {(trade_amount/capital_allocated)*100:.1f}% > 30%"
        
        return True, ""
    
    def _check_trader_performance(self, trade_data: Dict) -> Tuple[bool, str]:
        """Vérifie la performance du trader (STRICT mode)"""
        trader_win_rate = float(trade_data.get('trader_win_rate', 50))
        trader_pnl_percent = float(trade_data.get('trader_pnl_percent', 0))
        
        # Ne pas copier si win rate < 40%
        if trader_win_rate < 40:
            return False, f"❌ Win rate trop faible: {trader_win_rate}% < 40%"
        
        # Ne pas copier si PnL est très négatif
        if trader_pnl_percent < -50:
            return False, f"❌ PnL trop négatif: {trader_pnl_percent}% < -50%"
        
        return True, ""
    
    def get_validation_history(self, limit: int = 100) -> list:
        """Récupère l'historique de validation"""
        return self.validation_history[-limit:]
    
    def get_rejected_trades(self, limit: int = 100) -> list:
        """Récupère les trades rejetés"""
        return self.rejected_trades[-limit:]
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques de validation"""
        total_trades = len(self.validation_history) + len(self.rejected_trades)
        approved_trades = len(self.validation_history)
        rejected_trades = len(self.rejected_trades)
        
        approval_rate = (approved_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'approved': approved_trades,
            'rejected': rejected_trades,
            'approval_rate': round(approval_rate, 2),
            'validation_level': self.validation_level.value,
            'current_limits': {
                'min_trade_usd': self.min_trade_amount_usd,
                'max_trade_usd': self.max_trade_amount_usd,
                'max_slippage_bps': self.max_slippage_bps,
                'max_trades_per_hour': self.max_trades_per_hour,
                'max_concurrent': self.max_concurrent_trades
            }
        }

# Instance globale
trade_validator = TradeValidator(TradeValidationLevel.NORMAL)
