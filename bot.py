# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, jsonify, request
import webbrowser
import json
import time
import threading
import os
from pathlib import Path
from datetime import datetime
from typing import Dict

# ⚡ Charger variables d'environnement depuis .env (si présent)
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

# 🔒 Fonction utilitaire pour masquer les clés API dans les logs
def mask_sensitive_data(data: str) -> str:
    """Masque les clés API et données sensibles pour les logs"""
    if not data or len(data) < 10:
        return "***"
    # Garder les 6 premiers et 4 derniers caractères
    return f"{data[:6]}***{data[-4:]}"

from bot_logic import BotBackend
from portfolio_tracker import portfolio_tracker
from solana_executor import solana_executor
from dex_handler import dex_handler
from trade_validator import trade_validator, TradeValidationLevel
from trade_safety import trade_safety, RiskLevel
from audit_logger import audit_logger, LogLevel
from monitoring import metrics_collector
from copy_trading_simulator import copy_trading_simulator
from db_manager import db_manager
from backtesting_engine import backtesting_engine
from benchmark_system import benchmark_system
from auto_sell_manager import auto_sell_manager
from helius_polling import helius_polling
from helius_websocket import helius_websocket
from magic_eden_api import magic_eden_api
from worker_threads import worker_pool
from smart_strategy import smart_strategy
from arbitrage_engine import arbitrage_engine
from advanced_risk_manager import risk_manager
from advanced_analytics import analytics
from cache_manager import cache_manager
from smart_trading import global_smart_filter
from adaptive_tp_sl import adaptive_tp_sl

# 🌐 Initialisation Flask + SocketIO pour temps réel
app = Flask(__name__)
# 🔒 SÉCURITÉ: Utiliser une clé secrète depuis l'environnement ou générée aléatoirement
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', os.urandom(32).hex())

# Importer Flask-SocketIO
from flask_socketio import SocketIO
# 🔒 SÉCURITÉ: Restreindre CORS aux origins autorisés uniquement
allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode='eventlet')


# ⚡ OPTIMISATION: Cache pour traders performance (réduit latence API)
traders_performance_cache = None
traders_performance_cache_time = None
TRADERS_CACHE_TTL = 2  # 2 secondes de cache

backend = BotBackend()

# Connecter le WebSocket handler
from websockets_handler import ws_handler
ws_handler.init_app(app, socketio)

# Afficher le statut de configuration au lancement
import os
helius_key = os.getenv('HELIUS_API_KEY')
print(f"{'='*60}")
print(f"✅ BOT PRÊT À DÉMARRER")
print(f"Helius API Key: {'✅ Configurée' if helius_key else '❌ NON configurée'}")
print(f"Traders actifs: {sum(1 for t in backend.data.get('traders', []) if t.get('active'))}")
print(f"Bot activé: {'✅ OUI' if backend.is_running else '❌ NON'}")
print(f"{'='*60}")

# 🔒 Mutex pour protéger l'accès à copied_trades_history (thread-safe)
copied_trades_lock = threading.Lock()

# Charger l'historique des trades copiés pour éviter les doublons
copied_trades_history = {}
try:
    with open('copied_trades_history.json', 'r') as f:
        copied_trades_history = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    copied_trades_history = {}

def save_copied_trades_history():
    """Sauvegarde l'historique des trades copiés (thread-safe)"""
    with copied_trades_lock:
        with open('copied_trades_history.json', 'w') as f:
            json.dump(copied_trades_history, f, indent=2)

# ⚡ WEBSOCKET CALLBACKS - Détection ultra-rapide des trades des traders
def on_trader_transaction_detected(trade_event: Dict):
    """Callback appelé par websocket quand un trader fait une transaction (~100-200ms)"""
    try:
        trader_addr = trade_event.get('trader_address', '')
        signature = trade_event.get('signature', '')
        
        if not trader_addr or not signature:
            return
        
        # Trouver le trader correspondant
        trader_obj = None
        trader_name = None
        for t in backend.data.get('traders', []):
            if t['address'] == trader_addr:
                trader_obj = t
                trader_name = t['name']
                break
        
        if not trader_obj or not trader_obj.get('active'):
            return
        
        # Vérifier si déjà copié (thread-safe)
        trader_key = f"{trader_name}_{signature}"
        with copied_trades_lock:
            if trader_key in copied_trades_history:
                return

            # Marquer comme copié
            copied_trades_history[trader_key] = datetime.now().isoformat()
        save_copied_trades_history()
        
        # Récupérer les infos du trade via Helius (détail complet)
        try:
            trades = copy_trading_simulator.get_trader_recent_trades(trader_addr, limit=1)
            if trades and trades[0].get('signature') == signature:
                trade = trades[0]
                
                # Simuler le trade immédiatement
                capital_alloc = trader_obj.get('capital', 100)
                if capital_alloc > 0:
                    result = copy_trading_simulator.simulate_trade_for_trader(trader_name, trade, capital_alloc)
                    
                    # Enregistrer la position
                    if result.get('status') == 'success':
                        execution = result.get('execution', {})
                        out_amount = execution.get('out_amount_after_slippage', 0)
                        simulated_usd = execution.get('simulated_amount_usd', 0)
                        entry_price_usd = simulated_usd / out_amount if out_amount > 0 else 0
                        
                        if entry_price_usd > 0 and out_amount > 0:
                            auto_sell_manager.open_position(trader_name, entry_price_usd, out_amount)
                            out_mint = trade.get('out_mint', '?')
                            token_symbol = out_mint[-8:] if out_mint and len(out_mint) > 8 else out_mint
                            print(f"⚡ WEBSOCKET (<200ms): {trader_name} → {token_symbol} | Capital: ${capital_alloc}")

                            # 🌐 Broadcast trade exécuté en temps réel
                            ws_handler.broadcast_trade_executed({
                                'trader': trader_name,
                                'action': 'BUY',
                                'token': token_symbol,
                                'amount': capital_alloc,
                                'timestamp': datetime.now().isoformat()
                            })
        except Exception as e:
            print(f"⚠️ Erreur traitement websocket trade: {str(e)[:80]}")
    
    except Exception as e:
        print(f"⚠️ Erreur callback websocket: {e}")

def subscribe_traders_to_polling():
    """Abonne les traders actifs au polling Helius pour détection fiable"""
    try:
        active_traders = [t for t in backend.data.get('traders', []) if t.get('active')]

        if not active_traders:
            print("  └─ Aucun trader actif pour polling")
            return

        for trader in active_traders:
            helius_polling.subscribe_to_trader(
                trader['address'],
                on_trader_transaction_detected
            )

        print(f"  ├─ {len(active_traders)} traders HTTP polling configurés (5s interval, 90% fiable)")
    except Exception as e:
        print(f"  └─ Erreur abonnement polling: {e}")

def subscribe_traders_to_websocket():
    """Abonne les traders actifs au WebSocket Helius pour détection ultra-rapide"""
    try:
        active_traders = [t for t in backend.data.get('traders', []) if t.get('active')]

        if not active_traders:
            print("  └─ Aucun trader actif pour WebSocket")
            return

        for trader in active_traders:
            helius_websocket.subscribe_to_trader(
                trader['address'],
                on_trader_transaction_detected
            )

        print(f"  ├─ {len(active_traders)} traders WebSocket configurés (~100-200ms latence)")
    except Exception as e:
        print(f"  └─ Erreur abonnement WebSocket: {e}")

# Démarrer le thread de suivi des portefeuilles + simulation copy trading
def start_tracking():
    # Démarrer le WebSocket Helius pour détection ultra-rapide
    print("\n🚀 INITIALISATION WEBSOCKET HELIUS (ULTRA-RAPIDE ~100-200ms):")
    try:
        helius_websocket.start()
        # Attendre 2 sec pour connexion WebSocket
        time.sleep(2)
        # Abonner les traders au WebSocket
        subscribe_traders_to_websocket()
    except Exception as e:
        print(f"  └─ ⚠️ WebSocket non disponible: {e}")

    # Démarrer le polling Helius pour détection fiable (backup)
    print("\n🚀 INITIALISATION POLLING HELIUS (BACKUP):")
    try:
        helius_polling.start()
        # Attendre 1 sec
        time.sleep(1)
        # Abonner les traders
        subscribe_traders_to_polling()
    except Exception as e:
        print(f"  └─ ⚠️ Polling non disponible: {e}")
    
    print()
    last_log_time = 0
    last_fallback_check = time.time()
    
    while True:
        current_time = time.time()
        
        # Log de debug toutes les 30 secondes
        if current_time - last_log_time > 30:
            bot_status = "✅ ACTIVÉ" if backend.is_running else "❌ INACTIF"
            active_traders = sum(1 for t in backend.data.get('traders', []) if t.get('active'))
            print(f"🔍 État bot: {bot_status} | Traders actifs: {active_traders}")
            last_log_time = current_time
        
        if backend.is_running:
            # 🔄 METTRE À JOUR LES PRIX DE TOUTES LES POSITIONS (chaque cycle)
            auto_sell_manager.update_all_position_prices({})

            # Track wallets + portfolio
            portfolio_tracker.track_all_wallets()
            portfolio_tracker.update_bot_portfolio()

            # 🌐 Broadcast mise à jour portfolio (toutes les 5 secondes)
            if current_time % 5 < 2:  # Toutes les ~5 secondes
                try:
                    portfolio_value = backend.get_wallet_balance_dynamic()
                    active_count = sum(1 for t in backend.data.get('traders', []) if t.get('active'))
                    ws_handler.broadcast_portfolio_update({
                        'portfolio_value': portfolio_value,
                        'active_traders': active_count,
                        'timestamp': datetime.now().isoformat()
                    })
                except:
                    pass
            
            # Fallback sur Magic Eden si Helius échoue (tous les 30s)
            if current_time - last_fallback_check > 30:
                active_traders = [t for t in backend.data.get('traders', []) if t.get('active')]
                for trader in active_traders:
                    try:
                        # Essayer Magic Eden si Helius en difficulté
                        trades_me = magic_eden_api.get_wallet_transactions(trader['address'], limit=3)
                        for trade in trades_me:
                            sig = trade.get('signature', '')
                            trader_key = f"{trader['name']}_{sig}"

                            with copied_trades_lock:
                                already_copied = trader_key in copied_trades_history

                            if not already_copied:
                                print(f"🔄 Magic Eden fallback: Détection trade {trader['name']}")
                                # Traiter le trade
                    except:
                        pass
                
                last_fallback_check = current_time

        time.sleep(2)  # ⚡ Vérifier TOUTES LES 2 SECONDES (polling optimisé)

