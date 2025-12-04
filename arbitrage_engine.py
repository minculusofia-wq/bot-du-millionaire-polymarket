# -*- coding: utf-8 -*-
"""
Arbitrage Engine - Détection et exécution d'opportunités d'arbitrage multi-DEX
Supporte: Raydium, Orca, Jupiter
Détecte les écarts de prix entre DEX et exécute automatiquement
"""
from typing import Dict, List, Tuple, Optional
import requests
from datetime import datetime, timedelta
import time
import json
import os
import threading


class SimpleCache:
    """Cache simple en mémoire avec TTL"""
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    return value
                del self._cache[key]
        return None

    def set(self, key, value, ttl=60):
        with self._lock:
            expiry = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = (value, expiry)


class ArbitrageEngine:
    """
    Détecte et exécute des opportunités d'arbitrage sur Solana
    Supporte: Raydium, Orca, Jupiter
    """

    # Valeurs par défaut
    DEFAULT_CONFIG = {
        'enabled': False,  # Arbitrage désactivé par défaut
        'capital_dedicated': 100.0,  # Capital dédié à l'arbitrage (séparé du copy trading)
        'percent_per_trade': 10.0,  # % du capital arbitrage par opportunité
        'min_profit_threshold': 1.5,  # % minimum de profit net
        'min_amount_per_trade': 10.0,  # Montant minimum par trade ($)
        'max_amount_per_trade': 200.0,  # Montant maximum par trade ($)
        'cooldown_seconds': 30,  # Secondes entre 2 arbitrages du même token
        'max_concurrent_trades': 3,  # Max d'arbitrages simultanés
        'blacklist_tokens': []  # Tokens à éviter
    }

    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path

        # Charger la configuration
        self.config = self._load_config()

        # État
        self.enabled = self.config['enabled']
        self.capital_dedicated = self.config['capital_dedicated']
        self.percent_per_trade = self.config['percent_per_trade']
        self.min_profit_threshold = self.config['min_profit_threshold']
        self.min_amount = self.config['min_amount_per_trade']
        self.max_amount = self.config['max_amount_per_trade']
        self.cooldown_seconds = self.config['cooldown_seconds']
        self.max_concurrent = self.config['max_concurrent_trades']
        self.blacklist = set(self.config['blacklist_tokens'])

        # Statistiques
        self.opportunities_found = 0
        self.opportunities_executed = 0
        self.total_profit = 0.0
        self.win_count = 0
        self.loss_count = 0
        self.recent_opportunities = []  # Dernières 10 opportunités
        self.active_trades = []  # Trades en cours
        self.cooldown_tracker = {}  # {token: last_trade_time}
        self.last_update = None

        # URLs des APIs DEX
        self.dex_apis = {
            'Jupiter': 'https://price.jup.ag/v4/price',
            'Raydium': 'https://api.raydium.io/v2/main/price',
            'Orca': 'https://api.orca.so/v1/token/list'
        }

        # Frais estimés (% par transaction)
        self.estimated_fees = {
            'Jupiter': 0.25,  # 0.25% swap fee
            'Raydium': 0.25,  # 0.25% swap fee
            'Orca': 0.30      # 0.30% swap fee
        }

        # Cache interne
        self._cache = SimpleCache()

        print(f"💰 Arbitrage Engine initialisé")
        print(f"   Statut: {'✅ ACTIVÉ' if self.enabled else '❌ DÉSACTIVÉ'}")
        print(f"   Capital dédié: {self.capital_dedicated}$")
        print(f"   % par trade: {self.percent_per_trade}%")

    def _load_config(self) -> Dict:
        """Charge la configuration depuis config.json"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                    if 'arbitrage' in config:
                        print("✅ Configuration arbitrage chargée depuis config.json")
                        # Fusionner avec les valeurs par défaut
                        loaded_config = self.DEFAULT_CONFIG.copy()
                        loaded_config.update(config['arbitrage'])
                        return loaded_config
        except Exception as e:
            print(f"⚠️ Erreur chargement config arbitrage: {e}")

        print("ℹ️ Utilisation de la configuration arbitrage par défaut")
        return self.DEFAULT_CONFIG.copy()

    def save_config(self) -> bool:
        """Sauvegarde la configuration dans config.json"""
        try:
            # Charger le config.json existant
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Mettre à jour la section arbitrage
            config['arbitrage'] = {
                'enabled': self.enabled,
                'capital_dedicated': self.capital_dedicated,
                'percent_per_trade': self.percent_per_trade,
                'min_profit_threshold': self.min_profit_threshold,
                'min_amount_per_trade': self.min_amount,
                'max_amount_per_trade': self.max_amount,
                'cooldown_seconds': self.cooldown_seconds,
                'max_concurrent_trades': self.max_concurrent,
                'blacklist_tokens': list(self.blacklist)
            }

            # Sauvegarder
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print("✅ Configuration arbitrage sauvegardée")
            return True
        except Exception as e:
            print(f"❌ Erreur sauvegarde config arbitrage: {e}")
            return False

    def update_config(self, params: Dict) -> Dict:
        """Met à jour la configuration"""
        try:
            if 'enabled' in params:
                self.enabled = bool(params['enabled'])
            if 'capital_dedicated' in params:
                self.capital_dedicated = float(params['capital_dedicated'])
            if 'percent_per_trade' in params:
                self.percent_per_trade = float(params['percent_per_trade'])
            if 'min_profit_threshold' in params:
                self.min_profit_threshold = float(params['min_profit_threshold'])
            if 'min_amount_per_trade' in params:
                self.min_amount = float(params['min_amount_per_trade'])
            if 'max_amount_per_trade' in params:
                self.max_amount = float(params['max_amount_per_trade'])
            if 'cooldown_seconds' in params:
                self.cooldown_seconds = int(params['cooldown_seconds'])
            if 'max_concurrent_trades' in params:
                self.max_concurrent = int(params['max_concurrent_trades'])
            if 'blacklist_tokens' in params:
                self.blacklist = set(params['blacklist_tokens'])

            # Sauvegarder
            self.save_config()

            return {'success': True, 'message': 'Configuration mise à jour'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_config(self) -> Dict:
        """Retourne la configuration actuelle"""
        return {
            'enabled': self.enabled,
            'capital_dedicated': self.capital_dedicated,
            'percent_per_trade': self.percent_per_trade,
            'min_profit_threshold': self.min_profit_threshold,
            'min_amount_per_trade': self.min_amount,
            'max_amount_per_trade': self.max_amount,
            'cooldown_seconds': self.cooldown_seconds,
            'max_concurrent_trades': self.max_concurrent,
            'blacklist_tokens': list(self.blacklist)
        }

    def is_in_cooldown(self, token_mint: str) -> bool:
        """Vérifie si le token est en cooldown"""
        if token_mint not in self.cooldown_tracker:
            return False

        last_trade = self.cooldown_tracker[token_mint]
        elapsed = (datetime.now() - last_trade).total_seconds()
        return elapsed < self.cooldown_seconds

    def can_trade(self) -> Tuple[bool, str]:
        """Vérifie si on peut trader (vérifications de sécurité)"""
        if not self.enabled:
            return False, "Arbitrage désactivé"

        if len(self.active_trades) >= self.max_concurrent:
            return False, f"Max trades simultanés atteint ({self.max_concurrent})"

        if self.capital_dedicated <= 0:
            return False, "Capital dédié insuffisant"

        return True, "OK"

    def update_dex_prices(self, token_mint: str) -> Dict[str, float]:
        """Récupère les prix du token sur tous les DEX"""
        # Vérifier le cache
        cache_key = f"dex_prices_{token_mint}"
        cached_prices = self._cache.get(cache_key)
        if cached_prices is not None:
            return cached_prices

        prices = {}

        # 1. Jupiter API
        try:
            response = requests.get(
                f"{self.dex_apis['Jupiter']}?ids={token_mint}",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and token_mint in data['data']:
                    prices['Jupiter'] = float(data['data'][token_mint]['price'])
        except Exception as e:
            pass  # Silencieux

        # 2. Raydium API
        try:
            response = requests.get(self.dex_apis['Raydium'], timeout=3)
            if response.status_code == 200:
                data = response.json()
                if token_mint in data:
                    prices['Raydium'] = float(data[token_mint])
        except Exception as e:
            pass

        # 3. Orca API
        try:
            response = requests.get(self.dex_apis['Orca'], timeout=3)
            if response.status_code == 200:
                tokens = response.json()
                for token in tokens:
                    if token.get('mint') == token_mint:
                        price = token.get('price', 0)
                        if price:
                            prices['Orca'] = float(price)
                        break
        except Exception as e:
            pass

        # Mettre en cache
        self._cache.set(cache_key, prices, ttl=10)
        self.last_update = datetime.now()

        return prices

    def detect_arbitrage(self, token_mint: str) -> Dict:
        """Détecte les opportunités d'arbitrage"""
        # Vérifier blacklist
        if token_mint in self.blacklist:
            return {
                'opportunity': False,
                'reason': 'Token blacklisté',
                'token_mint': token_mint
            }

        # Vérifier cooldown
        if self.is_in_cooldown(token_mint):
            remaining = self.cooldown_seconds - (datetime.now() - self.cooldown_tracker[token_mint]).total_seconds()
            return {
                'opportunity': False,
                'reason': f'Cooldown actif ({remaining:.0f}s restant)',
                'token_mint': token_mint
            }

        # Récupérer les prix
        prices = self.update_dex_prices(token_mint)

        if len(prices) < 2:
            return {
                'opportunity': False,
                'reason': 'Pas assez de DEX disponibles (minimum 2)',
                'token_mint': token_mint
            }

        # Trouver le meilleur deal
        buy_dex = min(prices, key=prices.get)
        sell_dex = max(prices, key=prices.get)
        buy_price = prices[buy_dex]
        sell_price = prices[sell_dex]

        # Calculer le profit
        profit_percent = ((sell_price - buy_price) / buy_price) * 100
        buy_fee = self.estimated_fees.get(buy_dex, 0.25)
        sell_fee = self.estimated_fees.get(sell_dex, 0.25)
        total_fees = buy_fee + sell_fee
        net_profit = profit_percent - total_fees

        # Opportunité ?
        opportunity = net_profit >= self.min_profit_threshold

        result = {
            'opportunity': opportunity,
            'profit_percent': round(profit_percent, 2),
            'net_profit': round(net_profit, 2),
            'buy_dex': buy_dex,
            'buy_price': buy_price,
            'buy_fee': buy_fee,
            'sell_dex': sell_dex,
            'sell_price': sell_price,
            'sell_fee': sell_fee,
            'total_fees': total_fees,
            'timestamp': datetime.now().isoformat(),
            'token_mint': token_mint
        }

        if opportunity:
            self.opportunities_found += 1
            # Ajouter aux récentes (max 10)
            self.recent_opportunities.insert(0, result)
            self.recent_opportunities = self.recent_opportunities[:10]

            print(f"\n💰 OPPORTUNITÉ: {token_mint[:8]}... | {buy_dex} → {sell_dex} | +{net_profit:.2f}%")

        return result

    def calculate_trade_amount(self, opportunity: Dict) -> float:
        """Calcule le montant optimal pour le trade"""
        # Montant de base (% du capital dédié)
        base_amount = (self.capital_dedicated * self.percent_per_trade) / 100

        # Ajuster selon le profit (plus le profit est élevé, plus on trade)
        net_profit = opportunity.get('net_profit', 0)
        if net_profit > 5:
            multiplier = 1.5
        elif net_profit > 3:
            multiplier = 1.2
        else:
            multiplier = 1.0

        amount = base_amount * multiplier

        # Appliquer les limites
        amount = max(self.min_amount, min(amount, self.max_amount))
        amount = min(amount, self.capital_dedicated)  # Ne pas dépasser le capital dédié

        return round(amount, 2)

    def execute_arbitrage(self, opportunity: Dict, amount: float = None) -> Dict:
        """Exécute l'arbitrage (MODE TEST uniquement pour le moment)"""
        can_trade, reason = self.can_trade()
        if not can_trade:
            return {'success': False, 'error': reason}

        if not opportunity.get('opportunity'):
            return {'success': False, 'error': 'Pas d\'opportunité valide'}

        # Calculer le montant si non fourni
        if amount is None:
            amount = self.calculate_trade_amount(opportunity)

        # Calculer le profit estimé
        estimated_profit = amount * (opportunity['net_profit'] / 100)

        # MODE TEST uniquement
        print(f"✅ [TEST] Arbitrage exécuté: {opportunity['token_mint'][:8]}... | Montant: {amount}$ | Profit: +{estimated_profit:.2f}$")

        # Mettre à jour les statistiques
        self.opportunities_executed += 1
        self.total_profit += estimated_profit
        if estimated_profit > 0:
            self.win_count += 1
        else:
            self.loss_count += 1

        # Marquer le cooldown
        self.cooldown_tracker[opportunity['token_mint']] = datetime.now()

        return {
            'success': True,
            'mode': 'TEST',
            'amount': amount,
            'profit': round(estimated_profit, 2),
            'timestamp': datetime.now().isoformat()
        }

    def get_statistics(self) -> Dict:
        """Retourne les statistiques complètes"""
        total_trades = self.opportunities_executed
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0

        return {
            'enabled': self.enabled,
            'capital_dedicated': self.capital_dedicated,
            'opportunities_found': self.opportunities_found,
            'opportunities_executed': self.opportunities_executed,
            'total_profit': round(self.total_profit, 2),
            'win_rate': round(win_rate, 1),
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'active_trades': len(self.active_trades),
            'recent_opportunities': self.recent_opportunities,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }


# Instance globale
arbitrage_engine = ArbitrageEngine()
