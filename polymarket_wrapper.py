# -*- coding: utf-8 -*-
"""
Wrapper pour l'API Polymarket (CLOB)
Gère l'authentification et les interactions de base avec le carnet d'ordres.
"""
import os
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.constants import POLYGON
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolymarketWrapper")

class PolymarketWrapper:
    def __init__(self):
        load_dotenv()
        self.host = "https://clob.polymarket.com"
        self.chain_id = POLYGON
        self.client = self._connect()

    def _connect(self):
        """Établit la connexion avec le client CLOB"""
        try:
            key = os.getenv("POLYMARKET_API_KEY")
            secret = os.getenv("POLYMARKET_SECRET")
            passphrase = os.getenv("POLYMARKET_PASSPHRASE")
            private_key = os.getenv("POLYGON_PRIVATE_KEY")

            if not all([key, secret, passphrase, private_key]):
                logger.warning("⚠️ Identifiants Polymarket incomplets dans .env. Mode lecture seule ou limité.")
                # On pourrait retourner un client sans auth pour les appels publics si la lib le permet,
                # mais pour le trading on a besoin de tout.
                return None

            client = ClobClient(
                host=self.host,
                key=key,
                secret=secret,
                passphrase=passphrase,
                chain_id=self.chain_id,
                private_key=private_key
            )
            logger.info("✅ Client Polymarket initialisé avec succès")
            return client
        except Exception as e:
            logger.error(f"❌ Erreur connexion Polymarket: {e}")
            return None

    def get_market(self, condition_id):
        """Récupère les infos d'un marché via son condition_id"""
        if not self.client:
            return None
        try:
            return self.client.get_market(condition_id)
        except Exception as e:
            logger.error(f"Erreur récupération marché {condition_id}: {e}")
            return None

    def get_order_book(self, token_id):
        """Récupère le carnet d'ordres pour un token donné"""
        if not self.client:
            return None
        try:
            return self.client.get_order_book(token_id)
        except Exception as e:
            logger.error(f"Erreur récupération order book {token_id}: {e}")
            return None

    def place_order(self, token_id, price, size, side="BUY"):
        """Place un ordre (Limit Order)"""
        if not self.client:
            return None
        
        try:
            # Création de l'ordre
            order_args = OrderArgs(
                price=price,
                size=size,
                side=side,
                token_id=token_id,
            )
            # Signature et envoi
            resp = self.client.create_and_post_order(order_args)
            logger.info(f"✅ Ordre placé: {resp}")
            return resp
        except Exception as e:
            logger.error(f"❌ Erreur placement ordre: {e}")
            return None

# Instance globale
polymarket = PolymarketWrapper()
