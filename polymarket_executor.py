# -*- coding: utf-8 -*-
"""
Moteur d'exécution Polymarket
Gère le placement des ordres sur le CLOB en réponse aux signaux de copy trading.
"""
import os
import logging
from typing import Dict, Optional
from datetime import datetime
from polymarket_wrapper import polymarket

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolymarketExecutor")

class PolymarketExecutor:
    def __init__(self):
        self.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        self.max_position_size = float(os.getenv("MAX_POSITION_USD", "100"))
        self.min_position_size = float(os.getenv("MIN_POSITION_USD", "5"))
        self.executed_trades = {}  # Historique des trades exécutés
        
        if self.dry_run:
            logger.info("🔬 Mode DRY RUN activé - Aucun ordre réel ne sera placé")

    def calculate_position_size(self, signal: Dict, bot_capital: float) -> float:
        """
        Calcule la taille de position basée sur le signal et le capital du bot.
        Utilise un ratio proportionnel ou une taille fixe.
        """
        # Option 1: Taille fixe (configurable)
        position_size = min(self.max_position_size, bot_capital * 0.05)  # 5% du capital max
        
        # Respecter les limites min/max
        position_size = max(self.min_position_size, position_size)
        position_size = min(self.max_position_size, position_size)
        
        return round(position_size, 2)

    def get_market_price(self, token_id: str, side: str) -> Optional[float]:
        """
        Récupère le prix actuel du marché pour un token donné.
        side: 'BUY' ou 'SELL'
        """
        if not polymarket.client:
            logger.warning("⚠️ Client Polymarket non initialisé")
            return None
            
        try:
            order_book = polymarket.get_order_book(token_id)
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
        
        Args:
            signal: Dictionnaire contenant {type, wallet, asset_id, amount, ...}
            bot_capital: Capital disponible du bot en USD
            
        Returns:
            Résultat de l'exécution
        """
        try:
            signal_type = signal.get('type', '')
            asset_id = signal.get('asset_id', '')
            
            if not asset_id:
                return {'status': 'error', 'message': 'Asset ID manquant'}

            # Calculer la taille de position
            position_size = self.calculate_position_size(signal, bot_capital)
            
            # Récupérer le prix actuel
            side = 'BUY' if signal_type == 'BUY' else 'SELL'
            price = self.get_market_price(asset_id, side)
            
            if not price or price <= 0:
                # Utiliser un prix estimé si le marché n'est pas accessible
                price = 0.5  # Prix médian par défaut
                logger.warning(f"⚠️ Prix non disponible, utilisation du prix par défaut: {price}")

            # Calculer la quantité de shares à acheter/vendre
            shares = position_size / price if price > 0 else 0

            # Créer le résumé du trade
            trade_summary = {
                'timestamp': datetime.now().isoformat(),
                'signal_type': signal_type,
                'asset_id': asset_id[:30] + '...',
                'price': price,
                'shares': round(shares, 2),
                'value_usd': position_size,
                'status': 'pending'
            }

            if self.dry_run:
                # Mode simulation
                trade_summary['status'] = 'simulated'
                logger.info(f"🔬 [DRY RUN] {signal_type} {shares:.2f} shares @ ${price:.4f} = ${position_size:.2f}")
                return {'status': 'simulated', 'trade': trade_summary}
            
            # Mode réel - Placer l'ordre
            if not polymarket.client:
                return {'status': 'error', 'message': 'Client non initialisé'}
                
            result = polymarket.place_order(
                token_id=asset_id,
                price=price,
                size=shares,
                side=side
            )
            
            if result:
                trade_summary['status'] = 'executed'
                trade_summary['order_id'] = result.get('orderID', 'unknown')
                logger.info(f"✅ Ordre exécuté: {signal_type} {shares:.2f} shares @ ${price:.4f}")
                return {'status': 'success', 'trade': trade_summary, 'result': result}
            else:
                trade_summary['status'] = 'failed'
                return {'status': 'error', 'message': 'Échec placement ordre', 'trade': trade_summary}
                
        except Exception as e:
            logger.error(f"❌ Erreur execute_copy_trade: {e}")
            return {'status': 'error', 'message': str(e)}

    def on_signal_detected(self, signal: Dict):
        """
        Callback appelé quand un signal de trading est détecté.
        Connecté au PolymarketTracker.
        """
        logger.info(f"📡 Signal reçu: {signal.get('type')} de {signal.get('wallet', '')[:10]}...")
        
        # Exécuter le trade de copie
        result = self.execute_copy_trade(signal)
        
        # Logger le résultat
        if result.get('status') == 'success' or result.get('status') == 'simulated':
            logger.info(f"✅ Trade copié avec succès")
        else:
            logger.warning(f"⚠️ Trade non exécuté: {result.get('message', 'Erreur inconnue')}")
        
        return result

# Instance globale
executor = PolymarketExecutor()
