import requests
import time
import json
from datetime import datetime, timedelta
from bot_logic import BotBackend

class RealPortfolioTracker:
    def __init__(self):
        self.backend = BotBackend()
        self.rpc_url = self.backend.data['rpc_url']
        self.tracker_data = self._load_tracker_data()
        
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
            # Récupérer le solde SOL
            sol_balance = self._get_sol_balance(wallet_address)
            
            # Récupérer les tokens (simplifié pour l'instant)
            # Dans la vraie implémentation, vous devriez scanner tous les tokens
            token_value = 0
            
            # Prix SOL (utiliser une API de prix simple)
            sol_price = self._get_sol_price()
            
            total_value_usd = (sol_balance * sol_price) + token_value
            return total_value_usd
            
        except Exception as e:
            print(f"❌ Erreur get_wallet_value: {e}")
            return 0
            
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
            
    def _get_sol_price(self):
        """Récupère le prix actuel du SOL en USD"""
        try:
            # Utiliser une API de prix publique
            response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd', timeout=5)
            data = response.json()
            return data.get('solana', {}).get('usd', 100)  # Default 100 si erreur
        except:
            return 100  # Prix par défaut si erreur
            
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
        """Retourne la performance complète d'un trader"""
        if wallet_address in self.tracker_data:
            data = self.tracker_data[wallet_address]
            pnl_24h = self._get_pnl_for_period(wallet_address, 24)
            pnl_7d = self._get_pnl_for_period(wallet_address, 168)  # 7 jours = 168 heures
            
            return {
                'pnl': data['pnl'],
                'pnl_percent': data['pnl_percent'],
                'current_value': data['last_value'],
                'pnl_24h': pnl_24h['pnl'],
                'pnl_24h_percent': pnl_24h['pnl_percent'],
                'pnl_7d': pnl_7d['pnl'],
                'pnl_7d_percent': pnl_7d['pnl_percent']
            }
        return {
            'pnl': 0, 
            'pnl_percent': 0, 
            'current_value': 0,
            'pnl_24h': 0,
            'pnl_24h_percent': 0,
            'pnl_7d': 0,
            'pnl_7d_percent': 0
        }
        
    def update_bot_portfolio(self):
        """Met à jour le portefeuille du bot basé sur les traders actifs"""
        if not backend.is_running:
            return backend.virtual_balance
            
        total_value = 1000  # Capital de départ
        
        # Pour chaque trader actif, ajouter sa performance
        for trader in backend.data['traders']:
            if trader['active']:
                perf = self.get_trader_performance(trader['address'])
                # Si le trader gagne 5%, le bot gagne 5% du capital alloué
                capital_alloue = 1000 / backend.get_active_traders_count()
                gain_perte = capital_alloue * (perf['pnl_percent'] / 100)
                total_value += gain_perte
                
        backend.virtual_balance = total_value
        return round(total_value, 2)

# Instance globale
portfolio_tracker = RealPortfolioTracker()
