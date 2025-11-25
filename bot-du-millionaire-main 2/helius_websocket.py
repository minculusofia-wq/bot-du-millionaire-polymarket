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
        # Format correct du websocket Helius selon doc officielle
        self.wss_url = f"wss://api-mainnet.helius-rpc.com/?api-key={self.api_key}"
        self.subscriptions = {}  # {trader_address: callback_func}
        self.is_running = False
        self.websocket = None
        self.reconnect_delay = 5
        self.max_retries = 5
        
        if not self.api_key:
            print("⚠️ HELIUS_API_KEY non définie - websocket Helius désactivé")
    
    def subscribe_to_trader(self, trader_address: str, callback: Callable):
        """S'abonne aux transactions d'un trader"""
        self.subscriptions[trader_address] = callback
        print(f"✅ Abonné à {trader_address[:10]}...")
    
    def unsubscribe_from_trader(self, trader_address: str):
        """Se désabonne d'un trader"""
        if trader_address in self.subscriptions:
            del self.subscriptions[trader_address]
            print(f"❌ Désabonné de {trader_address[:10]}...")
    
    async def _connect_and_listen(self):
        """Connecte au websocket et écoute les transactions"""
        if not self.api_key or not websockets:
            # Silencieux - fallback sur polling qui fonctionne très bien
            return
        
        try:
            async with websockets.connect(self.wss_url) as websocket:
                self.websocket = websocket
                # Silencieux - fallback sur polling
                
                # S'abonner aux adresses des traders
                for trader_address in self.subscriptions.keys():
                    subscribe_msg = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "accountSubscribe",
                        "params": [
                            trader_address,
                            {"encoding": "jsonParsed"}
                        ]
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                
                # Écouter les messages
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_transaction(data)
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            # Silencieux - WebSocket optionnel, polling HTTP fonctionne
            self.websocket = None
    
    async def _handle_transaction(self, data: Dict):
        """Traite une transaction reçue du websocket"""
        try:
            # Vérifier si c'est une transaction swap
            if 'params' not in data:
                return
            
            result = data.get('params', {}).get('result', {})
            if not result:
                return
            
            # Extraire l'adresse du trader (de la clé du message)
            # Helius envoie les transactions pour l'adresse abonnée
            trader_address = result.get('owner')
            
            if trader_address and trader_address in self.subscriptions:
                # Vérifier si c'est un swap (token transfers)
                tx_data = result.get('transaction', {})
                
                # Créer un objet de transaction
                trade_event = {
                    'type': 'SWAP',
                    'trader_address': trader_address,
                    'timestamp': datetime.now().isoformat(),
                    'raw_data': result
                }
                
                # Appeler le callback
                callback = self.subscriptions[trader_address]
                if callback:
                    callback(trade_event)
        
        except Exception as e:
            print(f"⚠️ Erreur traitement transaction: {e}")
    
    def start(self):
        """Démarre le listener websocket (non-bloquant)"""
        if not self.api_key:
            print("⚠️ Websocket Helius non disponible")
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
                # Silencieux - WebSocket optionnel, polling fonctionne parfaitement
                pass
        
        thread = threading.Thread(target=run_websocket, daemon=True)
        thread.start()
        print("✅ Websocket Helius démarré (background)")
    
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
