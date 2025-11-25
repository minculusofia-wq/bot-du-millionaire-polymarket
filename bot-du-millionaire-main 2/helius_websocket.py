"""
Websocket Helius - Détection ULTRA-RAPIDE des transactions des traders
Remplace le polling par un listener temps réel (~200ms latence)
"""
import asyncio
import json
import os
import threading
from typing import Optional, Dict, List, Callable
from datetime import datetime

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
        self.max_retries = 5
        self.url_index = 0  # Track which URL we're trying
        
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
    
    async def _connect_and_listen(self):
        """Connecte au websocket et écoute les transactions"""
        if not self.api_key or not websockets:
            print("⚠️ Websocket Helius non disponible - fallback sur polling")
            return
        
        retry_count = 0
        
        while self.is_running and retry_count < self.max_retries:
            try:
                # Essayer les différents formats WSS
                self.wss_url = self.wss_urls[self.url_index % len(self.wss_urls)]
                print(f"🔌 Connexion websocket Helius... (tentative {retry_count + 1}, URL format {self.url_index + 1})")
                
                async with websockets.connect(self.wss_url) as websocket:
                    self.websocket = websocket
                    retry_count = 0  # Reset retry count on successful connection
                    print("✅ Websocket Helius connecté")
                    
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
                    
                    # Écouter les messages
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
                
            except asyncio.CancelledError:
                print("🛑 Websocket Helius arrêté")
                break
            except Exception as e:
                retry_count += 1
                # Essayer URL suivante après 2 tentatives
                if retry_count % 2 == 0:
                    self.url_index += 1
                
                if self.is_running:
                    print(f"⚠️ Erreur websocket (retry {retry_count}/{self.max_retries}): {str(e)[:80]}")
                    if retry_count < self.max_retries:
                        await asyncio.sleep(self.reconnect_delay)
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
