# -*- coding: utf-8 -*-
"""
HFT Trade Monitor - Surveillance temps réel des trades HFT
Utilise Goldsky Subgraph pour détecter les changements de positions.
Optimisé pour une latence minimale sur les marchés 15-min crypto.

Optimisations v3.1:
- Polling réduit à 2 secondes
- Wallets pollés en parallèle (ThreadPoolExecutor)
- Cache Gamma API avec TTL 30s
- Pré-chargement positions au démarrage
"""
import os
import threading
import time
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HFTTradeMonitor")


@dataclass
class HFTSignal:
    """Signal de trade HFT détecté"""
    id: str
    wallet_address: str
    wallet_name: str
    token_id: str
    condition_id: str
    side: str           # BUY ou SELL
    price: float
    size: float         # En shares
    value_usd: float    # En USD
    market_question: str
    crypto_asset: str   # BTC, ETH
    direction: str      # UP, DOWN
    tx_hash: str
    timestamp: datetime
    latency_ms: int     # Temps entre trade on-chain et détection

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


class HFTTradeMonitor:
    """
    Moniteur de trades HFT ultra-rapide.
    Utilise Goldsky Subgraph pour détecter les changements de positions.
    """

    # APIs
    GOLDSKY_POSITIONS = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
    GAMMA_API = "https://gamma-api.polymarket.com"

    def __init__(self, market_discovery=None):
        self.market_discovery = market_discovery
        self.tracked_wallets: Dict[str, Dict] = {}  # {address: config}
        self.callbacks: List[Callable] = []

        # État
        self._running = False
        self._poll_thread = None
        self._poll_interval = 2  # 2 secondes - optimisé pour HFT (était 5s)

        # Cache positions précédentes pour détecter les changements
        self._last_positions: Dict[str, Dict] = {}  # {wallet: {asset_id: balance}}

        # Cache pour éviter les doublons de signaux
        self._processed_signals: Set[str] = set()
        self._max_cache_size = 500

        # Cache Gamma API avec TTL (optimisation latence)
        self._market_cache: Dict[str, Tuple[Dict, float]] = {}  # {token_id: (data, timestamp)}
        self._cache_ttl = 30  # 30 secondes TTL

        # Buffer de signaux récents
        self.recent_signals: deque = deque(maxlen=100)

        # Stats
        self.signals_detected = 0
        self.last_signal_time: Optional[datetime] = None
        self.polls_count = 0
        self.cache_hits = 0
        self.cache_misses = 0

        # ThreadPool pour polling parallèle
        self._executor: Optional[ThreadPoolExecutor] = None

        logger.info("HFTTradeMonitor initialisé (Goldsky + Gamma, polling 2s, parallèle)")

    def add_wallet(self, address: str, name: str = "HFT Wallet", config: Dict = None):
        """Ajoute un wallet à surveiller"""
        addr = address.lower()
        self.tracked_wallets[addr] = {
            'address': addr,
            'name': name,
            'config': config or {},
            'added_at': datetime.now().isoformat()
        }
        # Initialiser le cache de positions
        self._last_positions[addr] = {}
        logger.info(f"HFT Wallet ajouté: {name} ({addr[:10]}...)")

    def remove_wallet(self, address: str):
        """Retire un wallet de la surveillance"""
        addr = address.lower()
        if addr in self.tracked_wallets:
            del self.tracked_wallets[addr]
        if addr in self._last_positions:
            del self._last_positions[addr]
        logger.info(f"HFT Wallet retiré: {addr[:10]}...")

    def add_callback(self, callback: Callable):
        """Ajoute un callback appelé lors de la détection d'un signal"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, signal: HFTSignal):
        """Notifie tous les callbacks"""
        for callback in self.callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Erreur callback: {e}")

    # =========================================================================
    # GOLDSKY SUBGRAPH - Positions actuelles
    # =========================================================================

    def _get_user_positions(self, address: str) -> Dict[str, float]:
        """Récupère les positions actuelles d'un wallet via Goldsky"""
        query = """
        {
          userBalances(first: 100, where: {user: "%s", balance_gt: "0"}) {
            id
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
            resp = requests.post(
                self.GOLDSKY_POSITIONS,
                json={'query': query},
                timeout=3,  # Réduit de 10s à 3s pour HFT
                headers={'Content-Type': 'application/json'}
            )

            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'].get('userBalances'):
                    positions = {}
                    for bal in data['data']['userBalances']:
                        asset_id = bal['asset']['id']
                        # Balance en micro-unités, convertir en unités normales
                        balance = float(bal['balance']) / 1e6
                        positions[asset_id] = balance
                    return positions
            return {}
        except Exception as e:
            logger.debug(f"Erreur get_user_positions: {e}")
            return {}

    # =========================================================================
    # GAMMA API - Infos marché
    # =========================================================================

    def _get_market_info(self, token_id: str) -> Dict:
        """Récupère les infos d'un marché via Gamma API (avec cache TTL 30s)"""
        now = time.time()

        # Vérifier le cache
        if token_id in self._market_cache:
            cached_data, cached_time = self._market_cache[token_id]
            if now - cached_time < self._cache_ttl:
                self.cache_hits += 1
                return cached_data

        self.cache_misses += 1

        try:
            resp = requests.get(
                f"{self.GAMMA_API}/markets",
                params={'clob_token_ids': token_id},
                timeout=3  # Réduit de 5s à 3s
            )
            if resp.status_code == 200:
                markets = resp.json()
                if markets and len(markets) > 0:
                    market = markets[0]
                    result = {
                        'question': market.get('question', ''),
                        'condition_id': market.get('condition_id', ''),
                        'yes_price': float(market.get('outcomePrices', '["0.5","0.5"]').strip('[]').split(',')[0].strip('"') or 0.5),
                    }
                    # Stocker en cache
                    self._market_cache[token_id] = (result, now)
                    return result
        except Exception as e:
            logger.debug(f"Erreur get_market_info: {e}")

        return {}

    # =========================================================================
    # DÉTECTION DE TRADES
    # =========================================================================

    def _detect_position_changes(self, wallet_addr: str, wallet_info: Dict) -> List[HFTSignal]:
        """Détecte les changements de position pour un wallet"""
        signals = []
        detection_time = datetime.now()

        # Récupérer positions actuelles
        current_positions = self._get_user_positions(wallet_addr)
        previous_positions = self._last_positions.get(wallet_addr, {})

        # Détecter les changements
        all_assets = set(current_positions.keys()) | set(previous_positions.keys())

        for asset_id in all_assets:
            current_bal = current_positions.get(asset_id, 0)
            previous_bal = previous_positions.get(asset_id, 0)
            diff = current_bal - previous_bal

            # Seuil minimum de changement ($1)
            if abs(diff) < 1:
                continue

            # Créer un ID unique pour éviter les doublons
            signal_id = f"{wallet_addr[:8]}_{asset_id[:16]}_{int(detection_time.timestamp())}"
            if signal_id in self._processed_signals:
                continue

            # Déterminer le side
            side = 'BUY' if diff > 0 else 'SELL'

            # Récupérer les infos du marché
            market_info = self._get_market_info(asset_id)

            # Vérifier si c'est un marché 15-min crypto (via market_discovery)
            crypto_asset = ''
            direction = ''
            market_question = market_info.get('question', '')

            if self.market_discovery:
                market_data = self.market_discovery.get_market_by_token(asset_id)
                if market_data:
                    crypto_asset = market_data.crypto_asset
                    direction = market_data.direction
                    market_question = market_data.question

            # Estimer le prix
            price = market_info.get('yes_price', 0.5)
            if price <= 0:
                price = 0.5

            # Créer le signal
            signal = HFTSignal(
                id=signal_id,
                wallet_address=wallet_addr,
                wallet_name=wallet_info.get('name', 'HFT Wallet'),
                token_id=asset_id,
                condition_id=market_info.get('condition_id', ''),
                side=side,
                price=price,
                size=abs(diff),
                value_usd=abs(diff) * price,
                market_question=market_question,
                crypto_asset=crypto_asset,
                direction=direction,
                tx_hash='',
                timestamp=detection_time,
                latency_ms=0
            )

            signals.append(signal)
            self._processed_signals.add(signal_id)

            # Nettoyer le cache si trop grand
            if len(self._processed_signals) > self._max_cache_size:
                self._processed_signals = set(list(self._processed_signals)[-250:])

        # Mettre à jour le cache
        self._last_positions[wallet_addr] = current_positions

        return signals

    # =========================================================================
    # POLLING LOOP (PARALLÈLE)
    # =========================================================================

    def _poll_all_wallets_parallel(self) -> List[HFTSignal]:
        """Poll tous les wallets en parallèle pour réduire la latence"""
        all_signals = []

        if not self.tracked_wallets:
            return all_signals

        # Utiliser ThreadPoolExecutor pour polling parallèle
        with ThreadPoolExecutor(max_workers=min(10, len(self.tracked_wallets) + 1)) as executor:
            futures = {
                executor.submit(self._detect_position_changes, addr, info): addr
                for addr, info in self.tracked_wallets.items()
            }

            for future in as_completed(futures, timeout=self._poll_interval + 3):
                try:
                    signals = future.result()
                    all_signals.extend(signals)
                except Exception as e:
                    wallet_addr = futures[future]
                    logger.debug(f"Erreur polling {wallet_addr[:10]}...: {e}")

        return all_signals

    def _poll_loop(self):
        """Boucle de polling principale (optimisée avec parallélisation)"""
        logger.info(f"HFT Poll loop démarrée (interval: {self._poll_interval}s, parallèle)")

        while self._running:
            poll_start = time.time()

            try:
                self.polls_count += 1

                # Polling parallèle de tous les wallets
                signals = self._poll_all_wallets_parallel()

                for signal in signals:
                    if not self._running:
                        break

                    self.signals_detected += 1
                    self.last_signal_time = signal.timestamp
                    self.recent_signals.append(signal)

                    logger.info(
                        f"⚡ HFT Signal: {signal.wallet_name} | {signal.side} "
                        f"{signal.crypto_asset or 'TOKEN'} | ${signal.value_usd:.2f}"
                    )

                    # Notifier les callbacks
                    self._notify_callbacks(signal)

            except Exception as e:
                logger.error(f"Erreur poll loop: {e}")

            # Calculer le temps restant à attendre
            poll_duration = time.time() - poll_start
            sleep_time = max(0, self._poll_interval - poll_duration)

            if sleep_time > 0:
                time.sleep(sleep_time)

    # =========================================================================
    # CONTROL
    # =========================================================================

    def _preload_positions_parallel(self):
        """Pré-charge les positions de tous les wallets en parallèle"""
        if not self.tracked_wallets:
            return

        logger.info(f"Pré-chargement positions HFT ({len(self.tracked_wallets)} wallets)...")

        with ThreadPoolExecutor(max_workers=min(10, len(self.tracked_wallets) + 1)) as executor:
            futures = {
                executor.submit(self._get_user_positions, addr): addr
                for addr in self.tracked_wallets.keys()
            }

            for future in as_completed(futures, timeout=15):
                wallet_addr = futures[future]
                try:
                    positions = future.result()
                    self._last_positions[wallet_addr] = positions
                    logger.info(f"  ✓ {wallet_addr[:10]}...: {len(positions)} positions")
                except Exception as e:
                    logger.warning(f"  ✗ {wallet_addr[:10]}...: {e}")
                    self._last_positions[wallet_addr] = {}

    def start(self):
        """Démarre le monitoring"""
        if self._running:
            logger.warning("HFTTradeMonitor déjà en cours")
            return

        self._running = True

        # Pré-charger les positions en parallèle (évite faux signaux au démarrage)
        self._preload_positions_parallel()

        # Démarrer le polling
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        logger.info(f"HFTTradeMonitor démarré ({len(self.tracked_wallets)} wallets, polling {self._poll_interval}s)")

    def stop(self):
        """Arrête le monitoring"""
        self._running = False
        logger.info("HFTTradeMonitor arrêté")

    def get_recent_signals(self, limit: int = 50) -> List[Dict]:
        """Retourne les signaux récents"""
        return [s.to_dict() for s in list(self.recent_signals)[-limit:]]

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        cache_total = self.cache_hits + self.cache_misses
        cache_hit_rate = round(self.cache_hits / max(1, cache_total) * 100, 1)

        return {
            'running': self._running,
            'tracked_wallets': len(self.tracked_wallets),
            'signals_detected': self.signals_detected,
            'last_signal': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'poll_interval': self._poll_interval,
            'polls_count': self.polls_count,
            'recent_signals_count': len(self.recent_signals),
            # Nouvelles stats cache
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self._market_cache)
        }
