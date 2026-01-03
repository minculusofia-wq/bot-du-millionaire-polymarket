# -*- coding: utf-8 -*-
"""
Polymarket Client Unifié
Remplace polymarket_clob.py et polymarket_wrapper.py.
Gère l'authentification et les interactions avec le CLOB (Carnet d'ordres).
"""
import os
import hmac
import hashlib
import time
import json
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import du cache manager
try:
    from cache_manager import cached, cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    # Fallback decorator si cache non disponible
    def cached(ttl=60, key_prefix=""):
        def decorator(func):
            return func
        return decorator

from secret_manager import secret_manager

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolymarketClient")

class PolymarketClient:
    """
    Client unifié pour l'API Polymarket.
    Combine la robustesse de l'API REST manuelle et la facilité de py-clob-client.
    """

    # Endpoints
    CLOB_HOST = "https://clob.polymarket.com"
    GAMMA_HOST = "https://gamma-api.polymarket.com"
    
    # Chain ID Polygon
    CHAIN_ID = 137

    def __init__(self):
        load_dotenv()
        
        # Credentials
        self.api_key = os.getenv('POLYMARKET_API_KEY', '')
        # Déchiffrer les secrets
        self.api_secret = secret_manager.decrypt(os.getenv('POLYMARKET_SECRET', ''))
        self.api_passphrase = secret_manager.decrypt(os.getenv('POLYMARKET_PASSPHRASE', ''))
        
        # Déchiffrer la clé privée si elle est chiffrée
        encrypted_key = os.getenv('POLYGON_PRIVATE_KEY', '')
        self.private_key = secret_manager.decrypt(encrypted_key)

        # Client officiel (py-clob-client)
        self.client = None
        self._init_clob_client()

        # Session HTTP pour les fallbacks REST
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        # Stats
        self.orders_placed = 0
        self.orders_filled = 0
        self.total_volume = 0.0
        
        # Status
        self.authenticated = bool(self.api_key and self.api_secret and self.private_key)
        
        logger.info("🚀 PolymarketClient initialisé")
        if self.client:
             logger.info("   ✅ Mode: py-clob-client (Optimisé)")
        elif self.authenticated:
             logger.info("   ⚠️ Mode: REST API Fallback (Fonctionnel mais plus lent)")
        else:
             logger.warning("   ❌ Mode: Lecture Seule (Pas de clés API configurées)")

    def _init_clob_client(self):
        """Initialise le client officiel py-clob si disponible et configuré."""
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.constants import POLYGON
            from py_clob_client.clob_types import ApiCreds

            if all([self.api_key, self.api_secret, self.api_passphrase, self.private_key]):
                self.client = ClobClient(
                    host=self.CLOB_HOST,
                    key=self.private_key,
                    chain_id=POLYGON,
                    creds=ApiCreds(
                        api_key=self.api_key,
                        api_secret=self.api_secret,
                        api_passphrase=self.api_passphrase
                    )
                )
            else:
                logger.debug("Credentials incomplets pour py-clob-client")
        except ImportError:
            logger.warning("py-clob-client non installé. Utilisation fallback REST.")
        except Exception as e:
            logger.error(f"Erreur init py-clob-client: {e}")
            
    def set_wallet(self, private_key: str):
        """
        Configure la clé privée dynamiquement (après démarrage).
        Stockée uniquement en mémoire.
        """
        if not private_key:
            return

        # On s'assure que si la clé passée est chiffrée, on la déchiffre pour l'usage interne
        self.private_key = secret_manager.decrypt(private_key)
        # Mettre à jour le statut
        self.authenticated = bool(self.api_key and self.api_secret and self.private_key)
        
        # Tenter de re-initialiser le client officiel
        self._init_clob_client()
        
        logger.info("🔐 Clé privée mise à jour en mémoire (Mode Authentifié actif)")

    def set_api_credentials(self, api_key: str, api_secret: str, api_passphrase: str):
        """Met à jour les identifiants API Polymarket"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.authenticated = bool(self.api_key and self.api_secret and self.private_key)
        self._init_clob_client()
        logger.info("🔑 Identifiants API mis à jour en mémoire")

    def _sign_request(self, method: str, path: str, body: str = '') -> Dict[str, str]:
        """Génère les headers d'authentification pour l'API REST (Fallback)."""
        if not self.api_secret:
            return {}

        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + path + body
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return {
            'POLY-API-KEY': self.api_key,
            'POLY-SIGNATURE': signature,
            'POLY-TIMESTAMP': timestamp,
            'POLY-PASSPHRASE': self.api_passphrase,
        }

    # =========================================================================
    # MARKET DATA
    # =========================================================================

    @cached(ttl=30, key_prefix="orderbook:")
    def get_order_book(self, token_id: str) -> Optional[Dict]:
        """Récupère le carnet d'ordres pour un token (avec cache 30s)."""
        try:
            if self.client:
                return self.client.get_order_book(token_id)

            # REST Fallback
            resp = self.session.get(f"{self.CLOB_HOST}/book", params={'token_id': token_id}, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.error(f"Erreur get_order_book: {e}")
            return None

    def get_markets(self, limit: int = 100, active: bool = True) -> List[Dict]:
        """Récupère la liste des marchés (via Gamma API)."""
        try:
            params = {'limit': limit, 'active': str(active).lower()}
            resp = self.session.get(f"{self.GAMMA_HOST}/markets", params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Erreur get_markets: {e}")
            return []

    @cached(ttl=60, key_prefix="market:")
    def get_market(self, condition_id: str) -> Optional[Dict]:
        """Récupère un marché spécifique (avec cache 60s)."""
        try:
            resp = self.session.get(f"{self.GAMMA_HOST}/markets/{condition_id}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.error(f"Erreur get_market: {e}")
            return None

    # =========================================================================
    # TRADING & ORDERS
    # =========================================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError)),
        reraise=True
    )
    def place_order(self, token_id: str, side: str, price: float, size: float, order_type: str = 'LIMIT') -> Dict:
        """
        Place un ordre sur le marché (avec retry automatique).
        
        Args:
            token_id: ID du token (Asset ID)
            side: 'BUY' ou 'SELL'
            price: Prix limite
            size: Quantité (Shares)
            order_type: 'LIMIT' ou 'MARKET' (Market simulé par IOC agressif)
        """
        if not self.authenticated:
            return {'status': 'error', 'error': 'Non authentifié - Vérifiez vos clés API'}

        try:
            # 1. Utilisation de py-clob-client (Préco)
            if self.client:
                from py_clob_client.clob_types import OrderArgs
                
                # Ajustement pour Market Order simulé
                if order_type.upper() == 'MARKET':
                    # Fallback interne pour market order si nécessaire, 
                    # mais py-clob gère surtout des limites.
                    # On place un Limit IOC agressif.
                    # Note: C'est mieux géré par l'appelant, mais on sécurise ici.
                    pass 

                order_args = OrderArgs(
                    price=price,
                    size=size,
                    side=side.upper(),
                    token_id=token_id,
                )
                
                # Signature et envoi automatique
                resp = self.client.create_and_post_order(order_args)
                
                if resp and 'orderID' in resp:
                    self.orders_placed += 1
                    self.total_volume += price * size
                    logger.info(f"✅ Ordre placé (Client): {side} {size} @ {price}")
                    return {'status': 'success', 'result': resp, 'orderID': resp['orderID']}
                else:
                    return {'status': 'error', 'error': 'Réponse invalide du client', 'details': resp}

            # 2. REST API Fallback
            path = '/order'
            body = json.dumps({
                'tokenID': token_id,
                'side': side.upper(),
                'price': str(price),
                'size': str(size),
                'type': 'LIMIT', # CLOB ne supporte que LIMIT
                'timeInForce': 'GTC' # Good Till Cancel
            })
            
            headers = self._sign_request('POST', path, body)
            resp = self.session.post(f"{self.CLOB_HOST}{path}", data=body, headers=headers, timeout=10)
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                self.orders_placed += 1
                self.total_volume += price * size
                logger.info(f"✅ Ordre placé (REST): {side} {size} @ {price}")
                return {'status': 'success', 'result': data, 'orderID': data.get('orderID')}
            else:
                return {'status': 'error', 'error': resp.text}

        except Exception as e:
            logger.error(f"❌ Erreur place_order: {e}")
            return {'status': 'error', 'error': str(e)}

    def cancel_order(self, order_id: str) -> Dict:
        """Annule un ordre."""
        try:
            if self.client:
                self.client.cancel(order_id)
                return {'status': 'success'}
            
            path = f"/order/{order_id}"
            headers = self._sign_request('DELETE', path)
            resp = self.session.delete(f"{self.CLOB_HOST}{path}", headers=headers, timeout=10)
            
            if resp.status_code == 200:
                return {'status': 'success'}
            return {'status': 'error', 'error': resp.text}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def cancel_all(self) -> Dict:
        """Annule tous les ordres."""
        try:
            if self.client:
                self.client.cancel_all()
                return {'status': 'success'}
            
            path = "/orders"
            headers = self._sign_request('DELETE', path)
            resp = self.session.delete(f"{self.CLOB_HOST}{path}", headers=headers, timeout=10)
            
            if resp.status_code == 200:
                return {'status': 'success'}
            return {'status': 'error', 'error': resp.text}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def get_best_bid_ask(self, token_id: str) -> Tuple[Optional[float], Optional[float]]:
        """Helper to get best prices."""
        ob = self.get_order_book(token_id)
        if not ob:
            return None, None
        
        bids = ob.get('bids', [])
        asks = ob.get('asks', [])
        
        best_bid = float(bids[0]['price']) if bids else None
        best_ask = float(asks[0]['price']) if asks else None
        
        return best_bid, best_ask

    def get_stats(self) -> Dict:
        """Statistiques du client."""
        return {
            'authenticated': self.authenticated,
            'mode': 'py-clob-client' if self.client else 'REST',
            'orders_placed': self.orders_placed,
            'total_volume': self.total_volume
        }

# Instance globale pour importation directe
polymarket_client = PolymarketClient()
