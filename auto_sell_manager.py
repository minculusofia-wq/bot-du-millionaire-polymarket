# -*- coding: utf-8 -*-
"""
Gestionnaire de vente automatique
- Détecte AUTOMATIQUEMENT les ventes du trader
- Vend AUTOMATIQUEMENT en respectant TP/SL
- Si TP/SL = 0, vend EXACTEMENT comme le trader
- Vente manuelle = bonus optionnel
- IDENTIQUE en MODE TEST et MODE REAL
"""

import json
from datetime import datetime
from typing import Dict, Optional, List
from db_manager import db_manager

class AutoSellManager:
    """Gère la vente automatique (principale) et manuelle (bonus)"""
    
    def __init__(self):
        self.open_positions = self._load_open_positions()
        self.auto_sell_config = self._load_auto_sell_config()
        
    def _load_open_positions(self) -> Dict:
        """Charge les positions ouvertes"""
        try:
            with open('open_positions.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_open_positions(self):
        """Sauvegarde les positions ouvertes"""
        with open('open_positions.json', 'w') as f:
            json.dump(self.open_positions, f, indent=2)
    
    def _load_auto_sell_config(self) -> Dict:
        """Charge la configuration de vente auto"""
        try:
            with open('auto_sell_config.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'tp_levels': [
                    {'percent_of_position': 33, 'profit_target': 10},
                    {'percent_of_position': 33, 'profit_target': 25},
                    {'percent_of_position': 34, 'profit_target': 50}
                ],
                'sl_level': {'percent_of_position': 100, 'loss_limit': 5}
            }
    
    def _save_auto_sell_config(self):
        """Sauvegarde la configuration"""
        with open('auto_sell_config.json', 'w') as f:
            json.dump(self.auto_sell_config, f, indent=2)
    
    def open_position(self, 
                     trader_name: str,
                     entry_price: float,
                     amount: float) -> Dict:
        """
        Ouvre une position (appelé lors du copie de l'achat du trader)
        AUTOMATIQUE - MODE TEST = MODE REAL
        """
        position_id = f"{trader_name}_{datetime.now().timestamp()}"
        
        # Récupérer la config TP/SL actuelle
        tp_config = self.auto_sell_config.get('tp_levels', [])
        sl_config = self.auto_sell_config.get('sl_level', {})
        
        # Calculer TP/SL moyen (pour tracking)
        avg_tp = sum(t.get('profit_target', 0) for t in tp_config) / len(tp_config) if tp_config else 0
        avg_sl = sl_config.get('loss_limit', 0)
        
        position = {
            'position_id': position_id,
            'trader_name': trader_name,
            'entry_price': entry_price,
            'amount': amount,
            'entry_time': datetime.now().isoformat(),
            'status': 'OPEN',
            'current_price': entry_price,
            'pnl': 0,
            'pnl_percent': 0,
            'tp_target': avg_tp,  # Pour info
            'sl_target': avg_sl,  # Pour info
            'tp_price': entry_price * (1 + avg_tp / 100) if avg_tp > 0 else None,
            'sl_price': entry_price * (1 - avg_sl / 100) if avg_sl > 0 else None,
            'sell_reason': None,
            'exit_time': None,
            'exit_price': None,
            'sell_type': None
        }
        
        self.open_positions[position_id] = position
        self._save_open_positions()
        
        return position
    
    def update_position_price(self, position_id: str, current_price: float) -> Optional[Dict]:
        """
        Met à jour le prix et vérifie les conditions de sortie (TP/SL)
        AUTOMATIQUE - appelé continuellement
        """
        if position_id not in self.open_positions:
            return None
        
        position = self.open_positions[position_id]
        
        if position['status'] != 'OPEN':
            return position
        
        # Calculer PnL (évite division par zéro)
        pnl = (current_price - position['entry_price']) * position['amount']
        pnl_percent = ((current_price - position['entry_price']) / position['entry_price'] * 100) if position['entry_price'] != 0 else 0
        
        position['current_price'] = current_price
        position['pnl'] = pnl
        position['pnl_percent'] = pnl_percent
        
        # Vérifier si TP/SL atteint (AUTOMATIQUE)
        exit_reason = self._check_tp_sl_conditions(position, current_price)
        
        if exit_reason:
            # VENTE AUTOMATIQUE
            self._close_position_auto(position_id, current_price, exit_reason)
            return self.open_positions.get(position_id)
        
        self._save_open_positions()
        return position
    
    def _check_tp_sl_conditions(self, position: Dict, current_price: float) -> Optional[str]:
        """
        Vérifie TP/SL pour fermeture automatique
        Si TP/SL = 0, pas de vérification (vente quand trader vend)
        """
        if position['status'] != 'OPEN':
            return None
        
        # Si TP n'est pas défini (TP/SL = 0), pas de vérification automatique
        if position['tp_price'] is None:
            return None
        
        # Vérifier TP
        if current_price >= position['tp_price']:
            return 'TP_HIT'
        
        # Vérifier SL
        if position['sl_price'] and current_price <= position['sl_price']:
            return 'SL_HIT'
        
        return None
    
    def detect_trader_sell_and_close(self, position_id: str, trader_sell_price: float) -> Dict:
        """
        Le TRADER a vendu → BOT VEND AUTOMATIQUEMENT à ce prix
        AUTOMATIQUE - MODE TEST = MODE REAL
        """
        if position_id not in self.open_positions:
            return {'error': f'Position {position_id} not found'}
        
        return self._close_position_auto(position_id, trader_sell_price, 'TRADER_SOLD')
    
    def _close_position_auto(self, 
                             position_id: str, 
                             exit_price: float,
                             reason: str) -> Dict:
        """
        Ferme une position AUTOMATIQUEMENT
        (appelée par TP/SL ou détection trader vend)
        """
        if position_id not in self.open_positions:
            return {'error': f'Position {position_id} not found'}
        
        position = self.open_positions[position_id]
        
        # Calculer PnL final (évite division par zéro)
        final_pnl = (exit_price - position['entry_price']) * position['amount']
        final_pnl_percent = ((exit_price - position['entry_price']) / position['entry_price'] * 100) if position['entry_price'] != 0 else 0
        
        # Mettre à jour la position
        position['status'] = 'CLOSED'
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now().isoformat()
        position['sell_reason'] = reason
        position['sell_type'] = 'AUTO'
        position['final_pnl'] = final_pnl
        position['final_pnl_percent'] = final_pnl_percent
        
        self._save_open_positions()
        
        # Log
        db_manager.execute(
            """
            INSERT INTO trade_history 
            (trader_name, entry_price, exit_price, amount, pnl, pnl_percent, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position['trader_name'],
                position['entry_price'],
                exit_price,
                position['amount'],
                final_pnl,
                final_pnl_percent,
                f"{reason}_AUTO",
                datetime.now().isoformat()
            )
        )
        
        return position
    
    def manual_sell(self, position_id: str, current_price: float) -> Dict:
        """
        Vente MANUELLE (bonus optionnel - utilisateur clique "Vendre")
        """
        if position_id not in self.open_positions:
            return {'error': f'Position {position_id} not found'}
        
        position = self.open_positions[position_id]
        
        if position['status'] != 'OPEN':
            return {'error': 'Position already closed'}
        
        # Calculer PnL final (évite division par zéro)
        final_pnl = (current_price - position['entry_price']) * position['amount']
        final_pnl_percent = ((current_price - position['entry_price']) / position['entry_price'] * 100) if position['entry_price'] != 0 else 0
        
        # Fermer la position
        position['status'] = 'CLOSED'
        position['exit_price'] = current_price
        position['exit_time'] = datetime.now().isoformat()
        position['sell_reason'] = 'MANUAL_SELL'
        position['sell_type'] = 'MANUAL'
        position['final_pnl'] = final_pnl
        position['final_pnl_percent'] = final_pnl_percent
        
        self._save_open_positions()
        
        # Log
        db_manager.execute(
            """
            INSERT INTO trade_history 
            (trader_name, entry_price, exit_price, amount, pnl, pnl_percent, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position['trader_name'],
                position['entry_price'],
                current_price,
                position['amount'],
                final_pnl,
                final_pnl_percent,
                'MANUAL_SELL',
                datetime.now().isoformat()
            )
        )
        
        return position
    
    def get_open_positions(self, trader_name: str = None) -> List[Dict]:
        """Récupère les positions ouvertes"""
        positions = []
        for pos_id, position in self.open_positions.items():
            if position['status'] == 'OPEN':
                if trader_name is None or position['trader_name'] == trader_name:
                    positions.append(position)
        return positions
    
    def get_closed_positions(self, trader_name: str = None) -> List[Dict]:
        """Récupère les positions fermées"""
        positions = []
        for pos_id, position in self.open_positions.items():
            if position['status'] == 'CLOSED':
                if trader_name is None or position['trader_name'] == trader_name:
                    positions.append(position)
        return positions
    
    def get_position_summary(self) -> Dict:
        """Résumé de toutes les positions"""
        open_positions = self.get_open_positions()
        closed_positions = self.get_closed_positions()
        
        total_open_pnl = sum(p['pnl'] for p in open_positions)
        total_closed_pnl = sum(p.get('final_pnl', 0) for p in closed_positions)
        total_pnl = total_open_pnl + total_closed_pnl
        
        return {
            'open_positions_count': len(open_positions),
            'closed_positions_count': len(closed_positions),
            'total_open_pnl': total_open_pnl,
            'total_closed_pnl': total_closed_pnl,
            'total_pnl': total_pnl,
            'open_positions': open_positions,
            'closed_positions': closed_positions[-10:]
        }
    
    def update_tp_sl_config(self, tp_levels: List[Dict], sl_level: Dict) -> Dict:
        """
        Met à jour la configuration TP/SL
        Appliqué à TOUTES les futures positions
        Si TP/SL = 0, bot vend exactement comme le trader
        """
        self.auto_sell_config['tp_levels'] = tp_levels
        self.auto_sell_config['sl_level'] = sl_level
        self._save_auto_sell_config()
        return self.auto_sell_config
    
    def get_auto_sell_config(self) -> Dict:
        """Récupère la config actuelle"""
        return self.auto_sell_config
    
    def get_trader_pnl(self, trader_name: str) -> Dict:
        """Calcule le PnL total d'un trader (positions ouvertes + fermées)"""
        open_positions = self.get_open_positions(trader_name)
        closed_positions = self.get_closed_positions(trader_name)
        
        total_open_pnl = sum(p['pnl'] for p in open_positions)
        total_closed_pnl = sum(p.get('final_pnl', 0) for p in closed_positions)
        total_pnl = total_open_pnl + total_closed_pnl
        
        # Calculer le capital total investi
        total_invested = sum(p['entry_price'] * p['amount'] for p in open_positions + closed_positions)
        
        pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'pnl': round(total_pnl, 2),
            'pnl_percent': round(pnl_percent, 2),
            'open_pnl': round(total_open_pnl, 2),
            'closed_pnl': round(total_closed_pnl, 2),
            'open_count': len(open_positions),
            'closed_count': len(closed_positions),
            'total_invested': round(total_invested, 2)
        }
    
    def update_all_position_prices(self, token_prices: Dict[str, float]) -> None:
        """Met à jour les prix de TOUTES les positions ouvertes"""
        for position_id, position in self.open_positions.items():
            if position['status'] == 'OPEN':
                # Chercher le token mint dans les données disponibles
                # En mode TEST, on simule les prix avec une variation réaliste
                token_key = f"token_{position_id}"
                
                # Si prix disponible, utiliser; sinon appliquer variation simulée
                if token_key in token_prices:
                    current_price = token_prices[token_key]
                else:
                    # Simulation de mouvement de prix réaliste (+/- 2% par update)
                    import random
                    variation = random.uniform(0.98, 1.02)  # +/- 2%
                    current_price = position['current_price'] * variation
                
                self.update_position_price(position_id, current_price)

# Instance globale
auto_sell_manager = AutoSellManager()
