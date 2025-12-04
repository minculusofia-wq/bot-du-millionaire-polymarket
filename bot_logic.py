# -*- coding: utf-8 -*-
"""
Bot Logic - Backend pour Polymarket Copy Trading + Arbitrage Solana
"""
import json
import threading
from datetime import datetime

class BotBackend:
    def __init__(self):
        self.config_file = "config.json"

        # Locks pour sauvegarde thread-safe
        self._save_timer = None
        self._save_lock = threading.Lock()
        self._pending_save = False

        self.load_config()
        self.is_running = self.data.get('is_running', False)

    def load_config(self):
        """Charge la configuration depuis config.json"""
        try:
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
                self._migrate_config()
        except FileNotFoundError:
            self._create_default_config()
        except Exception as e:
            print(f"❌ Erreur chargement config: {e}")
            self._create_default_config()

    def _migrate_config(self):
        """Migre les anciennes configurations vers la nouvelle structure"""
        needs_save = False

        # Supprimer les anciennes clés si présentes
        old_keys = ['total_capital', 'slippage', 'tp1_percent', 'tp1_profit',
                    'tp2_percent', 'tp2_profit', 'tp3_percent', 'tp3_profit',
                    'sl_percent', 'sl_loss', 'active_traders_limit', 'currency',
                    'wallet_private_key', 'rpc_url', 'traders']
        for key in old_keys:
            if key in self.data:
                del self.data[key]
                needs_save = True
                print(f"🔄 Migration: Suppression de '{key}'")

        # Ajouter is_running si manquant
        if 'is_running' not in self.data:
            self.data['is_running'] = False
            needs_save = True

        # Ajouter params_saved si manquant
        if 'params_saved' not in self.data:
            self.data['params_saved'] = False
            needs_save = True

        # Ajouter polymarket_wallet si manquant
        if 'polymarket_wallet' not in self.data:
            self.data['polymarket_wallet'] = {
                "address": "",
                "private_key": ""
            }
            needs_save = True
            print("🔄 Migration: Ajout polymarket_wallet")

        # Ajouter solana_wallet si manquant
        if 'solana_wallet' not in self.data:
            self.data['solana_wallet'] = {
                "address": "",
                "private_key": "",
                "rpc_url": "https://api.mainnet-beta.solana.com"
            }
            needs_save = True
            print("🔄 Migration: Ajout solana_wallet")

        # Ajouter polymarket config si manquant
        if 'polymarket' not in self.data:
            self.data['polymarket'] = {
                "enabled": False,
                "dry_run": True,
                "tracked_wallets": [],
                "polling_interval": 30,
                "max_position_usd": 0,
                "min_position_usd": 0,
                "copy_percentage": 100,
                "signals_detected": 0,
                "trades_copied": 0,
                "total_profit": 0,
                "win_rate": 0
            }
            needs_save = True
            print("🔄 Migration: Ajout config polymarket")

        # Ajouter arbitrage config si manquant
        if 'arbitrage' not in self.data:
            self.data['arbitrage'] = {
                "enabled": False,
                "capital_dedicated": 0,
                "percent_per_trade": 0,
                "min_profit_threshold": 0.5,
                "min_amount_per_trade": 0,
                "max_amount_per_trade": 0,
                "cooldown_seconds": 60,
                "max_concurrent_trades": 3,
                "dex_list": ["raydium", "orca", "jupiter"],
                "blacklist_tokens": []
            }
            needs_save = True
            print("🔄 Migration: Ajout config arbitrage")

        # Reset à 0 si params_saved = False
        if not self.data.get('params_saved', False):
            print("🔄 Reset: Paramètres à 0 (pas de sauvegarde précédente)")

            # Reset polymarket
            if 'polymarket' in self.data:
                self.data['polymarket']['enabled'] = False
                self.data['polymarket']['polling_interval'] = 30
                self.data['polymarket']['max_position_usd'] = 0
                self.data['polymarket']['min_position_usd'] = 0
                self.data['polymarket']['signals_detected'] = 0
                self.data['polymarket']['trades_copied'] = 0
                self.data['polymarket']['total_profit'] = 0
                self.data['polymarket']['win_rate'] = 0

            # Reset arbitrage
            if 'arbitrage' in self.data:
                self.data['arbitrage']['enabled'] = False
                self.data['arbitrage']['capital_dedicated'] = 0
                self.data['arbitrage']['percent_per_trade'] = 0

            needs_save = True
        else:
            print("✅ Paramètres chargés depuis sauvegarde précédente")

        if needs_save:
            self.save_config_sync()
            print("✅ Migration de config effectuée")

    def _create_default_config(self):
        """Crée une configuration par défaut"""
        self.data = {
            "is_running": False,
            "params_saved": False,

            "polymarket_wallet": {
                "address": "",
                "private_key": ""
            },

            "solana_wallet": {
                "address": "",
                "private_key": "",
                "rpc_url": "https://api.mainnet-beta.solana.com"
            },

            "polymarket": {
                "enabled": False,
                "dry_run": True,
                "tracked_wallets": [],
                "polling_interval": 30,
                "max_position_usd": 0,
                "min_position_usd": 0,
                "copy_percentage": 100,
                "signals_detected": 0,
                "trades_copied": 0,
                "total_profit": 0,
                "win_rate": 0
            },

            "arbitrage": {
                "enabled": False,
                "capital_dedicated": 0,
                "percent_per_trade": 0,
                "min_profit_threshold": 0.5,
                "min_amount_per_trade": 0,
                "max_amount_per_trade": 0,
                "cooldown_seconds": 60,
                "max_concurrent_trades": 3,
                "dex_list": ["raydium", "orca", "jupiter"],
                "blacklist_tokens": []
            }
        }
        self.save_config_sync()
        print("✅ Configuration par défaut créée")

    def _do_save(self):
        """Effectue la sauvegarde réelle sur disque"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            self._pending_save = False
        except Exception as e:
            print(f"❌ Erreur sauvegarde config: {e}")

    def save_config(self):
        """Sauvegarde ASYNCHRONE avec debouncing (500ms)"""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()

            self._save_timer = threading.Timer(0.5, self._do_save)
            self._save_timer.daemon = True
            self._save_timer.start()
            self._pending_save = True

    def save_config_sync(self):
        """Sauvegarde SYNCHRONE immédiate"""
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
            self._do_save()

    def toggle_bot(self, status):
        """Toggle l'état du bot et persiste dans config"""
        self.is_running = status
        self.data['is_running'] = status
        self.save_config_sync()
        print(f"🤖 Bot {'ACTIVÉ ✅' if status else 'DÉSACTIVÉ ❌'}")
