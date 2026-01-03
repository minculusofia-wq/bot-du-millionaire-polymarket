# -*- coding: utf-8 -*-
"""
Moteur d'exécution Polymarket
Gère le placement des ordres sur le CLOB en réponse aux signaux de copy trading.
"""
import os
import logging
from typing import Dict, Optional
from datetime import datetime
from polymarket_client import polymarket_client # UPDATED IMPORT
from db_manager import db_manager
from strategy_engine import strategy_engine # ✨ Import Strategy Engine
from position_lock_manager import position_lock, PositionLockError # 🔒 Anti-double vente

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolymarketExecutor")

class PolymarketExecutor:
    def __init__(self, backend=None, socketio=None):
        self.backend = backend
        self.socketio = socketio # ✨ WebSocket instance
        # Valeurs fallback (.env)
        self.env_max_position = float(os.getenv("MAX_POSITION_USD", "100"))
        self.env_min_position = float(os.getenv("MIN_POSITION_USD", "5"))
        self.executed_trades = {}  # Historique des trades exécutés
        self.backend_ref = backend # Alias
        
        logger.info("🚀 Executeur Polymarket initialisé en mode RÉEL")

    def set_wallet(self, private_key: str):
        """Configure le wallet sur le client sous-jacent"""
        polymarket_client.set_wallet(private_key)

    def calculate_position_size(self, signal: Dict, bot_capital: float, price: float = None) -> float:
        """
        Calcule la taille de position.
        """
        trader_address = signal.get('wallet', '')
        
        # 0. Vérifier si Kelly Criterion est activé pour ce trader
        if signal.get('use_kelly', False):
            logger.info(f"🧠 Kelly Criterion ACTIF pour {trader_address[:6]}...")
            
            # Récupérer capital alloué (ou global par défaut)
            wallet_capital = float(signal.get('capital_allocated', 0))
            if wallet_capital <= 0:
                wallet_capital = self.env_max_position # Fallback
                
            # Utiliser le prix fourni ou essayer d'en obtenir un
            if not price:
                asset_id = signal.get('asset_id', '')
                if asset_id:
                    price = self.get_market_price(asset_id, 'BUY')
            
            # Calculer les cotes réelles (odds)
            # odds = 1 / price (ex: $0.50 => odds 2.0)
            market_odds = (1.0 / price) if (price and price > 0) else 2.0
            
            # Calculer taille via Strategy Engine
            kelly_size = strategy_engine.calculate_kelly_size(
                trader_address=trader_address,
                base_capital=wallet_capital,
                market_odds=market_odds
            )
            return kelly_size

        # 1. Config Spécifique Wallet (Classique)
        wallet_capital = float(signal.get('capital_allocated', 0))
        wallet_percent = float(signal.get('percent_per_trade', 0))

        if wallet_capital > 0 and wallet_percent > 0:
            target_size = wallet_capital * (wallet_percent / 100.0)
            logger.info(f"💡 Calcul taille spécifique: ${wallet_capital} * {wallet_percent}% = ${target_size}")
            return round(target_size, 2)

        # 2. Mode Global (Fallback)
        max_pos = self.env_max_position
        min_pos = self.env_min_position
        copy_pct = 100
        
        if self.backend:
            pm_config = self.backend.data.get('polymarket', {})
            conf_max = float(pm_config.get('max_position_usd', 0))
            conf_min = float(pm_config.get('min_position_usd', 0))
            if conf_max > 0: max_pos = conf_max
            if conf_min > 0: min_pos = conf_min
            copy_pct = int(pm_config.get('copy_percentage', 100))

        # Scaling sur trade origine
        whale_amount = float(signal.get('amount', 0))
        if whale_amount > 0:
             target_size = whale_amount * (copy_pct / 100.0)
        else:
             target_size = max_pos
             
        # Capping Global
        position_size = min(target_size, max_pos)
        position_size = max(min_pos, position_size)
        
        return round(position_size, 2)

    def get_market_price(self, token_id: str, side: str) -> Optional[float]:
        """
        Récupère le prix actuel du marché pour un token donné.
        """
        if not polymarket_client.authenticated:
             # Try anyway, maybe read-only mode works for book
             pass
            
        try:
            order_book = polymarket_client.get_order_book(token_id)
            if not order_book:
                return None
                
            if side == 'BUY':
                # Pour acheter, on prend le meilleur ask (offre de vente)
                asks = order_book.get('asks', [])
                if asks:
                    return float(asks[0].get('price', 0))
            else:
                # Pour vendre, on prend le meilleur bid (offre d'achat)
                bids = order_book.get('bids', [])
                if bids:
                    return float(bids[0].get('price', 0))
            return None
        except Exception as e:
            logger.error(f"❌ Erreur récupération prix: {e}")
            return None

    def execute_copy_trade(self, signal: Dict, bot_capital: float = 1000.0) -> Dict:
        """
        Exécute un trade de copie basé sur un signal détecté.
        Version 2.0: Enregistre source_wallet et SL/TP individuels + Validation
        """
        try:
            signal_type = signal.get('type', '')
            asset_id = signal.get('asset_id', '')
            source_wallet = signal.get('wallet', '') or signal.get('source_wallet', 'UNKNOWN')
            market_info = signal.get('market', {})
            market_slug = market_info.get('slug', 'unknown') if isinstance(market_info, dict) else 'unknown'
            outcome = signal.get('outcome', '')
            
            if not asset_id:
                return {'status': 'error', 'message': 'Asset ID manquant'}

            # ✨ NOUVEAU: Validation du trade avant exécution
            from trade_validator import TradeValidator
            from db_manager import db_manager
            
            validator = TradeValidator(self.backend.data.get('polymarket', {}))
            current_positions = db_manager.get_bot_positions()
            
            # Récupérer le prix actuel
            side = 'BUY' if signal_type == 'BUY' else 'SELL'
            price = self.get_market_price(asset_id, side)
            
            if not price or price <= 0:
                logger.error(f"❌ Prix non disponible pour {asset_id}. Annulation du trade.")
                return {'status': 'error', 'message': 'Prix non disponible'}

            # Calculer la taille de position pour la validation
            position_size = self.calculate_position_size(signal, bot_capital, price=price)
            
            # Ajouter value_usd au signal pour la validation
            signal_with_value = {**signal, 'value_usd': position_size}
            
            # Valider le trade
            is_valid, reason = validator.validate(signal_with_value, current_positions)
            
            if not is_valid:
                logger.warning(f"❌ Trade rejeté par validation: {reason}")
                return {
                    'status': 'rejected',
                    'reason': reason,
                    'signal': signal_type,
                    'asset_id': asset_id
                }
            
            logger.info(f"✅ Trade validé: {reason}")
            
            # Récupérer le prix actuel
            side = 'BUY' if signal_type == 'BUY' else 'SELL'
            price = self.get_market_price(asset_id, side)
            
            if not price or price <= 0:
                logger.error(f"❌ Prix non disponible pour {asset_id}. Annulation du trade.")
                return {'status': 'error', 'message': 'Prix non disponible'}

            # Calculer la quantité de shares
            shares = position_size / price if price > 0 else 0

            # Créer le résumé du trade
            trade_summary = {
                'timestamp': datetime.now().isoformat(),
                'signal_type': signal_type,
                'asset_id': asset_id,
                'market_slug': market_slug,
                'price': price,
                'shares': round(shares, 2),
                'value_usd': position_size,
                'status': 'pending'
            }

            # Mode réel - Placer l'ordre via le CLIENT UNIFIÉ
            result = polymarket_client.place_order(
                token_id=asset_id,
                side=side,
                price=price,
                size=shares,
                order_type='LIMIT' # Standard
            )
            
            if result.get('status') == 'success':
                trade_summary['status'] = 'executed'
                trade_summary['order_id'] = result.get('orderID', 'unknown')
                logger.info(f"✅ Ordre exécuté: {signal_type} {shares:.2f} shares @ ${price:.4f}")
                
                # ✅ Sauvegarder dans la DB
                db_manager.save_polymarket_trade({
                    'order_id': trade_summary['order_id'],
                    'timestamp': trade_summary['timestamp'],
                    'market_slug': market_slug,
                    'token_id': asset_id,
                    'side': side,
                    'price': price,
                    'size': shares,
                    'value_usd': position_size,
                    'status': 'EXECUTED',
                    'signal_type': signal_type,
                    'tx_hash': result.get('result', {}).get('transactionHash', '')
                })
                
                # ✅ Récupérer la config SL/TP du trader
                sl_percent = None
                tp_percent = None
                use_trailing = False
                
                if self.backend:
                    tracked_wallets = self.backend.data.get('polymarket', {}).get('tracked_wallets', [])
                    wallet_config = next((w for w in tracked_wallets if w.get('address') == source_wallet), None)
                    if wallet_config:
                        sl_percent = wallet_config.get('sl_percent')
                        tp_percent = wallet_config.get('tp_percent')
                        use_trailing = wallet_config.get('use_trailing', False)
                
                # ✅ Enregistrer la position avec source_wallet et SL/TP (Version 2.0)
                position_id = db_manager.add_position({
                    'token_id': asset_id,
                    'source_wallet': source_wallet,
                    'market_slug': market_slug,
                    'outcome': outcome,
                    'side': side,
                    'shares': shares,
                    'size': shares,
                    'avg_price': price,
                    'entry_price': price,
                    'current_price': price,
                    'value_usd': position_size,
                    'sl_percent': sl_percent,
                    'tp_percent': tp_percent,
                    'use_trailing': use_trailing, # ✨ Trailing Flag
                    'unrealized_pnl': 0,
                    'status': 'OPEN',
                    'opened_at': datetime.now().isoformat()
                })

                # ✨ WebSocket Emission
                if self.socketio:
                    self.socketio.emit('position_update', {'type': 'NEW_POSITION', 'id': position_id})
                    logger.debug("📡 Update position émis via WebSocket")
                
                logger.info(f"💾 Position #{position_id} créée pour {source_wallet[:10]}... (SL: {sl_percent}%, TP: {tp_percent}%)")
                
                return {
                    'status': 'success',
                    'trade': trade_summary,
                    'result': result,
                    'position_id': position_id
                }
            else:
                trade_summary['status'] = 'failed'
                logger.error(f"❌ Échec ordre: {result.get('error')}")
                return {'status': 'error', 'message': result.get('error'), 'trade': trade_summary}
                
        except Exception as e:
            logger.error(f"❌ Erreur execute_copy_trade: {e}")
            return {'status': 'error', 'message': str(e)}

    def on_signal_detected(self, signal: Dict):
        """
        Callback appelé quand un signal de trading est détecté.
        """
        logger.info(f"📡 Signal reçu: {signal.get('type')} de {signal.get('wallet', '')[:10]}...")
        
        # Check if enabled in config via backend reference
        if self.backend:
             if not self.backend.data.get('polymarket', {}).get('enabled', False):
                 logger.info("ℹ️ Bot désactivé globalement, signal ignoré.")
                 return
                 
        result = self.execute_copy_trade(signal)
        return result

    def sell_position(self, position_id, amount: float = None, market: str = None, side: str = None) -> Dict:
        """
        Vend une position (totalement ou partiellement).
        Version 2.1: Avec protection anti-double vente via locks

        Args:
            position_id: ID unique de la position (int) ou token_id (str)
            amount: Montant USD à vendre (None = tout vendre)
            market: Slug du marché (optionnel)
            side: Côté (optionnel)
        """
        try:
            import time

            # Résoudre l'ID de position pour le lock
            resolved_id = position_id if isinstance(position_id, int) else None
            if not resolved_id:
                # Trouver l'ID depuis token_id
                current_positions = db_manager.get_bot_positions(status=None)
                position = next((p for p in current_positions if p.get('token_id') == position_id), None)
                if position:
                    resolved_id = position.get('id') or position.get('position_id')

            # 🔒 Vérifier si la position est déjà en cours de vente
            if resolved_id and position_lock.is_locked(resolved_id):
                logger.warning(f"⚠️ Position #{resolved_id} déjà en cours de traitement")
                return {'success': False, 'error': 'Position déjà en cours de vente'}

            # 🔒 Acquérir le verrou (non-bloquant pour éviter les attentes)
            if resolved_id and not position_lock.try_lock(resolved_id):
                logger.warning(f"⚠️ Impossible de verrouiller position #{resolved_id}")
                return {'success': False, 'error': 'Position verrouillée par un autre processus'}

            try:
                return self._execute_sell(position_id, amount, market, side)
            finally:
                # 🔒 Toujours libérer le verrou
                if resolved_id:
                    position_lock.release(resolved_id)

        except Exception as e:
            logger.error(f"❌ Erreur sell_position: {e}")
            return {'success': False, 'error': str(e)}

    def _execute_sell(self, position_id, amount: float = None, market: str = None, side: str = None) -> Dict:
        """Exécution interne de la vente (appelée avec le lock acquis)."""
        try:
            import time

            # Déterminer si c'est un ID numérique ou un token_id
            if isinstance(position_id, int):
                # Nouveau format: ID de position unique
                position = db_manager.get_position_by_id(position_id)
                if not position:
                    return {'success': False, 'error': f'Position #{position_id} introuvable'}
                
                token_id = position['token_id']
                shares_to_sell = position['shares'] if amount is None else (amount / position.get('current_price', 1))
                market = market or position.get('market_slug', 'unknown')
                side = side or position.get('side', 'BUY')
                avg_entry = position.get('entry_price', 0)
                
            else:
                # Ancien format: token_id (rétrocompatibilité)
                token_id = position_id
                current_positions = db_manager.get_bot_positions(status=None)
                position = next((p for p in current_positions if p.get('token_id') == token_id), None)
                
                if not position:
                    return {'success': False, 'error': f'Position {token_id} introuvable'}
                
                position_id = position.get('id') or position.get('position_id')
                shares_to_sell = position['shares'] if amount is None else (amount / position.get('current_price', 1))
                avg_entry = position.get('entry_price', 0)
            
            logger.info(f"🔻 Vente position #{position_id} ({market}): {shares_to_sell:.2f} shares")
            
            # 1. Prix pour VENDRE
            price = self.get_market_price(token_id, 'SELL')
            
            if not price or price <= 0:
                return {'success': False, 'error': 'Prix non disponible'}
            
            # 3. Exécuter
            result = polymarket_client.place_order(
                token_id=token_id,
                side='SELL',
                price=price,
                size=shares_to_sell,
                order_type='LIMIT'
            )
            
            if result.get('status') == 'success':
                logger.info(f"✅ Vente exécutée: {shares_to_sell:.2f} shares @ ${price:.4f}")
                
                # Calculer le PnL réalisé
                cost_basis = shares_to_sell * avg_entry
                sell_value = shares_to_sell * price
                realized_pnl = sell_value - cost_basis
                
                # Mettre à jour la position
                remaining_shares = position['shares'] - shares_to_sell
                
                if remaining_shares < 0.0001:
                    # Fermeture complète
                    db_manager.close_position(position_id, realized_pnl, status='CLOSED_MANUAL')
                    logger.info(f"💾 Position #{position_id} fermée complètement (PnL: ${realized_pnl:.2f})")
                else:
                    # Fermeture partielle
                    db_manager.update_position_shares(position_id, remaining_shares)
                    logger.info(f"💾 Position #{position_id} réduite à {remaining_shares:.2f} shares")
                
                # Sauvegarder le trade de vente
                db_manager.save_polymarket_trade({
                    'order_id': result.get('orderID', f'sell_{int(time.time())}'),
                    'timestamp': datetime.now().isoformat(),
                    'market_slug': market or 'unknown',
                    'token_id': token_id,
                    'side': 'SELL',
                    'price': price,
                    'size': shares_to_sell,
                    'value_usd': sell_value,
                    'status': 'EXECUTED',
                    'pnl': realized_pnl,
                    'signal_type': 'MANUAL_SELL',
                    'tx_hash': result.get('result', {}).get('transactionHash', '')
                })

                return {
                    'success': True,
                    'result': result,
                    'pnl': realized_pnl,
                    'shares_sold': shares_to_sell,
                    'price': price
                }
            else:
                return {'success': False, 'error': result.get('error')}
                
        except Exception as e:
            logger.error(f"❌ Erreur sell_position: {e}")
            return {'success': False, 'error': str(e)}

# Instance globale
executor = PolymarketExecutor()
