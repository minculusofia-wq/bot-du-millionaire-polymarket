#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot du Millionnaire - Polymarket Copy Trading
================================================================
Bot de copy trading sur Polymarket.
"""

import os
import json
import threading
import time
import logging # ✨ Logging
import subprocess
import signal
import requests
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit

# ⚡ Libérer le port 5000 au démarrage
def kill_port(port=5000):
    """Tue les processus utilisant le port spécifié"""
    try:
        # Trouver les PID sur le port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')
        for pid in pids:
            if pid:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"🔄 Process {pid} sur port {port} terminé")
                except:
                    pass
        time.sleep(1)
    except Exception as e:
        pass  # Silencieux si erreur

kill_port(5000)

# ⚡ Charger variables d'environnement depuis .env
def load_env_file():
    """Charge les variables d'environnement depuis .env"""
    env_file = Path('.env')
    if env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
            print("✅ Fichier .env chargé")
        except Exception as e:
            print(f"⚠️ Erreur lecture .env: {e}")

load_env_file()

# Imports locaux
from bot_logic import BotBackend
from db_manager import db_manager
from audit_logger import audit_logger
from secret_manager import secret_manager

# 🔧 Optimisations
from logging_config import setup_logging, get_logger
from startup_reconciler import run_startup_reconciliation
from cache_manager import start_cleanup_scheduler

# Init Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading') # Utiliser threading pour compatibilité simple

# 🔧 Configuration Logging Structuré
log_level = os.getenv('LOG_LEVEL', 'INFO')
setup_logging(level=log_level, log_to_file=True, json_logs=False)
logger = get_logger("BotBackend")

# 🔧 Démarrer le nettoyage automatique du cache
start_cleanup_scheduler(interval=300)  # Toutes les 5 minutes

backend = BotBackend()

# Imports Polymarket (avec fallback)
try:
    from polymarket_tracking import PolymarketTracker
    from polymarket_executor import PolymarketExecutor
    from trailing_monitor import TrailingStopMonitor # ✨ Import Monitor
    
    polymarket_tracker = PolymarketTracker(socketio=socketio)
    polymarket_executor = PolymarketExecutor(backend=backend, socketio=socketio)
    
    # 🔌 CONNEXION CRITIQUE : Connecter le Tracker à l'Exécuteur
    polymarket_tracker.add_callback(polymarket_executor.on_signal_detected)
    print("✅ Tracker connecté à l'Exécuteur")
    
    # 🚀 Démarrer le monitoring en arrière-plan
    monitoring_interval = backend.data.get('polymarket', {}).get('polling_interval', 5)
    polymarket_tracker.start_monitoring(interval=monitoring_interval)
    print("✅ Monitoring Polymarket démarré")
    
    # 🛡️ Démarrer le Trailing Stop Monitor
    trailing_monitor = TrailingStopMonitor(db_manager, polymarket_executor)
    trailing_monitor.start()
    
except ImportError as e:
    print(f"⚠️ Modules Polymarket non disponibles: {e}")
    polymarket_tracker = None
    polymarket_executor = None
    trailing_monitor = None

# Imports WebSocket Polygon (avec fallback)
try:
    from polygon_websocket import PolygonWebSocket
    polygon_ws = PolygonWebSocket()
except ImportError as e:
    print(f"⚠️ WebSocket Polygon non disponible: {e}")
    polygon_ws = None

# Imports CLOB Polymarket (avec fallback)
try:
    from polymarket_client import polymarket_client as polymarket_clob
    print(f"✅ Client Polymarket unifié chargé: {polymarket_clob.get_stats()}")
except ImportError as e:
    print(f"⚠️ CLOB Polymarket non disponible: {e}")
    polymarket_clob = None

# ============================================================================
# INITIALISATION
# ============================================================================



print("=" * 60)
print("🎯 BOT DU MILLIONNAIRE - POLYMARKET COPY TRADING")
print("=" * 60)
print(f"✅ Configuration chargée")
print(f"📊 Polymarket: {'Activé' if backend.data.get('polymarket', {}).get('enabled') else 'Désactivé'}")
print(f"🔌 WebSocket Polygon: {'Disponible' if polygon_ws else 'Non disponible'}")
print(f"📈 CLOB Polymarket: {'Disponible' if polymarket_clob else 'Non disponible'}")
print("=" * 60)


# ============================================================================
# ROUTES API
# ============================================================================

