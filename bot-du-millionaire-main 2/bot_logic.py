import json
import random
import time
from datetime import datetime, timedelta

class BotBackend:
    def __init__(self):
        self.config_file = "config.json"
        self.load_config()
        self.is_running = False
        self.virtual_balance = self.data.get('total_capital', 1000.0)
        self.test_trades = []  # Historique des trades de test
        self.simulated_prices = {}  # Prix simulés pour chaque trader
        self.trader_capital_used = {}  # Capital utilisé par trader
        self.portfolio_cache = None
        self.portfolio_cache_time = None
        self.portfolio_cache_ttl = 5  # Cache 5 secondes
        
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
                self._validate_config()
        except FileNotFoundError:
            self._create_default_config()
        except Exception as e:
            print(f"❌ Erreur chargement config: {e}")
            self._create_default_config()
    
    def _validate_config(self):
        """Valide la configuration et ajoute les champs manquants"""
        required_fields = ["mode", "slippage", "active_traders_limit", "currency", "traders"]
        for field in required_fields:
            if field not in self.data:
                print(f"⚠️ Champ manquant: {field}")
        
        for trader in self.data.get("traders", []):
            if "capital" not in trader:
                trader["capital"] = 0
            if "per_trade_amount" not in trader:
                trader["per_trade_amount"] = 10
            if "min_trade_amount" not in trader:
                trader["min_trade_amount"] = 0
    
    def _create_default_config(self):
        """Crée une configuration par défaut"""
        self.data = {
            "mode": "TEST",
            "slippage": 1.0,
            "active_traders_limit": 3,
            "currency": "USD",
            "total_capital": 1000,
            "wallet_private_key": "",
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "tp1_percent": 33,
            "tp1_profit": 10,
            "tp2_percent": 33,
            "tp2_profit": 25,
            "tp3_percent": 34,
            "tp3_profit": 50,
            "sl_percent": 100,
            "sl_loss": 5,
            "traders": [
                {"name": "AlphaMoon", "emoji": "🚀", "address": "EQaxqKT3N981QBmdSUGNzAGK5S26zUwAdRHhBCgn87zD", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "DeFiKing", "emoji": "♛", "address": "2undvDBttb5ohSggdzEhGUq6mhNBf9JsiLTcsguPp51c", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "SolShark", "emoji": "🦈", "address": "DfMxre4cKmvogbLrPigxmibVTTQDuzjdXojWzjCXXhzj", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "Merlin", "emoji": "🧙", "address": "89HbgWduLwoxcofWpmn1EiF9wEdpgkNDEyPjzZ72mkDi", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "Zap", "emoji": "⚡", "address": "BBPKQwYLyiPjAX2KTFxanR7vxwa7majAF7c7yoaRX8oR", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "Dragon", "emoji": "🐉", "address": "CTC7HVkCkPuChSJjArVip375ogvMUtQLhdzLfiPizdEc", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "Wisdom", "emoji": "🦉", "address": "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "Sniper", "emoji": "🎯", "address": "DmB4xRNaVH2Y2FVBFsJKYvdPDKYjx2sgC8aQFRBF4gB2", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "Pirate", "emoji": "🏴‍☠️", "address": "EzLu595m6CRxPybAUjSser9FmjDvjS3d3vyX4CPiu8Xn", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0},
                {"name": "ApeTrain", "emoji": "🚂", "address": "PMJA8UQDyWTFw2Smhyp9jGA6aTaP7jKHR7BPudrgyYN", "active": False, "capital": 0, "per_trade_amount": 10, "min_trade_amount": 0}
            ]
        }
        self.save_config()

    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"❌ Erreur sauvegarde config: {e}")

    def initialize_test_prices(self):
        """Initialise les prix simulés pour le mode TEST"""
        for trader in self.data['traders']:
            address = trader['address']
            self.simulated_prices[address] = {
                'current_price': random.uniform(0.5, 2.0),  # Prix initial simulé
                'price_history': [],
                'last_trade_time': 0
            }

    def simulate_price_movement(self, address):
        """Simule un mouvement de prix réaliste"""
        if address not in self.simulated_prices:
            self.simulated_prices[address] = {
                'current_price': random.uniform(0.5, 2.0),
                'price_history': [],
                'last_trade_time': 0
            }
        
        data = self.simulated_prices[address]
        # Variation réaliste : +/- 5% par étape
        variation = random.uniform(-0.05, 0.05)
        new_price = data['current_price'] * (1 + variation)
        new_price = max(0.1, new_price)  # Pas de prix négatif
        
        data['current_price'] = new_price
        data['price_history'].append({
            'timestamp': datetime.now().isoformat(),
            'price': new_price
        })
        
        return new_price

    def generate_test_trade(self, trader_index):
        """Génère un trade simulé pour un trader en mode TEST"""
        if not self.is_running or self.data.get("mode") != "TEST":
            return None
        
        trader = self.data['traders'][trader_index]
        address = trader['address']
        
        # Générer un prix
        current_price = self.simulate_price_movement(address)
        
        # 30% de chance d'avoir un trade à chaque itération
        if random.random() > 0.7:
            return None
        
        # Créer un trade simulé
        entry_price = current_price * random.uniform(0.95, 0.98)  # Entre légèrement en dessous
        amount = random.uniform(0.1, 5.0)  # Montant en tokens
        
        trade = {
            'trader': trader['name'],
            'emoji': trader['emoji'],
            'address': address,
            'entry_price': round(entry_price, 6),
            'current_price': round(current_price, 6),
            'amount': round(amount, 2),
            'entry_time': datetime.now().isoformat(),
            'status': 'OPEN',
            'pnl': 0,
            'pnl_percent': 0
        }
        
        # Stocker le trade
        self.test_trades.append(trade)
        
        # Simuler les prises de profit et stop loss
        self._simulate_trade_exit(trade_index=len(self.test_trades) - 1)
        
        return trade

    def _simulate_trade_exit(self, trade_index):
        """Simule la sortie d'un trade avec TP/SL"""
        if trade_index >= len(self.test_trades):
            return
        
        trade = self.test_trades[trade_index]
        entry_price = trade['entry_price']
        current_price = trade['current_price']
        
        price_change_percent = ((current_price - entry_price) / entry_price * 100) if entry_price != 0 else 0
        
        # Vérifier Stop Loss
        sl_loss = self.data.get('sl_loss', 5)
        if price_change_percent <= -sl_loss:
            trade['status'] = 'SL_HIT'
            trade['exit_price'] = entry_price * (1 - sl_loss / 100)
            trade['pnl'] = (trade['exit_price'] - entry_price) * trade['amount']
            trade['pnl_percent'] = -sl_loss
            trade['exit_time'] = datetime.now().isoformat()
            return
        
        # Vérifier Take Profits
        tp_levels = [
            (self.data.get('tp1_profit', 10), self.data.get('tp1_percent', 33) / 100),
            (self.data.get('tp2_profit', 25), self.data.get('tp2_percent', 33) / 100),
            (self.data.get('tp3_profit', 50), self.data.get('tp3_percent', 34) / 100),
        ]
        
        for tp_level, tp_percent in tp_levels:
            if price_change_percent >= tp_level:
                exit_price = entry_price * (1 + tp_level / 100)
                trade['status'] = f'TP_HIT'
                trade['exit_price'] = exit_price
                trade['pnl'] = (exit_price - entry_price) * trade['amount'] * tp_percent
                trade['pnl_percent'] = tp_level
                trade['exit_time'] = datetime.now().isoformat()
                break

    def update_test_trades(self):
        """Met à jour les trades ouverts avec les nouveau prix"""
        if not self.is_running or self.data.get("mode") != "TEST":
            return
        
        for trade in self.test_trades:
            if trade['status'] == 'OPEN':
                address = trade['address']
                new_price = self.simulate_price_movement(address)
                trade['current_price'] = round(new_price, 6)
                
                # Recalculer PnL (évite division par zéro)
                entry_price = trade['entry_price']
                pnl = (new_price - entry_price) * trade['amount']
                pnl_percent = ((new_price - entry_price) / entry_price * 100) if entry_price != 0 else 0
                
                trade['pnl'] = round(pnl, 2)
                trade['pnl_percent'] = round(pnl_percent, 2)
                
                # Vérifier exits
                self._simulate_trade_exit(self.test_trades.index(trade))

    def get_portfolio_value(self):
        """Calcule la valeur du portefeuille"""
        # Vérifier le cache
        if self.portfolio_cache is not None and self.portfolio_cache_time is not None:
            elapsed = time.time() - self.portfolio_cache_time
            if elapsed < self.portfolio_cache_ttl:
                return self.portfolio_cache
        
        if not self.is_running:
            result = round(self.virtual_balance, 2)
        elif self.data.get("mode") == "TEST":
            # En mode TEST, calculer basé sur les trades
            closed_pnl = sum([t['pnl'] for t in self.test_trades if t['status'] != 'OPEN'])
            open_pnl = sum([t['pnl'] for t in self.test_trades if t['status'] == 'OPEN'])
            result = round(1000 + closed_pnl + open_pnl, 2)
        else:
            # En mode REEL, variation légère
            self.virtual_balance += random.uniform(-5, 10)
            result = round(self.virtual_balance, 2)
        
        # Mettre en cache
        self.portfolio_cache = result
        self.portfolio_cache_time = time.time()
        return result

    def get_total_pnl(self):
        """Retourne le PnL total À PARTIR DES DONNÉES RÉELLES DES TRADERS"""
        try:
            import json
            with open('portfolio_tracker.json', 'r') as f:
                data = json.load(f)
                total_pnl = sum(trader.get('pnl', 0) for trader in data.values())
                return round(total_pnl, 2)
        except:
            return 0
    
    def get_total_pnl_percent(self):
        """Retourne le PnL % moyen"""
        try:
            import json
            with open('portfolio_tracker.json', 'r') as f:
                data = json.load(f)
                if not data:
                    return 0
                avg_pnl_percent = sum(trader.get('pnl_percent', 0) for trader in data.values()) / len(data)
                return round(avg_pnl_percent, 2)
        except:
            return 0

    def get_test_trades(self):
        """Retourne les 10 derniers trades"""
        return sorted(self.test_trades, key=lambda x: x['entry_time'], reverse=True)[:10]

    def get_active_traders_count(self):
        return sum(1 for t in self.data['traders'] if t['active'])

    def toggle_trader(self, index, state):
        current_active = self.get_active_traders_count()
        if state and current_active >= self.data['active_traders_limit'] and not self.data['traders'][index]['active']:
            return False
        self.data['traders'][index]['active'] = state
        self.save_config()
        return True

    def toggle_bot(self, status):
        self.is_running = status
        if status and self.data.get("mode") == "TEST":
            self.initialize_test_prices()

    def update_trader(self, index, name, emoji, address, capital=None, per_trade_amount=None, min_trade_amount=None):
        self.data['traders'][index]['name'] = name
        self.data['traders'][index]['emoji'] = emoji
        self.data['traders'][index]['address'] = address
        if capital is not None:
            self.data['traders'][index]['capital'] = float(capital)
        if per_trade_amount is not None:
            self.data['traders'][index]['per_trade_amount'] = float(per_trade_amount)
        if min_trade_amount is not None:
            self.data['traders'][index]['min_trade_amount'] = float(min_trade_amount)
        self.save_config()
    
    def update_take_profit(self, tp1_percent, tp1_profit, tp2_percent, tp2_profit, tp3_percent, tp3_profit, sl_percent, sl_loss):
        self.data['tp1_percent'] = tp1_percent
        self.data['tp1_profit'] = tp1_profit
        self.data['tp2_percent'] = tp2_percent
        self.data['tp2_profit'] = tp2_profit
        self.data['tp3_percent'] = tp3_percent
        self.data['tp3_profit'] = tp3_profit
        self.data['sl_percent'] = sl_percent
        self.data['sl_loss'] = sl_loss
        self.save_config()

    def clear_test_trades(self):
        """Réinitialise les trades de test"""
        self.test_trades = []
        self.virtual_balance = 1000.0
    
    def set_trader_capital(self, trader_index, capital):
        """Définit le capital alloué pour un trader"""
        if 0 <= trader_index < len(self.data['traders']):
            self.data['traders'][trader_index]['capital'] = float(capital)
            self.save_config()
            return True
        return False
    
    def get_trader_capital(self, trader_index):
        """Récupère le capital alloué pour un trader"""
        if 0 <= trader_index < len(self.data['traders']):
            return self.data['traders'][trader_index].get('capital', 100)
        return 0
    
    def get_total_allocated_capital(self):
        """Retourne le capital total alloué à tous les traders actifs"""
        total = 0
        for trader in self.data['traders']:
            if trader['active']:
                total += trader.get('capital', 100)
        return total
    
    def set_total_capital(self, capital):
        """Définit le capital total du portefeuille"""
        self.data['total_capital'] = float(capital)
        self.virtual_balance = float(capital)
        self.save_config()
        return True
    
    def get_total_capital(self):
        """Retourne le capital total du portefeuille"""
        return self.data.get('total_capital', 1000.0)
    
    def get_capital_summary(self):
        """Retourne un résumé du capital : total, utilisé, restant"""
        total_capital = self.get_total_capital()
        allocated_capital = sum(t.get('capital', 0) for t in self.data['traders'])
        remaining_capital = total_capital - allocated_capital
        
        traders_capital = []
        for i, trader in enumerate(self.data['traders']):
            traders_capital.append({
                'index': i,
                'name': trader['name'],
                'emoji': trader['emoji'],
                'capital': trader.get('capital', 0),
                'active': trader['active']
            })
        
        return {
            'total_capital': total_capital,
            'allocated_capital': allocated_capital,
            'remaining_capital': remaining_capital,
            'traders': traders_capital
        }
