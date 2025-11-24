import requests
import time
import json
from datetime import datetime, timedelta
from bot_logic import BotBackend

# Imports conditionnels pour macOS/dev
try:
    from solana_integration import solana_tracker, SolanaValidator
except Exception as e:
    print(f"⚠️ Solana import skipped (dev mode): {type(e).__name__}")
    solana_tracker = None
    SolanaValidator = None

class RealPortfolioTracker:
    def __init__(self):
        self.backend = BotBackend()
        self.rpc_url = self.backend.data.get('rpc_url', 'https://api.mainnet-beta.solana.com')
        self.tracker_data = self._load_tracker_data()
        self.cache = {}  # Cache pour éviter le rate limiting
        self.cache_ttl = 120  # 2 minutes de cache
        self.last_rpc_call = 0
        self.rpc_delay = 1  # 1 seconde entre les appels RPC
        
    def _load_tracker_data(self):
        """Charge les données de suivi des portefeuilles"""
        try:
            with open('portfolio_tracker.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_tracker_data(self):
        """Sauvegarde les données de suivi"""
        with open('portfolio_tracker.json', 'w') as f:
            json.dump(self.tracker_data, f, indent=2)
            
    def get_wallet_value(self, wallet_address):
        """Récupère la valeur totale d'un wallet en USD"""
        try:
            # Vérifier le cache
            cache_key = f"wallet_{wallet_address}"
            if cache_key in self.cache:
                try:
                    cache_entry = self.cache[cache_key]
                    # Vérifier que l'entrée du cache est bien formatée
                    if isinstance(cache_entry, tuple) and len(cache_entry) == 2:
                        cache_time, cached_value = cache_entry
                        if isinstance(cache_time, datetime) and isinstance(cached_value, (int, float)):
                            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                                return float(cached_value)
                except (TypeError, ValueError) as e:
                    # Cache corrompu, le supprimer
                    del self.cache[cache_key]
            
            # Valider l'adresse (si Solana disponible)
            if SolanaValidator:
                validator = SolanaValidator()
                if not validator.is_valid_solana_address(wallet_address):
                    return 0.0
            else:
                # Validation basique sans Solana
                if not isinstance(wallet_address, str) or len(wallet_address) < 10:
                    return 0.0
            
            # Throttle les appels RPC
            current_time = time.time()
            if current_time - self.last_rpc_call < self.rpc_delay:
                time.sleep(self.rpc_delay - (current_time - self.last_rpc_call))
            self.last_rpc_call = time.time()
            
            # EN MODE TEST OU REEL: Récupérer les VRAIES données Solana via RPC
            # Les trades sont simulés en TEST, réels en REEL - mais les données portefeuille sont toujours réelles
            sol_balance = self._get_sol_balance(wallet_address)
            
            # Prix SOL réel
            sol_price_value = float(self._fetch_sol_price())
            
            # Token value (pour après, quand on parsera les transactions)
            token_value = 0.0
            
            # Calcul total en USD
            total_value_usd = (sol_balance * sol_price_value) + token_value
            total_value_usd = float(total_value_usd)
            
            # Mettre en cache
            self.cache[cache_key] = (datetime.now(), total_value_usd)
            
            return total_value_usd
            
        except Exception as e:
            print(f"❌ Erreur get_wallet_value: {e}")
            return 0.0
    
    def _fetch_sol_price(self):
        """Récupère le prix du SOL en USD"""
        try:
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd',
                timeout=5
            )
            sol_price_data = response.json()
            sol_price = sol_price_data.get('solana', {}).get('usd', 100)
            self.cache["sol_price"] = (datetime.now(), sol_price)
            return sol_price
        except Exception:
            return 100
            
    def _get_sol_balance(self, wallet_address):
        """Récupère le solde SOL d'un wallet"""
        payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getBalance",
            "params": [wallet_address]
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            result = response.json()
            balance_lamports = result.get('result', {}).get('value', 0)
            return balance_lamports / 1_000_000_000  # Convertir lamports -> SOL
        except:
            return 0
            
    def track_all_wallets(self):
        """Suivre tous les wallets des traders et calculer les PnL"""
        print("📊 Suivi des portefeuilles en cours...")
        current_timestamp = datetime.now().isoformat()
        
        for trader in self.backend.data['traders']:
            wallet = trader['address']
            current_value = self.get_wallet_value(wallet)
            
            # Initialiser si nouveau
            if wallet not in self.tracker_data:
                self.tracker_data[wallet] = {
                    'name': trader['name'],
                    'emoji': trader['emoji'],
                    'initial_value': current_value,
                    'last_value': current_value,
                    'pnl': 0,
                    'pnl_percent': 0,
                    'history': [
                        {'timestamp': current_timestamp, 'value': current_value}
                    ]
                }
            else:
                # Mettre à jour la valeur actuelle
                initial_value = self.tracker_data[wallet]['initial_value']
                
                pnl = current_value - initial_value
                pnl_percent = (pnl / initial_value * 100) if initial_value > 0 else 0
                
                self.tracker_data[wallet]['last_value'] = current_value
                self.tracker_data[wallet]['pnl'] = pnl
                self.tracker_data[wallet]['pnl_percent'] = pnl_percent
                
                # Ajouter au historique
                if 'history' not in self.tracker_data[wallet]:
                    self.tracker_data[wallet]['history'] = []
                
                self.tracker_data[wallet]['history'].append({
                    'timestamp': current_timestamp,
                    'value': current_value
                })
                
                # Nettoyer l'historique (garder seulement 8 jours)
                cutoff_date = datetime.now() - timedelta(days=8)
                self.tracker_data[wallet]['history'] = [
                    h for h in self.tracker_data[wallet]['history']
                    if datetime.fromisoformat(h['timestamp']) > cutoff_date
                ]
                
        self._save_tracker_data()
        print("✅ Suivi des portefeuilles mis à jour")
        
    def _get_pnl_for_period(self, wallet_address, hours):
        """Calcule le PnL sur une période donnée"""
        if wallet_address not in self.tracker_data:
            return {'pnl': 0, 'pnl_percent': 0}
        
        data = self.tracker_data[wallet_address]
        current_value = data['last_value']
        history = data.get('history', [])
        
        if not history:
            return {'pnl': 0, 'pnl_percent': 0}
        
        # Trouver la valeur il y a X heures
        target_time = datetime.now() - timedelta(hours=hours)
        past_value = None
        
        for entry in history:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time >= target_time:
                past_value = entry['value']
                break
        
        # Si pas de donnée suffisamment ancienne, prendre la plus ancienne
        if past_value is None and history:
            past_value = history[0]['value']
        
        if past_value and past_value > 0:
            pnl = current_value - past_value
            pnl_percent = (pnl / past_value * 100)
            return {'pnl': pnl, 'pnl_percent': pnl_percent}
        
        return {'pnl': 0, 'pnl_percent': 0}
    
    def get_trader_performance(self, wallet_address):
        """Retourne la performance complète d'un trader via Solana réelle"""
        # Valider l'adresse
        if SolanaValidator:
            validator = SolanaValidator()
            if not validator.is_valid_solana_address(wallet_address):
                return {
                    'pnl': 0, 
                    'pnl_percent': 0, 
                    'current_value': 0,
                    'pnl_24h': 0,
                    'pnl_24h_percent': 0,
                    'pnl_7d': 0,
                    'pnl_7d_percent': 0
                }
        else:
            # Validation basique si SolanaValidator non disponible
            if not isinstance(wallet_address, str) or len(wallet_address) < 32:
                return {
                    'pnl': 0, 
                    'pnl_percent': 0, 
                    'current_value': 0,
                    'pnl_24h': 0,
                    'pnl_24h_percent': 0,
                    'pnl_7d': 0,
                    'pnl_7d_percent': 0
                }
        
        # Récupérer les vraies données du wallet
        current_value = self.get_wallet_value(wallet_address)
        
        if wallet_address in self.tracker_data:
            data = self.tracker_data[wallet_address]
            initial_value = data.get('initial_value', current_value)
            
            # Calculs PnL
            pnl = current_value - initial_value
            pnl_percent = (pnl / initial_value * 100) if initial_value > 0 else 0
            
            # PnL périodes
            pnl_24h = self._get_pnl_for_period(wallet_address, 24)
            pnl_7d = self._get_pnl_for_period(wallet_address, 168)
            
            return {
                'pnl': round(pnl, 2),
                'pnl_percent': round(pnl_percent, 2),
                'current_value': round(current_value, 2),
                'pnl_24h': round(pnl_24h['pnl'], 2),
                'pnl_24h_percent': round(pnl_24h['pnl_percent'], 2),
                'pnl_7d': round(pnl_7d['pnl'], 2),
                'pnl_7d_percent': round(pnl_7d['pnl_percent'], 2)
            }
        
        # Initialiser les données si pas encore présentes
        return {
            'pnl': 0, 
            'pnl_percent': 0, 
            'current_value': round(current_value, 2),
            'pnl_24h': 0,
            'pnl_24h_percent': 0,
            'pnl_7d': 0,
            'pnl_7d_percent': 0
        }
        
    def update_bot_portfolio(self):
        """Met à jour le portefeuille du bot basé sur les traders actifs"""
        if not self.backend.is_running:
            return self.backend.virtual_balance
            
        total_capital = self.backend.data.get('total_capital', 1000)
        total_value = total_capital  # Capital de départ
        
        # Pour chaque trader actif, ajouter sa performance
        for trader in self.backend.data['traders']:
            if trader['active']:
                perf = self.get_trader_performance(trader['address'])
                # Utiliser le montant par trade alloué à ce trader
                per_trade_amount = trader.get('per_trade_amount', 10)
                if per_trade_amount > 0:
                    gain_perte = per_trade_amount * (perf['pnl_percent'] / 100)
                    total_value += gain_perte
                
        self.backend.virtual_balance = total_value
        return round(total_value, 2)

# Instance globale
portfolio_tracker = RealPortfolioTracker()
