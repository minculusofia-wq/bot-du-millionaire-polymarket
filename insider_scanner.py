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





@dataclass
class InsiderAlert:
    """Structure d'une alerte insider"""
    id: str
    wallet_address: str
    alert_type: str  # [NEW] Type principal de l'alerte (ex: "FRESH_WALLET", "RISKY_BET")
    market_question: str
    market_slug: str
    market_url: str  # [NEW] URL directe vers le marche
    token_id: str
    bet_amount: float
    bet_outcome: str
    outcome_odds: float
    trigger_details: str # [NEW] Details humains du declencheur (ex: "New Wallet (>500$)")
    bet_details: str     # [NEW] Description precise du pari (ex: "$600 on NO @ 0.30")
    wallet_stats: Dict
    timestamp: str
    dedup_key: str
    suspicion_score: int = 70  # Score de suspicion (requis par DB)
    nickname: str = ""

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

        # Configuration - Seuils de detection (Triggers Independants)
        self.config = {
            # TRIGGER A: RISKY BET (Le Sniper)
            # Detecte les paris sur cotes faibles ou gros montants
            'risky_bet': {
                'enabled': True,
                'min_amount': 50.0,      # Seuil min pour analyser
                'max_odds': 0.35,        # Cote faible (< 35%)
                'high_amount': 1000.0    # Ou tres gros montant (> 1000$)
            },
            
            # TRIGGER B: WHALE WAKEUP (Le Revenant)
            # Detecte les wallets inactifs qui reviennent
            'whale_wakeup': {
                'enabled': True,
                'min_amount': 100.0,     # Seuil moyen
                'dormant_days': 30       # Jours d'inactivite
            },

            # TRIGGER C: FRESH WALLET (Le Nouveau)
            # Detecte les nouveaux wallets avec GROSSE mise
            'fresh_wallet': {
                'enabled': True,
                'max_tx': 5,             # Nouveau wallet
                'min_amount': 500.0      # STRICT: Que les gros montants
            },

            'categories': self.DEFAULT_CATEGORIES.copy()
        }

        # Deduplication cache: {dedup_key: timestamp}
        self.recent_alerts = {}
        self.dedup_window = 3600  # 1 heure

        # Callbacks pour integrations externes
        self.callbacks = []

        # Cache pour eviter requetes repetees
        self._wallet_tx_cache = {}  # {address: {count, timestamp}}
        self._wallet_activity_cache = {}  # {address: {last_activity, timestamp}}
        self._market_cache = {}  # {token_id: {data, timestamp}}
        self._market_snapshots = {} # [NEW] {condition_id: {user: balance}} pour detection de variation (diff)

        # Stats
        self.alerts_generated = 0
        self.markets_scanned = 0
        self.last_scan = None

        logger.info("🔍 InsiderScanner initialise")
        if self.polygonscan_api_key:
            logger.info("   ✅ Polygonscan API configuree")
        else:
            logger.info("   ⚠️ Polygonscan API non configuree (detection profil limitee)")
        
        # Charger la config persistante
        self.load_config_from_file()

    def set_polygonscan_key(self, api_key: str):
        """Met à jour la clé API Polygonscan à chaud"""
        self.polygonscan_api_key = api_key
        logger.info(f"✅ Clé Polygonscan mise à jour pour InsiderScanner ({api_key[:6]}...)")

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    def set_config(self, new_config: Dict):
        """Met a jour la configuration du scanner avec fusion intelligente et sauvegarde"""
        for key, value in new_config.items():
            # Si c'est un dictionnaire (ex: un trigger), on merge au lieu d'ecraser
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                self.config[key].update(value)
            elif key in self.config:
                self.config[key] = value

        self.save_config_to_file()
        logger.info(f"📝 Config mise a jour et sauvegardee.")

    def save_config_to_file(self):
        """Sauvegarde la configuration dans un fichier JSON"""
        try:
            import json
            with open('insider_config.json', 'w') as f:
                # Save purely the config dict, not runtime state like running/stats
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde config: {e}")

    def load_config_from_file(self):
        """Charge la configuration depuis un fichier JSON"""
        try:
            import json
            if os.path.exists('insider_config.json'):
                with open('insider_config.json', 'r') as f:
                    saved_config = json.load(f)
                    
                    # Merge loaded config into default config
                    for key, value in saved_config.items():
                         if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                            self.config[key].update(value)
                         else:
                            self.config[key] = value
                logger.info("✅ Configuration chargée depuis insider_config.json")
        except Exception as e:
            logger.error(f"❌ Erreur chargement config: {e}")

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

    def get_recent_market_activity(self, condition_id: str, limit: int = 300) -> List[Dict]:
        """
        Recupere les NOUVELLES positions ou AUGMENTATIONS de positions via snapshot diff.
        Ceci permet de detecter les "achats recents" meme sans API d'historique de trades.
        """
        if not condition_id:
            return []

        # 1. Recuperer l'etat ACTUEL des balances (Top N holders pour avoir une bonne couverture)
        # On ne filtre pas par high balance pour voir les petits insiders.
        query = """
        {
          userBalances(
            first: %d,
            orderBy: balance,
            orderDirection: desc,
            where: { asset_: { condition: "%s" }, balance_gt: "0" } 
          ) {
            id
            user
            balance
            asset {
              id
              token_id
            }
          }
        }
        """ % (limit, condition_id)

        try:
            resp = requests.post(self.GOLDSKY_POSITIONS, json={'query': query}, timeout=15)
            
            current_holders = {} # {user: balance}
            activities = []

            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'].get('userBalances'):
                    raw_positions = data['data']['userBalances']
                    
                    # Construire la map actuelle
                    for p in raw_positions:
                        user = p.get('user')
                        balance = float(p.get('balance', 0))
                        current_holders[user] = balance
            
            # 2. Comparer avec le snapshot PRECEDENT
            # Si c'est le premier scan, on ne genere PAS d'alerte (sinon on alerte sur tout le monde)
            # On initialise juste le snapshot.
            if condition_id in self._market_snapshots:
                last_holders = self._market_snapshots[condition_id]
                
                # Detecter les NOUVEAUX et les AUGMENTATIONS
                for user, current_bal in current_holders.items():
                    old_bal = last_holders.get(user, 0)
                    
                    # Seuil minimum de changement (ex: 10$ -> ~10_000_000 units)
                    # Mais on laisse process_activity filtrer par montant USD ($10)
                    if current_bal > old_bal:
                        diff = current_bal - old_bal
                        
                        # Generer une activite synthetique "BUY/HOLD"
                        activities.append({
                            'user': user,
                            'amount': diff,   # Le montant de l'augmentation = le montant du pari recent
                            'timestamp': datetime.now().timestamp(),
                            'type': 'POSITION_INCREASE'
                        })
            else:
                # Premier passage : on ne sait pas ce qui est nouveau, on apprend juste l'etat du marche.
                # logger.debug(f"Snapshot initial pour {condition_id} ({len(current_holders)} holders)")
                pass

            # 3. Mettre a jour le snapshot
            self._market_snapshots[condition_id] = current_holders
            
            return activities

        except Exception as e:
            logger.debug(f"Error fetching activity snapshot: {e}")
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
        """Calcule les stats de performance d'un wallet via Gamma API public-profile"""
        stats = {
            'pnl': 0.0,
            'win_rate': 0.0,
            'roi': 0.0,
            'total_trades': 0
        }

        try:
            # Utiliser l'API Gamma pour les stats du profil (plus fiable que le subgraph)
            url = f"{self.GAMMA_API}/public-profile?address={address.lower()}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Extraire les stats disponibles
                pnl = data.get('pnl') or data.get('profit') or 0
                win_rate = data.get('winRate') or data.get('win_rate') or 0
                trades = data.get('tradesCount') or data.get('trades_count') or data.get('betsCount') or 0
                
                if isinstance(pnl, str):
                    pnl = float(pnl.replace('$', '').replace(',', '')) if pnl else 0
                if isinstance(win_rate, str):
                    win_rate = float(win_rate.replace('%', '')) if win_rate else 0
                    
                stats['pnl'] = round(float(pnl), 2)
                stats['win_rate'] = round(float(win_rate), 1)
                stats['total_trades'] = int(trades) if trades else 0
                
                # Calcul ROI si on a le volume
                volume = data.get('volume') or data.get('totalVolume') or 0
                if volume and float(volume) > 0:
                    stats['roi'] = round((float(pnl) / float(volume)) * 100, 1)
                    
        except Exception as e:
            logger.debug(f"Error getting wallet performance from Gamma: {e}")
            
            # Fallback: utiliser Goldsky subgraph
            try:
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
                
                resp = requests.post(self.GOLDSKY_POSITIONS, json={'query': query}, timeout=15)
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
                            if balance > cost and cost > 0:
                                wins += 1

                    if trades > 0:
                        stats['total_trades'] = trades
                        if total_cost > 0:
                            stats['win_rate'] = round((wins / trades) * 100, 1)
                            stats['pnl'] = round(total_value - total_cost, 2)
                            stats['roi'] = round(((total_value - total_cost) / total_cost) * 100, 1)
                        else:
                            # Si on n'a pas le cost, au moins montrer la valeur totale
                            stats['pnl'] = round(total_value, 2)
                            
            except Exception as e2:
                logger.debug(f"Fallback Goldsky also failed: {e2}")

        return stats


    # =========================================================================
    # TRIGGER DETECTION ALGORITHM
    # =========================================================================

    def detect_triggers(self, wallet: str, bet_amount: float, outcome_odds: float) -> List[Dict]:
        """
        Verifie si l'activite declenche un ou plusieurs triggers.
        Retourne une liste de triggers actifs: [{'type': 'RISKY_BET', 'details': '...'}]
        """
        triggers = []
        
        # 1. TRIGGER A: RISKY BET (Le Sniper)
        cfg_risky = self.config['risky_bet']
        if cfg_risky['enabled']:
            # Condition: Mise > 50$ ET (Cote < 35% OU Mise > 1000$)
            if bet_amount >= cfg_risky['min_amount']:
                is_low_odds = outcome_odds <= cfg_risky['max_odds']
                is_high_amount = bet_amount >= cfg_risky['high_amount']
                
                if is_low_odds or is_high_amount:
                    reason = "Low Odds" if is_low_odds else "High Stake"
                    triggers.append({
                        'type': 'RISKY_BET',
                        'label': 'Pari Risqué',
                        'details': f"{reason} (Odds: {outcome_odds:.2f})"
                    })
                    logger.debug(f"  [TRIGGER] RISKY_BET: ${bet_amount} @ {outcome_odds:.2f}")

        # Les triggers suivants necessitent des appels API couteux (Polygonscan)
        # On ne les verifie que si le montant depasse le seuil minimum du trigger LE PLUS BAS (ici 100$)
        # pour eviter de spammer l'API pour des paris de 10$ qui ne triggeront rien de toute facon.
        
        min_profile_check = min(self.config['whale_wakeup']['min_amount'], self.config['fresh_wallet']['min_amount'])
        if bet_amount < min_profile_check:
            return triggers

        # Recuperation des infos wallet (avec cache)
        last_activity = self.get_wallet_last_activity(wallet)
        tx_count = self.get_wallet_tx_count(wallet)

        # 2. TRIGGER B: WHALE WAKEUP (Le Revenant)
        cfg_whale = self.config['whale_wakeup']
        if cfg_whale['enabled'] and bet_amount >= cfg_whale['min_amount']:
            if last_activity:
                days_since = (datetime.now() - last_activity).days
                if days_since >= cfg_whale['dormant_days']:
                    triggers.append({
                        'type': 'WHALE_WAKEUP',
                        'label': 'Réveil Dormant',
                        'details': f"Inactif {days_since}j"
                    })
                    logger.debug(f"  [TRIGGER] WHALE_WAKEUP: Inactif {days_since}j")

        # 3. TRIGGER C: FRESH WALLET (Le Nouveau)
        cfg_fresh = self.config['fresh_wallet']
        if cfg_fresh['enabled'] and bet_amount >= cfg_fresh['min_amount']:
            # Note: tx_count peut etre 999 si API key manquante -> Le trigger ne s'active pas (safe)
            if tx_count <= cfg_fresh['max_tx']:
                triggers.append({
                    'type': 'FRESH_WALLET',
                    'label': 'Nouveau Wallet',
                    'details': f"Seulement {tx_count} txs"
                })
                logger.debug(f"  [TRIGGER] FRESH_WALLET: {tx_count} txs, ${bet_amount}")

        return triggers

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
        """Traite une activite et genere une alerte si un trigger est active"""
        wallet = activity.get('user', '')
        if not wallet:
            return None

        # Calculer le montant en USD
        amount_raw = int(activity.get('amount', 0))
        bet_amount = amount_raw / 1e6  # USDC 6 decimals

        # [MODIFIED] Filtre global abaisse de 100$ a 10$ pour laisser passer les "Risky Bets"
        if bet_amount < 10.0:
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
        
        # Logique de determination du pari (YES/NO et Odds)
        if outcome_prices and len(outcome_prices) >= 2:
            yes_price = float(outcome_prices[0]) if outcome_prices[0] else 0.5
            # no_price = float(outcome_prices[1]) if outcome_prices[1] else 0.5 # Unused
            
            # Si le prix de l'activité est cohérent (entre 0 et 1)
            if 0 < price < 1:
                outcome_odds = price
                # Si on achete a ce prix, on parie sur l'outcome correspondant.
                # Simplification: On assume souvent que c'est du Binary.
                # Si price correspond au YES, c'est YES.
                # Mais ici on garde la logique existante: on déduit le side.
                # Pour faire simple et robuste:
                bet_outcome = "YES" # Par defaut
                # Si c'est un "Sell", c'est l'inverse, mais ici on scanne les "Buys" (activités positives)
                # Amélioration: le scanner regarde les positions, donc c'est implicitement un "Hold/Buy"
            else:
                # Fallback sur les prix actuels
                outcome_odds = yes_price
                bet_outcome = "YES"
        else:
            outcome_odds = price if price > 0 else 0.5
            bet_outcome = "YES"

        # Verifier la deduplication
        dedup_key = self._generate_dedup_key(wallet, market_slug)
        if self._is_duplicate(dedup_key):
            return None

        # [MODIFIED] Detection par Triggers
        active_triggers = self.detect_triggers(wallet, bet_amount, outcome_odds)

        if not active_triggers:
            return None

        # On prend le trigger le plus prioritaire/important comme type principal
        primary_trigger = active_triggers[0]
        
        # Recuperer les stats du wallet pour enrichir
        wallet_stats = self.get_wallet_performance(wallet)
        
        # Formater les details pour l'affichage humain
        trigger_desc = ", ".join([f"{t['label']} ({t['details']})" for t in active_triggers])
        bet_desc = f"${bet_amount:.0f} sur {bet_outcome} @ {outcome_odds:.2f}"

        # Calculer le score de suspicion basé sur les triggers
        suspicion_score = 50  # Base score
        for trigger in active_triggers:
            if trigger['type'] == 'FRESH_WALLET':
                suspicion_score += 30  # Nouveau wallet = très suspect
            elif trigger['type'] == 'WHALE_WAKEUP':
                suspicion_score += 25  # Reveil dormant = suspect
            elif trigger['type'] == 'RISKY_BET':
                suspicion_score += 20  # Pari risqué = modérément suspect
        
        # Bonus pour gros montants
        if bet_amount >= 1000:
            suspicion_score += 10
        if bet_amount >= 5000:
            suspicion_score += 10
            
        # Cap à 100
        suspicion_score = min(suspicion_score, 100)

        # Generer l'alerte
        alert = InsiderAlert(
            id=f"alert_{int(datetime.now().timestamp() * 1000)}_{wallet[:8]}",
            wallet_address=wallet,
            alert_type=primary_trigger['type'], # ex: FRESH_WALLET
            market_question=market_question,
            market_slug=market_slug,
            market_url=f"https://polymarket.com/event/{market_slug}",
            token_id=token_id,
            bet_amount=bet_amount,
            bet_outcome=bet_outcome,
            outcome_odds=outcome_odds,
            trigger_details=trigger_desc,
            bet_details=bet_desc,
            wallet_stats=wallet_stats,
            timestamp=datetime.now().isoformat(),
            dedup_key=dedup_key,
            suspicion_score=suspicion_score,
            nickname=self.get_polymarket_username(wallet) or ""
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
        total_activities = 0
        total_markets_with_activity = 0

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
                    
                    if activities:
                        total_markets_with_activity += 1
                        total_activities += len(activities)

                    for activity in activities:
                        # Si on utilise 'positions' au lieu de 'activities', le type est implicite ou dans un autre champ
                        # Pour le scanner insider, on s'interesse aux entrees
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
                                    print(f"💾 Saving alert for {alert.wallet_address} to DB...")
                                    self.db_manager.save_insider_alert(alert.to_dict())
                                    print("✅ Alert saved successfully")
                                except Exception as e:
                                    print(f"❌ Error saving alert to DB: {e}")
                                    logger.error(f"Erreur sauvegarde alerte: {e}")
                            else:
                                print("❌ DB Manager is None in scanner!")

                            # Notifier les callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(alert)
                                except Exception as e:
                                    logger.error(f"Callback error: {e}")

                            logger.info(f"🚨 ALERT [{alert.alert_type}] {alert.wallet_address[:8]}... | {alert.bet_details} | {alert.trigger_details}")

                    # Petit delai pour eviter rate limiting
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ Erreur scan categorie {category}: {e}")

        # Log résumé du scan
        if total_activities > 0:
            logger.info(f"📊 Scan terminé: {total_activities} activités sur {total_markets_with_activity} marchés, {len(all_alerts)} alertes générées")
        else:
            logger.debug(f"📊 Scan terminé: Aucune nouvelle activité détectée (snapshots en cours d'initialisation)")

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

    def get_polymarket_username(self, address: str) -> Optional[str]:
        """Récupère le pseudonyme/name Polymarket pour une adresse donnée"""
        try:
            url = f"https://gamma-api.polymarket.com/public-profile?address={address.lower()}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # On priorise 'name' (nickname choisi par l'user) puis 'pseudonym'
                return data.get('name') or data.get('pseudonym')
        except Exception as e:
            logger.error(f"⚠️ Erreur récupération username pour {address}: {e}")
        return None

    def get_market_info(self, token_id: str) -> Dict:
        """Recupere les infos d'un marche via Gamma API (Cache 1h)"""
        addr_lower = token_id.lower()
        if addr_lower in self._market_cache:
            cached = self._market_cache[addr_lower]
            if (datetime.now() - cached['timestamp']).total_seconds() < 3600:
                return cached['data']

        try:
            # On cherche par token_id (assetId sur Gamma)
            # Normalement l'API Gamma permet de chercher un marché par un de ses tokens
            resp = requests.get(f"{self.GAMMA_API}/markets/{token_id}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                market_info = {
                    'question': data.get('question', 'Marche inconnu'),
                    'slug': data.get('slug', ''),
                    'price': data.get('outcomePrices', [0, 0])[0] # Prix indicatif
                }
                self._market_cache[addr_lower] = {'data': market_info, 'timestamp': datetime.now()}
                return market_info
        except:
            pass
            
        return {'question': 'Marche inconnu', 'slug': '', 'price': 0}

    def get_wallet_positions(self, address: str) -> List[Dict]:
        """Recupere les positions d'un wallet via Goldsky (Schema 0.0.7)"""
        # Note: balance_gt attend souvent une chaine pour les BigInt dans Goldsky
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

        # Calcul PnL et Winrate basique sur les positions actuelles
        total_cost = 0
        total_value = 0
        wins = 0
        
        for pos in positions:
            # Goldsky balance est en 1e6 (USDC)
            balance = float(pos.get('balance', 0)) / 1e6
            asset_id = pos.get('asset', {}).get('id')
            
            # Puisque 'cost' n'est plus dans le subgraph, on fait une estimation 
            # ou on affiche au moins la valeur actuelle
            cost = 0 # On ne peut plus le savoir directement via ce subgraph
            
            if balance > 0.01:
                stats['total_trades'] += 1
                
                # Optionnel: Chercher le nom du marché pour enrichir (utile pour le logging/UI plus tard)
                # market_info = self.get_market_info(asset_id)
                
                total_value += balance
                # Sans cost, on ne peut pas vraiment calculer PnL/Winrate precision
                # Mais on peut considerer que si balance > 0, c'est une position active
                # Pour eviter les 0 partout, on va au moins montrer le PnL non-realise indicatif
                # Si on n'a pas le cost, on met le PnL à 0 mais on garde le total_value
        
        # Pour l'instant, on retourne au moins quelque chose si des positions existent
        # Si vous voulez un vrai PnL, il faudrait scanner l'historique complet des trades
        stats['pnl'] = round(total_value, 2) # On affiche la valeur totale pour l'instant
        if stats['total_trades'] > 0:
            stats['win_rate'] = 0.0 # On ne peut pas savoir sans cost
            
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
                # 🚀 Récupérer la source actuelle pour ne pas l'écraser (ex: MANUAL)
                existing_wallets = self.db_manager.get_saved_insider_wallets()
                existing_wallet = next((w for w in existing_wallets if w.get('address') and w['address'].lower() == wallet_address.lower()), None)
                source = existing_wallet['source'] if existing_wallet else 'SCANNER'

                # Chercher le nickname Polymarket si absent
                nickname = existing_wallet['nickname'] if existing_wallet else ''
                if not nickname or nickname == 'Wallet Sync':
                    poly_name = self.get_polymarket_username(wallet_address)
                    if poly_name:
                        nickname = poly_name
                        logger.info(f"👤 Nickname trouvé pour {wallet_address}: {nickname}")

                # Mise à jour complète du wallet avec les nouvelles stats
                self.db_manager.save_insider_wallet({
                    'address': wallet_address.lower(),
                    'pnl': stats['pnl'],
                    'win_rate': stats['win_rate'],
                    'nickname': nickname,
                    'notes': (existing_wallet.get('notes') or f"Profilé le {datetime.now().strftime('%d/%m %H:%M')}") if existing_wallet else f"Profilé le {datetime.now().strftime('%d/%m %H:%M')}"
                }, source=source)
                
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
