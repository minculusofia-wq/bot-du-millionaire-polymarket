# -*- coding: utf-8 -*-
"""
Insider Scanner - Detection de comportements suspects sur Polymarket
Scanne les marches actifs pour identifier les wallets avec des patterns de trading suspects.
"""
import os
import requests
import threading
import time
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InsiderScanner")


class SuspicionCriteria(Enum):
    """Criteres de detection de comportement suspect"""
    UNLIKELY_BET = "unlikely_bet"           # Pari sur outcome improbable
    ABNORMAL_BEHAVIOR = "abnormal_behavior" # Comportement anormal
    SUSPICIOUS_PROFILE = "suspicious_profile" # Profil suspect (nouveau wallet)


class ScoringPreset(Enum):
    """Presets de ponderation du scoring"""
    BALANCED = "balanced"
    PROFILE_PRIORITY = "profile_priority"
    BEHAVIOR_PRIORITY = "behavior_priority"
    BET_PRIORITY = "bet_priority"
    CUSTOM = "custom"


# Poids par preset
PRESET_WEIGHTS = {
    ScoringPreset.BALANCED: {'unlikely_bet': 35, 'abnormal_behavior': 35, 'suspicious_profile': 30},
    ScoringPreset.PROFILE_PRIORITY: {'unlikely_bet': 25, 'abnormal_behavior': 25, 'suspicious_profile': 50},
    ScoringPreset.BEHAVIOR_PRIORITY: {'unlikely_bet': 25, 'abnormal_behavior': 50, 'suspicious_profile': 25},
    ScoringPreset.BET_PRIORITY: {'unlikely_bet': 50, 'abnormal_behavior': 25, 'suspicious_profile': 25},
}


@dataclass
class InsiderAlert:
    """Structure d'une alerte insider"""
    id: str
    wallet_address: str
    suspicion_score: int
    market_question: str
    market_slug: str
    token_id: str
    bet_amount: float
    bet_outcome: str
    outcome_odds: float
    criteria_matched: List[str]
    wallet_stats: Dict
    scoring_mode: str
    timestamp: str
    dedup_key: str

    def to_dict(self) -> Dict:
        return asdict(self)