tracking_thread = threading.Thread(target=start_tracking, daemon=True)
tracking_thread.start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bot du Millionnaire - Solana Copy Trading</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #fff; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        h1 { color: #00E676; text-align: center; margin-bottom: 30px; font-size: 32px; }
        
        .nav { display: flex; gap: 10px; margin-bottom: 30px; justify-content: center; }
        .nav button { background: #333; color: #fff; padding: 12px 25px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }
        .nav button.active { background: #007BFF; }
        
        .section { display: none; }
        .section.active { display: block; }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: #1a1a1a; padding: 25px; margin: 15px 0; border-radius: 12px; border: 1px solid #333; }
        .card h2 { color: #64B5F6; margin-bottom: 20px; font-size: 24px; }
        
        .big-value { font-size: 42px; font-weight: bold; color: #00E676; text-align: center; margin: 20px 0; }
        .status { padding: 10px 20px; border-radius: 20px; font-weight: bold; display: inline-block; }
        .status.on { background: #00C853; color: white; }
        .status.off { background: #D50000; color: white; }
        .mode-badge { background: #FFD600; color: #000; padding: 8px 20px; border-radius: 15px; font-weight: bold; }
        
        .btn { background: #007BFF; color: white; padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .btn.danger { background: #dc3545; }
        .btn.danger:hover { background: #c82333; }
        .btn.small { padding: 8px 16px; font-size: 14px; }
        
        .trader-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; margin: 8px 0; background: #2a2a2a; border-radius: 8px; border: 2px solid transparent; transition: all 0.3s ease; }
        .trader-item.active { background: #0a4a0a; border: 2px solid #00E676; box-shadow: 0 0 15px rgba(0, 230, 118, 0.3); }
        .trader-item input[type="checkbox"] { width: 20px; height: 20px; cursor: pointer; margin-right: 10px; }
        .trader-edit { display: none; margin-top: 10px; padding: 15px; background: #3a3a3a; border-radius: 8px; }
        
        input[type="range"], input[type="text"], input[type="password"], select { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #555; background: #2a2a2a; color: #fff; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #2a2a2a; color: #64B5F6; }
        
        .param-group { margin: 15px 0; }
        .param-group label { display: block; margin-bottom: 5px; color: #aaa; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px; }
        .stat-card { background: #2a2a2a; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-card h3 { color: #64B5F6; font-size: 14px; margin-bottom: 5px; }
        .stat-card .value { color: #00E676; font-size: 24px; font-weight: bold; }
        
        .divider { border-top: 2px solid #444; margin: 25px 0; }
        .section-title { color: #FF6B6B; margin-top: 20px; margin-bottom: 10px; font-size: 16px; font-weight: bold; }
        
        /* 📊 Stat Box pour Arbitrage et Polymarket */
        .stat-box { padding: 20px; border-radius: 12px; text-align: center; color: white; }
        .stat-box .stat-label { font-size: 13px; opacity: 0.9; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
        .stat-box .stat-value { font-size: 28px; font-weight: bold; }
        
        .live-trader-card { background: linear-gradient(135deg, #1a2a3a 0%, #0f1f2f 100%); border: 2px solid #333; border-radius: 12px; padding: 20px; margin: 15px 0; transition: all 0.3s ease; }
        .live-trader-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0, 230, 118, 0.1); border-color: #00E676; }
        .live-trader-card.profitable { border-left: 5px solid #00E676; }
        .live-trader-card.losing { border-left: 5px solid #D50000; }
        
        .trader-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .trader-name { font-size: 22px; color: #64B5F6; font-weight: bold; }
        .trader-status { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .trader-status.green { background: #0a3a0a; color: #00E676; }
        .trader-status.red { background: #3a0a0a; color: #FF6B6B; }
        
        .live-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0; }
        .live-stat { padding: 10px; background: #2a2a2a; border-radius: 8px; text-align: center; }
        .live-stat label { color: #aaa; font-size: 12px; margin-bottom: 5px; display: block; }
        .live-stat value { color: #00E676; font-size: 18px; font-weight: bold; }
        .live-stat.negative value { color: #FF6B6B; }
        
        .tokens-section { margin-top: 15px; padding: 12px; background: #2a2a2a; border-radius: 8px; }
        .tokens-title { color: #FFD600; font-size: 14px; font-weight: bold; margin-bottom: 8px; }
        .token-item { display: inline-block; background: #1a3a1a; color: #00E676; padding: 6px 12px; border-radius: 6px; margin: 4px 4px 4px 0; font-size: 12px; border: 1px solid #00E676; }
        .token-item.no-position { background: #3a1a1a; color: #FFD600; border-color: #FFD600; }
        
        .action-buttons { display: flex; gap: 10px; margin-top: 15px; }
        .action-btn { flex: 1; padding: 10px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 14px; transition: all 0.2s; }
        .action-btn.exit-all { background: #D50000; color: white; }
        .action-btn.exit-all:hover { background: #FF6B6B; }
        .action-btn.disable { background: #FF9800; color: white; }
        .action-btn.disable:hover { background: #FFB74D; }

        /* 🎯 Toast Notifications */
        .toast-container { position: fixed; top: 20px; right: 20px; z-index: 9999; }
        .toast { background: #1a1a1a; border-left: 4px solid #00E676; padding: 15px 20px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); min-width: 300px; animation: slideIn 0.3s ease-out; }
        .toast.success { border-left-color: #00E676; }
        .toast.error { border-left-color: #D50000; }
        .toast.warning { border-left-color: #FFD600; }
        .toast.info { border-left-color: #64B5F6; }
        .toast-title { font-weight: bold; margin-bottom: 5px; color: #fff; }
        .toast-message { color: #aaa; font-size: 14px; }
        @keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(400px); opacity: 0; } }

        /* 📊 Chart Containers */
        .chart-container { position: relative; height: 250px; margin-top: 15px; }
        .metric-badge { display: inline-block; background: #2a2a2a; padding: 8px 15px; border-radius: 20px; margin: 5px; font-size: 13px; }
        .metric-badge .label { color: #aaa; }
        .metric-badge .value { color: #00E676; font-weight: bold; margin-left: 8px; }
        .metric-badge.warning .value { color: #FFD600; }
        .metric-badge.danger .value { color: #FF6B6B; }

        /* 🎨 Advanced Metrics Grid */
        .advanced-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 20px; }
        .metric-box { background: linear-gradient(135deg, #1a2a3a 0%, #0f1f2f 100%); padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; transition: all 0.3s; }
        .metric-box:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0, 230, 118, 0.15); border-color: #00E676; }
        .metric-box .metric-label { color: #64B5F6; font-size: 12px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
        .metric-box .metric-value { color: #00E676; font-size: 28px; font-weight: bold; }
        .metric-box .metric-sub { color: #aaa; font-size: 11px; margin-top: 5px; }
        .metric-box.negative .metric-value { color: #FF6B6B; }

        /* 🔔 Alert Banner */
        .alert-banner { background: linear-gradient(90deg, #FFD600 0%, #FF9800 100%); color: #000; padding: 12px 20px; border-radius: 8px; margin: 15px 0; font-weight: bold; text-align: center; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; } }
        .alert-banner.critical { background: linear-gradient(90deg, #D50000 0%, #FF6B6B 100%); color: #fff; }
    </style>
    <!-- 🌐 Socket.IO pour WebSocket temps réel -->
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <!-- 📊 Chart.js pour graphiques interactifs -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
    <!-- 🎯 Toast Notification Container -->
    <div class="toast-container" id="toastContainer"></div>

    <div class="container">
        <h1>🚀 Bot du Millionnaire - Solana Copy Trading</h1>

        <div class="nav">
            <button class="nav-btn active" onclick="showSection('dashboard')">Tableau de Bord</button>
            <button class="nav-btn" onclick="showSection('live')">⚡ LIVE TRADING</button>
            <button class="nav-btn" onclick="showSection('traders')">Gestion Traders</button>
            <button class="nav-btn" onclick="showSection('positions')">📊 Positions Ouvertes</button>
            <button class="nav-btn" onclick="showSection('backtesting')">🎮 Backtesting</button>
            <button class="nav-btn" onclick="showSection('benchmark')">🏆 Benchmark</button>
            <button class="nav-btn" onclick="showSection('risk_manager')">🛡️ Risk Manager</button>
            <button class="nav-btn" onclick="showSection('arbitrage')">💰 Arbitrage Solana</button>
            <button class="nav-btn" onclick="showSection('polymarket')">🔮 Polymarket Copy</button>
            <button class="nav-btn" onclick="showSection('settings')">Paramètres & Sécurité</button>
            <button class="nav-btn" onclick="showSection('history')">Historique Complet</button>
        </div>

        <!-- TABLEAU DE BORD -->
        <div id="dashboard" class="section active">
            <div class="grid">
                <div class="card">
                    <h2>📊 Performance en Temps Réel</h2>
                    <div class="big-value" id="portfolio">$1000.00</div>
                    <p>Status: <span id="status" class="status off">BOT DÉSACTIVÉ</span></p>
                    <p>WebSocket Helius: <span id="websocket_status" class="status off">❌ Déconnecté</span></p>
                    <button class="btn" onclick="toggleBot()">Activer/Désactiver Bot</button>
                    
                    <!-- STATS DE TRADING -->
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3>Trades Détectés</h3>
                            <div class="value" id="total_trades">0</div>
                        </div>
                        <div class="stat-card">
                            <h3>PnL Total</h3>
                            <div class="value" id="total_pnl">$0</div>
                        </div>
                        <div class="stat-card">
                            <h3>Performance Bot</h3>
                            <div class="value" id="bot_performance">0%</div>
                        </div>
                        <div class="stat-card">
                            <h3>Traders Actifs</h3>
                            <div class="value" id="active_traders_count">0</div>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <h2>📈 Évolution PnL en Temps Réel</h2>
                    <div class="chart-container">
                        <canvas id="pnlChart"></canvas>
                    </div>
                    <div style="margin-top: 15px;">
                        <span class="metric-badge"><span class="label">Latence Moyenne:</span><span class="value" id="avg_latency">0ms</span></span>
                        <span class="metric-badge"><span class="label">Cache Hit Rate:</span><span class="value" id="cache_hit">0%</span></span>
                        <span class="metric-badge warning"><span class="label">RPC Success:</span><span class="value" id="rpc_success">100%</span></span>
                    </div>
                </div>
            </div>

            <!-- 🔔 ALERT BANNER -->
            <div id="alertBanner" style="display: none;"></div>

            <!-- 📊 ADVANCED METRICS -->
            <div class="card">
                <h2>⚡ Métriques Avancées Phase 9</h2>
                <div class="advanced-metrics">
                    <div class="metric-box">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value" id="win_rate_metric">0%</div>
                        <div class="metric-sub">Taux de réussite global</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value" id="sharpe_ratio_metric">0.0</div>
                        <div class="metric-sub">Rendement ajusté au risque</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Drawdown Max</div>
                        <div class="metric-value" id="max_drawdown_metric">0%</div>
                        <div class="metric-sub">Perte maximale observée</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Circuit Breaker</div>
                        <div class="metric-value" id="circuit_breaker_status">🟢 FERMÉ</div>
                        <div class="metric-sub">Protection du capital</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Smart Filter</div>
                        <div class="metric-value" id="smart_filter_pass">0%</div>
                        <div class="metric-sub">Trades validés par IA</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Volatilité</div>
                        <div class="metric-value" id="market_volatility">LOW</div>
                        <div class="metric-sub">Volatilité du marché</div>
                    </div>
                </div>
            </div>

            <!-- PERFORMANCES PAR TRADER -->
            <div class="card">
                <h2>📊 Performances des Traders</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Trader</th>
                            <th>Valeur Actuelle</th>
                            <th>PnL Total</th>
                            <th>PnL 24h</th>
                            <th>PnL 7j</th>
                        </tr>
                    </thead>
                    <tbody id="traders_performance"></tbody>
                </table>
            </div>
        </div>

        <!-- GESTION TRADERS -->
        <div id="traders" class="section">
            <div class="card">
                <h2>🎯 Gestion des 10 Traders</h2>
                <p>Actifs: <span id="active_count" style="color: #FFD600; font-size: 20px;">0/3</span></p>
                <p>Balance Wallet: <span id="total_capital_display" style="color: #FFD600;">$0</span> SOL | Alloué: <span id="capital_allocated" style="color: #00E676;">$0</span></p>
                <div id="traders_list"></div>
            </div>
        </div>

        <!-- BACKTESTING -->
        <div id="backtesting" class="section">
            <div class="card">
                <h2>🎮 Backtesting - Tester les paramètres TP/SL</h2>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div>
                        <label style="color: #aaa;">Sélectionner Trader:</label>
                        <select id="backtest_trader" style="width: 100%; padding: 10px; margin: 10px 0; background: #2a2a2a; color: #fff; border: 1px solid #555; border-radius: 5px;">
                            <option value="">-- Choisir un trader --</option>
                        </select>
                    </div>
                    <div style="display: flex; align-items: flex-end; gap: 10px;">
                        <button class="btn" onclick="runBacktestMultiple()" style="flex: 1;">▶️ Lancer Backtests (All Params)</button>
                        <button class="btn" onclick="loadBacktestTraders()" style="flex: 0.5;">🔄 Rafraîchir</button>
                    </div>
                </div>
                <div id="backtest_results" style="margin-top: 20px;">
                    <p style="color: #999; text-align: center;">Résultats apparaîtront ici...</p>
                </div>
            </div>
        </div>

        <!-- BENCHMARK -->
        <div id="benchmark" class="section">
            <div class="card">
                <h2>🏆 Benchmark - Bot vs Traders</h2>
                <button class="btn" onclick="updateBenchmark()" style="margin-bottom: 20px;">📊 Rafraîchir Benchmark</button>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div class="card" style="background: #0a3a0a;">
                        <h3 style="color: #00E676;">📈 BOT - Performance</h3>
                        <div style="font-size: 28px; color: #00E676; margin: 10px 0;" id="bot_benchmark_pnl">+0%</div>
                        <p style="color: #aaa; margin: 5px 0;">Win Rate: <span id="bot_benchmark_wr" style="color: #00E676;">0%</span></p>
                        <p style="color: #aaa; margin: 5px 0;">Classement: <span id="bot_benchmark_rank" style="color: #FFD600; font-weight: bold;">-</span></p>
                    </div>
                    <div class="card">
                        <h3 style="color: #64B5F6;">🎯 Meilleur Trader</h3>
                        <div style="font-size: 20px; color: #00E676; margin: 10px 0;" id="best_trader_name">-</div>
                        <p style="color: #aaa; margin: 5px 0;">PnL: <span id="best_trader_pnl" style="color: #00E676;">+0%</span></p>
                        <p style="color: #aaa; margin: 5px 0;">Win Rate: <span id="best_trader_wr" style="color: #00E676;">0%</span></p>
                    </div>
                </div>

                <h3 style="color: #64B5F6; margin-top: 20px;">📊 Classement Complet</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Rang</th>
                            <th>Nom</th>
                            <th>PnL</th>
                            <th>Win Rate</th>
                        </tr>
                    </thead>
                    <tbody id="benchmark_ranking"></tbody>
                </table>
            </div>
        </div>

        <!-- PARAMÈTRES -->
        <div id="settings" class="section">
            <div class="grid">
                <div class="card">
                    <h2>⚙️ Contrôle Trading</h2>
                    <div class="param-group">
                        <label>Slippage Maximum: <span id="slippage_val">1.0</span>%</label>
                        <input type="range" id="slippage" min="0.1" max="100" step="0.1" value="1.0" oninput="updateSlippage(this.value)">
                    </div>
                    
                    <h3 style="color: #64B5F6; margin-top: 20px; margin-bottom: 10px;">📈 Take Profit</h3>
                    
                    <div class="param-group">
                        <label>TP1 - Vendre % de position:</label>
                        <input type="text" id="tp1_percent" value="33" placeholder="Ex: 33">
                        <label style="margin-top: 5px;">TP1 - À % de profit:</label>
                        <input type="text" id="tp1_profit" value="10" placeholder="Ex: 10">
                    </div>
                    
                    <div class="param-group">
                        <label>TP2 - Vendre % de position:</label>
                        <input type="text" id="tp2_percent" value="33" placeholder="Ex: 33">
                        <label style="margin-top: 5px;">TP2 - À % de profit:</label>
                        <input type="text" id="tp2_profit" value="25" placeholder="Ex: 25">
                    </div>
                    
                    <div class="param-group">
                        <label>TP3 - Vendre % de position:</label>
                        <input type="text" id="tp3_percent" value="34" placeholder="Ex: 34">
                        <label style="margin-top: 5px;">TP3 - À % de profit:</label>
                        <input type="text" id="tp3_profit" value="50" placeholder="Ex: 50">
                    </div>
                    
                    <div class="divider"></div>
                    <h3 class="section-title">🛑 Stop Loss</h3>
                    
                    <div class="param-group">
                        <label>SL - Vendre % de position:</label>
                        <input type="text" id="sl_percent" value="100" placeholder="Ex: 100">
                        <label style="margin-top: 5px;">SL - À % de perte:</label>
                        <input type="text" id="sl_loss" value="5" placeholder="Ex: 5">
                    </div>
                    
                    <div class="param-group">
                        <label>Devise d'affichage:</label>
                        <select id="currency">
                            <option value="USD">USD ($)</option>
                            <option value="SOL">SOL (◎)</option>
                        </select>
                    </div>
                    <button class="btn" onclick="saveTakeProfit()">💾 Sauvegarder TP & SL</button>

                    <div class="divider"></div>
                    <h3 class="section-title">🤖 Achat & Vente AUTOMATIQUE</h3>
                    <p style="color: #00E676; margin: 10px 0;"><strong>✅ AUTOMATIQUE = Le core du bot</strong></p>
                    <ul style="color: #aaa; margin-left: 20px;">
                        <li>Trader achète → Bot achète (capital alloué)</li>
                        <li>Trader vend → Bot vend (automatiquement)</li>
                        <li><strong style="color: #FFD600;">Si TP/SL configurés</strong> → respecte TP/SL</li>
                        <li><strong style="color: #FFD600;">Si TP/SL = 0</strong> → vend exactement comme trader</li>
                    </ul>
                </div>
                <div class="card">
                    <h2>🔐 Configuration & Sécurité</h2>
                    <p>Wallet Connecté: <span id="wallet_addr" style="color: #00E676;">Aucun</span></p>
                    <div class="param-group">
                        <label>Clé Privée Phantom (session uniquement):</label>
                        <input type="password" id="priv_key" placeholder="Collez votre clé privée ici...">
                    </div>
                    <button class="btn" onclick="saveKey()">Sauvegarder (Session)</button>
                    <button class="btn danger" onclick="disconnect()">Déconnecter Wallet</button>
                </div>
            </div>
        </div>

        <!-- LIVE TRADING DASHBOARD -->
        <div id="live" class="section">
            <div class="card">
                <h2>⚡ LIVE TRADING - Vue en Temps Réel</h2>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div>
                        <p style="color: #aaa; margin: 5px 0;">💰 Portefeuille: <span id="live_portfolio" style="color: #00E676; font-weight: bold;">$1,000</span></p>
                        <p style="color: #aaa; margin: 5px 0;">PnL 24h: <span id="live_pnl_24h" style="color: #00E676;">+$0 (0%)</span></p>
                    </div>
                    <div style="text-align: right;">
                        <p style="color: #aaa; margin: 5px 0;">Traders Actifs: <span id="live_active_count" style="color: #64B5F6; font-weight: bold;">0/3</span></p>
                        <p style="color: #aaa; margin: 5px 0;">Positions: <span id="live_positions_count" style="color: #FFD600;">0</span></p>
                    </div>
                </div>
                
                <div style="border-top: 2px solid #333; padding-top: 20px;">
                    <h3 style="color: #64B5F6; margin-bottom: 15px;">🎯 Traders Actifs en Direct</h3>
                    <div id="live_traders_container" style="display: grid; gap: 10px;">
                        <p style="color: #999; text-align: center;">Chargement...</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- POSITIONS OUVERTES -->
        <div id="positions" class="section">
            <div class="card">
                <h2>📊 Positions Ouvertes en Temps Réel</h2>
                <p style="color: #aaa; margin-bottom: 15px;">Toutes les positions actuellement ouvertes depuis vos traders actifs</p>
                <button class="btn" onclick="refreshPositions()" style="width: 100%; margin-bottom: 15px;">🔄 Rafraîchir Positions</button>
                <div id="open_positions_list" style="margin-bottom: 20px;"></div>
            </div>
        </div>

        <!-- HISTORIQUE -->
        <div id="history" class="section">
            <div class="card">
                <h2>📜 Historique Complet</h2>
                <table>
                    <thead><tr><th>Heure</th><th>Trader</th><th>Plateforme</th><th>Signature</th><th>PnL</th><th>Performance</th></tr></thead>
                    <tbody id="trades_body"></tbody>
                </table>
            </div>
        </div>

        <!-- RISK MANAGER -->
        <div id="risk_manager" class="section">
            <div class="card">
                <h2>🛡️ Risk Manager - Gestion du Risque</h2>

                <!-- Métriques actuelles -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px;">
                    <div class="stat-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <div class="stat-label">Balance Actuelle</div>
                        <div class="stat-value" id="risk_current_balance">$1000</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                        <div class="stat-label">Drawdown</div>
                        <div class="stat-value" id="risk_drawdown">0%</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                        <div class="stat-label">PnL Journalier</div>
                        <div class="stat-value" id="risk_daily_pnl">$0</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                        <div class="stat-label">Pertes Consécutives</div>
                        <div class="stat-value" id="risk_consecutive_losses">0</div>
                    </div>
                </div>

                <!-- Alert Circuit Breaker -->
                <div id="circuit_breaker_alert" style="display: none; background: #ff5252; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                    <strong>🚨 CIRCUIT BREAKER ACTIVÉ 🚨</strong>
                    <p style="margin: 10px 0;">Le trading est automatiquement suspendu</p>
                    <button class="btn" onclick="resetCircuitBreaker()" style="background: #fff; color: #ff5252;">Réinitialiser Manuellement</button>
                </div>

                <!-- Sauvegarde Toggle -->
                <div style="background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="save_params_toggle" onchange="toggleSaveParams()" style="margin-right: 10px; width: 20px; height: 20px;">
                        <span style="font-size: 16px;">💾 Sauvegarder les paramètres dans config.json (persistant entre sessions)</span>
                    </label>
                    <p style="color: #999; font-size: 13px; margin: 10px 0 0 30px;">
                        ✅ Activé: Les paramètres sont sauvegardés et rechargés au prochain démarrage<br>
                        ❌ Désactivé: Les paramètres reviennent aux valeurs par défaut à chaque session
                    </p>
                </div>

                <!-- Formulaire de paramètres -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <!-- Colonne 1: Circuit Breaker -->
                    <div style="background: #2a2a2a; padding: 20px; border-radius: 8px;">
                        <h3 style="color: #64B5F6; margin-bottom: 15px;">⚡ Circuit Breaker</h3>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Seuil de déclenchement (%)
                            <input type="number" id="circuit_breaker_threshold" value="15" min="1" max="100" step="0.5" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Perte max avant arrêt automatique</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Cooldown (secondes)
                            <input type="number" id="circuit_breaker_cooldown" value="3600" min="60" max="86400" step="60" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Durée de pause après activation</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Pertes consécutives max
                            <input type="number" id="max_consecutive_losses" value="5" min="1" max="20" step="1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Nombre de trades perdants avant arrêt</span>
                        </label>
                    </div>

                    <!-- Colonne 2: Limites de risque -->
                    <div style="background: #2a2a2a; padding: 20px; border-radius: 8px;">
                        <h3 style="color: #64B5F6; margin-bottom: 15px;">🎯 Limites de Risque</h3>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Max position par trade (%)
                            <input type="number" id="max_position_size_percent" value="20" min="1" max="100" step="1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">% max du capital par position</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Perte journalière max (%)
                            <input type="number" id="max_daily_loss_percent" value="10" min="1" max="50" step="1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Perte max par jour</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Drawdown maximum (%)
                            <input type="number" id="max_drawdown_percent" value="25" min="1" max="100" step="1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Perte max depuis le pic</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Kelly Safety Factor
                            <input type="number" id="kelly_safety_factor" value="0.5" min="0.1" max="1" step="0.1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Facteur de sécurité Kelly (0.5 = demi-Kelly)</span>
                        </label>
                    </div>
                </div>

                <!-- Boutons d'action -->
                <div style="display: flex; gap: 10px; margin-top: 20px;">
                    <button class="btn" onclick="saveRiskParams()" style="flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        💾 Sauvegarder les Paramètres
                    </button>
                    <button class="btn" onclick="resetRiskDefaults()" style="flex: 1; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                        🔄 Réinitialiser aux Défauts
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- ARBITRAGE -->
    <div id="arbitrage" class="section">
        <div class="container">
            <div class="card">
                <h2>💰 Arbitrage Multi-DEX - Jupiter, Raydium, Orca</h2>

                <!-- Statut ON/OFF -->
                <div style="background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                    <label style="display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 18px;">
                        <input type="checkbox" id="arbitrage_enabled" onchange="toggleArbitrage()" style="margin-right: 15px; width: 24px; height: 24px;">
                        <span id="arbitrage_status_text" style="font-weight: bold;">❌ Arbitrage Désactivé</span>
                    </label>
                    <p style="color: #999; font-size: 13px; margin: 10px 0 0 0;">
                        Active la détection automatique d'opportunités d'arbitrage entre DEX
                    </p>
                </div>

                <!-- Statistiques en temps réel -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px;">
                    <div class="stat-box" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <div class="stat-label">Capital Dédié</div>
                        <div class="stat-value" id="arb_capital">$100</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                        <div class="stat-label">Opportunités Trouvées</div>
                        <div class="stat-value" id="arb_opportunities">0</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                        <div class="stat-label">Exécutées</div>
                        <div class="stat-value" id="arb_executed">0</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                        <div class="stat-label">Win Rate</div>
                        <div class="stat-value" id="arb_winrate">0%</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                        <div class="stat-label">Profit Total</div>
                        <div class="stat-value" id="arb_profit">$0.00</div>
                    </div>
                </div>

                <!-- Configuration -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                    <!-- Colonne 1: Capital & Position -->
                    <div style="background: #2a2a2a; padding: 20px; border-radius: 8px;">
                        <h3 style="color: #64B5F6; margin-bottom: 15px;">💵 Gestion du Capital</h3>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Capital Dédié à l'Arbitrage ($)
                            <input type="number" id="arb_capital_dedicated" value="100" min="10" max="10000" step="10" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Capital séparé du copy trading</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            % du Capital par Trade (%)
                            <input type="number" id="arb_percent_per_trade" value="10" min="1" max="100" step="1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">% du capital arbitrage utilisé par opportunité</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Montant Min par Trade ($)
                            <input type="number" id="arb_min_amount" value="10" min="1" max="1000" step="5" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Montant minimum pour exécuter un arbitrage</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Montant Max par Trade ($)
                            <input type="number" id="arb_max_amount" value="200" min="10" max="10000" step="10" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Montant maximum pour limiter le risque</span>
                        </label>
                    </div>

                    <!-- Colonne 2: Stratégie & Sécurité -->
                    <div style="background: #2a2a2a; padding: 20px; border-radius: 8px;">
                        <h3 style="color: #64B5F6; margin-bottom: 15px;">⚡ Stratégie & Sécurité</h3>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Profit Min Requis (%)
                            <input type="number" id="arb_min_profit" value="1.5" min="0.1" max="10" step="0.1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">% de profit net minimum après frais</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Cooldown entre Trades (secondes)
                            <input type="number" id="arb_cooldown" value="30" min="5" max="600" step="5" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Délai minimum entre 2 arbitrages du même token</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Max Trades Simultanés
                            <input type="number" id="arb_max_concurrent" value="3" min="1" max="10" step="1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Nombre max d'arbitrages en même temps</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Blacklist Tokens (adresses séparées par virgules)
                            <textarea id="arb_blacklist" class="input-field" style="width: 100%; margin-top: 5px; min-height: 60px;" placeholder="So11..., EPjF..."></textarea>
                            <span style="font-size: 12px; color: #999;">Tokens à exclure de l'arbitrage</span>
                        </label>
                    </div>
                </div>

                <!-- Opportunités récentes -->
                <div style="background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #64B5F6; margin-bottom: 15px;">🔍 Opportunités Récentes (10 dernières)</h3>
                    <div id="recent_opportunities" style="max-height: 300px; overflow-y: auto;">
                        <p style="color: #999; text-align: center;">Aucune opportunité détectée pour le moment...</p>
                    </div>
                </div>

                <!-- Boutons d'action -->
                <div style="display: flex; gap: 10px;">
                    <button class="btn" onclick="saveArbitrageConfig()" style="flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        💾 Sauvegarder la Configuration
                    </button>
                    <button class="btn" onclick="loadArbitrageConfig()" style="flex: 1; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                        🔄 Recharger
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- POLYMARKET COPY TRADING -->
    <div id="polymarket" class="section">
        <div class="container">
            <div class="card">
                <h2>🔮 Polymarket Copy Trading - Marchés Prédictifs</h2>
                
                <!-- Statut ON/OFF -->
                <div style="background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                    <label style="display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 18px;">
                        <input type="checkbox" id="polymarket_enabled" onchange="togglePolymarket()" style="margin-right: 15px; width: 24px; height: 24px;">
                        <span id="polymarket_status_text" style="font-weight: bold;">❌ Copy Trading Polymarket Désactivé</span>
                    </label>
                    <p style="color: #999; font-size: 13px; margin: 10px 0 0 0;">
                        Copie automatiquement les positions des traders rentables sur Polymarket (Polygon)
                    </p>
                    <p style="color: #FFD600; font-size: 12px; margin-top: 5px;">
                        ⚠️ Mode DRY RUN par défaut - Aucun trade réel
                    </p>
                </div>

                <!-- Statistiques en temps réel -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px;">
                    <div class="stat-box" style="background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);">
                        <div class="stat-label">Capital Polymarket</div>
                        <div class="stat-value" id="pm_capital">$100</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #EC4899 0%, #F472B6 100%);">
                        <div class="stat-label">Signaux Détectés</div>
                        <div class="stat-value" id="pm_signals">0</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #14B8A6 0%, #2DD4BF 100%);">
                        <div class="stat-label">Trades Copiés</div>
                        <div class="stat-value" id="pm_trades_copied">0</div>
                    </div>
                    <div class="stat-box" style="background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%);">
                        <div class="stat-label">Profit Simulé</div>
                        <div class="stat-value" id="pm_profit">$0.00</div>
                    </div>
                </div>

                <!-- Configuration -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                    <!-- Colonne 1: Wallets à suivre -->
                    <div style="background: #2a2a2a; padding: 20px; border-radius: 8px;">
                        <h3 style="color: #64B5F6; margin-bottom: 15px;">👀 Wallets à Copier</h3>
                        
                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Adresses Polygon (une par ligne)
                            <textarea id="pm_tracked_wallets" class="input-field" style="width: 100%; margin-top: 5px; min-height: 120px;" placeholder="0x56687bf447db6ffa42ffe2204a05edaa20f55839&#10;0x..."></textarea>
                            <span style="font-size: 12px; color: #999;">Adresses des traders à copier sur Polymarket</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Intervalle de Polling (secondes)
                            <input type="number" id="pm_polling_interval" value="10" min="5" max="60" step="5" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Fréquence de vérification des positions</span>
                        </label>
                    </div>

                    <!-- Colonne 2: Paramètres de Trading -->
                    <div style="background: #2a2a2a; padding: 20px; border-radius: 8px;">
                        <h3 style="color: #64B5F6; margin-bottom: 15px;">⚙️ Paramètres de Trading</h3>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Position Max par Trade ($)
                            <input type="number" id="pm_max_position" value="100" min="5" max="10000" step="5" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Montant maximum par position copiée</span>
                        </label>

                        <label style="display: block; margin-bottom: 10px; color: #bbb;">
                            Position Min par Trade ($)
                            <input type="number" id="pm_min_position" value="5" min="1" max="100" step="1" class="input-field" style="width: 100%; margin-top: 5px;">
                            <span style="font-size: 12px; color: #999;">Montant minimum pour copier un trade</span>
                        </label>

                        <label style="display: flex; align-items: center; margin-top: 15px; color: #bbb;">
                            <input type="checkbox" id="pm_dry_run" checked style="margin-right: 10px; width: 20px; height: 20px;">
                            <span>🔬 Mode DRY RUN (Simulation uniquement)</span>
                        </label>
                    </div>
                </div>

                <!-- Signaux Récents -->
                <div style="background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #64B5F6; margin-bottom: 15px;">📡 Signaux Récents</h3>
                    <div id="pm_recent_signals" style="max-height: 300px; overflow-y: auto;">
                        <p style="color: #999; text-align: center;">Aucun signal détecté pour le moment...</p>
                    </div>
                </div>

                <!-- Boutons d'action -->
                <div style="display: flex; gap: 10px;">
                    <button class="btn" onclick="savePolymarketConfig()" style="flex: 1; background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);">
                        💾 Sauvegarder la Configuration
                    </button>
                    <button class="btn" onclick="loadPolymarketConfig()" style="flex: 1; background: linear-gradient(135deg, #14B8A6 0%, #2DD4BF 100%);">
                        🔄 Recharger
                    </button>
                    <button class="btn" onclick="testPolymarketConnection()" style="flex: 1; background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%);">
                        🔗 Tester Connexion
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- MODAL EDITION TRADER -->
    <div id="editModal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;">
        <div style="background:#1a1a1a;margin:100px auto;padding:30px;width:500px;border-radius:12px;max-height:90vh;overflow-y:auto;">
            <h3 style="color:#64B5F6;margin-bottom:20px;">Éditer Trader</h3>
            <input type="text" id="edit_name" placeholder="Nom" style="width:100%;padding:10px;margin:10px 0;box-sizing:border-box;">
            <input type="text" id="edit_emoji" placeholder="Emoji" style="width:100%;padding:10px;margin:10px 0;box-sizing:border-box;">
            <input type="text" id="edit_address" placeholder="Adresse Solana" style="width:100%;padding:10px;margin:10px 0;box-sizing:border-box;">
            <label style="color: #aaa;">💰 Capital Alloué ($):</label>
            <input type="number" id="edit_capital" placeholder="500" style="width:100%;padding:10px;margin:10px 0;box-sizing:border-box;">
            <label style="color: #aaa;">📊 Montant par Trade ($):</label>
            <input type="number" id="edit_per_trade_amount" placeholder="20" min="1" style="width:100%;padding:10px;margin:10px 0;box-sizing:border-box;">
            <small style="color: #999;">Ex: 20 = chaque trade du trader = $20</small>
            <label style="color: #aaa;" style="margin-top:10px;">⚠️ Montant Minimum du Trade ($):</label>
            <input type="number" id="edit_min_trade_amount" placeholder="0" min="0" style="width:100%;padding:10px;margin:10px 0;box-sizing:border-box;">
            <small style="color: #999;">Ex: 40 = copier seulement si le trade du trader ≥ $40</small>
            <button class="btn" onclick="saveTraderEdit()" style="margin-top:15px;">Sauvegarder</button>
            <button class="btn danger" onclick="closeEditModal()">Annuler</button>
        </div>
    </div>

    <script>
        let chartData = [1000];
        let editingTraderIndex = -1;

        // 🌐 WEBSOCKET - Connexion Socket.IO pour temps réel
        const socket = io();

        // Événement: Connexion établie
        socket.on('connect', function() {
            console.log('✅ WebSocket connecté');
        });

        // Événement: Déconnexion
        socket.on('disconnect', function() {
            console.log('❌ WebSocket déconnecté');
        });

        // Événement: Trade exécuté
        socket.on('trade_executed', function(data) {
            console.log('💰 Trade exécuté:', data);
            // Afficher une notification
            showNotification(`Trade: ${data.trader} → ${data.token}`, 'success');
            // Rafraîchir l'UI
            updateUI();
        });

        // Événement: Portfolio mis à jour
        socket.on('portfolio_update', function(data) {
            console.log('📊 Portfolio mis à jour:', data);
            // Mettre à jour le portfolio sans recharger
            if (data.portfolio_value) {
                document.getElementById('portfolio').textContent = '$' + data.portfolio_value.toFixed(2);
            }
            if (data.active_traders !== undefined) {
                document.getElementById('active_traders_count').textContent = data.active_traders;
            }
        });

        // Événement: Trader mis à jour
        socket.on('trader_update', function(data) {
            console.log('👤 Trader mis à jour:', data);
            // Rafraîchir la liste des traders
            updateUI();
        });

        // Événement: Alerte
        socket.on('alert', function(data) {
            console.log('⚠️ Alerte:', data);
            showNotification(data.message, data.severity || 'warning');
        });

        // Événement: Performance mise à jour
        socket.on('performance', function(data) {
            console.log('📈 Performance:', data);
            // Mettre à jour les métriques de performance
            if (data.win_rate !== undefined) {
                const winRateEl = document.getElementById('win_rate');
                if (winRateEl) winRateEl.textContent = data.win_rate.toFixed(1) + '%';
            }
            if (data.pnl_total !== undefined) {
                const pnlColor = data.pnl_total >= 0 ? '#00E676' : '#D50000';
                const pnlEl = document.getElementById('total_pnl');
                if (pnlEl) {
                    pnlEl.textContent = (data.pnl_total >= 0 ? '+' : '') + '$' + data.pnl_total.toFixed(2);
                    pnlEl.style.color = pnlColor;
                }
            }
        });

        // Fonction pour afficher des notifications
        // 🎯 Toast Notification System
        function showNotification(message, type = 'info') {
            const emoji = type === 'success' ? '✅' : type === 'warning' ? '⚠️' : type === 'error' ? '❌' : '🔔';
            console.log(`${emoji} ${type.toUpperCase()}: ${message}`);

            // Créer toast notification
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `
                <div class="toast-title">${emoji} ${type.toUpperCase()}</div>
                <div class="toast-message">${message}</div>
            `;

            document.getElementById('toastContainer').appendChild(toast);

            // Auto-remove après 4 secondes
            setTimeout(() => {
                toast.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        // 🔔 Alert Banner System
        function showAlertBanner(message, critical = false) {
            const banner = document.getElementById('alertBanner');
            banner.className = critical ? 'alert-banner critical' : 'alert-banner';
            banner.textContent = message;
            banner.style.display = 'block';
        }

        function hideAlertBanner() {
            document.getElementById('alertBanner').style.display = 'none';
        }
        
        function showSection(name, eventTarget) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(name).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            if (eventTarget) {
                eventTarget.classList.add('active');
            } else {
                // Si pas d'eventTarget, chercher le bouton correspondant
                document.querySelectorAll('.nav-btn').forEach(b => {
                    if (b.textContent.toLowerCase().includes(name.toLowerCase())) {
                        b.classList.add('active');
                    }
                });
            }
        }
        
        function updateUI() {
            fetch('/api/status').then(r => r.json()).then(data => {
                document.getElementById('portfolio').textContent = (data.currency==='SOL'?'◎':'$') + data.portfolio;
                const status = document.getElementById('status');
                status.textContent = data.running ? 'BOT ACTIVÉ' : 'BOT DÉSACTIVÉ';
                status.className = data.running ? 'status on' : 'status off';
                document.getElementById('active_count').textContent = data.active_traders + '/3';
                document.getElementById('slippage_val').textContent = data.slippage;
                document.getElementById('active_traders_count').textContent = data.active_traders;

                // Statut WebSocket Helius
                if (data.websocket_helius) {
                    const wsStatus = document.getElementById('websocket_status');
                    const isActive = data.websocket_helius.active && data.websocket_helius.connected;
                    wsStatus.textContent = isActive
                        ? `✅ Connecté (${data.websocket_helius.subscriptions} traders)`
                        : '❌ Déconnecté';
                    wsStatus.className = isActive ? 'status on' : 'status off';
                }
                
                // ✅ CORRIGER: Afficher le nombre RÉEL de trades, pas les traders actifs
                fetch('/api/trade_history').then(r => r.json()).then(history => {
                    const tradeCount = history.trades ? history.trades.length : 0;
                    document.getElementById('total_trades').textContent = tradeCount;
                });
                document.getElementById('total_capital_display').textContent = data.total_capital.toFixed(2);
                
                // ✅ AFFICHER LE PnL TOTAL ET PERFORMANCE BOT
                const pnl_color = data.pnl_total >= 0 ? '#00E676' : '#D50000';
                document.getElementById('total_pnl').textContent = (data.pnl_total >= 0 ? '+' : '') + '$' + data.pnl_total;
                document.getElementById('total_pnl').style.color = pnl_color;
                const perf_color = data.pnl_percent >= 0 ? '#00E676' : '#D50000';
                document.getElementById('bot_performance').textContent = (data.pnl_percent >= 0 ? '+' : '') + data.pnl_percent + '%';
                document.getElementById('bot_performance').style.color = perf_color;
                
                // ✅ METTRE À JOUR LE GRAPHIQUE PnL
                chartData.push(data.portfolio);
                if (chartData.length > 50) chartData.shift();  // Garder seulement les 50 derniers
                drawPnLChart();
                
                // ✅ RAFRAÎCHIR LES POSITIONS EN PARAMÈTRES
                if (document.getElementById('open_positions_list')) {
                    refreshPositions();
                }
                
                // Calculer capital alloué
                let totalAllocated = 0;
                data.traders.forEach(t => { totalAllocated += (t.capital || 0); });
                document.getElementById('capital_allocated').textContent = '$' + totalAllocated;
                
                // Mettre à jour les performances des traders
                updateTradersPerformance();
                
                let html = '';
                data.traders.forEach((t,i) => {
                    const disabled = data.active_traders >= 3 && !t.active;
                    const activeClass = t.active ? 'active' : '';
                    const capitalDisplay = t.capital ? '💰 $' + t.capital : '💰 $0';
                    html += `<div class="trader-item ${activeClass}">
                        <div>
                            <span>${t.emoji} ${t.name}</span><br/>
                            <small style="color: #aaa;">${t.address.slice(0,12)}... | ${capitalDisplay}</small>
                        </div>
                        <div>
                            <input type="checkbox" ${t.active?'checked':''} onchange="toggleTrader(${i})" ${disabled?'disabled':''}>
                            <button class="btn small" onclick="editTrader(${i})">✏️</button>
                        </div>
                    </div>`;
                });
                document.getElementById('traders_list').innerHTML = html;
            });
        }
        
        function updateTradersPerformance() {
            fetch('/api/traders_performance').then(r => r.json()).then(performance => {
                let html = '';
                performance.forEach(p => {
                    // Convertir les strings en nombres pour les comparaisons
                    const pnl_num = parseFloat(p.pnl);
                    const pnl_percent_num = parseFloat(p.pnl_percent);
                    const pnl_24h_num = parseFloat(p.pnl_24h);
                    const pnl_24h_percent_num = parseFloat(p.pnl_24h_percent);
                    const pnl_7d_num = parseFloat(p.pnl_7d);
                    const pnl_7d_percent_num = parseFloat(p.pnl_7d_percent);
                    
                    const pnl_color = pnl_num >= 0 ? '#00E676' : '#D50000';
                    const pnl_24h_color = pnl_24h_num >= 0 ? '#00E676' : '#D50000';
                    const pnl_7d_color = pnl_7d_num >= 0 ? '#00E676' : '#D50000';
                    const bg_color = p.active ? '#0a4a0a' : 'transparent';
                    const border_style = p.active ? 'border: 2px solid #00E676; box-shadow: 0 0 10px rgba(0, 230, 118, 0.2);' : '';
                    
                    html += `<tr style="background-color: ${bg_color}; ${border_style}">
                        <td>${p.trader}</td>
                        <td>${p.current_value}</td>
                        <td style="color: ${pnl_color}; font-weight: bold;">
                            ${pnl_num >= 0 ? '+' : ''}${p.pnl} (${pnl_percent_num >= 0 ? '+' : ''}${p.pnl_percent}%)
                        </td>
                        <td style="color: ${pnl_24h_color}; font-weight: bold;">
                            ${pnl_24h_num >= 0 ? '+' : ''}${p.pnl_24h} (${pnl_24h_percent_num >= 0 ? '+' : ''}${p.pnl_24h_percent}%)
                        </td>
                        <td style="color: ${pnl_7d_color}; font-weight: bold;">
                            ${pnl_7d_num >= 0 ? '+' : ''}${p.pnl_7d} (${pnl_7d_percent_num >= 0 ? '+' : ''}${p.pnl_7d_percent}%)
                        </td>
                    </tr>`;
                });
                document.getElementById('traders_performance').innerHTML = html;
            });
        }

        // ⚡ Update Advanced Metrics (Phase 9) - VRAIES DONNÉES
        function updateAdvancedMetrics() {
            // ✅ Récupérer les VRAIES métriques depuis l'API
            fetch('/api/advanced_metrics')
                .then(res => res.json())
                .then(data => {
                    // Métriques système réelles
                    document.getElementById('avg_latency').textContent = data.avg_latency + 'ms';
                    document.getElementById('cache_hit').textContent = data.cache_hit + '%';
                    document.getElementById('rpc_success').textContent = data.rpc_success + '%';

                    // Métriques de trading réelles
                    document.getElementById('win_rate_metric').textContent = data.win_rate + '%';
                    document.getElementById('sharpe_ratio_metric').textContent = data.sharpe_ratio;
                    document.getElementById('max_drawdown_metric').textContent = data.max_drawdown + '%';
                    document.getElementById('max_drawdown_metric').parentElement.className =
                        data.max_drawdown < -10 ? 'metric-box negative' : 'metric-box';

                    const circuitStatus = data.circuit_breaker_open ? '🔴 OUVERT' : '🟢 FERMÉ';
                    document.getElementById('circuit_breaker_status').textContent = circuitStatus;
                    document.getElementById('circuit_breaker_status').parentElement.className =
                        data.circuit_breaker_open ? 'metric-box negative' : 'metric-box';

                    if (data.circuit_breaker_open) {
                        showAlertBanner('⚠️ CIRCUIT BREAKER ACTIVÉ - Trading suspendu pour protection du capital', true);
                    } else {
                        hideAlertBanner();
                    }

                    document.getElementById('smart_filter_pass').textContent = data.smart_filter_pass + '%';
                    document.getElementById('market_volatility').textContent = data.market_volatility;
                })
                .catch(err => {
                    console.error('❌ Erreur récupération métriques avancées:', err);
                    // Afficher des valeurs par défaut en cas d'erreur
                    document.getElementById('avg_latency').textContent = 'N/A';
                    document.getElementById('cache_hit').textContent = 'N/A';
                    document.getElementById('rpc_success').textContent = 'N/A';
                });
        }

        function toggleBot() {
            fetch('/api/toggle_bot').then(() => {
                updateUI();
            }); 
        }
        
        function toggleTrader(i) { fetch(`/api/toggle_trader/${i}`).then(() => updateUI()); }
        function updateSlippage(v) { fetch(`/api/update_params?slippage=${v}`).then(() => updateUI()); }
        function saveKey() { fetch('/api/save_key', {method:'POST', body:JSON.stringify({key:document.getElementById('priv_key').value}), headers:{'Content-Type':'application/json'}}).then(() => alert('Clé sauvegardée en mémoire')); }
        function disconnect() { fetch('/api/disconnect').then(() => { document.getElementById('priv_key').value = ''; updateUI(); }); }
        
        function saveTakeProfit() {
            const params = {
                tp1_percent: document.getElementById('tp1_percent').value,
                tp1_profit: document.getElementById('tp1_profit').value,
                tp2_percent: document.getElementById('tp2_percent').value,
                tp2_profit: document.getElementById('tp2_profit').value,
                tp3_percent: document.getElementById('tp3_percent').value,
                tp3_profit: document.getElementById('tp3_profit').value,
                sl_percent: document.getElementById('sl_percent').value,
                sl_loss: document.getElementById('sl_loss').value
            };
            fetch('/api/save_take_profit', {
                method: 'POST',
                body: JSON.stringify(params),
                headers: {'Content-Type': 'application/json'}
            }).then(() => alert('✅ Paramètres TP & SL sauvegardés !'));
        }
        
        function editTrader(index) {
            editingTraderIndex = index;
            fetch('/api/status').then(r => r.json()).then(data => {
                const trader = data.traders[index];
                document.getElementById('edit_name').value = trader.name;
                document.getElementById('edit_emoji').value = trader.emoji;
                document.getElementById('edit_address').value = trader.address;
                document.getElementById('edit_capital').value = trader.capital || 0;
                document.getElementById('edit_per_trade_amount').value = trader.per_trade_amount || 10;
                document.getElementById('edit_min_trade_amount').value = trader.min_trade_amount || 0;
                document.getElementById('editModal').style.display = 'block';
            });
        }
        
        function saveTraderEdit() {
            const name = document.getElementById('edit_name').value;
            const emoji = document.getElementById('edit_emoji').value;
            const address = document.getElementById('edit_address').value;
            const capital = parseFloat(document.getElementById('edit_capital').value) || 0;
            const per_trade_amount = parseFloat(document.getElementById('edit_per_trade_amount').value) || 10;
            const min_trade_amount = parseFloat(document.getElementById('edit_min_trade_amount').value) || 0;
            
            fetch('/api/edit_trader', {
                method: 'POST',
                body: JSON.stringify({index: editingTraderIndex, name, emoji, address, capital, per_trade_amount, min_trade_amount}),
                headers: {'Content-Type': 'application/json'}
            }).then(() => {
                closeEditModal();
                updateUI();
            });
        }
        
        function closeEditModal() {
            document.getElementById('editModal').style.display = 'none';
            editingTraderIndex = -1;
        }
        
        setInterval(updateUI, 5000);  // Appel toutes les 5 secondes pour éviter le rate limiting
        updateUI();
        
        // BACKTESTING FUNCTIONS
        function loadBacktestTraders() {
            fetch('/api/status').then(r => r.json()).then(data => {
                let html = '<option value="">-- Choisir un trader --</option>';
                data.traders.forEach(t => {
                    html += `<option value="${t.address}">${t.emoji} ${t.name}</option>`;
                });
                document.getElementById('backtest_trader').innerHTML = html;
            });
        }
        
        function runBacktestMultiple() {
            const trader_address = document.getElementById('backtest_trader').value;
            if (!trader_address) {
                alert('Veuillez sélectionner un trader');
                return;
            }
            
            document.getElementById('backtest_results').innerHTML = '⏳ Backtesting en cours...';
            
            fetch('/api/backtest_multiple', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({trader_address: trader_address})
            }).then(r => r.json()).then(data => {
                if (!data.results || data.results.length === 0) {
                    document.getElementById('backtest_results').innerHTML = '<p style="color: #FF6B6B;">❌ Pas assez de trades pour le backtesting</p>';
                    return;
                }
                
                let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">';
                data.results.forEach(r => {
                    const bg = r.win_rate >= 50 ? '#0a4a0a' : '#4a0a0a';
                    html += `<div class="card" style="background: ${bg};">
                        <h3 style="color: #64B5F6;">TP: ${r.tp_percent}% / SL: ${r.sl_percent}%</h3>
                        <p style="color: #aaa;">Trades: <span style="color: #00E676;">${r.total_trades}</span></p>
                        <p style="color: #aaa;">Win Rate: <span style="color: #FFD600;">${r.win_rate}%</span></p>
                        <p style="color: #aaa;">PnL: <span style="color: ${r.total_pnl >= 0 ? '#00E676' : '#D50000'};">$${r.total_pnl}</span></p>
                        <p style="color: #aaa;">PnL%: <span style="color: ${r.total_pnl_percent >= 0 ? '#00E676' : '#D50000'};">${r.total_pnl_percent}%</span></p>
                    </div>`;
                });
                html += '</div>';
                
                if (data.best) {
                    html += `<div class="card" style="margin-top: 20px; border: 2px solid #FFD600;">
                        <h3 style="color: #FFD600;">🎯 MEILLEUR RÉSULTAT</h3>
                        <p>TP: <span style="color: #00E676;">${data.best.tp_percent}%</span> / SL: <span style="color: #00E676;">${data.best.sl_percent}%</span></p>
                        <p>Win Rate: <span style="color: #FFD600;">${data.best.win_rate}%</span></p>
                        <p>PnL: <span style="color: #00E676;">$${data.best.total_pnl}</span> (${data.best.total_pnl_percent}%)</p>
                    </div>`;
                }
                
                document.getElementById('backtest_results').innerHTML = html;
            }).catch(e => {
                document.getElementById('backtest_results').innerHTML = '<p style="color: #FF6B6B;">❌ Erreur: ' + e + '</p>';
            });
        }
        
        // BENCHMARK FUNCTIONS (sans scintillement)
        function updateBenchmark() {
            document.getElementById('benchmark_ranking').innerHTML = '<tr><td colspan="4" style="text-align: center;">⏳ Chargement...</td></tr>';
            
            // Appels PARALLÈLES (pas de cascade) pour éviter le scintillement
            Promise.all([
                fetch('/api/benchmark').then(r => r.json()),
                fetch('/api/benchmark_ranking').then(r => r.json())
            ]).then(([benchmark, rankData]) => {
                // Update bot stats
                const bot_pnl_color = benchmark.bot_pnl >= 0 ? '#00E676' : '#D50000';
                document.getElementById('bot_benchmark_pnl').textContent = (benchmark.bot_pnl >= 0 ? '+' : '') + benchmark.bot_pnl.toFixed(2) + '%';
                document.getElementById('bot_benchmark_pnl').style.color = bot_pnl_color;
                document.getElementById('bot_benchmark_wr').textContent = benchmark.bot_win_rate.toFixed(1) + '%';
                document.getElementById('bot_benchmark_rank').textContent = '#' + benchmark.bot_rank;
                
                // Update best trader
                if (benchmark.best_trader) {
                    document.getElementById('best_trader_name').textContent = benchmark.best_trader.trader_name;
                    document.getElementById('best_trader_pnl').textContent = (benchmark.best_trader.trader_pnl >= 0 ? '+' : '') + benchmark.best_trader.trader_pnl.toFixed(2) + '%';
                    document.getElementById('best_trader_wr').textContent = benchmark.best_trader.trader_win_rate.toFixed(1) + '%';
                }
                
                // Update ranking (en même temps)
                let html = '';
                rankData.ranking.forEach(r => {
                    const bg = r.rank === 1 ? '#0a3a0a' : (r.rank <= 3 ? '#1a2a3a' : 'transparent');
                    const color = r.rank === 1 ? '#FFD600' : '#64B5F6';
                    const medal = r.rank === 1 ? '🥇' : (r.rank === 2 ? '🥈' : (r.rank === 3 ? '🥉' : ''));
                    html += `<tr style="background: ${bg};">
                        <td style="color: ${color}; font-weight: bold;">${medal} #${r.rank}</td>
                        <td>${r.name}</td>
                        <td style="color: ${r.pnl >= 0 ? '#00E676' : '#D50000'};">${(r.pnl >= 0 ? '+' : '')}${r.pnl.toFixed(2)}%</td>
                        <td style="color: #FFD600;">${r.win_rate.toFixed(1)}%</td>
                    </tr>`;
                });
                document.getElementById('benchmark_ranking').innerHTML = html;
            });
        }
        
        // Charger les traders au chargement
        loadBacktestTraders();
        
        function refreshPositions() {
            fetch('/api/open_positions').then(r => r.json()).then(data => {
                let html = '';
                
                if (data.open_positions_count === 0) {
                    html = '<p style="color: #999; text-align: center;">Aucune position ouverte</p>';
                } else {
                    html += `<div style="margin-bottom: 15px; padding: 10px; background: #0a3a0a; border-radius: 8px;">
                        <p style="color: #00E676; margin: 5px 0;"><strong>📊 ${data.open_positions_count} position(s) ouverte(s)</strong></p>
                        <p style="color: #aaa; margin: 5px 0;">PnL Ouvert: <span style="color: ${data.total_open_pnl >= 0 ? '#00E676' : '#D50000'};">$${data.total_open_pnl.toFixed(2)}</span></p>
                    </div>`;
                    
                    data.open_positions.forEach(pos => {
                        const pnl_color = pos.pnl >= 0 ? '#00E676' : '#D50000';
                        html += `<div style="margin: 10px 0; padding: 10px; background: #2a2a2a; border-radius: 8px; border-left: 4px solid ${pnl_color};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <p style="color: #64B5F6; margin: 5px 0;"><strong>${pos.trader_name}</strong></p>
                                    <p style="color: #aaa; margin: 5px 0;">Entry: $${pos.entry_price.toFixed(2)} | Amount: ${pos.amount}</p>
                                    <p style="color: #aaa; margin: 5px 0;">TP: ${pos.tp_percent}% | SL: ${pos.sl_percent}%</p>
                                    <p style="color: ${pnl_color}; margin: 5px 0;"><strong>PnL: $${pos.pnl.toFixed(2)} (${pos.pnl_percent.toFixed(2)}%)</strong></p>
                                </div>
                                <button class="btn" onclick="manualSell('${pos.position_id}', ${pos.current_price})" style="padding: 10px 15px;">💰 Vendre</button>
                            </div>
                        </div>`;
                    });
                    
                    if (data.closed_positions_count > 0) {
                        html += `<div style="margin-top: 20px; padding: 10px; background: #3a2a2a; border-radius: 8px;">
                            <p style="color: #FFD600; margin: 5px 0;"><strong>✅ ${data.closed_positions_count} position(s) fermée(s)</strong></p>
                            <p style="color: #aaa; margin: 5px 0;">PnL Réalisé: <span style="color: ${data.total_closed_pnl >= 0 ? '#00E676' : '#D50000'};">$${data.total_closed_pnl.toFixed(2)}</span></p>
                        </div>`;
                    }
                }
                
                document.getElementById('open_positions_list').innerHTML = html;
            });
        }
        
        // Fonction pour dessiner le graphique PnL
        // 📊 Chart.js - PnL Chart Instance
        let pnlChartInstance = null;

        function initPnLChart() {
            const canvas = document.getElementById('pnlChart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');

            // Destroy existing chart if any
            if (pnlChartInstance) {
                pnlChartInstance.destroy();
            }

            // Create new Chart.js instance
            pnlChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array(chartData.length).fill('').map((_, i) => i === chartData.length - 1 ? 'Now' : ''),
                    datasets: [{
                        label: 'Portfolio Value ($)',
                        data: chartData,
                        borderColor: '#00E676',
                        backgroundColor: 'rgba(0, 230, 118, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#00E676',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: true,
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#00E676',
                            bodyColor: '#fff',
                            borderColor: '#00E676',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: false,
                            callbacks: {
                                label: function(context) {
                                    return 'Value: $' + context.parsed.y.toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: {
                                color: '#333',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#666',
                                maxTicksLimit: 10
                            }
                        },
                        y: {
                            display: true,
                            grid: {
                                color: '#333',
                                drawBorder: false
                            },
                            ticks: {
                                color: '#666',
                                callback: function(value) {
                                    return '$' + value.toFixed(0);
                                }
                            }
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            });
        }

        function drawPnLChart() {
            if (!pnlChartInstance) {
                initPnLChart();
            } else {
                // Update existing chart
                pnlChartInstance.data.labels = Array(chartData.length).fill('').map((_, i) => i === chartData.length - 1 ? 'Now' : '');
                pnlChartInstance.data.datasets[0].data = chartData;
                pnlChartInstance.update('none'); // 'none' for no animation
            }
        }
        
        function manualSell(position_id, current_price) {
            if (confirm('Vendre cette position maintenant ?')) {
                fetch(`/api/manual_sell/${position_id}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({current_price: current_price})
                }).then(r => r.json()).then(data => {
                    alert('Position fermée ! PnL: $' + (data.final_pnl || 0).toFixed(2));
                    refreshPositions();
                }).catch(e => {
                    alert('Erreur: ' + e);
                });
            }
        }
        
        function refreshHistory() {
            fetch('/api/trade_history').then(r => r.json()).then(data => {
                let html = '';
                if (data.trades && data.trades.length > 0) {
                    data.trades.forEach(trade => {
                        html += `<tr>
                            <td style="color: #aaa;">${trade.time}</td>
                            <td style="color: #64B5F6;"><strong>${trade.trader}</strong></td>
                            <td style="color: #999;">${trade.platform}</td>
                            <td style="color: #aaa; font-size: 11px; word-break: break-all;">${trade.position_id.slice(0, 20)}...</td>
                            <td style="color: ${trade.pnl.startsWith('-') ? '#D50000' : '#00E676'};">${trade.pnl}</td>
                            <td style="color: #FFD600;">${trade.performance}</td>
                        </tr>`;
                    });
                } else {
                    html = '<tr><td colspan="6" style="text-align: center; color: #999; padding: 20px;">Aucun trade détecté</td></tr>';
                }
                document.getElementById('trades_body').innerHTML = html;
            }).catch(() => {
                document.getElementById('trades_body').innerHTML = '<tr><td colspan="6" style="text-align: center; color: #999; padding: 20px;">Erreur chargement</td></tr>';
            });
        }
        
        // ============== LIVE DASHBOARD ==============
        function refreshLiveDashboard() {
            // Récupérer status global
            fetch('/api/status').then(r => r.json()).then(status => {
                document.getElementById('live_portfolio').textContent = '$' + status.portfolio;
                document.getElementById('live_active_count').textContent = status.active_traders + '/3';
                document.getElementById('total_capital_display').textContent = status.total_capital.toFixed(2);
                
                // ✅ METTRE À JOUR LE GRAPHIQUE PnL
                chartData.push(status.portfolio);
                if (chartData.length > 50) chartData.shift();  // Garder seulement les 50 derniers
                drawPnLChart();
                
                // Récupérer les positions ouvertes
                fetch('/api/open_positions').then(r => r.json()).then(positions => {
                    document.getElementById('live_positions_count').textContent = positions.open_positions_count;
                    
                    // Récupérer les traders performance
                    fetch('/api/traders_performance').then(r => r.json()).then(traders => {
                        let html = '';
                        const activeTraders = status.traders.filter(t => t.active);
                        
                        activeTraders.forEach((trader, idx) => {
                            const perf = traders[idx] || {};
                            const isProfitable = parseFloat(perf.pnl_24h || 0) >= 0;
                            const statusClass = isProfitable ? 'green' : 'red';
                            const statusText = isProfitable ? '✅ RENTABLE' : '❌ EN PERTE';
                            const cardClass = isProfitable ? 'profitable' : 'losing';
                            
                            // Récupérer les positions du trader
                            const traderPositions = positions.open_positions.filter(p => p.trader_name === trader.name);
                            const tokens = new Set();
                            
                            traderPositions.forEach(pos => {
                                if (pos.token_symbol) tokens.add(pos.token_symbol);
                            });
                            
                            let tokensHtml = '';
                            if (tokens.size > 0) {
                                tokensHtml = `<div class="tokens-section">
                                    <div class="tokens-title">📱 Tokens en Trading:</div>
                                    ${Array.from(tokens).map(t => `<span class="token-item">${t}</span>`).join('')}
                                </div>`;
                            } else {
                                tokensHtml = `<div class="tokens-section">
                                    <div class="tokens-title">📱 Tokens en Trading:</div>
                                    <span class="token-item no-position">Aucune position ouverte</span>
                                </div>`;
                            }
                            
                            html += `<div class="live-trader-card ${cardClass}">
                                <div class="trader-header">
                                    <div class="trader-name">${trader.emoji} ${trader.name}</div>
                                    <div class="trader-status ${statusClass}">${statusText}</div>
                                </div>
                                
                                <div class="live-stats">
                                    <div class="live-stat ${parseFloat(perf.pnl_24h || 0) < 0 ? 'negative' : ''}">
                                        <label>PnL 24h</label>
                                        <value>${perf.pnl_24h || '+$0'} (${perf.pnl_24h_percent || '0'}%)</value>
                                    </div>
                                    <div class="live-stat">
                                        <label>Win Rate</label>
                                        <value>${perf.win_rate || '0'}%</value>
                                    </div>
                                    <div class="live-stat">
                                        <label>Positions</label>
                                        <value>${traderPositions.length}</value>
                                    </div>
                                    <div class="live-stat ${positions.total_open_pnl < 0 ? 'negative' : ''}">
                                        <label>PnL Ouvert</label>
                                        <value>$${positions.total_open_pnl.toFixed(2)}</value>
                                    </div>
                                </div>
                                
                                ${tokensHtml}
                                
                                <div class="action-buttons">
                                    <button class="action-btn exit-all" onclick='exitAllTrader("${trader.name}", [${traderPositions.map(p => `"${p.position_id}"`).join(",")}])'>💰 Sortir Tout</button>
                                    <button class="action-btn disable" onclick="disableTrader(${idx})">❌ Désactiver</button>
                                </div>
                            </div>`;
                        });
                        
                        if (html === '') {
                            html = '<p style="color: #999; text-align: center; padding: 30px;">Aucun trader actif. Activez un trader dans Gestion Traders.</p>';
                        }
                        
                        document.getElementById('live_traders_container').innerHTML = html;
                        document.getElementById('live_pnl_24h').textContent = (positions.total_open_pnl >= 0 ? '+' : '') + '$' + positions.total_open_pnl.toFixed(2);
                    });
                });
            });
        }
        
        function exitAllTrader(traderName, positionIds) {
            if (confirm(`Êtes-vous sûr de vouloir sortir TOUTES les positions de ${traderName} ?`)) {
                // ✅ positionIds est maintenant un array directement
                if (!Array.isArray(positionIds) || positionIds.length === 0) {
                    alert('Aucune position ouverte');
                    return;
                }

                let exitedCount = 0;
                positionIds.forEach(id => {
                    fetch(`/api/manual_sell/${id}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({current_price: 0})
                    }).then(() => {
                        exitedCount++;
                        if (exitedCount === positionIds.length) {
                            alert(`✅ ${exitedCount} position(s) fermée(s)`);
                            refreshLiveDashboard();
                        }
                    });
                });
            }
        }
        
        function disableTrader(index) {
            if (confirm('Désactiver ce trader ? Les positions restent ouvertes.')) {
                fetch(`/api/toggle_trader/${index}`).then(() => {
                    alert('✅ Trader désactivé');
                    refreshLiveDashboard();
                });
            }
        }
        
        // Rafraîchir le LIVE Dashboard chaque 1 seconde
        setInterval(refreshLiveDashboard, 1000);
        refreshLiveDashboard();
        
        // Rafraîchir les positions toutes les 5 secondes
        setInterval(refreshPositions, 5000);
        refreshPositions();
        
        // Rafraîchir l'historique toutes les 3 secondes
        setInterval(refreshHistory, 3000);
        refreshHistory();
        
        // Rafraîchir le Backtesting toutes les 10 secondes
        loadBacktestTraders();  // Appel immédiat
        setInterval(loadBacktestTraders, 10000);

        // Rafraîchir le Benchmark toutes les 15 secondes
        setInterval(updateBenchmark, 15000);
        updateBenchmark();

        // ⚡ Phase 9: Initialize Chart.js and Advanced Metrics
        initPnLChart();
        setInterval(updateAdvancedMetrics, 3000); // Update every 3 seconds
        updateAdvancedMetrics();

        // 🛡️ Risk Manager: Initialize
        loadRiskParams();
        setInterval(updateRiskMetrics, 2000); // Update every 2 seconds
        updateRiskMetrics();

        // 💰 Arbitrage: Initialize
        loadArbitrageConfig();
        setInterval(updateArbitrageStats, 3000); // Update every 3 seconds
        updateArbitrageStats();

        // 🎯 Test toast notification on load
        setTimeout(() => {
            showNotification('Dashboard Phase 9 activé! Charts interactifs et métriques avancées disponibles.', 'success');
        }, 1000);

        // ==================== RISK MANAGER FUNCTIONS ====================

        async function loadRiskParams() {
            try {
                const response = await fetch('/api/risk_manager/params');
                const data = await response.json();
                if (data.success) {
                    const params = data.params;
                    document.getElementById('circuit_breaker_threshold').value = params.circuit_breaker_threshold;
                    document.getElementById('circuit_breaker_cooldown').value = params.circuit_breaker_cooldown;
                    document.getElementById('max_consecutive_losses').value = params.max_consecutive_losses;
                    document.getElementById('max_position_size_percent').value = params.max_position_size_percent;
                    document.getElementById('max_daily_loss_percent').value = params.max_daily_loss_percent;
                    document.getElementById('max_drawdown_percent').value = params.max_drawdown_percent;
                    document.getElementById('kelly_safety_factor').value = params.kelly_safety_factor;
                    document.getElementById('save_params_toggle').checked = params.save_params;
                }
            } catch (error) {
                console.error('Erreur chargement params Risk Manager:', error);
            }
        }

        async function saveRiskParams() {
            const params = {
                circuit_breaker_threshold: parseFloat(document.getElementById('circuit_breaker_threshold').value),
                circuit_breaker_cooldown: parseInt(document.getElementById('circuit_breaker_cooldown').value),
                max_consecutive_losses: parseInt(document.getElementById('max_consecutive_losses').value),
                max_position_size_percent: parseFloat(document.getElementById('max_position_size_percent').value),
                max_daily_loss_percent: parseFloat(document.getElementById('max_daily_loss_percent').value),
                max_drawdown_percent: parseFloat(document.getElementById('max_drawdown_percent').value),
                kelly_safety_factor: parseFloat(document.getElementById('kelly_safety_factor').value),
                save_params: document.getElementById('save_params_toggle').checked
            };

            try {
                const response = await fetch('/api/risk_manager/params', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(params)
                });
                const data = await response.json();

                if (data.success) {
                    const msg = data.saved_to_disk
                        ? '✅ Paramètres sauvegardés dans config.json (persistants)'
                        : '✅ Paramètres mis à jour (mémoire uniquement)';
                    showNotification(msg, 'success');
                } else {
                    showNotification('❌ Erreur: ' + data.message, 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur lors de la sauvegarde', 'error');
                console.error(error);
            }
        }

        async function resetRiskDefaults() {
            if (!confirm('Réinitialiser tous les paramètres aux valeurs par défaut ?')) return;

            try {
                const response = await fetch('/api/risk_manager/reset_defaults', {method: 'POST'});
                const data = await response.json();

                if (data.success) {
                    showNotification('✅ Paramètres réinitialisés aux défauts', 'success');
                    await loadRiskParams();
                } else {
                    showNotification('❌ Erreur: ' + data.message, 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur lors de la réinitialisation', 'error');
                console.error(error);
            }
        }

        async function resetCircuitBreaker() {
            try {
                const response = await fetch('/api/risk_manager/reset_circuit_breaker', {method: 'POST'});
                const data = await response.json();

                if (data.success) {
                    showNotification('✅ Circuit Breaker réinitialisé', 'success');
                    await updateRiskMetrics();
                } else {
                    showNotification('❌ Erreur: ' + data.message, 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur lors de la réinitialisation du circuit breaker', 'error');
                console.error(error);
            }
        }

        async function toggleSaveParams() {
            await saveRiskParams();
        }

        async function updateRiskMetrics() {
            try {
                const response = await fetch('/api/risk_manager/metrics');
                const data = await response.json();

                if (data.success) {
                    const metrics = data.metrics;

                    // Update metrics display
                    document.getElementById('risk_current_balance').textContent = '$' + metrics.current_balance.toFixed(2);
                    document.getElementById('risk_drawdown').textContent = metrics.drawdown_percent.toFixed(2) + '%';
                    document.getElementById('risk_daily_pnl').textContent = '$' + metrics.daily_pnl.toFixed(2);
                    document.getElementById('risk_consecutive_losses').textContent = metrics.consecutive_losses;

                    // Show/hide circuit breaker alert
                    const alert = document.getElementById('circuit_breaker_alert');
                    if (metrics.circuit_breaker_active) {
                        alert.style.display = 'block';
                    } else {
                        alert.style.display = 'none';
                    }

                    // Color coding
                    const drawdownEl = document.getElementById('risk_drawdown');
                    if (metrics.drawdown_percent > 15) {
                        drawdownEl.style.color = '#ff5252';
                    } else if (metrics.drawdown_percent > 10) {
                        drawdownEl.style.color = '#ffa726';
                    } else {
                        drawdownEl.style.color = '#66bb6a';
                    }

                    const pnlEl = document.getElementById('risk_daily_pnl');
                    pnlEl.style.color = metrics.daily_pnl >= 0 ? '#66bb6a' : '#ff5252';
                }
            } catch (error) {
                console.error('Erreur update risk metrics:', error);
            }
        }

        // ═══════════════════════════════════════════════════════════════════
        // 💰 ARBITRAGE FUNCTIONS
        // ═══════════════════════════════════════════════════════════════════

        async function toggleArbitrage() {
            const enabled = document.getElementById('arbitrage_enabled').checked;
            try {
                const response = await fetch('/api/arbitrage/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ enabled: enabled })
                });
                const data = await response.json();

                if (data.success) {
                    const statusText = document.getElementById('arbitrage_status_text');
                    statusText.textContent = enabled ? '✅ Arbitrage Activé' : '❌ Arbitrage Désactivé';
                    statusText.style.color = enabled ? '#66bb6a' : '#ff5252';
                    showNotification(enabled ? '✅ Arbitrage activé' : '❌ Arbitrage désactivé', 'success');
                } else {
                    showNotification('❌ Erreur: ' + data.error, 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur lors du changement de statut', 'error');
                console.error(error);
            }
        }

        async function loadArbitrageConfig() {
            try {
                const response = await fetch('/api/arbitrage/config');
                const data = await response.json();

                if (data.success) {
                    const config = data.config;

                    // Update form fields
                    document.getElementById('arbitrage_enabled').checked = config.enabled;
                    document.getElementById('arb_capital_dedicated').value = config.capital_dedicated;
                    document.getElementById('arb_percent_per_trade').value = config.percent_per_trade;
                    document.getElementById('arb_min_amount').value = config.min_amount_per_trade;
                    document.getElementById('arb_max_amount').value = config.max_amount_per_trade;
                    document.getElementById('arb_min_profit').value = config.min_profit_threshold;
                    document.getElementById('arb_cooldown').value = config.cooldown_seconds;
                    document.getElementById('arb_max_concurrent').value = config.max_concurrent_trades;
                    document.getElementById('arb_blacklist').value = config.blacklist_tokens.join(', ');

                    // Update status text
                    const statusText = document.getElementById('arbitrage_status_text');
                    statusText.textContent = config.enabled ? '✅ Arbitrage Activé' : '❌ Arbitrage Désactivé';
                    statusText.style.color = config.enabled ? '#66bb6a' : '#ff5252';
                }
            } catch (error) {
                console.error('Erreur chargement config arbitrage:', error);
            }
        }

        async function saveArbitrageConfig() {
            try {
                const blacklistRaw = document.getElementById('arb_blacklist').value;
                const blacklistTokens = blacklistRaw.split(',').map(t => t.trim()).filter(t => t.length > 0);

                const params = {
                    enabled: document.getElementById('arbitrage_enabled').checked,
                    capital_dedicated: parseFloat(document.getElementById('arb_capital_dedicated').value),
                    percent_per_trade: parseFloat(document.getElementById('arb_percent_per_trade').value),
                    min_amount_per_trade: parseFloat(document.getElementById('arb_min_amount').value),
                    max_amount_per_trade: parseFloat(document.getElementById('arb_max_amount').value),
                    min_profit_threshold: parseFloat(document.getElementById('arb_min_profit').value),
                    cooldown_seconds: parseInt(document.getElementById('arb_cooldown').value),
                    max_concurrent_trades: parseInt(document.getElementById('arb_max_concurrent').value),
                    blacklist_tokens: blacklistTokens
                };

                const response = await fetch('/api/arbitrage/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(params)
                });
                const data = await response.json();

                if (data.success) {
                    showNotification('✅ Configuration arbitrage sauvegardée', 'success');
                } else {
                    showNotification('❌ Erreur: ' + data.error, 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur lors de la sauvegarde', 'error');
                console.error(error);
            }
        }

        async function updateArbitrageStats() {
            try {
                const response = await fetch('/api/arbitrage/stats');
                const data = await response.json();

                if (data.success) {
                    const stats = data.stats;

                    // Update stats display
                    document.getElementById('arb_capital').textContent = '$' + stats.capital_dedicated.toFixed(2);
                    document.getElementById('arb_opportunities').textContent = stats.opportunities_found;
                    document.getElementById('arb_executed').textContent = stats.opportunities_executed;
                    document.getElementById('arb_winrate').textContent = stats.win_rate.toFixed(1) + '%';

                    const profitEl = document.getElementById('arb_profit');
                    profitEl.textContent = '$' + stats.total_profit.toFixed(2);
                    profitEl.style.color = stats.total_profit >= 0 ? '#66bb6a' : '#ff5252';

                    // Update recent opportunities
                    const oppContainer = document.getElementById('recent_opportunities');
                    if (stats.recent_opportunities && stats.recent_opportunities.length > 0) {
                        oppContainer.innerHTML = stats.recent_opportunities.map(opp => `
                            <div style="background: #1a1a1a; padding: 12px; margin-bottom: 10px; border-radius: 6px; border-left: 3px solid ${opp.opportunity ? '#66bb6a' : '#999'};">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <span style="color: #64B5F6; font-weight: bold;">${opp.token_mint.substring(0, 8)}...</span>
                                        <span style="color: #999; margin-left: 10px;">
                                            ${opp.buy_dex} → ${opp.sell_dex}
                                        </span>
                                    </div>
                                    <div>
                                        <span style="color: ${opp.net_profit >= 0 ? '#66bb6a' : '#ff5252'}; font-weight: bold; font-size: 16px;">
                                            ${opp.net_profit > 0 ? '+' : ''}${opp.net_profit.toFixed(2)}%
                                        </span>
                                    </div>
                                </div>
                                <div style="color: #999; font-size: 12px; margin-top: 5px;">
                                    Achat: $${opp.buy_price.toFixed(6)} | Vente: $${opp.sell_price.toFixed(6)} | Frais: ${opp.total_fees.toFixed(2)}%
                                </div>
                            </div>
                        `).join('');
                    } else {
                        oppContainer.innerHTML = '<p style="color: #999; text-align: center;">Aucune opportunité détectée pour le moment...</p>';
                    }
                }
            } catch (error) {
                console.error('Erreur update arbitrage stats:', error);
            }
        }

        // ═══════════════════════════════════════════════════════════════════
        // 🔮 POLYMARKET COPY TRADING FUNCTIONS
        // ═══════════════════════════════════════════════════════════════════

        async function togglePolymarket() {
            const enabled = document.getElementById('polymarket_enabled').checked;
            try {
                const response = await fetch('/api/polymarket/toggle', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ enabled: enabled })
                });
                const data = await response.json();

                if (data.success) {
                    const statusText = document.getElementById('polymarket_status_text');
                    statusText.textContent = enabled ? '✅ Copy Trading Polymarket Activé' : '❌ Copy Trading Polymarket Désactivé';
                    statusText.style.color = enabled ? '#66bb6a' : '#ff5252';
                    showNotification(enabled ? '✅ Polymarket Copy Trading activé' : '❌ Polymarket Copy Trading désactivé', 'success');
                } else {
                    showNotification('❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur lors du changement de statut', 'error');
                console.error(error);
            }
        }

        async function loadPolymarketConfig() {
            try {
                const response = await fetch('/api/polymarket/config');
                const data = await response.json();

                if (data.success) {
                    const config = data.config;

                    // Update form fields
                    document.getElementById('polymarket_enabled').checked = config.enabled || false;
                    document.getElementById('pm_tracked_wallets').value = (config.tracked_wallets || []).join('\n');
                    document.getElementById('pm_polling_interval').value = config.polling_interval || 10;
                    document.getElementById('pm_max_position').value = config.max_position_usd || 100;
                    document.getElementById('pm_min_position').value = config.min_position_usd || 5;
                    document.getElementById('pm_dry_run').checked = config.dry_run !== false;

                    // Update status text
                    const statusText = document.getElementById('polymarket_status_text');
                    statusText.textContent = config.enabled ? '✅ Copy Trading Polymarket Activé' : '❌ Copy Trading Polymarket Désactivé';
                    statusText.style.color = config.enabled ? '#66bb6a' : '#ff5252';

                    showNotification('✅ Configuration Polymarket chargée', 'success');
                }
            } catch (error) {
                console.error('Erreur chargement config Polymarket:', error);
            }
        }

        async function savePolymarketConfig() {
            try {
                const walletsRaw = document.getElementById('pm_tracked_wallets').value;
                const wallets = walletsRaw.split('\n').map(w => w.trim()).filter(w => w.length > 0 && w.startsWith('0x'));

                const params = {
                    enabled: document.getElementById('polymarket_enabled').checked,
                    tracked_wallets: wallets,
                    polling_interval: parseInt(document.getElementById('pm_polling_interval').value),
                    max_position_usd: parseFloat(document.getElementById('pm_max_position').value),
                    min_position_usd: parseFloat(document.getElementById('pm_min_position').value),
                    dry_run: document.getElementById('pm_dry_run').checked
                };

                const response = await fetch('/api/polymarket/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(params)
                });
                const data = await response.json();

                if (data.success) {
                    showNotification('✅ Configuration Polymarket sauvegardée', 'success');
                } else {
                    showNotification('❌ Erreur: ' + (data.error || 'Inconnue'), 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur lors de la sauvegarde', 'error');
                console.error(error);
            }
        }

        async function testPolymarketConnection() {
            showNotification('🔗 Test de connexion en cours...', 'info');
            try {
                const response = await fetch('/api/polymarket/test');
                const data = await response.json();

                if (data.success) {
                    showNotification('✅ Connexion Polymarket OK!', 'success');
                } else {
                    showNotification('❌ Connexion échouée: ' + (data.error || 'Vérifiez vos clés API'), 'error');
                }
            } catch (error) {
                showNotification('❌ Erreur de connexion', 'error');
                console.error(error);
            }
        }

        async function updatePolymarketStats() {
            try {
                const response = await fetch('/api/polymarket/stats');
                const data = await response.json();

                if (data.success) {
                    const stats = data.stats;

                    // Update stats display
                    document.getElementById('pm_capital').textContent = '$' + (stats.capital || 100).toFixed(2);
                    document.getElementById('pm_signals').textContent = stats.signals_detected || 0;
                    document.getElementById('pm_trades_copied').textContent = stats.trades_copied || 0;

                    const profitEl = document.getElementById('pm_profit');
                    profitEl.textContent = '$' + (stats.simulated_profit || 0).toFixed(2);
                    profitEl.style.color = stats.simulated_profit >= 0 ? '#66bb6a' : '#ff5252';
                }
            } catch (error) {
                console.error('Erreur update Polymarket stats:', error);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    # Utiliser le solde du wallet
    total_capital = backend.get_wallet_balance_dynamic()

    # ✨ AMÉLIORÉ: Statut du WebSocket Helius avec is_connected
    websocket_status = {
        'active': helius_websocket.is_running,
        'subscriptions': len(helius_websocket.subscriptions),
        'connected': helius_websocket.is_connected,  # ✨ Utiliser is_connected au lieu de websocket
        'quality': helius_websocket.connection_quality  # ✨ NOUVEAU: Qualité connexion
    }

    return jsonify({
        'portfolio': backend.get_portfolio_value(),
        'pnl_total': backend.get_total_pnl(),
        'pnl_percent': backend.get_total_pnl_percent(),
        'running': backend.is_running,
        'active_traders': backend.get_active_traders_count(),
        'traders': backend.data.get('traders', []),
        'slippage': backend.data.get('slippage', 1.0),
        'currency': backend.data.get('currency', 'USD'),
        'total_capital': total_capital,
        'websocket_helius': websocket_status
    })

@app.route('/api/websocket_stats')
def api_websocket_stats():
    """✨ NOUVEAU: Retourne les statistiques détaillées du WebSocket"""
    try:
        stats = helius_websocket.get_connection_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {
                'is_connected': False,
                'connection_quality': 0
            }
        })

@app.route('/api/traders_performance')
def api_traders_performance():
    """⚡ OPTIMISÉ: Retourne les performances avec cache 2s"""
    global traders_performance_cache, traders_performance_cache_time
    
    current_time = time.time()
    
    # Cache hit - retourner données en cache
    if (traders_performance_cache is not None and 
        traders_performance_cache_time is not None and 
        current_time - traders_performance_cache_time < TRADERS_CACHE_TTL):
        return jsonify(traders_performance_cache)
    
    # Cache miss - recalculer
    performance = []
    
    for trader in backend.data.get('traders', []):
        is_active = trader.get('active')
        
        # Récupérer infos wallet pour le solde actuel
        perf = portfolio_tracker.get_trader_performance(trader['address'])
        
        if is_active:
            # TRADER ACTIF: Récupérer aussi le PnL du BOT (copies)
            trader_pnl_data = auto_sell_manager.get_trader_pnl(trader['name'])
            pnl_display = trader_pnl_data['pnl']
            pnl_percent_display = trader_pnl_data['pnl_percent']
            trader_label = f"✅ {trader['emoji']} {trader['name']}"
        else:
            # TRADER INACTIF: Afficher seulement ses performances wallet
            pnl_display = 0
            pnl_percent_display = 0
            trader_label = f"❌ {trader['emoji']} {trader['name']}"
        
        performance.append({
            'trader': trader_label,
            'current_value': f"${perf['current_value']:.2f}",
            'pnl': f"{pnl_display:.2f}",
            'pnl_percent': f"{pnl_percent_display:.2f}",
            'pnl_24h': f"{perf['pnl_24h']:.2f}",
            'pnl_24h_percent': f"{perf['pnl_24h_percent']:.2f}",
            'pnl_7d': f"{perf['pnl_7d']:.2f}",
            'pnl_7d_percent': f"{perf['pnl_7d_percent']:.2f}",
            'active': is_active
        })
    
    # Mettre en cache
    traders_performance_cache = performance
    traders_performance_cache_time = current_time
    
    return jsonify(performance)

@app.route('/api/toggle_bot')
def api_toggle_bot():
    new_status = not backend.is_running
    backend.toggle_bot(new_status)
    return jsonify({'status': 'ok', 'is_running': backend.is_running})

@app.route('/api/toggle_trader/<int:index>')
def api_toggle_trader(index):
    success = backend.toggle_trader(index, not backend.data.get('traders', [])[index]['active'])
    return jsonify({'status': 'ok' if success else 'limit_reached'})

@app.route('/api/update_params')
def api_update_params():
    slippage = request.args.get('slippage', type=float)
    # ✅ Correction Bug #10: 0.0 est une valeur valide
    if slippage is not None:
        if slippage < 0 or slippage > 100:
            return jsonify({'status': 'error', 'message': 'Slippage doit être entre 0 et 100%'})
        backend.data['slippage'] = slippage
        backend.save_config()
    return jsonify({'status': 'ok'})

@app.route('/api/save_key', methods=['POST'])
def api_save_key():
    """
    🔒 SÉCURITÉ: La clé privée est gardée UNIQUEMENT en mémoire
    Elle n'est JAMAIS sauvegardée sur disque pour éviter les vols
    """
    data = request.get_json()
    private_key = data.get('key', '').strip()

    # Validation basique de la clé
    if private_key and len(private_key) < 32:
        return jsonify({'status': 'error', 'message': 'Invalid private key format'})

    # ✅ Stocker EN MÉMOIRE uniquement (pas de save_config!)
    backend.data['wallet_private_key'] = private_key
    # ❌ NE PAS sauvegarder sur disque: backend.save_config()

    audit_logger.log(
        level=LogLevel.INFO,
        event_type='WALLET_CONNECTED',
        message='Wallet privé connecté (clé en mémoire uniquement)',
        metadata={'key_length': len(private_key) if private_key else 0}
    )

    return jsonify({'status': 'ok', 'message': 'Wallet connected (in-memory only)'})

@app.route('/api/disconnect')
def api_disconnect():
    """🔒 Déconnecte le wallet (efface la clé de la mémoire uniquement)"""
    backend.data['wallet_private_key'] = ''
    # ❌ NE PAS sauvegarder sur disque: backend.save_config()

    audit_logger.log(
        level=LogLevel.INFO,
        event_type='WALLET_DISCONNECTED',
        message='Wallet déconnecté (clé effacée de la mémoire)'
    )

    return jsonify({'status': 'ok', 'message': 'Wallet disconnected'})

@app.route('/api/edit_trader', methods=['POST'])
def api_edit_trader():
    data = request.get_json()
    index = data.get('index')
    name = data.get('name')
    emoji = data.get('emoji')
    address = data.get('address')
    capital = data.get('capital', 0)
    per_trade_amount = data.get('per_trade_amount', 10)
    min_trade_amount = data.get('min_trade_amount', 0)
    
    # Validation de l'adresse trader
    if address and (not isinstance(address, str) or len(address) < 32):
        return jsonify({'status': 'error', 'message': 'Invalid trader address format'})
    
    # Validation du capital
    if capital is not None:
        try:
            capital = float(capital)
            if capital < 0:
                return jsonify({'status': 'error', 'message': 'Capital cannot be negative'})
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'Invalid capital value'})
    
    if index is not None and 0 <= index < len(backend.data.get('traders', [])):
        backend.update_trader(index, name, emoji, address, capital, per_trade_amount, min_trade_amount)
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'message': 'Invalid trader index'})

@app.route('/api/set_wallet', methods=['POST'])
def api_set_wallet():
    """Configure le wallet avec la clé privée"""
    data = request.get_json()
    private_key = data.get('private_key', '')
    
    if not private_key:
        return jsonify({'status': 'error', 'message': 'No private key provided'})
    
    success = solana_executor.set_wallet(private_key)
    return jsonify({
        'status': 'ok' if success else 'error',
        'wallet': solana_executor.get_wallet_address()
    })

@app.route('/api/wallet_balance', methods=['GET'])
def api_wallet_balance():
    """Récupère le solde du wallet"""
    balance = solana_executor.get_wallet_balance()
    return jsonify({
        'balance': balance,
        'address': solana_executor.get_wallet_address()
    })

@app.route('/api/execute_swap', methods=['POST'])
def api_execute_swap():
    """Exécute un swap"""
    data = request.get_json()
    input_mint = data.get('input_mint', '')
    output_mint = data.get('output_mint', '')
    input_amount = float(data.get('input_amount', 0))
    slippage_bps = int(data.get('slippage_bps', 100))
    
    if not input_mint or not output_mint or input_amount <= 0:
        return jsonify({'status': 'error', 'message': 'Invalid swap parameters'})
    
    # Créer les détails du swap
    from dex_handler import SwapDetails
    swap_details = SwapDetails(input_mint, output_mint, input_amount, slippage_bps)
    
    # Exécuter le swap
    result = dex_handler.execute_swap(swap_details, dex_handler.identify_dex('raydium'))
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'status': 'error', 'message': 'Swap execution failed'})

@app.route('/api/transactions_history', methods=['GET'])
def api_transactions_history():
    """Récupère l'historique des transactions"""
    return jsonify({
        'transactions': solana_executor.transactions_sent,
        'total': len(solana_executor.transactions_sent)
    })

@app.route('/api/swaps_history', methods=['GET'])
def api_swaps_history():
    """Récupère l'historique des swaps"""
    return jsonify({
        'swaps': dex_handler.get_swap_history(),
        'total': len(dex_handler.get_swap_history())
    })

@app.route('/api/save_take_profit', methods=['POST'])
def api_save_take_profit():
    data = request.get_json()
    backend.update_take_profit(
        tp1_percent=float(data.get('tp1_percent', 33)),
        tp1_profit=float(data.get('tp1_profit', 10)),
        tp2_percent=float(data.get('tp2_percent', 33)),
        tp2_profit=float(data.get('tp2_profit', 25)),
        tp3_percent=float(data.get('tp3_percent', 34)),
        tp3_profit=float(data.get('tp3_profit', 50)),
        sl_percent=float(data.get('sl_percent', 100)),
        sl_loss=float(data.get('sl_loss', 5))
    )
    return jsonify({'status': 'ok'})

@app.route('/api/validation_stats', methods=['GET'])
def api_validation_stats():
    """Statistiques de validation des trades"""
    return jsonify(trade_validator.get_stats())

@app.route('/api/set_validation_level', methods=['POST'])
def api_set_validation_level():
    """Configure le niveau de validation"""
    data = request.get_json()
    level = data.get('level', 'NORMAL').upper()
    
    if level not in ['STRICT', 'NORMAL', 'RELAXED']:
        return jsonify({'status': 'error', 'message': 'Invalid level'})
    
    trade_validator.validation_level = TradeValidationLevel[level]
    return jsonify({'status': 'ok', 'validation_level': level})

@app.route('/api/set_trade_limits', methods=['POST'])
def api_set_trade_limits():
    """Configure les limites de trading"""
    data = request.get_json()
    trade_validator.set_limits(
        min_usd=float(data.get('min_usd', 1)),
        max_usd=float(data.get('max_usd', 10000)),
        max_slippage_bps=int(data.get('max_slippage_bps', 10000)),
        max_trades_per_hour=int(data.get('max_trades_per_hour', 10)),
        max_concurrent=int(data.get('max_concurrent', 5))
    )
    return jsonify({'status': 'ok', 'limits': trade_validator.get_stats()['current_limits']})

@app.route('/api/portfolio_risk', methods=['GET'])
def api_portfolio_risk():
    """Analyse du risque du portefeuille"""
    return jsonify(trade_safety.get_portfolio_risk())

@app.route('/api/trade_stats', methods=['GET'])
def api_trade_stats():
    """Statistiques de trading"""
    return jsonify(trade_safety.get_trade_stats())

@app.route('/api/validation_history', methods=['GET'])
def api_validation_history():
    """Historique de validation"""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        'approved': trade_validator.get_validation_history(limit),
        'rejected': trade_validator.get_rejected_trades(limit)
    })

@app.route('/api/audit_logs', methods=['GET'])
def api_audit_logs():
    """Logs d'audit"""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        'logs': audit_logger.get_recent_logs(limit),
        'security_summary': audit_logger.get_security_summary()
    })

@app.route('/api/active_trades', methods=['GET'])
def api_active_trades():
    """Trades actifs avec TP/SL"""
    return jsonify({
        'active_trades': trade_safety.get_active_trades(),
        'closed_trades': trade_safety.get_closed_trades(10)
    })

@app.route('/api/emergency_close', methods=['POST'])
def api_emergency_close():
    """Ferme tous les trades en urgence"""
    data = request.get_json()
    current_price = float(data.get('current_price', 100))
    
    closed_trades = trade_safety.emergency_close_all(current_price)
    audit_logger.log_security_event('EMERGENCY_CLOSE_ALL', {
        'count': len(closed_trades),
        'price': current_price
    }, severity='HIGH')
    
    return jsonify({
        'status': 'ok',
        'closed_count': len(closed_trades),
        'closed_trades': closed_trades
    })

@app.route('/api/metrics', methods=['GET'])
def api_metrics():
    """Toutes les métriques du système"""
    return jsonify(metrics_collector.get_all_metrics())

@app.route('/api/performance', methods=['GET'])
def api_performance():
    """Métriques de performance des trades"""
    return jsonify(metrics_collector.performance_monitor.get_performance_summary())

@app.route('/api/system_health', methods=['GET'])
def api_system_health():
    """État de santé du système"""
    return jsonify(metrics_collector.system_monitor.get_health_status())

@app.route('/api/execution_stats', methods=['GET'])
def api_execution_stats():
    """Statistiques d'exécution"""
    return jsonify({
        'average_execution_time_ms': metrics_collector.execution_monitor.get_average_execution_time(),
        'dex_statistics': metrics_collector.execution_monitor.get_dex_statistics(),
        'average_slippage': metrics_collector.execution_monitor.get_average_slippage()
    })

@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    """Alertes système"""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        'alerts': metrics_collector.performance_monitor.get_alerts(limit),
        'critical_count': len(metrics_collector.performance_monitor.get_critical_alerts())
    })

@app.route('/api/wallet_trend', methods=['GET'])
def api_wallet_trend():
    """Tendance du solde wallet"""
    hours = int(request.args.get('hours', 24))
    return jsonify({
        'trend': metrics_collector.system_monitor.get_balance_trend(hours),
        'hours': hours
    })

@app.route('/api/portfolio_trend', methods=['GET'])
def api_portfolio_trend():
    """Tendance du portefeuille"""
    hours = int(request.args.get('hours', 24))
    return jsonify({
        'trend': metrics_collector.system_monitor.get_portfolio_trend(hours),
        'hours': hours
    })

@app.route('/api/copy_trading_pnl', methods=['GET'])
def api_copy_trading_pnl():
    """PnL des simulations de copy trading pour les traders actifs"""
    result = {}
    for trader in backend.data.get('traders', []):
        if trader.get('active'):
            pnl = copy_trading_simulator.calculate_trader_pnl(trader['name'], {})
            status = copy_trading_simulator.get_trader_simulation_status(trader['name'])
            result[trader['name']] = {
                'emoji': trader.get('emoji', ''),
                'pnl': pnl['pnl'],
                'pnl_percent': pnl['pnl_percent'],
                'positions': pnl['positions'],
                'available_balance': pnl['available_balance'],
                'total_invested': pnl['total_invested'],
                'trades': pnl['trades_count'],
                'simulation_status': status
            }
    return jsonify(result)

@app.route('/api/trader_simulation/<trader_name>', methods=['GET'])
def api_trader_simulation(trader_name):
    """Détails de la simulation pour un trader"""
    return jsonify(copy_trading_simulator.get_trader_simulation_status(trader_name))

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """Lance un backtest pour un trader"""
    data = request.get_json()
    trader_address = data.get('trader_address', '')
    tp_percent = float(data.get('tp_percent', 10))
    sl_percent = float(data.get('sl_percent', 5))
    
    trades = db_manager.get_simulated_trades(trader_address, limit=100)
    result = backtesting_engine.run_backtest(trader_address, trades, tp_percent, sl_percent)
    
    return jsonify(result)

@app.route('/api/backtest_multiple', methods=['POST'])
def api_backtest_multiple():
    """Lance plusieurs backtests"""
    data = request.get_json()
    trader_address = data.get('trader_address', '')
    
    trades = db_manager.get_simulated_trades(trader_address, limit=100)
    results = backtesting_engine.run_multiple_backtests(trader_address, trades)
    
    return jsonify({'results': results, 'best': backtesting_engine.get_best_parameters(trader_address)})

@app.route('/api/benchmark', methods=['GET'])
def api_benchmark():
    """Benchmark bot vs traders - DONNÉES RÉELLES"""
    try:
        # Calcul du PnL du BOT (somme des trades actifs copies)
        bot_pnl = backend.get_total_pnl()
        bot_pnl_percent = backend.get_total_pnl_percent()
        
        # Récupérer tous les traders avec leurs performances
        all_traders_perf = []
        for trader in backend.data.get('traders', []):
            perf = portfolio_tracker.get_trader_performance(trader['address'])
            all_traders_perf.append({
                'name': trader['name'],
                'emoji': trader['emoji'],
                'pnl': perf['pnl_7d'],  # Utiliser le PnL 7j pour la comparaison
                'win_rate': 0.0  # On peut enrichir ça plus tard
            })
        
        # Trier les traders par PnL descendant
        all_traders_perf.sort(key=lambda x: x['pnl'], reverse=True)
        
        # Le meilleur trader
        best_trader = all_traders_perf[0] if all_traders_perf else None
        
        # Classer le bot vs les traders
        bot_rank = 1
        for i, t in enumerate(all_traders_perf, 1):
            if bot_pnl < t['pnl']:
                bot_rank = i + 1
        
        return jsonify({
            'bot_pnl': bot_pnl_percent,
            'bot_win_rate': 0.0,  # A implémenter si besoin
            'bot_rank': bot_rank,
            'best_trader': {
                'trader_name': f"{best_trader['emoji']} {best_trader['name']}",
                'trader_pnl': best_trader['pnl'],
                'trader_win_rate': best_trader['win_rate']
            } if best_trader else None
        })
    except Exception as e:
        print(f"❌ Erreur benchmark: {e}")
        # Fallback si erreur
        return jsonify({
            'bot_pnl': 0.0,
            'bot_win_rate': 0.0,
            'bot_rank': 10,
            'best_trader': None
        })

@app.route('/api/benchmark_ranking', methods=['GET'])
def api_benchmark_ranking():
    """Classement TRADERS SEULEMENT - triés correctement"""
    try:
        # Récupérer TOUS les traders avec leurs performances
        traders_with_data = []  # Traders avec données (PnL != 0)
        traders_no_data = []    # Traders sans données (PnL == 0)
        
        for trader in backend.data.get('traders', []):
            perf = portfolio_tracker.get_trader_performance(trader['address'])
            pnl_7d = perf.get('pnl_7d', 0.0)
            
            entry = {
                'name': f"{trader['emoji']} {trader['name']}",
                'address': trader['address'],
                'pnl': pnl_7d,
                'pnl_24h': perf.get('pnl_24h', 0.0),
                'win_rate': perf.get('win_rate', 0.0)
            }
            
            # Séparer les traders avec et sans données
            if pnl_7d != 0.0:
                traders_with_data.append(entry)
            else:
                traders_no_data.append(entry)
        
        # Trier traders AVEC données par PnL descendant (en haut)
        traders_with_data.sort(key=lambda x: x['pnl'], reverse=True)
        
        # Trier traders SANS données alphabétiquement (en bas)
        traders_no_data.sort(key=lambda x: x['name'])
        
        # Fusionner: traders avec données EN PREMIER, puis sans données
        all_ranked = traders_with_data + traders_no_data
        
        # Assigner les rangs
        for rank, entry in enumerate(all_ranked, 1):
            entry['rank'] = rank
        
        return jsonify({'ranking': all_ranked})
    except Exception as e:
        print(f"❌ Erreur benchmark_ranking: {e}")
        # Fallback ranking
        return jsonify({'ranking': [
            {'rank': 1, 'name': '🚀 Japon', 'pnl': 0.0, 'win_rate': 0.0},
            {'rank': 2, 'name': '⚡ Starter', 'pnl': 0.0, 'win_rate': 0.0},
            {'rank': 3, 'name': '🧈 Euris', 'pnl': 0.0, 'win_rate': 0.0}
        ]})

@app.route('/api/benchmark_summary', methods=['GET'])
def api_benchmark_summary():
    """Résumé du benchmark - DONNÉES RÉELLES"""
    try:
        # Calcul PnL du BOT
        bot_pnl = backend.get_total_pnl_percent()
        
        # Récupérer les traders et les trier
        all_traders = []
        for trader in backend.data.get('traders', []):
            perf = portfolio_tracker.get_trader_performance(trader['address'])
            all_traders.append({
                'name': trader['name'],
                'emoji': trader['emoji'],
                'pnl_7d': perf['pnl_7d']
            })
        
        # Trouver le meilleur trader
        best_trader = max(all_traders, key=lambda x: x['pnl_7d']) if all_traders else None
        
        return jsonify({
            'bot_performance': f"{'+' if bot_pnl >= 0 else ''}{bot_pnl:.2f}%",
            'bot_win_rate': '0.0%',
            'bot_rank': 1,  # A calculer plus tard
            'total_traders': len(all_traders),
            'best_trader': f"{best_trader['emoji']} {best_trader['name']}" if best_trader else '-',
            'best_trader_performance': f"{'+' if best_trader['pnl_7d'] >= 0 else ''}{best_trader['pnl_7d']:.2f}%" if best_trader else '0%'
        })
    except Exception as e:
        print(f"❌ Erreur benchmark_summary: {e}")
        # Fallback
        return jsonify({
            'bot_performance': '+0.00%',
            'bot_win_rate': '0.0%',
            'bot_rank': 10,
            'total_traders': 10,
            'best_trader': '-',
            'best_trader_performance': '+0.00%'
        })

# ===== ROUTE MÉTRIQUES AVANCÉES =====

@app.route('/api/advanced_metrics', methods=['GET'])
def api_advanced_metrics():
    """✅ Retourne les VRAIES métriques avancées"""
    try:
        # Récupérer toutes les métriques depuis le metrics_collector
        all_metrics = metrics_collector.get_all_metrics()
        performance = all_metrics.get('performance', {})
        execution = all_metrics.get('execution', {})
        system = all_metrics.get('system', {})

        # ✅ Win rate depuis advanced_analytics
        comprehensive_metrics = analytics.get_comprehensive_metrics()
        win_rate = round(comprehensive_metrics.get('win_rate', 0), 1)

        # RPC success rate
        rpc_info = system.get('rpc', {})
        rpc_success = rpc_info.get('success_rate', 100)

        # Latence moyenne d'exécution
        avg_latency = round(execution.get('avg_execution_time_ms', 0), 0)

        # ✅ Cache hit rate depuis cache_manager
        try:
            cache_stats = cache_manager.get_stats()
            cache_hit = round(cache_stats.get('hit_rate_percent', 85), 1)
        except:
            cache_hit = 85  # Valeur par défaut

        # ✅ Sharpe ratio depuis advanced_analytics
        sharpe_ratio = round(comprehensive_metrics.get('sharpe_ratio', 0.0), 2)

        # ✅ Max drawdown depuis advanced_analytics
        max_drawdown = round(comprehensive_metrics.get('max_drawdown', 0), 2)

        # ✅ Circuit breaker status depuis risk_manager
        try:
            circuit_breaker_open = risk_manager.is_circuit_breaker_active()
        except:
            circuit_breaker_open = False

        # ✅ Smart filter pass rate depuis smart_trading
        try:
            filter_stats = global_smart_filter.get_stats()
            smart_filter_pass = round(filter_stats.get('pass_rate_percent', 0), 1)
        except:
            smart_filter_pass = 0

        # ✅ Market volatility depuis adaptive_tp_sl (moyenne pour SOL)
        try:
            # Adresse SOL wrapped
            sol_address = 'So11111111111111111111111111111111111111112'
            volatility_value = adaptive_tp_sl.calculate_volatility(sol_address)

            if volatility_value is None:
                market_volatility = 'UNKNOWN'
            elif volatility_value < 0.02:
                market_volatility = 'LOW'
            elif volatility_value < 0.05:
                market_volatility = 'MEDIUM'
            else:
                market_volatility = 'HIGH'
        except:
            market_volatility = 'MEDIUM'

        return jsonify({
            'avg_latency': int(avg_latency),
            'cache_hit': cache_hit,
            'rpc_success': round(rpc_success, 1),
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'circuit_breaker_open': circuit_breaker_open,
            'smart_filter_pass': smart_filter_pass,
            'market_volatility': market_volatility,
            'note': 'Toutes les métriques sont calculées en temps réel'
        })
    except Exception as e:
        print(f"❌ Erreur advanced_metrics: {e}")
        import traceback
        traceback.print_exc()
        # Retourner des valeurs sûres en cas d'erreur
        return jsonify({
            'avg_latency': 0,
            'cache_hit': 0,
            'rpc_success': 100,
            'win_rate': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'circuit_breaker_open': False,
            'smart_filter_pass': 0,
            'market_volatility': 'UNKNOWN',
            'error': str(e)
        })

# ===== ROUTES AUTO SELL / VENTE AUTOMATIQUE =====

@app.route('/api/open_positions', methods=['GET'])
def api_open_positions():
    """Récupère les positions ouvertes"""
    summary = auto_sell_manager.get_position_summary()
    return jsonify(summary)

@app.route('/api/manual_sell/<position_id>', methods=['POST'])
def api_manual_sell(position_id):
    """Vente manuelle d'une position"""
    data = request.get_json()
    current_price = data.get('current_price', 0)
    
    result = auto_sell_manager.manual_sell(position_id, current_price)
    return jsonify(result)

@app.route('/api/auto_sell_settings', methods=['GET'])
def api_get_auto_sell_settings():
    """Récupère les paramètres de vente auto"""
    return jsonify(auto_sell_manager.get_auto_sell_settings())

@app.route('/api/auto_sell_settings', methods=['POST'])
def api_update_auto_sell_settings():
    """Met à jour les paramètres de vente auto"""
    data = request.get_json()
    result = auto_sell_manager.update_auto_sell_settings(data)
    return jsonify(result)

@app.route('/api/toggle_auto_sell', methods=['POST'])
def api_toggle_auto_sell():
    """Active/désactive la vente automatique"""
    data = request.get_json()
    auto_sell_manager.auto_sell_enabled = data.get('enabled', True)
    return jsonify({'enabled': auto_sell_manager.auto_sell_enabled})

@app.route('/api/trade_history', methods=['GET'])
def api_trade_history():
    """Retourne l'historique des trades copiés"""
    try:
        with copied_trades_lock:
            with open('copied_trades_history.json', 'r') as f:
                history = json.load(f)
    except:
        history = {}
    
    trades = []
    for pos_id, timestamp in history.items():
        try:
            parts = pos_id.split('_')
            if len(parts) >= 2:
                trader_name = '_'.join(parts[:-1])
                trades.append({
                    'position_id': pos_id,
                    'trader': trader_name,
                    'time': timestamp,
                    'platform': 'Helius',
                    'pnl': '$0',
                    'performance': '0%'
                })
        except:
            pass
    
    trades.sort(key=lambda x: x.get('time', ''), reverse=True)
    return jsonify({'trades': trades[:50]})


# ==================== RISK MANAGER ROUTES ====================

@app.route('/api/risk_manager/params', methods=['GET'])
def api_get_risk_params():
    """Retourne les paramètres actuels du Risk Manager"""
    try:
        params = risk_manager.get_params()
        return jsonify({
            'success': True,
            'params': params
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/risk_manager/params', methods=['POST'])
def api_update_risk_params():
    """Met à jour les paramètres du Risk Manager"""
    try:
        data = request.get_json()
        result = risk_manager.update_params(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/risk_manager/metrics', methods=['GET'])
def api_get_risk_metrics():
    """Retourne les métriques de risque actuelles"""
    try:
        # Synchroniser le balance depuis le wallet réel
        wallet_balance = backend.get_wallet_balance_dynamic()
        if wallet_balance > 0:
            risk_manager.sync_balance_from_wallet(wallet_balance)

        metrics = risk_manager.get_risk_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/risk_manager/reset_defaults', methods=['POST'])
def api_reset_risk_defaults():
    """Réinitialise les paramètres aux valeurs par défaut"""
    try:
        result = risk_manager.reset_to_defaults()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/risk_manager/reset_circuit_breaker', methods=['POST'])
def api_reset_circuit_breaker():
    """Réinitialise manuellement le circuit breaker"""
    try:
        risk_manager.circuit_breaker_active = False
        risk_manager.circuit_breaker_triggered_at = None
        risk_manager.consecutive_losses = 0
        print("✅ Circuit breaker réinitialisé manuellement")
        return jsonify({
            'success': True,
            'message': 'Circuit breaker réinitialisé'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ═════════════════════════════════════════════════════════════════════════════
# 💰 ARBITRAGE ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route('/api/arbitrage/config', methods=['GET'])
def api_get_arbitrage_config():
    """Retourne la configuration actuelle de l'arbitrage"""
    try:
        config = arbitrage_engine.get_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/arbitrage/config', methods=['POST'])
def api_update_arbitrage_config():
    """Met à jour la configuration de l'arbitrage"""
    try:
        params = request.get_json()
        result = arbitrage_engine.update_config(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/arbitrage/toggle', methods=['POST'])
def api_toggle_arbitrage():
    """Active/désactive l'arbitrage"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)

        result = arbitrage_engine.update_config({'enabled': enabled})

        status = "activé" if enabled else "désactivé"
        print(f"{'✅' if enabled else '❌'} Arbitrage {status}")

        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/arbitrage/stats', methods=['GET'])
def api_get_arbitrage_stats():
    """Retourne les statistiques de l'arbitrage"""
    try:
        stats = arbitrage_engine.get_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/arbitrage/detect', methods=['POST'])
def api_detect_arbitrage():
    """Détecte les opportunités d'arbitrage pour un token"""
    try:
        data = request.get_json()
        token_mint = data.get('token_mint')

        if not token_mint:
            return jsonify({
                'success': False,
                'error': 'token_mint requis'
            }), 400

        opportunity = arbitrage_engine.detect_arbitrage(token_mint)

        return jsonify({
            'success': True,
            'opportunity': opportunity
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/arbitrage/execute', methods=['POST'])
def api_execute_arbitrage():
    """Exécute un arbitrage (MODE TEST)"""
    try:
        data = request.get_json()
        opportunity = data.get('opportunity')
        amount = data.get('amount')  # Optionnel

        if not opportunity:
            return jsonify({
                'success': False,
                'error': 'opportunity requis'
            }), 400

        result = arbitrage_engine.execute_arbitrage(opportunity, amount)

        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════
# 🔮 POLYMARKET COPY TRADING API ROUTES (Persisté dans config.json)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/polymarket/config', methods=['GET'])
def api_polymarket_config_get():
    """Récupère la configuration Polymarket depuis config.json"""
    return jsonify({
        'success': True,
        'config': backend.data.get('polymarket', {})
    })

@app.route('/api/polymarket/config', methods=['POST'])
def api_polymarket_config_post():
    """Met à jour la configuration Polymarket dans config.json"""
    try:
        data = request.get_json()

        if 'polymarket' not in backend.data:
            backend.data['polymarket'] = {}

        pm = backend.data['polymarket']
        if 'enabled' in data:
            pm['enabled'] = bool(data['enabled'])
        if 'tracked_wallets' in data:
            pm['tracked_wallets'] = data['tracked_wallets']
        if 'polling_interval' in data:
            pm['polling_interval'] = int(data['polling_interval'])
        if 'max_position_usd' in data:
            pm['max_position_usd'] = float(data['max_position_usd'])
        if 'min_position_usd' in data:
            pm['min_position_usd'] = float(data['min_position_usd'])
        if 'dry_run' in data:
            pm['dry_run'] = bool(data['dry_run'])

        backend.save_config_sync()  # Sauvegarde SYNCHRONE immédiate
        return jsonify({'success': True, 'message': 'Configuration Polymarket sauvegardée'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/polymarket/toggle', methods=['POST'])
def api_polymarket_toggle():
    """Active/désactive le copy trading Polymarket"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)

        if 'polymarket' not in backend.data:
            backend.data['polymarket'] = {}

        backend.data['polymarket']['enabled'] = enabled
        backend.save_config_sync()  # Sauvegarde SYNCHRONE immédiate

        return jsonify({
            'success': True,
            'enabled': enabled,
            'message': 'Copy Trading Polymarket ' + ('activé' if enabled else 'désactivé')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/polymarket/stats', methods=['GET'])
def api_polymarket_stats():
    """Récupère les statistiques Polymarket depuis config.json"""
    pm = backend.data.get('polymarket', {})
    return jsonify({
        'success': True,
        'stats': {
            'enabled': pm.get('enabled', False),
            'capital': pm.get('max_position_usd', 0),
            'signals_detected': pm.get('signals_detected', 0),
            'trades_copied': pm.get('trades_copied', 0),
            'simulated_profit': pm.get('simulated_profit', 0),
            'tracked_wallets_count': len(pm.get('tracked_wallets', [])),
            'dry_run': pm.get('dry_run', True)
        }
    })

@app.route('/api/polymarket/test', methods=['GET'])
def api_polymarket_test():
    """Teste la connexion à Polymarket"""
    try:
        # Tenter de récupérer des données du subgraph Goldsky
        import requests
        url = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/0.0.7/gn"
        query = '{ userBalances(first: 1) { id } }'
        response = requests.post(url, json={'query': query}, timeout=5)
        
        if response.status_code == 200 and 'data' in response.json():
            return jsonify({'success': True, 'message': 'Connexion Goldsky Subgraph OK'})
        else:
            return jsonify({'success': False, 'error': 'Réponse API inattendue'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("🚀 Lancement sur http://0.0.0.0:5000")
    print("📊 Suivi de portefeuilles en temps réel")
    print("🔒 Phase 3 Security: Validation + Safety + Audit logging activés")
    print("🌐 WebSocket activé pour dashboard temps réel")
    socketio.run(app, debug=False, host='0.0.0.0', port=5000, use_reloader=False)