@app.route('/')
def index():
    """Page principale"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """Status complet du bot"""
    ws_count = 0
    try:
        if hasattr(socketio, 'server') and hasattr(socketio.server, 'eio'):
             ws_count = len(socketio.server.eio.clients)
    except:
        pass

    return jsonify({
        'is_running': backend.is_running,
        'polymarket': backend.data.get('polymarket', {}),
        'polymarket_wallet': {
            'address': backend.data.get('polymarket_wallet', {}).get('address', ''),
            'has_key': bool(os.getenv('POLYGON_PRIVATE_KEY'))
        },
        'polymarket_api': {
            'key': os.getenv('POLYMARKET_API_KEY', ''),
            'has_secret': bool(os.getenv('POLYMARKET_SECRET')),
            'has_passphrase': bool(os.getenv('POLYMARKET_PASSPHRASE'))
        },
        'ws_clients': ws_count
    })

@app.route('/health')
def health_check():
    """Health check endpoint pour monitoring"""
    ws_count = 0
    try:
        if hasattr(socketio, 'server') and hasattr(socketio.server, 'eio'):
             ws_count = len(socketio.server.eio.clients)
    except:
        pass

    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'db': db_manager.check_db(),
        'ws_clients': ws_count,
        'threads': [t.name for t in threading.enumerate()]
    })

@app.route('/api/toggle_bot', methods=['POST'])
def api_toggle_bot():
    """Activer/désactiver le bot"""
    backend.toggle_bot(not backend.is_running)
    return jsonify({
        'success': True,
        'is_running': backend.is_running
    })

@app.route('/api/balances')
def api_balances():
    """Récupérer les soldes du wallet Polymarket (Polygon)"""
    result = {
        'success': True,
        'polymarket': {'usdc': 0.0, 'matic': 0.0}
    }

    # Balance Polygon (Polymarket wallet)
    pm_address = backend.data.get('polymarket_wallet', {}).get('address', '')
    if pm_address:
        try:
            # USDC sur Polygon (contrat USDC.e)
            usdc_contract = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
            # Appel RPC Polygon pour balance USDC
            resp = requests.post(
                'https://polygon-rpc.com',
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{
                        "to": usdc_contract,
                        "data": f"0x70a08231000000000000000000000000{pm_address[2:]}"
                    }, "latest"],
                    "id": 1
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if 'result' in data and data['result'] != '0x':
                    balance_wei = int(data['result'], 16)
                    result['polymarket']['usdc'] = balance_wei / 1e6  # USDC has 6 decimals

            # Balance MATIC native
            resp2 = requests.post(
                'https://polygon-rpc.com',
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [pm_address, "latest"],
                    "id": 2
                },
                timeout=10
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                if 'result' in data2:
                    balance_wei = int(data2['result'], 16)
                    result['polymarket']['matic'] = balance_wei / 1e18
        except Exception as e:
            print(f"⚠️ Erreur récupération balance Polygon: {e}")

    return jsonify(result)

# ============================================================================
# POLYMARKET ROUTES
# ============================================================================

@app.route('/api/polymarket/toggle', methods=['POST'])
def api_polymarket_toggle():
    """Active/désactive le copy trading Polymarket"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)

        if 'polymarket' not in backend.data:
            backend.data['polymarket'] = {}

        backend.data['polymarket']['enabled'] = enabled
        backend.save_config_sync()

        return jsonify({
            'success': True,
            'enabled': enabled
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/polymarket/config', methods=['GET', 'POST'])
def api_polymarket_config():
    """Get/Set configuration Polymarket"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'config': backend.data.get('polymarket', {})
        })

    try:
        data = request.get_json()
        pm = backend.data.get('polymarket', {})

        if 'polling_interval' in data:
            pm['polling_interval'] = int(data['polling_interval'])
        if 'max_position_usd' in data:
            pm['max_position_usd'] = float(data['max_position_usd'])
        if 'min_position_usd' in data:
            pm['min_position_usd'] = float(data['min_position_usd'])
        if 'copy_percentage' in data:
            pm['copy_percentage'] = int(data['copy_percentage'])
        
        # dry_run is removed from config logic, so we ignore it or error if passed?
        # We just ignore it to be safe, ensuring it's not set.

        backend.data['polymarket'] = pm
        backend.save_config_sync()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/polymarket/stats')
def api_polymarket_stats():
    """Statistiques Polymarket"""
    pm = backend.data.get('polymarket', {})
    return jsonify({
        'success': True,
        'stats': {
            'enabled': pm.get('enabled', False),
            'signals_detected': pm.get('signals_detected', 0),
            'trades_copied': pm.get('trades_copied', 0),
            'total_profit': pm.get('total_profit', 0),
            'win_rate': pm.get('win_rate', 0)
        }
    })

# ============================================================================
# WALLETS ROUTES
# ============================================================================

@app.route('/api/wallets')
def api_wallets():
    """Liste des wallets suivis"""
    wallets = backend.data.get('polymarket', {}).get('tracked_wallets', [])
    return jsonify({
        'success': True,
        'wallets': wallets
    })

@app.route('/api/wallets/add', methods=['POST'])
def api_wallets_add():
    """Ajouter un wallet à suivre"""
    try:
        data = request.get_json()
        address = data.get('address', '').strip()
        name = data.get('name', 'Wallet')

        if not address:
            return jsonify({'success': False, 'error': 'Adresse requise'}), 400

        if 'polymarket' not in backend.data:
            backend.data['polymarket'] = {}
        if 'tracked_wallets' not in backend.data['polymarket']:
            backend.data['polymarket']['tracked_wallets'] = []

        # Vérifier si déjà présent
        for w in backend.data['polymarket']['tracked_wallets']:
            if w.get('address') == address:
                return jsonify({'success': False, 'error': 'Wallet déjà suivi'}), 400

        backend.data['polymarket']['tracked_wallets'].append({
            'address': address,
            'name': name,
            'added_at': datetime.now().isoformat()
        })
        backend.save_config_sync()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wallets/remove', methods=['POST'])
def api_wallets_remove():
    """Supprimer un wallet suivi"""
    try:
        data = request.get_json()
        address = data.get('address')

        wallets = backend.data.get('polymarket', {}).get('tracked_wallets', [])
        backend.data['polymarket']['tracked_wallets'] = [
            w for w in wallets if w.get('address') != address
        ]
        backend.save_config_sync()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wallets/config', methods=['POST'])
def api_wallets_config():
    """Configurer capital, % par trade, SL/TP pour un wallet"""
    try:
        data = request.get_json()
        address = data.get('address')
        capital_allocated = float(data.get('capital_allocated', 0))
        percent_per_trade = float(data.get('percent_per_trade', 0))
        sl_percent = data.get('sl_percent')
        tp_percent = data.get('tp_percent')
        use_kelly = data.get('use_kelly', False) # ✨ Config Kelly

        if not address:
            return jsonify({'success': False, 'error': 'Adresse requise'}), 400

        # Trouver et mettre à jour le wallet
        wallets = backend.data.get('polymarket', {}).get('tracked_wallets', [])
        wallet_found = False

        for wallet in wallets:
            if wallet.get('address') == address:
                wallet['capital_allocated'] = capital_allocated
                wallet['percent_per_trade'] = percent_per_trade
                wallet['sl_percent'] = float(sl_percent) if sl_percent is not None else None
                wallet['tp_percent'] = float(tp_percent) if tp_percent is not None else None
                wallet['use_kelly'] = bool(use_kelly) # ✨ Save Kelly Flag
                wallet['use_trailing'] = bool(data.get('use_trailing', False)) # ✨ Save Trailing Flag
                wallet_found = True
                break

        if not wallet_found:
            return jsonify({'success': False, 'error': 'Wallet non trouvé'}), 404

        backend.data['polymarket']['tracked_wallets'] = wallets
        backend.save_config_sync()

        print(f"✅ Config wallet mise à jour: {address[:10]}... | Capital: ${capital_allocated} | Kelly: {use_kelly}")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wallets/toggle', methods=['POST'])
def api_wallets_toggle():
    """Activer/désactiver un wallet suivi"""
    try:
        data = request.get_json()
        address = data.get('address')
        active = data.get('active', True)

        if not address:
            return jsonify({'success': False, 'error': 'Adresse requise'}), 400

        # Trouver et mettre à jour le wallet
        wallets = backend.data.get('polymarket', {}).get('tracked_wallets', [])
        wallet_found = False

        for wallet in wallets:
            if wallet.get('address') == address:
                wallet['active'] = active
                wallet_found = True
                break

        if not wallet_found:
            return jsonify({'success': False, 'error': 'Wallet non trouvé'}), 404

        backend.data['polymarket']['tracked_wallets'] = wallets
        backend.save_config_sync()

        status = "activé" if active else "désactivé"
        print(f"✅ Wallet {status}: {address[:10]}...")

        return jsonify({'success': True, 'active': active})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/polymarket/credentials', methods=['POST'])
def api_polymarket_credentials():
    """Sauvegarde les identifiants Polymarket (Wallet + API) de manière chiffrée"""
    try:
        data = request.get_json()
        address = data.get('address', '').strip()
        private_key = data.get('private_key', '').strip()
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()
        api_passphrase = data.get('api_passphrase', '').strip()

        # 1. Mise à jour de l'adresse dans config.json
        if address:
            backend.data['polymarket_wallet']['address'] = address
            backend.save_config_sync()

        # 2. Mise à jour du .env avec chiffrement
        env_path = os.path.join(os.getcwd(), '.env')
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()

        # Dictionnaire des clés à mettre à jour
        updates = {}
        if private_key: updates['POLYGON_PRIVATE_KEY'] = secret_manager.encrypt(private_key)
        if api_key: updates['POLYMARKET_API_KEY'] = api_key
        if api_secret: updates['POLYMARKET_SECRET'] = secret_manager.encrypt(api_secret)
        if api_passphrase: updates['POLYMARKET_PASSPHRASE'] = secret_manager.encrypt(api_passphrase)

        new_lines = []
        keys_found = set()
        
        for line in lines:
            found = False
            for k in updates:
                if line.startswith(f'{k}='):
                    new_lines.append(f'{k}="{updates[k]}"\n')
                    keys_found.add(k)
                    found = True
                    break
            if not found:
                new_lines.append(line)

        # Ajouter les clés non trouvées
        for k, v in updates.items():
            if k not in keys_found:
                new_lines.append(f'{k}="{v}"\n')

        with open(env_path, 'w') as f:
            f.writelines(new_lines)

        # 3. Informer les composants (Rechargement à chaud)
        if private_key:
            if polymarket_executor and hasattr(polymarket_executor, 'set_wallet'):
                polymarket_executor.set_wallet(private_key)
            if polymarket_clob:
                polymarket_clob.set_wallet(private_key)

        if api_key or api_secret or api_passphrase:
            current_key = api_key or os.getenv('POLYMARKET_API_KEY', '')
            # Pour le secret et passphrase, on récupère l'actuel déchiffré si non fourni
            current_secret = api_secret or secret_manager.decrypt(os.getenv('POLYMARKET_SECRET', ''))
            current_pass = api_passphrase or secret_manager.decrypt(os.getenv('POLYMARKET_PASSPHRASE', ''))
            
            if polymarket_clob and hasattr(polymarket_clob, 'set_api_credentials'):
                polymarket_clob.set_api_credentials(current_key, current_secret, current_pass)

        # Recharger les variables d'environnement pour le processus actuel
        for k, v in updates.items():
            os.environ[k] = v

        return jsonify({'success': True, 'message': 'Identifiants sauvegardés avec succès'})
    except Exception as e:
        print(f"❌ Erreur sauvegarde identifiants: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wallet/polymarket', methods=['POST'])
def api_wallet_polymarket():
    """Gardé pour compatibilité"""
    return api_polymarket_credentials()

# ============================================================================
# HISTORY & EXPORT
# ============================================================================

@app.route('/api/history')
def api_history():
    """Historique des trades (depuis DB)"""
    trades = db_manager.get_polymarket_trades(limit=100)
    return jsonify({
        'success': True,
        'trades': trades
    })

@app.route('/api/positions')
def api_positions():
    """Positions actives (depuis DB)"""
    positions = db_manager.get_bot_positions()
    return jsonify({
        'success': True,
        'positions': positions
    })

@app.route('/api/positions/sell', methods=['POST'])
def api_positions_sell():
    """Vendre une position (totalement ou partiellement)"""
    try:
        data = request.get_json()
        position_id = data.get('position_id')
        percent = int(data.get('percent', 100))

        if not position_id:
            return jsonify({'success': False, 'error': 'Position ID requise'}), 400

        if percent < 1 or percent > 100:
            return jsonify({'success': False, 'error': 'Pourcentage invalide (1-100)'}), 400

        # Trouver la position depuis la DB
        positions = db_manager.get_bot_positions()
        position = next((p for p in positions if p['id'] == position_id), None)

        if not position:
            return jsonify({'success': False, 'error': 'Position non trouvée'}), 404

        # Calculer le montant à vendre (en USD)
        current_amount_usd = float(position.get('amount', 0))
        amount_to_sell_usd = (current_amount_usd * percent) / 100
        
        # Exécution réelle via polymarket_executor
        if polymarket_executor:
            try:
                result = polymarket_executor.sell_position(
                    position_id=position_id,
                    amount=amount_to_sell_usd,
                    market=position.get('market'),
                    side=position.get('side')
                )
                if not result.get('success'):
                    return jsonify({'success': False, 'error': result.get('error', 'Erreur exécution')}), 500
                
                # Le PnL réalisé est calculé dans sell_position
                # Mais pour le retour immédiat à l'API, on peut l'estimer ou attendre l'update UI
                return jsonify({
                    'success': True,
                    'amount_sold': amount_to_sell_usd,
                    'dry_run': False
                })
            except Exception as e:
                return jsonify({'success': False, 'error': f'Erreur exécution: {str(e)}'}), 500
        else:
             return jsonify({'success': False, 'error': 'Polymarket Executor non disponible'}), 500

    except Exception as e:
        print(f"❌ Erreur vente position: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats/pnl_history')
def pnl_history():
    """Historique du PnL cumulé pour le graphique"""
    try:
        days = request.args.get('days', 30, type=int)
        history = db_manager.get_daily_pnl(days)
        
        # Inverser pour ordre chronologique (le SQL retourne DESC)
        history.reverse()

        dates = [row['day'] for row in history]
        daily_pnls = [row['daily_pnl'] for row in history]
        
        # Calcul cumulatif (simple addition pas à pas)
        cumulative = []
        current_sum = 0
        for val in daily_pnls:
            current_sum += (val or 0)
            cumulative.append(current_sum)
            
        return jsonify({
            'success': True,
            'dates': dates,
            'daily_values': daily_pnls,
            'cumulative_values': cumulative
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/benchmark')
def api_benchmark():
    """Benchmark des wallets suivis"""
    wallets = backend.data.get('polymarket', {}).get('tracked_wallets', [])
    benchmark = []
    for w in wallets:
        benchmark.append({
            'address': w.get('address'),
            'name': w.get('name'),
            'win_rate': 0,
            'pnl': 0,
            'trades': 0
        })
    return jsonify({
        'success': True,
        'benchmark': benchmark
    })

@app.route('/api/export')
def api_export():
    """Export des données"""
    try:
        trades = db_manager.get_polymarket_trades(limit=1000)
        positions = db_manager.get_bot_positions()
        
        data = {
            'config': backend.data,
            'history': trades,
            'positions': positions,
            'exported_at': datetime.now().isoformat()
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reset_stats', methods=['POST'])
def api_reset_stats():
    """Reset des statistiques"""
    try:
        if 'polymarket' in backend.data:
            backend.data['polymarket']['signals_detected'] = 0
            backend.data['polymarket']['trades_copied'] = 0
            backend.data['polymarket']['total_profit'] = 0
            backend.data['polymarket']['win_rate'] = 0
        backend.save_config_sync()

        # Nettoyer les tables DB
        # Note: ceci est une opération destructive
        db_manager._execute("DELETE FROM polymarket_trades")
        db_manager._execute("DELETE FROM bot_positions")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# WEBSOCKET POLYGON ROUTES
# ============================================================================

@app.route('/api/websocket/status')
def api_websocket_status():
    """Status du WebSocket Polygon"""
    if not polygon_ws:
        return jsonify({
            'success': True,
            'available': False,
            'message': 'WebSocket Polygon non disponible'
        })

    stats = polygon_ws.get_stats()
    return jsonify({
        'success': True,
        'available': True,
        'stats': stats
    })

@app.route('/api/websocket/start', methods=['POST'])
def api_websocket_start():
    """Démarrer le WebSocket Polygon"""
    if not polygon_ws:
        return jsonify({'success': False, 'error': 'WebSocket non disponible'}), 400

    try:
        # Ajouter tous les wallets suivis au WebSocket
        wallets = backend.data.get('polymarket', {}).get('tracked_wallets', [])
        for w in wallets:
            polygon_ws.add_wallet(w.get('address', ''))

        # Démarrer le WebSocket
        polygon_ws.start()

        return jsonify({
            'success': True,
            'message': 'WebSocket démarré'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/websocket/stop', methods=['POST'])
def api_websocket_stop():
    """Arrêter le WebSocket Polygon"""
    if not polygon_ws:
        return jsonify({'success': False, 'error': 'WebSocket non disponible'}), 400

    try:
        polygon_ws.stop()
        return jsonify({
            'success': True,
            'message': 'WebSocket arrêté'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# CLOB POLYMARKET ROUTES
# ============================================================================

@app.route('/api/clob/status')
def api_clob_status():
    """Status de l'API CLOB Polymarket"""
    if not polymarket_clob:
        return jsonify({
            'success': True,
            'available': False,
            'message': 'CLOB Polymarket non disponible'
        })

    stats = polymarket_clob.get_stats()
    return jsonify({
        'success': True,
        'available': True,
        'authenticated': polymarket_clob.authenticated,
        'stats': stats
    })

@app.route('/api/clob/orderbook/<token_id>')
def api_clob_orderbook(token_id):
    """Order book pour un marché"""
    if not polymarket_clob:
        return jsonify({'success': False, 'error': 'CLOB non disponible'}), 400

    try:
        orderbook = polymarket_clob.get_order_book(token_id)
        return jsonify({
            'success': True,
            'orderbook': orderbook
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clob/price/<token_id>')
def api_clob_price(token_id):
    """Meilleur prix bid/ask pour un marché"""
    if not polymarket_clob:
        return jsonify({'success': False, 'error': 'CLOB non disponible'}), 400

    try:
        prices = polymarket_clob.get_best_bid_ask(token_id)
        return jsonify({
            'success': True,
            'prices': prices
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clob/markets')
def api_clob_markets():
    """Liste des marchés actifs"""
    if not polymarket_clob:
        return jsonify({'success': False, 'error': 'CLOB non disponible'}), 400

    try:
        limit = request.args.get('limit', 50, type=int)
        markets = polymarket_clob.get_markets(limit=limit)
        return jsonify({
            'success': True,
            'markets': markets
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clob/place_order', methods=['POST'])
def api_clob_place_order():
    """Placer un ordre sur Polymarket"""
    if not polymarket_clob:
        return jsonify({'success': False, 'error': 'CLOB non disponible'}), 400

    if not polymarket_clob.authenticated:
        return jsonify({'success': False, 'error': 'CLOB non authentifié - configurez vos clés API'}), 401

    try:
        data = request.get_json()
        
        # REMOVE DRY RUN CHECK

        # Exécution réelle
        order_type = data.get('order_type', 'limit')
        if order_type == 'market':
            result = polymarket_clob.place_market_order(
                token_id=data.get('token_id'),
                side=data.get('side'),
                amount=float(data.get('amount', 0))
            )
        else:
            result = polymarket_clob.place_limit_order(
                token_id=data.get('token_id'),
                side=data.get('side'),
                price=float(data.get('price', 0)),
                size=float(data.get('size', 0))
            )

        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# TRACKER ROUTES
# ============================================================================

@app.route('/api/tracker/status')
def api_tracker_status():
    """Status du tracker Polymarket"""
    if not polymarket_tracker:
        return jsonify({
            'success': True,
            'available': False,
            'message': 'Tracker non disponible'
        })

    stats = polymarket_tracker.get_stats()
    return jsonify({
        'success': True,
        'available': True,
        'stats': stats
    })

@app.route('/api/tracker/check', methods=['POST'])
def api_tracker_check():
    """Vérifier les wallets manuellement"""
    if not polymarket_tracker:
        return jsonify({'success': False, 'error': 'Tracker non disponible'}), 400

    try:
        signals = polymarket_tracker.check_all_wallets()
        return jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tracker/wallet/<address>')
def api_tracker_wallet(address):
    """Résumé d'un wallet suivi"""
    if not polymarket_tracker:
        return jsonify({'success': False, 'error': 'Tracker non disponible'}), 400

    try:
        summary = polymarket_tracker.get_wallet_summary(address)
        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/markets/active')
def api_markets_active():
    """Marchés actifs Polymarket"""
    if not polymarket_tracker:
        return jsonify({'success': False, 'error': 'Tracker non disponible'}), 400

    try:
        limit = request.args.get('limit', 50, type=int)
        markets = polymarket_tracker.get_active_markets(limit=limit)
        return jsonify({
            'success': True,
            'markets': markets
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    # 🔄 Réconciliation des positions au démarrage
    print("\n🔄 Réconciliation des positions...")
    try:
        reconciliation_report = run_startup_reconciliation(polymarket_executor)
        print(f"✅ Réconciliation terminée: {reconciliation_report['positions_checked']} positions vérifiées")
        if reconciliation_report['positions_stale'] > 0:
            print(f"⚠️ {reconciliation_report['positions_stale']} positions marquées STALE")
        if reconciliation_report['errors']:
            print(f"⚠️ {len(reconciliation_report['errors'])} erreurs lors de la réconciliation")
    except Exception as e:
        print(f"⚠️ Réconciliation échouée: {e}")

    print(f"\n🚀 Bot démarré sur http://localhost:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
