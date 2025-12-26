# -*- coding: utf-8 -*-
"""
WebSocket Polygon - Surveillance temps réel des transactions Polymarket
Détecte les trades des wallets suivis en <1 seconde via Alchemy/Infura WebSocket.
"""
import os
import json
import threading
import time
import logging
from typing import Dict, List, Callable, Optional
from datetime import datetime

# WebSocket
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("⚠️ Module websocket-client non installé. pip install websocket-client")

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolygonWebSocket")


class PolygonWebSocket:
    """
    WebSocket pour surveiller les transactions Polygon en temps réel.
    Utilise Alchemy ou Infura pour les événements on-chain.
    """

    # Contrats Polymarket connus sur Polygon
    POLYMARKET_CONTRACTS = {
        'CTF_EXCHANGE': '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E'.lower(),
        'NEG_RISK_CTF_EXCHANGE': '0xC5d563A36AE78145C45a50134d48A1215220f80a'.lower(),
        'CONDITIONAL_TOKENS': '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045'.lower(),
        'USDC_POLYGON': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'.lower(),
    }

    def __init__(self):
        self.ws = None
        self.ws_thread = None
        self.running = False
        self.tracked_wallets = set()
        self.callbacks = []
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60

        # Stats
        self.events_received = 0
        self.trades_detected = 0
        self.last_event_time = None
        self.connected = False

        # API Keys
        self.alchemy_api_key = os.getenv('ALCHEMY_API_KEY', '')
        self.infura_api_key = os.getenv('INFURA_API_KEY', '')
        self.polygonscan_api_key = os.getenv('POLYGONSCAN_API_KEY', '')

        # Choisir le provider
        self.ws_url = self._get_ws_url()

        logger.info("🔌 PolygonWebSocket initialisé")
        if self.ws_url:
            logger.info(f"   Provider: {'Alchemy' if 'alchemy' in self.ws_url else 'Infura' if 'infura' in self.ws_url else 'Public'}")
        else:
            logger.warning("   ⚠️ Aucune clé API WebSocket configurée")

    def _get_ws_url(self) -> Optional[str]:
        """Retourne l'URL WebSocket du meilleur provider disponible"""
        if self.alchemy_api_key:
            return f"wss://polygon-mainnet.g.alchemy.com/v2/{self.alchemy_api_key}"
        elif self.infura_api_key:
            return f"wss://polygon-mainnet.infura.io/ws/v3/{self.infura_api_key}"
        else:
            # Fallback: polling via Polygonscan (pas de WebSocket)
            return None

    def add_wallet(self, address: str):
        """Ajoute un wallet à surveiller"""
        self.tracked_wallets.add(address.lower())
        logger.info(f"👁️ Wallet ajouté au WebSocket: {address[:10]}...")

        # Si WebSocket actif, mettre à jour les subscriptions
        if self.running and self.ws:
            self._subscribe_to_wallet(address)

    def remove_wallet(self, address: str):
        """Retire un wallet de la surveillance"""
        self.tracked_wallets.discard(address.lower())

    def add_callback(self, callback: Callable):
        """Ajoute un callback appelé lors de la détection d'un trade"""
        self.callbacks.append(callback)

    def _subscribe_to_wallet(self, address: str):
        """Souscrit aux événements pour un wallet spécifique"""
        if not self.ws:
            return

        # Subscription pour les logs (événements Transfer, OrderFilled, etc.)
        subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": [
                "logs",
                {
                    "address": list(self.POLYMARKET_CONTRACTS.values()),
                    "topics": [
                        None,  # Tous les événements
                        # Le wallet peut être dans topic[1] ou topic[2]
                    ]
                }
            ]
        }

        try:
            self.ws.send(json.dumps(subscription))
        except Exception as e:
            logger.error(f"❌ Erreur subscription: {e}")

    def _on_message(self, ws, message):
        """Callback lors de la réception d'un message WebSocket"""
        try:
            data = json.loads(message)
            self.events_received += 1
            self.last_event_time = datetime.now()

            # Vérifier si c'est un événement de subscription
            if 'result' in data and 'params' not in data:
                logger.debug(f"Subscription confirmée: {data.get('result')}")
                return

            # Traiter les événements de log
            if 'params' in data and 'result' in data['params']:
                log = data['params']['result']
                self._process_log(log)

        except Exception as e:
            logger.error(f"❌ Erreur traitement message: {e}")

    def _process_log(self, log: Dict):
        """Traite un événement de log Polygon"""
        try:
            topics = log.get('topics', [])
            tx_hash = log.get('transactionHash', '')
            address = log.get('address', '').lower()
            data = log.get('data', '')

            # Vérifier si c'est un contrat Polymarket
            if address not in self.POLYMARKET_CONTRACTS.values():
                return

            # Extraire les adresses des topics
            involved_addresses = set()
            for topic in topics[1:]:  # Skip le topic[0] (event signature)
                if topic and len(topic) >= 42:
                    # Extraire l'adresse des 20 derniers bytes
                    addr = '0x' + topic[-40:].lower()
                    involved_addresses.add(addr)

            # Vérifier si un wallet suivi est impliqué
            matched_wallets = involved_addresses.intersection(self.tracked_wallets)

            if matched_wallets:
                self.trades_detected += 1

                # Créer l'événement
                event = {
                    'type': 'TRADE_DETECTED',
                    'tx_hash': tx_hash,
                    'contract': address,
                    'wallets': list(matched_wallets),
                    'timestamp': datetime.now().isoformat(),
                    'raw_log': log
                }

                logger.info(f"🔔 Trade détecté! TX: {tx_hash[:20]}... | Wallets: {matched_wallets}")

                # Appeler les callbacks
                for callback in self.callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"❌ Erreur callback: {e}")

        except Exception as e:
            logger.error(f"❌ Erreur process_log: {e}")

    def _on_error(self, ws, error):
        """Callback lors d'une erreur WebSocket"""
        logger.error(f"❌ WebSocket erreur: {error}")
        self.connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """Callback lors de la fermeture du WebSocket"""
        logger.warning(f"🔌 WebSocket fermé: {close_status_code} - {close_msg}")
        self.connected = False

        # Reconnexion automatique si toujours en cours d'exécution
        if self.running:
            logger.info(f"⏳ Reconnexion dans {self.reconnect_delay}s...")
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            self._connect()

    def _on_open(self, ws):
        """Callback lors de l'ouverture du WebSocket"""
        logger.info("✅ WebSocket Polygon connecté!")
        self.connected = True
        self.reconnect_delay = 5  # Reset delay

        # Souscrire aux événements pour tous les wallets
        for wallet in self.tracked_wallets:
            self._subscribe_to_wallet(wallet)

    def _connect(self):
        """Établit la connexion WebSocket"""
        if not self.ws_url:
            logger.warning("⚠️ Pas d'URL WebSocket configurée, utilisation du polling")
            return False

        if not WEBSOCKET_AVAILABLE:
            logger.error("❌ Module websocket-client non disponible")
            return False

        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )

            # Lancer dans un thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()

            return True
        except Exception as e:
            logger.error(f"❌ Erreur connexion WebSocket: {e}")
            return False

    def start(self):
        """Démarre le WebSocket"""
        if self.running:
            return

        self.running = True

        if self.ws_url:
            self._connect()
        else:
            # Mode polling si pas de WebSocket
            logger.info("📡 Démarrage en mode polling (pas de WebSocket)")
            self._start_polling()

    def stop(self):
        """Arrête le WebSocket"""
        self.running = False
        if self.ws:
            self.ws.close()
        logger.info("🛑 WebSocket Polygon arrêté")

    def _start_polling(self):
        """Mode fallback: polling via Polygonscan API"""
        def poll_loop():
            while self.running:
                for wallet in list(self.tracked_wallets):
                    try:
                        self._poll_wallet_transactions(wallet)
                    except Exception as e:
                        logger.error(f"❌ Erreur polling {wallet[:10]}: {e}")
                time.sleep(10)  # Poll toutes les 10 secondes

        poll_thread = threading.Thread(target=poll_loop, daemon=True)
        poll_thread.start()

    def _poll_wallet_transactions(self, wallet: str):
        """Récupère les transactions récentes d'un wallet via Polygonscan"""
        if not self.polygonscan_api_key:
            return

        url = f"https://api.polygonscan.com/api"
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': wallet,
            'page': 1,
            'offset': 10,
            'sort': 'desc',
            'apikey': self.polygonscan_api_key
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1' and data.get('result'):
                    for tx in data['result']:
                        # Vérifier si c'est une interaction Polymarket
                        contract = tx.get('contractAddress', '').lower()
                        if contract in self.POLYMARKET_CONTRACTS.values():
                            self._handle_polled_transaction(wallet, tx)
        except Exception as e:
            logger.error(f"❌ Erreur Polygonscan API: {e}")

    def _handle_polled_transaction(self, wallet: str, tx: Dict):
        """Traite une transaction récupérée par polling"""
        tx_hash = tx.get('hash', '')

        # Éviter les doublons
        if hasattr(self, '_processed_txs'):
            if tx_hash in self._processed_txs:
                return
            self._processed_txs.add(tx_hash)
            # Limiter la taille du set
            if len(self._processed_txs) > 1000:
                self._processed_txs = set(list(self._processed_txs)[-500:])
        else:
            self._processed_txs = {tx_hash}

        self.trades_detected += 1

        event = {
            'type': 'TRADE_DETECTED',
            'tx_hash': tx_hash,
            'contract': tx.get('contractAddress', ''),
            'wallets': [wallet],
            'timestamp': datetime.now().isoformat(),
            'value': tx.get('value', '0'),
            'token_symbol': tx.get('tokenSymbol', ''),
            'from': tx.get('from', ''),
            'to': tx.get('to', ''),
            'source': 'polling'
        }

        logger.info(f"📡 [POLL] Trade détecté: {tx_hash[:20]}...")

        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"❌ Erreur callback: {e}")

    def get_stats(self) -> Dict:
        """Retourne les statistiques du WebSocket"""
        return {
            'connected': self.connected,
            'events_received': self.events_received,
            'trades_detected': self.trades_detected,
            'tracked_wallets': len(self.tracked_wallets),
            'last_event': self.last_event_time.isoformat() if self.last_event_time else None,
            'mode': 'websocket' if self.ws_url else 'polling'
        }


# Instance globale
polygon_ws = PolygonWebSocket()
