# -*- coding: utf-8 -*-
"""
Bot de Copy Trading Polymarket
Point d'entrée principal - Connecte le Tracker et l'Executor
"""
import os
import threading
import time
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

from polymarket_tracking import tracker
from polymarket_executor import executor

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("PolymarketBot")

# Charger la configuration
load_dotenv()

def load_config():
    """Charge la configuration depuis config.json"""
    config_path = Path('config.json')
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {
        'tracked_wallets': [],
        'polling_interval': 10,
        'dry_run': True,
        'max_position_usd': 100
    }

def save_config(config):
    """Sauvegarde la configuration"""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)

def on_trade_signal(signal):
    """Callback appelé quand un signal de trading est détecté"""
    logger.info(f"📡 Signal détecté: {signal['type']} depuis {signal['wallet'][:10]}...")
    result = executor.on_signal_detected(signal)
    return result

def start_monitoring(config):
    """Démarre le monitoring des wallets"""
    wallets = config.get('tracked_wallets', [])
    interval = config.get('polling_interval', 10)
    
    if not wallets:
        logger.warning("⚠️ Aucun wallet à suivre. Ajoutez des adresses dans config.json")
        return
    
    # Ajouter les wallets au tracker
    for wallet in wallets:
        tracker.add_wallet(wallet)
    
    logger.info(f"🚀 Démarrage du monitoring ({len(wallets)} wallets, intervalle {interval}s)")
    
    # Démarrer la boucle de monitoring
    tracker.monitor_loop(interval=interval, callback=on_trade_signal)

def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("🚀 POLYMARKET COPY TRADING BOT")
    print("=" * 60)
    
    # Charger la config
    config = load_config()
    
    # Afficher le statut
    dry_run = config.get('dry_run', True)
    wallets = config.get('tracked_wallets', [])
    
    print(f"Mode: {'🔬 DRY RUN (Simulation)' if dry_run else '💰 RÉEL'}")
    print(f"Wallets suivis: {len(wallets)}")
    print(f"Position max: ${config.get('max_position_usd', 100)}")
    print("=" * 60)
    
    if not wallets:
        print("\n⚠️ Aucun wallet configuré!")
        print("Ajoutez des adresses dans config.json:")
        print('  "tracked_wallets": ["0x..."]')
        print("\nExemple de config.json:")
        example_config = {
            'tracked_wallets': ['0x56687bf447db6ffa42ffe2204a05edaa20f55839'],
            'polling_interval': 10,
            'dry_run': True,
            'max_position_usd': 100
        }
        save_config(example_config)
        print(json.dumps(example_config, indent=2))
        return
    
    # Démarrer le monitoring dans un thread
    monitor_thread = threading.Thread(target=start_monitoring, args=(config,), daemon=True)
    monitor_thread.start()
    
    # Garder le processus principal actif
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bot...")

if __name__ == "__main__":
    main()