class InsiderScanner:
    """
    Scanne les marches Polymarket pour detecter des comportements suspects.
    """

    # API Endpoints
    GAMMA_API = "https://gamma-api.polymarket.com"
    GOLDSKY_POSITIONS = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
    GOLDSKY_ACTIVITY = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/0.0.4/gn"
    POLYGONSCAN_API = "https://api.polygonscan.com/api"

    # Categories de marches a scanner
    DEFAULT_CATEGORIES = ["politics", "sports", "crypto", "pop-culture"]

    def __init__(self, socketio=None, db_manager=None):
        self.socketio = socketio
        self.db_manager = db_manager
        self.polygonscan_api_key = os.getenv('POLYGONSCAN_API_KEY', '')

        # Scanner state
        self.running = False
        self.scan_thread = None
        self.scan_interval = 30  # seconds

        # Configuration - Seuils de detection (tous configurables)
        self.config = {
            # Seuils Unlikely Bet
            'min_bet_amount': 200.0,        # ✨ Abaissé de 1000 à 200
            'max_odds_threshold': 0.20,      # ✨ Augmenté de 0.10 à 0.20
            
            # Seuils Abnormal Behavior
            'dormant_days': 30,              # Jours d'inactivite
            'dormant_min_bet': 500.0,        # Mise min apres dormance ($)

            # Seuils Suspicious Profile
            'max_tx_count': 15,              # Max tx pour "nouveau" wallet
            'new_wallet_min_bet': 500.0,     # Mise min pour nouveau wallet ($)

            # Scoring
            'scoring_preset': ScoringPreset.BALANCED.value,
            'alert_threshold': 30,           # ✨ Abaissé de 60 à 30
            'categories': self.DEFAULT_CATEGORIES.copy(),

            # Poids custom (utilise si preset = custom)
            'custom_weights': {
                'unlikely_bet': 35,
                'abnormal_behavior': 35,
                'suspicious_profile': 30
            }
        }

    def set_polygonscan_key(self, api_key: str):
        """Met à jour la clé API Polygonscan à chaud"""
        self.polygonscan_api_key = api_key
        logger.info(f"✅ Clé Polygonscan mise à jour pour InsiderScanner ({api_key[:6]}...)")

        # Deduplication cache: {dedup_key: timestamp}
        self.recent_alerts = {}
        self.dedup_window = 3600  # 1 heure

        # Callbacks pour integrations externes
        self.callbacks = []

        # Cache pour eviter requetes repetees
        self._wallet_tx_cache = {}  # {address: {count, timestamp}}
        self._wallet_activity_cache = {}  # {address: {last_activity, timestamp}}
        self._market_cache = {}  # {token_id: {data, timestamp}}

        # Stats
        self.alerts_generated = 0
        self.markets_scanned = 0
        self.last_scan = None

        logger.info("🔍 InsiderScanner initialise")
        if self.polygonscan_api_key:
            logger.info("   ✅ Polygonscan API configuree")
        else:
            logger.info("   ⚠️ Polygonscan API non configuree (detection profil limitee)")

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    def set_config(self, new_config: Dict):
        """Met a jour la configuration du scanner"""
        for key, value in new_config.items():
            if key in self.config:
                self.config[key] = value

        logger.info(f"📝 Config mise a jour: preset={self.config['scoring_preset']}, threshold={self.config['alert_threshold']}")

    def get_config(self) -> Dict:
        """Retourne la configuration actuelle"""
        return {
            **self.config,
            'running': self.running,
            'alerts_generated': self.alerts_generated,
            'markets_scanned': self.markets_scanned,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None
        }

    def add_callback(self, callback: Callable):
        """Ajoute un callback pour notifications d'alertes"""
        self.callbacks.append(callback)

    def _get_weights(self) -> Dict:
        """Retourne les poids de scoring selon le preset actif"""
        preset_name = self.config['scoring_preset']

        if preset_name == ScoringPreset.CUSTOM.value:
            return self.config['custom_weights']

        try:
            preset = ScoringPreset(preset_name)
            return PRESET_WEIGHTS.get(preset, PRESET_WEIGHTS[ScoringPreset.BALANCED])
        except ValueError:
            return PRESET_WEIGHTS[ScoringPreset.BALANCED]

    # =========================================================================
    # DATA SOURCES
    # =========================================================================

    def get_markets_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Recupere les marches actifs par categorie via Gamma API"""
        try:
            params = {
                'limit': limit,
                'active': 'true',
                'tag': category,
                'order': 'volume',
                'ascending': 'false'
            }
            resp = requests.get(f"{self.GAMMA_API}/markets", params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"❌ Erreur get_markets_by_category ({category}): {e}")
            return []

    def get_all_active_markets(self, limit: int = 200) -> List[Dict]:
        """Recupere tous les marches actifs"""
        try:
            params = {'limit': limit, 'active': 'true'}
            resp = requests.get(f"{self.GAMMA_API}/markets", params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"❌ Erreur get_all_active_markets: {e}")
            return []

    def get_recent_market_activity(self, condition_id: str, limit: int = 100) -> List[Dict]:
        """Recupere l'activite recente sur un marche via Goldsky Activity Subgraph"""
        query = """
        {
          activities(
            first: %d,
            orderBy: timestamp,
            orderDirection: desc,
            where: {conditionId: "%s", type_in: ["BUY", "SELL"]}
          ) {
            id
            user
            type
            amount
            price
            timestamp
            asset {
              id
              condition {
                id
              }
            }
          }
        }
        """ % (limit, condition_id)

        try:
            resp = requests.post(self.GOLDSKY_ACTIVITY, json={'query': query}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('data', {}).get('activities', [])
            return []
        except Exception as e:
            logger.debug(f"Goldsky Activity error: {e}")
            return []

    def get_wallet_tx_count(self, address: str) -> int:
        """Recupere le nombre de transactions d'un wallet via Polygonscan (avec cache)"""
        if not self.polygonscan_api_key:
            return 999  # Assume pas nouveau si on ne peut pas verifier

        addr_lower = address.lower()

        # Verifier le cache (1 heure)
        if addr_lower in self._wallet_tx_cache:
            cached = self._wallet_tx_cache[addr_lower]
            if datetime.now() - cached['timestamp'] < timedelta(hours=1):
                return cached['count']

        try:
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'page': 1,
                'offset': 100,
                'sort': 'desc',
                'apikey': self.polygonscan_api_key
            }
            resp = requests.get(self.POLYGONSCAN_API, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1':
                    count = len(data.get('result', []))
                    self._wallet_tx_cache[addr_lower] = {'count': count, 'timestamp': datetime.now()}
                    return count
            return 0
        except Exception as e:
            logger.debug(f"Polygonscan tx count error: {e}")
            return 999

    def get_wallet_last_activity(self, address: str) -> Optional[datetime]:
        """Recupere la date de derniere activite d'un wallet (avec cache)"""
        if not self.polygonscan_api_key:
            return None

        addr_lower = address.lower()

        # Verifier le cache (1 heure)
        if addr_lower in self._wallet_activity_cache:
            cached = self._wallet_activity_cache[addr_lower]
            if datetime.now() - cached['timestamp'] < timedelta(hours=1):
                return cached['last_activity']

        try:
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'page': 1,
                'offset': 1,
                'sort': 'desc',
                'apikey': self.polygonscan_api_key
            }
            resp = requests.get(self.POLYGONSCAN_API, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1' and data.get('result'):
                    ts = int(data['result'][0].get('timeStamp', 0))
                    last_activity = datetime.fromtimestamp(ts) if ts > 0 else None
                    self._wallet_activity_cache[addr_lower] = {
                        'last_activity': last_activity,
                        'timestamp': datetime.now()
                    }
                    return last_activity
            return None
        except Exception as e:
            logger.debug(f"Polygonscan last activity error: {e}")
            return None

    def get_wallet_performance(self, address: str) -> Dict:
        """Calcule les stats de performance d'un wallet via Polymarket Subgraph"""
        query = """
        {
          userBalances(first: 200, where: {user: "%s"}) {
            id
            balance
            cost
            asset {
              id
            }
          }
        }
        """ % address.lower()

        stats = {
            'pnl': 0.0,
            'win_rate': 0.0,
            'roi': 0.0,
            'total_trades': 0
        }

        try:
            resp = requests.post(self.GOLDSKY_POSITIONS, json={'query': query}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                balances = data.get('data', {}).get('userBalances', [])

                total_cost = 0
                total_value = 0
                wins = 0
                trades = 0

                for b in balances:
                    balance = float(b.get('balance', 0)) / 1e6  # USDC 6 decimals
                    cost = float(b.get('cost', 0)) / 1e6

                    if balance > 0.01:  # Filtrer positions negligeables
                        trades += 1
                        total_cost += cost
                        total_value += balance
                        if balance > cost:
                            wins += 1

                if trades > 0:
                    stats['total_trades'] = trades
                    stats['win_rate'] = round((wins / trades) * 100, 1)
                    stats['pnl'] = round(total_value - total_cost, 2)
                    if total_cost > 0:
                        stats['roi'] = round(((total_value - total_cost) / total_cost) * 100, 1)

        except Exception as e:
            logger.debug(f"Error getting wallet performance: {e}")

        return stats

    # =========================================================================
    # SCORING ALGORITHM
    # =========================================================================

    def calculate_suspicion_score(self, wallet: str, bet_amount: float,
                                   outcome_odds: float) -> tuple:
        """
        Calcule le score de suspicion (0-100) avec les poids configurables.
        Retourne: (score, liste des criteres matches, details)
        """
        weights = self._get_weights()
        score = 0
        matched_criteria = []
        details = {}

        # 1. UNLIKELY BET DETECTION
        min_bet = self.config['min_bet_amount']
        max_odds = self.config['max_odds_threshold']

        if bet_amount >= min_bet and outcome_odds <= max_odds:
            score += weights['unlikely_bet']
            matched_criteria.append(SuspicionCriteria.UNLIKELY_BET.value)
            details['unlikely_bet'] = {
                'bet_amount': bet_amount,
                'odds': outcome_odds,
                'thresholds': {'min_bet': min_bet, 'max_odds': max_odds}
            }
            logger.debug(f"  [UNLIKELY_BET] ${bet_amount:.2f} @ {outcome_odds:.2%} odds")

        # 2. ABNORMAL BEHAVIOR - Wallet dormant qui revient
        dormant_days = self.config['dormant_days']
        dormant_min_bet = self.config['dormant_min_bet']

        last_activity = self.get_wallet_last_activity(wallet)
        if last_activity:
            days_since_activity = (datetime.now() - last_activity).days
            if days_since_activity > dormant_days and bet_amount >= dormant_min_bet:
                score += weights['abnormal_behavior']
                matched_criteria.append(SuspicionCriteria.ABNORMAL_BEHAVIOR.value)
                details['abnormal_behavior'] = {
                    'days_dormant': days_since_activity,
                    'bet_amount': bet_amount,
                    'thresholds': {'dormant_days': dormant_days, 'min_bet': dormant_min_bet}
                }
                logger.debug(f"  [ABNORMAL] Dormant {days_since_activity} jours, mise ${bet_amount:.2f}")

        # 3. SUSPICIOUS PROFILE - Nouveau wallet
        max_tx = self.config['max_tx_count']
        new_wallet_min = self.config['new_wallet_min_bet']

        tx_count = self.get_wallet_tx_count(wallet)
        if tx_count < max_tx and bet_amount >= new_wallet_min:
            score += weights['suspicious_profile']
            matched_criteria.append(SuspicionCriteria.SUSPICIOUS_PROFILE.value)
            details['suspicious_profile'] = {
                'tx_count': tx_count,
                'bet_amount': bet_amount,
                'thresholds': {'max_tx': max_tx, 'min_bet': new_wallet_min}
            }
            logger.debug(f"  [SUSPICIOUS_PROFILE] Nouveau wallet ({tx_count} tx), mise ${bet_amount:.2f}")

        return score, matched_criteria, details

    # =========================================================================
    # ALERT GENERATION
    # =========================================================================

    def _generate_dedup_key(self, wallet: str, market_slug: str) -> str:
        """Genere une cle de deduplication"""
        return f"{wallet.lower()}_{market_slug}"

    def _is_duplicate(self, dedup_key: str) -> bool:
        """Verifie si une alerte a deja ete generee dans la fenetre de dedup"""
        if dedup_key in self.recent_alerts:
            last_time = self.recent_alerts[dedup_key]
            if (datetime.now() - last_time).total_seconds() < self.dedup_window:
                return True
        return False

    def _cleanup_dedup_cache(self):
        """Nettoie les entrees expirees du cache de dedup"""
        now = datetime.now()
        expired = [k for k, v in self.recent_alerts.items()
                   if (now - v).total_seconds() > self.dedup_window]
        for k in expired:
            del self.recent_alerts[k]

    def process_activity(self, activity: Dict, market: Dict) -> Optional[InsiderAlert]:
        """Traite une activite et genere une alerte si suspecte"""
        wallet = activity.get('user', '')
        if not wallet:
            return None

        # Calculer le montant en USD
        amount_raw = int(activity.get('amount', 0))
        bet_amount = amount_raw / 1e6  # USDC 6 decimals

        # Ignorer les petits paris
        if bet_amount < 100:
            return None

        # Infos marche
        market_slug = market.get('slug', 'unknown')
        market_question = market.get('question', 'Unknown Market')
        token_id = activity.get('asset', {}).get('id', '') if isinstance(activity.get('asset'), dict) else ''

        # Determiner l'outcome et les odds
        outcome_prices = market.get('outcomePrices', [])
        activity_type = activity.get('type', 'BUY')

        # Parser le prix de l'activite ou utiliser les odds du marche
        price = float(activity.get('price', 0)) / 1e6 if activity.get('price') else 0.5

        if outcome_prices and len(outcome_prices) >= 2:
            yes_price = float(outcome_prices[0]) if outcome_prices[0] else 0.5
            no_price = float(outcome_prices[1]) if outcome_prices[1] else 0.5
            # Determiner quel outcome
            if price > 0 and price < 0.5:
                outcome_odds = price
                bet_outcome = "NO" if yes_price > 0.5 else "YES"
            else:
                outcome_odds = min(yes_price, no_price)
                bet_outcome = "NO" if yes_price > 0.5 else "YES"
        else:
            outcome_odds = price if price > 0 else 0.5
            bet_outcome = "YES"

        # Verifier la deduplication
        dedup_key = self._generate_dedup_key(wallet, market_slug)
        if self._is_duplicate(dedup_key):
            return None

        # Calculer le score de suspicion
        score, matched_criteria, _ = self.calculate_suspicion_score(wallet, bet_amount, outcome_odds)

        # Filtrer selon le seuil
        if score < self.config['alert_threshold']:
            return None

        # Recuperer les stats du wallet
        wallet_stats = self.get_wallet_performance(wallet)

        # Generer l'alerte
        alert = InsiderAlert(
            id=f"alert_{int(datetime.now().timestamp() * 1000)}_{wallet[:8]}",
            wallet_address=wallet,
            suspicion_score=score,
            market_question=market_question,
            market_slug=market_slug,
            token_id=token_id,
            bet_amount=bet_amount,
            bet_outcome=bet_outcome,
            outcome_odds=outcome_odds,
            criteria_matched=matched_criteria,
            wallet_stats=wallet_stats,
            scoring_mode=self.config['scoring_preset'],
            timestamp=datetime.now().isoformat(),
            dedup_key=dedup_key
        )

        # Marquer comme vu
        self.recent_alerts[dedup_key] = datetime.now()

        return alert

    # =========================================================================
    # MAIN SCAN LOOP
    # =========================================================================

    def scan_all_markets(self) -> List[InsiderAlert]:
        """Scanne tous les marches configures pour activite suspecte"""
        all_alerts = []
        self._cleanup_dedup_cache()

        categories = self.config.get('categories', self.DEFAULT_CATEGORIES)

        for category in categories:
            try:
                markets = self.get_markets_by_category(category, limit=30)
                self.markets_scanned += len(markets)

                for market in markets:
                    condition_id = market.get('conditionId', '')
                    if not condition_id:
                        continue

                    # Recuperer l'activite recente sur ce marche
                    activities = self.get_recent_market_activity(condition_id, limit=50)

                    for activity in activities:
                        # Ne traiter que les achats (pas les ventes)
                        if activity.get('type') != 'BUY':
                            continue

                        alert = self.process_activity(activity, market)
                        if alert:
                            all_alerts.append(alert)
                            self.alerts_generated += 1

                            # Emettre via WebSocket
                            if self.socketio:
                                self.socketio.emit('insider_alert', alert.to_dict())

                            # Sauvegarder en DB
                            if self.db_manager:
                                try:
                                    self.db_manager.save_insider_alert(alert.to_dict())
                                except Exception as e:
                                    logger.error(f"Erreur sauvegarde alerte: {e}")

                            # Notifier les callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(alert)
                                except Exception as e:
                                    logger.error(f"Callback error: {e}")

                            logger.info(f"🚨 ALERTE Score {alert.suspicion_score} | {alert.wallet_address[:10]}... | ${alert.bet_amount:.2f} sur '{market_slug[:30]}...'")

                    # Petit delai pour eviter rate limiting
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ Erreur scan categorie {category}: {e}")

        self.last_scan = datetime.now()
        return all_alerts

    def start_scanning(self, interval: int = None):
        """Demarre la boucle de scan en arriere-plan"""
        if self.running:
            logger.warning("⚠️ Scanner deja en cours")
            return

        if interval:
            self.scan_interval = interval

        self.running = True

        def scan_loop():
            logger.info(f"🚀 Insider Scanner demarre (intervalle: {self.scan_interval}s)")
            while self.running:
                try:
                    alerts = self.scan_all_markets()
                    if alerts:
                        logger.info(f"📊 {len(alerts)} alerte(s) generee(s)")
                except Exception as e:
                    logger.error(f"❌ Erreur scan loop: {e}")

                time.sleep(self.scan_interval)

        self.scan_thread = threading.Thread(target=scan_loop, daemon=True)
        self.scan_thread.start()

    def stop_scanning(self):
        """Arrete la boucle de scan"""
        self.running = False
        logger.info("🛑 Insider Scanner arrete")

    def get_wallet_positions(self, address: str) -> List[Dict]:
        """Recupere les positions d'un wallet via Goldsky"""
        query = """
        {
          userBalances(first: 100, where: {user: "%s", balance_gt: 0}) {
            id
            balance
            cost
            asset {
              id
              symbol
              condition {
                id
                slug
                question
              }
            }
          }
        }
        """ % address.lower()

        try:
            resp = requests.post(self.GOLDSKY_POSITIONS, json={'query': query}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('data', {}).get('userBalances', [])
        except Exception as e:
            logger.debug(f"Error getting wallet positions: {e}")
        return []

    def get_wallet_tx_history(self, address: str, limit: int = 20) -> List[Dict]:
        """Recupere l'historique des transactions via Polygonscan"""
        if not self.polygonscan_api_key:
            return []

        try:
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'page': 1,
                'offset': limit,
                'sort': 'desc',
                'apikey': self.polygonscan_api_key
            }
            resp = requests.get(self.POLYGONSCAN_API, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1':
                    return data.get('result', [])
        except Exception as e:
            logger.debug(f"Polygonscan history error: {e}")
        return []

    def _analyze_wallet_stats(self, address: str, positions: List[Dict], activity: Optional[datetime], history: List[Dict]) -> Dict:
        """Analyse les donnees brutes pour generer des statistiques complètes"""
        stats = {
            'pnl': 0.0,
            'win_rate': 0.0,
            'roi': 0.0,
            'total_trades': 0,
            'active_positions': len(positions),
            'last_activity': activity.isoformat() if activity else None,
            'tx_count': len(history) if self.polygonscan_api_key else 0
        }

        # Calcul PnL et Winrate basique sur les positions actuelles (unrealized + realized mix via cost)
        total_cost = 0
        total_value = 0
        wins = 0
        
        for pos in positions:
            balance = float(pos.get('balance', 0)) / 1e6
            cost = float(pos.get('cost', 0)) / 1e6
            
            if balance > 0.01:
                stats['total_trades'] += 1
                total_cost += cost
                total_value += balance
                if balance > cost:
                    wins += 1

        stats['pnl'] = round(total_value - total_cost, 2)
        if stats['total_trades'] > 0:
            stats['win_rate'] = round((wins / stats['total_trades']) * 100, 1)
        if total_cost > 0:
            stats['roi'] = round(((total_value - total_cost) / total_cost) * 100, 1)

        # Si on a l'historique Polygonscan, on pourrait affiner le tx_count
        # Mais pour l'instant on utilise ce qu'on a.
        return stats

    def profile_wallet(self, wallet_address: str):
        """Profile un wallet à la demande (sans créer d'alerte)"""
        if not wallet_address:
            return

        logger.info(f"🔍 Profiling manuel du wallet: {wallet_address}")
        self._scan_specific_wallet(wallet_address)

    def _scan_specific_wallet(self, wallet_address: str):
        """Scanne un wallet spécifique et met à jour ses stats en DB"""
        try:
            # 1. Recuperer les donnees
            last_activity = self.get_wallet_last_activity(wallet_address)
            positions = self.get_wallet_positions(wallet_address)
            tx_history = self.get_wallet_tx_history(wallet_address)
            
            # 2. Analyser
            stats = self._analyze_wallet_stats(wallet_address, positions, last_activity, tx_history)
            
            logger.info(f"📊 Stats profiling {wallet_address}: PnL=${stats['pnl']} WinRate={stats['win_rate']}%")

            # 3. Mettre a jour la DB
            # On calcule un score indicatif
            score = 0
            if stats['pnl'] > 1000 and stats['win_rate'] > 60: score = 60
            if stats['pnl'] > 5000 and stats['win_rate'] > 70: score = 80
            if stats['pnl'] < -500: score = 10 # Bad performer
            
            if self.db_manager:
                # 🚀 Mise à jour complète du wallet avec les nouvelles stats
                self.db_manager.save_insider_wallet({
                    'address': wallet_address.lower(),
                    'pnl': stats['pnl'],
                    'win_rate': stats['win_rate'],
                    'notes': f"Profilé le {datetime.now().strftime('%d/%m %H:%M')}"
                })
                
                # Optionnel: On peut aussi garder l'update direct pour les champs spécifiques si besoin
                self.db_manager._execute('''
                    UPDATE saved_insider_wallets
                    SET last_activity = ?, total_alerts = ?
                    WHERE address = ?
                ''', (
                    datetime.now().isoformat(),
                    stats['total_trades'],
                    wallet_address.lower()
                ), commit=True)
                
        except Exception as e:
            logger.error(f"❌ Erreur scan spécifique {wallet_address}: {e}")

    def get_stats(self) -> Dict:
        """Retourne les statistiques du scanner"""
        return {
            'running': self.running,
            'alerts_generated': self.alerts_generated,
            'markets_scanned': self.markets_scanned,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None,
            'enabled_categories': self.config.get('categories', []),
            'alert_threshold': self.config.get('alert_threshold', 60),
            'scan_interval': self.scan_interval,
            'scoring_preset': self.config.get('scoring_preset', 'balanced')
        }


# Instance globale (sera initialisee avec socketio et db_manager dans bot.py)
insider_scanner = InsiderScanner()
