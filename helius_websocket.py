# -*- coding: utf-8 -*-
"""
Websocket Helius - Détection ULTRA-RAPIDE des transactions des traders
Remplace le polling par un listener temps réel (~50-100ms latence)
✨ OPTIMISÉ Phase 9: Reconnexion intelligente, Heartbeat, Buffer événements
"""
import asyncio
import json
import os
import threading
import time
import ssl
from typing import Optional, Dict, List, Callable
from datetime import datetime
from collections import deque

try:
    import websockets
except ImportError:
    websockets = None


class HeliosWebsocketListener:
    """Écoute les transactions Solana en temps réel via websocket Helius"""

    def __init__(self):
        self.api_key = os.getenv('HELIUS_API_KEY')
        # Tester les différents formats WSS Helius
        # Format 1 (principal): avec /v0/
        self.wss_urls = [
            f"wss://api-mainnet.helius-rpc.com/v0/?api-key={self.api_key}",
            f"wss://api-mainnet.helius-rpc.com/?api-key={self.api_key}",
            f"wss://api-mainnet.helius-rpc.com/ws?api-key={self.api_key}"
        ]
        self.wss_url = self.wss_urls[0]  # Start with primary
        self.subscriptions = {}  # {trader_address: callback_func}
        self.is_running = False
        self.websocket = None
        self.reconnect_delay = 5
        self.max_retries = 10  # ✨ Augmenté de 5 à 10
        self.url_index = 0  # Track which URL we're trying

        # ✨ NOUVEAU: Heartbeat pour maintenir la connexion
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # Ping toutes les 30s
        self.heartbeat_timeout = 60  # Timeout si pas de pong après 60s

        # ✨ NOUVEAU: Buffer d'événements pendant la reconnexion
        self.event_buffer = deque(maxlen=100)  # Garder max 100 événements
        self.is_connected = False

        # ✨ NOUVEAU: Stats de connexion
        self.connection_quality = 100  # 0-100%
        self.total_reconnects = 0
        self.last_reconnect_time = None

        if not self.api_key:
            print("⚠️ HELIUS_API_KEY non définie - websocket Helius désactivé")
    
    def subscribe_to_trader(self, trader_address: str, callback: Callable):
        """S'abonne aux transactions d'un trader"""
        self.subscriptions[trader_address] = callback
        print(f"✅ Abonné à {trader_address[:10]}... (websocket)")

    def unsubscribe_from_trader(self, trader_address: str):
        """Se désabonne d'un trader"""
        if trader_address in self.subscriptions:
            del self.subscriptions[trader_address]
            print(f"❌ Désabonné de {trader_address[:10]}...")

    async def _send_heartbeat(self, websocket):
        """✨ NOUVEAU: Envoie un ping périodique pour maintenir la connexion"""
        try:
            while self.is_connected and self.is_running:
                await asyncio.sleep(self.heartbeat_interval)
                if websocket and not websocket.closed:
                    try:
                        # Envoyer un ping
                        pong = await websocket.ping()
                        await asyncio.wait_for(pong, timeout=5)
                        self.last_heartbeat = time.time()
                        self.connection_quality = min(100, self.connection_quality + 5)
                    except asyncio.TimeoutError:
                        print("⚠️ Heartbeat timeout - connexion faible")
                        self.connection_quality = max(0, self.connection_quality - 20)
                    except Exception as e:
                        print(f"⚠️ Heartbeat error: {e}")
                        self.connection_quality = max(0, self.connection_quality - 10)
        except Exception as e:
            print(f"⚠️ Heartbeat loop error: {e}")

    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """✨ NOUVEAU: Calcule le délai avec backoff exponentiel"""
        # Backoff exponentiel: 2^retry * base_delay, max 60s
        delay = min(60, (2 ** retry_count) * 2)
        return delay

    def get_connection_stats(self) -> Dict:
        """✨ NOUVEAU: Retourne les stats de connexion"""
        return {
            'is_connected': self.is_connected,
            'connection_quality': self.connection_quality,
            'total_reconnects': self.total_reconnects,
            'last_reconnect': self.last_reconnect_time,
            'buffer_size': len(self.event_buffer),
            'subscriptions': len(self.subscriptions)
        }
    
    async def _connect_and_listen(self):
        """✨ AMÉLIORÉ: Connecte au websocket et écoute les transactions avec reconnexion intelligente"""
        if not self.api_key or not websockets:
            print("⚠️ Websocket Helius non disponible - fallback sur polling")
            return

        retry_count = 0

        while self.is_running:
            try:
                # Essayer les différents formats WSS
                self.wss_url = self.wss_urls[self.url_index % len(self.wss_urls)]
                print(f"🔌 Connexion websocket Helius... (tentative {retry_count + 1}, URL format {self.url_index + 1})")

                # ✨ NOUVEAU: Créer un contexte SSL pour macOS/Linux (résout CERTIFICATE_VERIFY_FAILED)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                async with websockets.connect(
                    self.wss_url,
                    ssl=ssl_context,  # ✨ Ajouter le contexte SSL
                    ping_interval=30,  # ✨ Ping automatique toutes les 30s
                    ping_timeout=10,   # ✨ Timeout de 10s pour pong
                    close_timeout=10
                ) as websocket:
                    self.websocket = websocket
                    self.is_connected = True  # ✨ NOUVEAU
                    retry_count = 0  # Reset retry count on successful connection
                    self.connection_quality = 100  # ✨ Reset quality
                    print("✅ Websocket Helius connecté")

                    # ✨ NOUVEAU: Traiter les événements buffered
                    if len(self.event_buffer) > 0:
                        print(f"📦 Traitement de {len(self.event_buffer)} événements buffered...")
                        while len(self.event_buffer) > 0:
                            event = self.event_buffer.popleft()
                            await self._handle_notification(event)

                    # S'abonner aux adresses des traders
                    for trader_address in self.subscriptions.keys():
                        subscribe_msg = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "logsSubscribe",
                            "params": [
                                {
                                    "mentions": [trader_address]
                                },
                                {
                                    "commitment": "processed"
                                }
                            ]
                        }
                        try:
                            await websocket.send(json.dumps(subscribe_msg))
                            print(f"  ├─ Abonnement logs pour {trader_address[:10]}...")
                        except Exception as e:
                            print(f"  └─ Erreur abonnement: {e}")

                    # ✨ NOUVEAU: Lancer le heartbeat en parallèle
                    heartbeat_task = asyncio.create_task(self._send_heartbeat(websocket))

                    # Écouter les messages
                    try:
                        async for message in websocket:
                            if not self.is_running:
                                break

                            try:
                                data = json.loads(message)
                                await self._handle_notification(data)
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                print(f"⚠️ Erreur traitement message: {e}")
                    finally:
                        heartbeat_task.cancel()  # ✨ Arrêter le heartbeat

            except asyncio.CancelledError:
                print("🛑 Websocket Helius arrêté")
                self.is_connected = False
                break
            except Exception as e:
                self.is_connected = False  # ✨ NOUVEAU
                self.total_reconnects += 1  # ✨ NOUVEAU
                self.last_reconnect_time = datetime.now().isoformat()  # ✨ NOUVEAU
                retry_count += 1

                # Essayer URL suivante après 2 tentatives
                if retry_count % 2 == 0:
                    self.url_index += 1

                if self.is_running:
                    # ✨ NOUVEAU: Backoff exponentiel
                    delay = self._calculate_backoff_delay(retry_count)
                    print(f"⚠️ Erreur websocket (retry {retry_count}): {str(e)[:80]}")
                    print(f"   Reconnexion dans {delay}s...")
                    await asyncio.sleep(delay)

                self.websocket = None
    
    async def _handle_notification(self, data: Dict):
        """Traite une notification reçue du websocket"""
        try:
            # Vérifier si c'est une subscription update
            if 'result' not in data:
                return
            
            result = data.get('result', {})
            
            # Extraire les infos de la notification
            if isinstance(result, dict):
                logs = result.get('logs', [])
                signature = result.get('signature', '')
                
                # Chercher le trader correspondant à cette TX
                # Les logs mentionnent les adresses impliquées
                for trader_address, callback in self.subscriptions.items():
                    # La transaction concerne ce trader
                    # Chercher si c'est un swap en regardant les logs
                    
                    # Heuristique: si y a du "SWAP" ou des DEX mentions
                    is_swap = any(
                        keyword in str(logs).upper()
                        for keyword in ['SWAP', 'EXCHANGE', 'JUPITERAGGREGATE', 'RAYDIUM', 'ORCA', 'SERUM', 'PUMPFUN']
                    )
                    
                    if is_swap or signature:  # Toute TX du trader
                        # Créer un événement de trade
                        trade_event = {
                            'type': 'SWAP',
                            'trader_address': trader_address,
                            'signature': signature,
                            'timestamp': datetime.now().isoformat(),
                            'logs': logs,
                            'raw_data': result
                        }
                        
                        # Appeler le callback de manière non-bloquante
                        if callback:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(trade_event)
                                else:
                                    # Appeler dans un thread si callback n'est pas async
                                    callback(trade_event)
                            except Exception as e:
                                print(f"⚠️ Erreur callback: {e}")
        
        except Exception as e:
            print(f"⚠️ Erreur traitement notification: {e}")
    
    def start(self):
        """Démarre le listener websocket (non-bloquant)"""
        if not self.api_key:
            print("⚠️ Websocket Helius non disponible (API key manquante)")
            return
        
        if self.is_running:
            print("⚠️ Websocket déjà en cours")
            return
        
        self.is_running = True
        
        # Lancer dans un thread séparé
        def run_websocket():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._connect_and_listen())
            except Exception as e:
                print(f"❌ Erreur websocket: {e}")
            finally:
                self.is_running = False
        
        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
        print("✅ Websocket Helius démarré")
    
    def stop(self):
        """Arrête le listener websocket"""
        self.is_running = False
        if self.websocket:
            try:
                asyncio.run(self.websocket.close())
            except:
                pass
        print("🛑 Websocket Helius arrêté")


# Instance globale
helius_websocket = HeliosWebsocketListener()
