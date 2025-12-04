# -*- coding: utf-8 -*-
"""
Module de suivi des traders Polymarket (Tracker)
Surveille les positions et l'activité des portefeuilles cibles via le Subgraph Goldsky.
"""
import requests
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolymarketTracker")

class PolymarketTracker:
    def __init__(self):
        # Endpoint Goldsky pour les positions (validé)
        self.positions_url = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
        self.activity_url = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"
        self.tracked_wallets = set()
        self.last_positions = {}  # {wallet_address: {asset_id: balance}}

    def add_wallet(self, address: str):
        """Ajoute un wallet à la liste de surveillance"""
        self.tracked_wallets.add(address.lower())
        logger.info(f"🔭 Wallet ajouté au tracking: {address[:10]}...")

    def remove_wallet(self, address: str):
        """Retire un wallet de la surveillance"""
        addr = address.lower()
        if addr in self.tracked_wallets:
            self.tracked_wallets.remove(addr)

    def get_user_positions(self, address: str) -> List[Dict]:
        """
        Récupère les positions actuelles d'un utilisateur via Goldsky Subgraph.
        """
        query = """
        {
          userBalances(first: 100, where: {user: "%s", balance_gt: "0"}) {
            id
            user
            balance
            asset {
              id
              condition {
                id
              }
            }
          }
        }
        """ % address.lower()

        try:
            resp = requests.post(self.positions_url, json={'query': query}, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'].get('userBalances'):
                    return data['data']['userBalances']
                else:
                    logger.warning(f"⚠️ Aucune position trouvée pour {address[:10]}...")
                    return []
            else:
                logger.warning(f"⚠️ Erreur API ({resp.status_code})")
                return []
        except Exception as e:
            logger.error(f"❌ Exception get_user_positions: {e}")
            return []

    def detect_changes(self, address: str) -> List[Dict]:
        """
        Détecte les changements de position pour un wallet donné.
        Compare l'état actuel avec le dernier état connu.
        Retourne une liste d'événements (BUY/SELL).
        """
        current_positions = self.get_user_positions(address)
        if not current_positions:
            return []

        # Convertir en dictionnaire pour comparaison {asset_id: balance}
        current_map = {}
        for p in current_positions:
            asset_id = p.get('asset', {}).get('id') if isinstance(p.get('asset'), dict) else p.get('id')
            if asset_id:
                current_map[asset_id] = int(p.get('balance', 0))

        last_map = self.last_positions.get(address.lower(), {})
        changes = []

        # 1. Détecter nouvelles positions ou augmentations (ACHAT)
        for asset_id, balance in current_map.items():
            old_balance = last_map.get(asset_id, 0)
            if balance > old_balance:
                diff = balance - old_balance
                changes.append({
                    "type": "BUY",
                    "wallet": address,
                    "asset_id": asset_id,
                    "amount": diff,
                    "total_balance": balance,
                    "timestamp": datetime.now().isoformat()
                })

        # 2. Détecter réductions ou fermetures (VENTE)
        for asset_id, old_balance in last_map.items():
            new_balance = current_map.get(asset_id, 0)
            if new_balance < old_balance:
                diff = old_balance - new_balance
                changes.append({
                    "type": "SELL",
                    "wallet": address,
                    "asset_id": asset_id,
                    "amount": diff,
                    "remaining_balance": new_balance,
                    "timestamp": datetime.now().isoformat()
                })

        # Mettre à jour l'état connu
        self.last_positions[address.lower()] = current_map
        return changes

    def monitor_loop(self, interval=5, callback=None):
        """Boucle principale de surveillance (pour thread dédié)"""
        logger.info("🚀 Démarrage du monitoring Polymarket...")
        while True:
            for wallet in list(self.tracked_wallets):
                changes = self.detect_changes(wallet)
                for change in changes:
                    logger.info(f"🔔 Signal [{wallet[:6]}]: {change['type']} {change['amount']} (Asset: {change['asset_id'][:20]}...)")
                    if callback:
                        callback(change)
            
            time.sleep(interval)

# Instance globale
tracker = PolymarketTracker()
