# -*- coding: utf-8 -*-
"""
Module de suivi des traders Polymarket (Tracker) - Version Améliorée
Surveille les positions et l'activité des portefeuilles cibles via:
- Goldsky Subgraph (positions)
- Polygonscan API (transactions historiques)
- Gamma Markets API (prix marchés)
"""
import os
import requests
import time
import threading
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolymarketTracker")


class PolymarketTracker:
    """
    Tracker avancé pour Polymarket avec multiple sources de données.
    """

    # URLs des APIs
    GOLDSKY_POSITIONS = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
    GOLDSKY_ACTIVITY = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"
    GAMMA_API = "https://gamma-api.polymarket.com"
    POLYGONSCAN_API = "https://api.polygonscan.com/api"

    # Contrats Polymarket
    POLYMARKET_CONTRACTS = {
        'CTF_EXCHANGE': '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E',
        'NEG_RISK_CTF_EXCHANGE': '0xC5d563A36AE78145C45a50134d48A1215220f80a',
        'CONDITIONAL_TOKENS': '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045',
        'USDC_POLYGON': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    }

    def __init__(self, socketio=None):
        self.tracked_wallets = {}  # {address: {name, capital, percent, ...}}
        self.last_positions = {}   # {wallet_address: {asset_id: balance}}
        self.last_transactions = {}  # {wallet_address: last_tx_hash}
        self.callbacks = []
        self.running = False
        self.monitor_thread = None
        self.socketio = socketio # ✨ WebSocket instance

        # API Keys
        self.polygonscan_api_key = os.getenv('POLYGONSCAN_API_KEY', '')

        # Stats
        self.signals_detected = 0
        self.last_check = None

        # Cache marchés
        self._markets_cache = {}
        self._markets_cache_time = None

        logger.info("🔭 PolymarketTracker initialisé")
        if self.polygonscan_api_key:
            logger.info("   ✅ Polygonscan API configurée")
        else:
            logger.info("   ⚠️ Polygonscan API non configurée (historique limité)")

    def add_wallet(self, address: str, name: str = "Wallet", capital: float = 0, percent: float = 0):
        """Ajoute un wallet à la liste de surveillance avec sa config"""
        addr = address.lower()
        self.tracked_wallets[addr] = {
            'address': address,
            'name': name,
            'capital_allocated': capital,
            'percent_per_trade': percent,
            'added_at': datetime.now().isoformat()
        }
        logger.info(f"🔭 Wallet ajouté: {name} ({address[:10]}...) | Capital: ${capital} | %/trade: {percent}%")

    def remove_wallet(self, address: str):
        """Retire un wallet de la surveillance"""
        addr = address.lower()
        if addr in self.tracked_wallets:
            del self.tracked_wallets[addr]
            if addr in self.last_positions:
                del self.last_positions[addr]

    def add_callback(self, callback: Callable):
        """Ajoute un callback appelé lors de la détection d'un signal"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, signal: Dict):
        """Notifie tous les callbacks d'un nouveau signal"""
        for callback in self.callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"❌ Erreur callback: {e}")

    # =========================================================================
    # GOLDSKY SUBGRAPH - Positions actuelles
    # =========================================================================

    def get_user_positions(self, address: str) -> List[Dict]:
        """Récupère les positions actuelles d'un utilisateur via Goldsky Subgraph."""
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
            resp = requests.post(self.GOLDSKY_POSITIONS, json={'query': query}, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'].get('userBalances'):
                    return data['data']['userBalances']
            return []
        except Exception as e:
            logger.error(f"❌ Erreur get_user_positions: {e}")
            return []

    def detect_position_changes(self, address: str) -> List[Dict]:
        """Détecte les changements de position pour un wallet donné."""
        current_positions = self.get_user_positions(address)

        # Convertir en dictionnaire {asset_id: balance}
        current_map = {}
        for p in current_positions:
            asset_id = p.get('asset', {}).get('id') if isinstance(p.get('asset'), dict) else p.get('id')
            if asset_id:
                current_map[asset_id] = int(p.get('balance', 0))

        last_map = self.last_positions.get(address.lower(), {})
        changes = []
        wallet_info = self.tracked_wallets.get(address.lower(), {})

        # Détecter ACHATS (nouvelles positions ou augmentations)
        for asset_id, balance in current_map.items():
            old_balance = last_map.get(asset_id, 0)
            if balance > old_balance:
                diff = balance - old_balance

                # Enrichir avec infos marché
                market_info = self.get_market_info(asset_id)

                changes.append({
                    "type": "BUY",
                    "wallet": address,
                    "wallet_name": wallet_info.get('name', 'Unknown'),
                    "asset_id": asset_id,
                    "amount": diff,
                    "total_balance": balance,
                    "market": market_info,
                    "capital_allocated": wallet_info.get('capital_allocated', 0),
                    "percent_per_trade": wallet_info.get('percent_per_trade', 0),
                    "use_kelly": wallet_info.get('use_kelly', False), # ✨ Config Kelly
                    "timestamp": datetime.now().isoformat(),
                    "source": "goldsky"
                })

        # Détecter VENTES (réductions ou fermetures)
        for asset_id, old_balance in last_map.items():
            new_balance = current_map.get(asset_id, 0)
            if new_balance < old_balance:
                diff = old_balance - new_balance

                market_info = self.get_market_info(asset_id)

                changes.append({
                    "type": "SELL",
                    "wallet": address,
                    "wallet_name": wallet_info.get('name', 'Unknown'),
                    "asset_id": asset_id,
                    "amount": diff,
                    "remaining_balance": new_balance,
                    "market": market_info,
                    "timestamp": datetime.now().isoformat(),
                    "source": "goldsky"
                })

        # Mettre à jour l'état
        self.last_positions[address.lower()] = current_map
        return changes

    # =========================================================================
    # POLYGONSCAN API - Historique transactions
    # =========================================================================

    def get_recent_transactions(self, address: str, limit: int = 20) -> List[Dict]:
        """Récupère les transactions récentes d'un wallet via Polygonscan."""
        if not self.polygonscan_api_key:
            return []

        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': 1,
            'offset': limit,
            'sort': 'desc',
            'apikey': self.polygonscan_api_key
        }

        try:
            resp = requests.get(self.POLYGONSCAN_API, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1':
                    return data.get('result', [])
            return []
        except Exception as e:
            logger.error(f"❌ Erreur Polygonscan txlist: {e}")
            return []

    def get_token_transfers(self, address: str, limit: int = 20) -> List[Dict]:
        """Récupère les transferts de tokens ERC-20 via Polygonscan."""
        if not self.polygonscan_api_key:
            return []

        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'page': 1,
            'offset': limit,
            'sort': 'desc',
            'apikey': self.polygonscan_api_key
        }

        try:
            resp = requests.get(self.POLYGONSCAN_API, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1':
                    return data.get('result', [])
            return []
        except Exception as e:
            logger.error(f"❌ Erreur Polygonscan tokentx: {e}")
            return []

    def detect_polymarket_transactions(self, address: str) -> List[Dict]:
        """Détecte les transactions Polymarket récentes d'un wallet."""
        transactions = self.get_recent_transactions(address, limit=50)
        polymarket_txs = []

        contract_addresses = [c.lower() for c in self.POLYMARKET_CONTRACTS.values()]
        wallet_info = self.tracked_wallets.get(address.lower(), {})
        last_tx = self.last_transactions.get(address.lower(), '')

        for tx in transactions:
            # Arrêter si on a déjà vu cette transaction
            if tx.get('hash') == last_tx:
                break

            to_addr = tx.get('to', '').lower()
            if to_addr in contract_addresses:
                polymarket_txs.append({
                    'type': 'TRANSACTION',
                    'tx_hash': tx.get('hash'),
                    'wallet': address,
                    'wallet_name': wallet_info.get('name', 'Unknown'),
                    'to': tx.get('to'),
                    'value': int(tx.get('value', 0)) / 1e18,  # Wei to MATIC
                    'gas_used': int(tx.get('gasUsed', 0)),
                    'timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))).isoformat(),
                    'block': tx.get('blockNumber'),
                    'source': 'polygonscan'
                })

        # Mettre à jour le dernier hash vu
        if transactions:
            self.last_transactions[address.lower()] = transactions[0].get('hash', '')

        return polymarket_txs

    # =========================================================================
    # GAMMA MARKETS API - Infos marchés
    # =========================================================================

    def get_market_info(self, token_id: str) -> Optional[Dict]:
        """Récupère les informations d'un marché via Gamma API."""
        # Vérifier le cache (5 minutes)
        cache_key = token_id[:20]
        if cache_key in self._markets_cache:
            cached = self._markets_cache[cache_key]
            if datetime.now() - cached['time'] < timedelta(minutes=5):
                return cached['data']

        try:
            # Essayer l'API Gamma
            resp = requests.get(f"{self.GAMMA_API}/markets/{token_id}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                market_info = {
                    'question': data.get('question', 'Unknown Market'),
                    'slug': data.get('slug', ''),
                    'yes_price': data.get('outcomePrices', [0, 0])[0] if data.get('outcomePrices') else 0,
                    'no_price': data.get('outcomePrices', [0, 0])[1] if data.get('outcomePrices') else 0,
                    'volume': data.get('volume', 0),
                    'liquidity': data.get('liquidity', 0),
                }
                self._markets_cache[cache_key] = {'data': market_info, 'time': datetime.now()}
                return market_info
        except Exception as e:
            logger.debug(f"Gamma API error: {e}")

        return {'question': f'Market {token_id[:10]}...', 'slug': '', 'yes_price': 0, 'no_price': 0}

    def get_active_markets(self, limit: int = 100) -> List[Dict]:
        """Récupère les marchés actifs de Polymarket."""
        try:
            resp = requests.get(f"{self.GAMMA_API}/markets", params={'limit': limit, 'active': True}, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"❌ Erreur récupération marchés: {e}")
            return []

    # =========================================================================
    # MONITORING LOOP
    # =========================================================================

    def check_all_wallets(self) -> List[Dict]:
        """Vérifie tous les wallets suivis et retourne les signaux détectés."""
        all_signals = []
        self.last_check = datetime.now()

        for wallet_address in list(self.tracked_wallets.keys()):
            try:
                # ✨ Vérifier si le wallet est actif
                wallet_info = self.tracked_wallets.get(wallet_address, {})
                is_active = wallet_info.get('active', True)  # Par défaut actif
                
                if not is_active:
                    logger.debug(f"⏸️ Wallet {wallet_address[:10]}... est inactif, ignoré")
                    continue
                
                # 1. Vérifier les changements de positions (Goldsky)
                position_changes = self.detect_position_changes(wallet_address)
                for change in position_changes:
                    self.signals_detected += 1
                    logger.info(f"🔔 [{change['wallet_name']}] {change['type']} détecté - Asset: {change['asset_id'][:20]}...")
                    
                    # ✨ WebSocket Emission
                    if self.socketio:
                        self.socketio.emit('new_signal', change)
                        logger.debug("📡 Signal émis via WebSocket")

                    all_signals.append(change)
                    self._notify_callbacks(change)

                # 2. Vérifier les transactions Polymarket (Polygonscan)
                if self.polygonscan_api_key:
                    txs = self.detect_polymarket_transactions(wallet_address)
                    for tx in txs:
                        logger.debug(f"📡 TX Polymarket: {tx['tx_hash'][:20]}...")

            except Exception as e:
                logger.error(f"❌ Erreur vérification {wallet_address[:10]}: {e}")

        return all_signals

    def start_monitoring(self, interval: int = 30):
        """Démarre la boucle de monitoring en arrière-plan."""
        if self.running:
            logger.warning("⚠️ Monitoring déjà en cours")
            return

        self.running = True

        def monitor_loop():
            logger.info(f"🚀 Monitoring Polymarket démarré (intervalle: {interval}s)")
            while self.running:
                try:
                    signals = self.check_all_wallets()
                    if signals:
                        logger.info(f"📊 {len(signals)} signal(s) détecté(s)")
                except Exception as e:
                    logger.error(f"❌ Erreur monitoring loop: {e}")

                time.sleep(interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Arrête la boucle de monitoring."""
        self.running = False
        logger.info("🛑 Monitoring Polymarket arrêté")

    # =========================================================================
    # STATS & EXPORT
    # =========================================================================

    def get_stats(self) -> Dict:
        """Retourne les statistiques du tracker."""
        return {
            'tracked_wallets': len(self.tracked_wallets),
            'signals_detected': self.signals_detected,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'running': self.running,
            'polygonscan_enabled': bool(self.polygonscan_api_key),
            'wallets': [
                {
                    'address': w['address'],
                    'name': w['name'],
                    'capital': w.get('capital_allocated', 0),
                    'percent': w.get('percent_per_trade', 0)
                }
                for w in self.tracked_wallets.values()
            ]
        }

    def get_wallet_summary(self, address: str) -> Dict:
        """Retourne un résumé complet d'un wallet suivi."""
        addr = address.lower()
        wallet_info = self.tracked_wallets.get(addr, {})
        positions = self.last_positions.get(addr, {})

        # Enrichir avec les infos marchés
        positions_detailed = []
        for asset_id, balance in positions.items():
            market_info = self.get_market_info(asset_id)
            positions_detailed.append({
                'asset_id': asset_id,
                'balance': balance,
                'market': market_info
            })

        return {
            'wallet': wallet_info,
            'positions': positions_detailed,
            'position_count': len(positions)
        }


# Instance globale
tracker = PolymarketTracker()
