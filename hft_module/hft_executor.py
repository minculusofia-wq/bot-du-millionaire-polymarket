# -*- coding: utf-8 -*-
"""
HFT Executor - Exécution rapide des trades HFT
Exécute les ordres sans validation lourde pour minimiser la latence.

Optimisations v3.1:
- DB write asynchrone (fire-and-forget)
- Ne bloque pas le retour de l'exécution
"""
import logging
import threading
from typing import Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HFTExecutor")


class HFTExecutor:
    """
    Exécuteur de trades HFT ultra-rapide.
    Différences avec l'exécuteur classique:
    - Pas de validation TradeValidator
    - Pas de Kelly Criterion
    - Position fixe par wallet
    - Slippage toléré plus large
    """

    DEFAULT_MAX_SLIPPAGE_BPS = 50  # 0.5%
    DEFAULT_TIMEOUT_SEC = 2

    def __init__(self, polymarket_client=None, db_manager=None, socketio=None):
        self.polymarket_client = polymarket_client
        self.db_manager = db_manager
        self.socketio = socketio

        # Configuration
        self.max_slippage_bps = self.DEFAULT_MAX_SLIPPAGE_BPS
        self.timeout_sec = self.DEFAULT_TIMEOUT_SEC
        self.enabled = True

        # Stats
        self.trades_executed = 0
        self.trades_failed = 0
        self.total_volume_usd = 0.0

        logger.info("HFTExecutor initialisé")

    def set_config(self, config: Dict):
        """Met à jour la configuration"""
        if 'max_slippage_bps' in config:
            self.max_slippage_bps = int(config['max_slippage_bps'])
        if 'timeout_sec' in config:
            self.timeout_sec = int(config['timeout_sec'])
        if 'enabled' in config:
            self.enabled = bool(config['enabled'])

        logger.info(f"HFTExecutor config: slippage={self.max_slippage_bps}bps, timeout={self.timeout_sec}s")

    def calculate_position_size(self, signal: Dict, wallet_config: Dict) -> float:
        """
        Calcule la taille de position pour un trade HFT.
        Simple et rapide - pas de Kelly Criterion.
        """
        capital = float(wallet_config.get('capital_allocated', 100))
        percent = float(wallet_config.get('percent_per_trade', 10))

        position_usd = capital * (percent / 100)

        # Minimum $5
        position_usd = max(5, position_usd)

        return round(position_usd, 2)

    def get_best_price(self, token_id: str, side: str) -> Optional[float]:
        """Récupère le meilleur prix disponible"""
        if not self.polymarket_client:
            return None

        try:
            order_book = self.polymarket_client.get_order_book(token_id)
            if not order_book:
                return None

            if side == 'BUY':
                asks = order_book.get('asks', [])
                if asks:
                    return float(asks[0].get('price', 0))
            else:
                bids = order_book.get('bids', [])
                if bids:
                    return float(bids[0].get('price', 0))

            return None

        except Exception as e:
            logger.error(f"Erreur get_best_price: {e}")
            return None

    def execute_copy_trade(self, signal: Dict, wallet_config: Dict) -> Dict:
        """
        Exécute un trade de copie HFT.

        Args:
            signal: Signal HFT détecté (du HFTTradeMonitor)
            wallet_config: Configuration du wallet HFT

        Returns:
            Résultat de l'exécution
        """
        if not self.enabled:
            return {
                'status': 'disabled',
                'message': 'HFT Executor désactivé'
            }

        if not self.polymarket_client:
            return {
                'status': 'error',
                'message': 'Client Polymarket non configuré'
            }

        start_time = datetime.now()

        try:
            token_id = signal.get('token_id', '')
            side = signal.get('side', 'BUY')
            signal_price = float(signal.get('price', 0))

            if not token_id:
                return {
                    'status': 'error',
                    'message': 'Token ID manquant'
                }

            # 1. Récupérer le meilleur prix actuel
            best_price = self.get_best_price(token_id, side)

            if not best_price or best_price <= 0:
                # Fallback sur le prix du signal
                if signal_price > 0:
                    best_price = signal_price
                else:
                    return {
                        'status': 'error',
                        'message': 'Prix non disponible'
                    }

            # 2. Calculer le prix limite avec slippage
            slippage_mult = self.max_slippage_bps / 10000

            if side == 'BUY':
                limit_price = best_price * (1 + slippage_mult)
            else:
                limit_price = best_price * (1 - slippage_mult)

            limit_price = round(limit_price, 4)

            # 3. Calculer la taille de position
            position_usd = self.calculate_position_size(signal, wallet_config)
            shares = position_usd / limit_price if limit_price > 0 else 0

            if shares <= 0:
                return {
                    'status': 'error',
                    'message': 'Taille de position invalide'
                }

            shares = round(shares, 2)

            # 4. Placer l'ordre (sans validation lourde)
            logger.info(f"HFT Order: {side} {shares} shares @ ${limit_price} (${position_usd})")

            order_result = self.polymarket_client.place_order(
                token_id=token_id,
                side=side,
                price=limit_price,
                size=shares,
                order_type='LIMIT'
            )

            execution_time = datetime.now()
            latency_ms = int((execution_time - start_time).total_seconds() * 1000)

            if order_result and order_result.get('success'):
                self.trades_executed += 1
                self.total_volume_usd += position_usd

                result = {
                    'status': 'executed',
                    'order_id': order_result.get('orderID', order_result.get('order_id', '')),
                    'token_id': token_id,
                    'side': side,
                    'price': limit_price,
                    'shares': shares,
                    'value_usd': position_usd,
                    'latency_ms': latency_ms,
                    'timestamp': execution_time.isoformat()
                }

                # Sauvegarder en DB
                if self.db_manager:
                    self._save_trade_to_db(signal, result, wallet_config)

                # Notification WebSocket
                if self.socketio:
                    self.socketio.emit('hft_trade_executed', result, namespace='/')

                logger.info(f"HFT Trade exécuté: {side} ${position_usd} en {latency_ms}ms")

                return result

            else:
                self.trades_failed += 1
                error_msg = order_result.get('error', 'Erreur inconnue') if order_result else 'Pas de réponse'

                return {
                    'status': 'failed',
                    'message': error_msg,
                    'latency_ms': latency_ms
                }

        except Exception as e:
            self.trades_failed += 1
            logger.error(f"Erreur execute_copy_trade: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _save_trade_to_db(self, signal: Dict, result: Dict, wallet_config: Dict):
        """
        Sauvegarde le trade en base de données de manière ASYNCHRONE.
        Fire-and-forget : ne bloque pas l'exécution.
        """
        # Préparer les données avant le thread pour éviter race conditions
        trade_data = {
            'signal_timestamp': signal.get('timestamp', datetime.now().isoformat()),
            'execution_timestamp': result.get('timestamp'),
            'source_wallet': signal.get('wallet_address', ''),
            'trader_name': signal.get('wallet_name', wallet_config.get('name', '')),
            'market_question': signal.get('market_question', ''),
            'token_id': result.get('token_id', ''),
            'condition_id': signal.get('condition_id', ''),
            'side': result.get('side', ''),
            'signal_price': signal.get('price', 0),
            'execution_price': result.get('price', 0),
            'size_usd': result.get('value_usd', 0),
            'shares': result.get('shares', 0),
            'latency_ms': result.get('latency_ms', 0),
            'status': result.get('status', 'unknown'),
            'order_id': result.get('order_id', ''),
            'error_message': result.get('message', '') if result.get('status') != 'executed' else ''
        }

        # Fire-and-forget : lancer en background sans attendre
        threading.Thread(
            target=self._do_save_trade,
            args=(trade_data,),
            daemon=True
        ).start()

    def _do_save_trade(self, trade_data: Dict):
        """Exécute la sauvegarde DB dans un thread séparé"""
        try:
            self.db_manager.save_hft_trade(trade_data)
            logger.debug(f"Trade sauvegardé en DB: {trade_data.get('order_id', 'N/A')}")
        except Exception as e:
            logger.error(f"Erreur save_trade_to_db (async): {e}")

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return {
            'enabled': self.enabled,
            'trades_executed': self.trades_executed,
            'trades_failed': self.trades_failed,
            'total_volume_usd': round(self.total_volume_usd, 2),
            'success_rate': round(
                self.trades_executed / max(1, self.trades_executed + self.trades_failed) * 100, 1
            ),
            'max_slippage_bps': self.max_slippage_bps,
            'timeout_sec': self.timeout_sec
        }
