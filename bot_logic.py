# -*- coding: utf-8 -*-
import json
import random
import time
import threading
from datetime import datetime, timedelta

try:
    from solders.keypair import Keypair
except ImportError:
    Keypair = None

class BotBackend:
    def __init__(self):
        self.config_file = "config.json"
        
        # ⚡ OPTIMISATION: Initialiser locks AVANT load_config
        self._save_timer = None
        self._save_lock = threading.Lock()
        self._pending_save = False
        
        self.load_config()
        # Charger is_running depuis config ou False par défaut
        self.is_running = self.data.get('is_running', False)
        # MODE REAL uniquement - pas de capital fictif
        self.trader_capital_used = {}  # Capital utilisé par trader
        self.portfolio_cache = None
        self.portfolio_cache_time = None
        self.portfolio_cache_ttl = 5  # Cache 5 secondes
        self.wallet_balance_cache = None
        self.wallet_balance_cache_time = None
        self.wallet_balance_cache_ttl = 10  # Cache 10 secondes
        
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
                self._validate_config()
                self._migrate_config()  # Migration des anciennes configs
        except FileNotFoundError:
            self._create_default_config()
        except Exception as e:
            print(f"❌ Erreur chargement config: {e}")
            self._create_default_config()
    
    def _validate_config(self):
        """Valide la configuration et ajoute les champs manquants"""
        required_fields = ["slippage", "active_traders_limit", "currency", "traders"]
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
    

    def _migrate_config(self):
        """Migre les anciennes configurations vers les nouveaux defaults"""
        needs_save = False
        
        # Supprimer total_capital si présent (MODE TEST deprecated)
        if 'total_capital' in self.data:
            del self.data['total_capital']
            needs_save = True
            print("🔄 Migration: Suppression de total_capital (MODE REAL uniquement)")
        
        # Ajouter is_running si manquant
        if 'is_running' not in self.data:
            self.data['is_running'] = False
            needs_save = True
        
        # Ajouter arbitrage config si manquant avec defaults à 0
        if 'arbitrage' not in self.data:
            self.data['arbitrage'] = {
                "enabled": False,
                "capital_dedicated": 0,
                "percent_per_trade": 0,
                "min_profit_threshold": 0,
                "min_amount_per_trade": 0,
                "max_amount_per_trade": 0,
                "cooldown_seconds": 30,
                "max_concurrent_trades": 0,
                "blacklist_tokens": []
            }
            needs_save = True
            print("🔄 Migration: Ajout config arbitrage (defaults à 0)")
        
        # Ajouter params_saved si manquant
        if 'params_saved' not in self.data:
            self.data['params_saved'] = False
            needs_save = True
        
        # Reset à 0 si params_saved = False (pas de sauvegarde explicite)
        if not self.data.get('params_saved', False):
            print("🔄 Reset: Paramètres à 0 (Mode Mirror - Pas de sauvegarde)")
            self.data['slippage'] = 0
            self.data['tp1_percent'] = 0
            self.data['tp1_profit'] = 0
            self.data['tp2_percent'] = 0
            self.data['tp2_profit'] = 0
            self.data['tp3_percent'] = 0
            self.data['tp3_profit'] = 0
            self.data['sl_percent'] = 0
            self.data['sl_loss'] = 0
            
            # Reset arbitrage aussi
            if 'arbitrage' in self.data:
                self.data['arbitrage']['enabled'] = False
                self.data['arbitrage']['capital_dedicated'] = 0
                self.data['arbitrage']['percent_per_trade'] = 0
                self.data['arbitrage']['min_profit_threshold'] = 0
                self.data['arbitrage']['min_amount_per_trade'] = 0
                self.data['arbitrage']['max_amount_per_trade'] = 0
                self.data['arbitrage']['max_concurrent_trades'] = 0
            
            needs_save = True
        else:
            print("✅ Paramètres chargés depuis sauvegarde précédente")
        
        if needs_save:
            self.save_config_sync()
            print("✅ Migration de config effectuée")

    def _create_default_config(self):
        """Crée une configuration par défaut"""
        self.data = {
            "slippage": 0,  # Mode Mirror par défaut (0 = suit exactement le trader)
            "active_traders_limit": 3,
            "currency": "USD",
            "wallet_private_key": "",
            "rpc_url": "https://api.mainnet-beta.solana.com",
            "is_running": False,  # État du bot
            "params_saved": False,  # Flag de sauvegarde explicite
            "tp1_percent": 0,  # Désactivé par défaut
            "tp1_profit": 0,
            "tp2_percent": 0,
            "tp2_profit": 0,
            "tp3_percent": 0,
            "tp3_profit": 0,
            "sl_percent": 0,
            "sl_loss": 0,
            # Configuration Arbitrage par défaut
            "arbitrage": {
                "enabled": False,  # Désactivé par défaut
                "capital_dedicated": 0,
                "percent_per_trade": 0,
                "min_profit_threshold": 0,
                "min_amount_per_trade": 0,
                "max_amount_per_trade": 0,
                "cooldown_seconds": 30,
                "max_concurrent_trades": 0,
                "blacklist_tokens": []
            },
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
        self.save_config_sync()  # Sauvegarde immédiate pour création

    def _do_save(self):
        """Effectue la sauvegarde réelle sur disque"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=2)  # indent=2 au lieu de 4 (plus rapide)
            self._pending_save = False
        except Exception as e:
            print(f"❌ Erreur sauvegarde config: {e}")

    def save_config(self):
        """⚡ Sauvegarde ASYNCHRONE avec debouncing (500ms)"""
        with self._save_lock:
            # Annuler le timer précédent si existant
            if self._save_timer is not None:
                self._save_timer.cancel()
            
            # Planifier sauvegarde dans 500ms
            self._save_timer = threading.Timer(0.5, self._do_save)
            self._save_timer.daemon = True
            self._save_timer.start()
            self._pending_save = True

    def save_config_sync(self):
        """Sauvegarde SYNCHRONE immédiate (pour cas critiques)"""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
            self._do_save()

    def get_portfolio_value(self):
        """Calcule la valeur du portefeuille = capital initial + PnL total"""
        # Calculer le PnL total depuis les positions réelles
        total_pnl = self.get_total_pnl()

        # Utiliser le solde réel du wallet
        initial_capital = self.get_wallet_balance_dynamic()

        result = round(initial_capital + total_pnl, 2)
        return result

    def get_total_pnl(self):
        """Retourne le PnL total RÉEL depuis auto_sell_manager (SEULEMENT des traders ACTIFS)"""
        try:
            from auto_sell_manager import auto_sell_manager
            
            total_pnl = 0
            # Boucler sur les traders actifs et additionner leur PnL réel
            for trader in self.data['traders']:
                if trader.get('active'):
                    trader_pnl_data = auto_sell_manager.get_trader_pnl(trader['name'])
                    total_pnl += trader_pnl_data.get('pnl', 0)
            
            return round(total_pnl, 2)
        except Exception as e:
            print(f"⚠️ Erreur calcul PnL total: {e}")
            return 0

    def get_wallet_balance_dynamic(self):
        """Retourne le balance réel du wallet depuis Solana (avec cache 10s)"""
        current_time = time.time()
        
        # Cache hit
        if (self.wallet_balance_cache is not None and 
            self.wallet_balance_cache_time is not None and 
            current_time - self.wallet_balance_cache_time < self.wallet_balance_cache_ttl):
            return self.wallet_balance_cache
        
        # Cache miss - récupérer balance réel
        try:
            from solana_integration import solana_integration
            
            wallet_address = self.data.get('wallet_address')
            if not wallet_address:
                private_key = self.data.get('wallet_private_key', '')
                if private_key and Keypair:
                    try:
                        keypair = Keypair.from_secret_key(bytes.fromhex(private_key))
                        wallet_address = str(keypair.pubkey())
                    except:
                        return 0
                else:
                    return 0
            
            balance_sol = solana_integration.get_sol_balance(wallet_address)
            self.wallet_balance_cache = balance_sol
            self.wallet_balance_cache_time = current_time
            return balance_sol
        except Exception as e:
            print(f"⚠️ Erreur get_wallet_balance_dynamic: {e}")
            return 0

    def get_active_traders_count(self):
        return sum(1 for t in self.data['traders'] if t['active'])

    def toggle_trader(self, index, state):
        """⚡ OPTIMISÉ: Toggle avec sauvegarde asynchrone"""
        current_active = self.get_active_traders_count()
        if state and current_active >= self.data['active_traders_limit'] and not self.data['traders'][index]['active']:
            return False
        self.data['traders'][index]['active'] = state
        self.save_config()  # Asynchrone avec debouncing
        return True

    def toggle_bot(self, status):
        """Toggle l'état du bot et persiste dans config"""
        self.is_running = status
        self.data['is_running'] = status  # Persister l'état
        self.save_config()  # Sauvegarder (asynchrone avec debouncing)
        print(f"🤖 Bot {'ACTIVÉ ✅' if status else 'DÉSACTIVÉ ❌'}")

    def update_trader(self, index, name, emoji, address, capital=None, per_trade_amount=None, min_trade_amount=None):
        """⚡ OPTIMISÉ: Update avec sauvegarde asynchrone"""
        self.data['traders'][index]['name'] = name
        self.data['traders'][index]['emoji'] = emoji
        self.data['traders'][index]['address'] = address
        if capital is not None:
            self.data['traders'][index]['capital'] = float(capital)
        if per_trade_amount is not None:
            self.data['traders'][index]['per_trade_amount'] = float(per_trade_amount)
        if min_trade_amount is not None:
            self.data['traders'][index]['min_trade_amount'] = float(min_trade_amount)
        self.save_config()  # Asynchrone avec debouncing
    
    def update_take_profit(self, tp1_percent, tp1_profit, tp2_percent, tp2_profit, tp3_percent, tp3_profit, sl_percent, sl_loss):
        """⚡ OPTIMISÉ: Update TP/SL avec sauvegarde asynchrone"""
        self.data['tp1_percent'] = tp1_percent
        self.data['tp1_profit'] = tp1_profit
        self.data['tp2_percent'] = tp2_percent
        self.data['tp2_profit'] = tp2_profit
        self.data['tp3_percent'] = tp3_percent
        self.data['tp3_profit'] = tp3_profit
        self.data['sl_percent'] = sl_percent
        self.data['sl_loss'] = sl_loss
        self.data['params_saved'] = True  # Marquer comme sauvegardé
        print("💾 Paramètres sauvegardés - seront préservés au prochain démarrage")
        self.save_config()  # Asynchrone avec debouncing

    def set_trader_capital(self, trader_index, capital):
        """Définit le capital alloué pour un trader"""
        if 0 <= trader_index < len(self.data['traders']):
            self.data['traders'][trader_index]['capital'] = float(capital)
            self.save_config()  # Asynchrone avec debouncing
            return True
        return False


    def update_slippage(self, slippage):
        """Met à jour le slippage et marque comme sauvegardé"""
        self.data['slippage'] = float(slippage)
        self.data['params_saved'] = True
        print("💾 Slippage sauvegardé - sera préservé au prochain démarrage")
        self.save_config()
    
    def update_arbitrage_config(self, arbitrage_config):
        """Met à jour la config arbitrage et marque comme sauvegardé"""
        self.data['arbitrage'] = arbitrage_config
        self.data['params_saved'] = True
        print("💾 Config arbitrage sauvegardée - sera préservée au prochain démarrage")
        self.save_config()

    def initialize_test_prices(self):
        """Initialise les prix simulés pour MODE TEST (DEPRECATED - MODE REAL uniquement)"""
        pass

    def get_capital_summary(self):
        """Retourne un résumé du capital alloué"""
        # Utiliser le capital réel du wallet
        total_capital = self.get_wallet_balance_dynamic()
        
        allocated_capital = sum(
            trader.get('capital', 0) 
            for trader in self.data['traders'] 
            if trader.get('active', False)
        )
        
        remaining_capital = total_capital - allocated_capital
        
        return {
            'total_capital': total_capital,
            'allocated_capital': allocated_capital,
            'remaining_capital': max(0, remaining_capital),
            'allocation_percent': round((allocated_capital / total_capital * 100) if total_capital > 0 else 0, 1)
        }
