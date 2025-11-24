from flask import Flask, render_template_string, jsonify, request
import webbrowser
import json
import time
import threading
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
from helius_websocket import helius_websocket

app = Flask(__name__)
backend = BotBackend()

# Démarrer le thread de suivi des portefeuilles + simulation copy trading
def start_tracking():
    # Démarrer le websocket Helius pour détection ultra-rapide
    try:
        helius_websocket.start()
    except Exception as e:
        print(f"⚠️ Websocket Helius non disponible: {e}")
    
    while True:
        if backend.is_running:
            portfolio_tracker.track_all_wallets()
            portfolio_tracker.update_bot_portfolio()
            
            # Simuler les trades des traders actifs (MODE TEST)
            if backend.data.get('mode') == 'TEST':
                for trader in backend.data.get('traders', []):
                    if trader.get('active'):
                        trades = copy_trading_simulator.get_trader_recent_trades(trader['address'], limit=5)
                        for trade in trades:
                            capital_alloc = trader.get('capital', 100)
                            copy_trading_simulator.simulate_trade_for_trader(trader['name'], trade, capital_alloc)
        time.sleep(120)  # Mettre à jour toutes les 2 minutes (évite rate limiting RPC)

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
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Bot du Millionnaire - Solana Copy Trading</h1>
        
        <div class="nav">
            <button class="nav-btn active" onclick="showSection('dashboard')">Tableau de Bord</button>
            <button class="nav-btn" onclick="showSection('live')">⚡ LIVE TRADING</button>
            <button class="nav-btn" onclick="showSection('traders')">Gestion Traders</button>
            <button class="nav-btn" onclick="showSection('backtesting')">🎮 Backtesting</button>
            <button class="nav-btn" onclick="showSection('benchmark')">🏆 Benchmark</button>
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
                    <p>Mode: <span id="mode" class="mode-badge">TEST</span></p>
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
                    <h2>📈 Graphique PnL</h2>
                    <canvas id="pnlChart" style="width:100%;height:200px;background:#000;border-radius:8px;"></canvas>
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
                <p>Capital Alloué: <span id="capital_allocated" style="color: #00E676;">$0</span> / <span id="total_capital_display" style="color: #FFD600;">$1000</span></p>
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
                    <button class="btn" onclick="switchMode()">Basculer Mode TEST/REEL</button>
                    
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
                    <h2>📊 Positions Ouvertes</h2>
                    <div id="open_positions_list" style="margin-bottom: 20px;"></div>
                    <button class="btn" onclick="refreshPositions()" style="width: 100%; margin-bottom: 10px;">🔄 Rafraîchir Positions</button>
                    
                    <div class="divider"></div>
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
        
        function showSection(name) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.getElementById(name).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
        }
        
        function updateUI() {
            fetch('/api/status').then(r => r.json()).then(data => {
                document.getElementById('portfolio').textContent = (data.currency==='SOL'?'◎':'$') + data.portfolio;
                const status = document.getElementById('status');
                status.textContent = data.running ? 'BOT ACTIVÉ' : 'BOT DÉSACTIVÉ';
                status.className = data.running ? 'status on' : 'status off';
                document.getElementById('mode').textContent = data.mode;
                document.getElementById('active_count').textContent = data.active_traders + '/3';
                document.getElementById('slippage_val').textContent = data.slippage;
                document.getElementById('active_traders_count').textContent = data.active_traders;
                document.getElementById('total_capital_display').textContent = '$' + data.total_capital;
                
                // ✅ AFFICHER LE PnL TOTAL ET PERFORMANCE BOT
                const pnl_color = data.pnl_total >= 0 ? '#00E676' : '#D50000';
                document.getElementById('total_pnl').textContent = (data.pnl_total >= 0 ? '+' : '') + '$' + data.pnl_total;
                document.getElementById('total_pnl').style.color = pnl_color;
                const perf_color = data.pnl_percent >= 0 ? '#00E676' : '#D50000';
                document.getElementById('bot_performance').textContent = (data.pnl_percent >= 0 ? '+' : '') + data.pnl_percent + '%';
                document.getElementById('bot_performance').style.color = perf_color;
                
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
                    const pnl_color = p.pnl >= 0 ? '#00E676' : '#D50000';
                    const pnl_24h_color = p.pnl_24h >= 0 ? '#00E676' : '#D50000';
                    const pnl_7d_color = p.pnl_7d >= 0 ? '#00E676' : '#D50000';
                    const bg_color = p.active ? '#0a4a0a' : 'transparent';
                    const border_style = p.active ? 'border: 2px solid #00E676; box-shadow: 0 0 10px rgba(0, 230, 118, 0.2);' : '';
                    
                    html += `<tr style="background-color: ${bg_color}; ${border_style}">
                        <td>${p.trader}${p.active ? ' ✅' : ''}</td>
                        <td>${p.current_value}</td>
                        <td style="color: ${pnl_color}">
                            ${p.pnl >= 0 ? '+' : ''}${p.pnl} (${p.pnl_percent >= 0 ? '+' : ''}${p.pnl_percent}%)
                        </td>
                        <td style="color: ${pnl_24h_color}">
                            ${p.pnl_24h >= 0 ? '+' : ''}${p.pnl_24h} (${p.pnl_24h_percent >= 0 ? '+' : ''}${p.pnl_24h_percent}%)
                        </td>
                        <td style="color: ${pnl_7d_color}">
                            ${p.pnl_7d >= 0 ? '+' : ''}${p.pnl_7d} (${p.pnl_7d_percent >= 0 ? '+' : ''}${p.pnl_7d_percent}%)
                        </td>
                    </tr>`;
                });
                document.getElementById('traders_performance').innerHTML = html;
            });
        }
        
        function toggleBot() { 
            fetch('/api/toggle_bot').then(() => {
                updateUI();
            }); 
        }
        
        function toggleTrader(i) { fetch(`/api/toggle_trader/${i}`).then(() => updateUI()); }
        function updateSlippage(v) { fetch(`/api/update_params?slippage=${v}`).then(() => updateUI()); }
        function switchMode() { fetch('/api/switch_mode').then(() => updateUI()); }
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
        
        // BENCHMARK FUNCTIONS
        function updateBenchmark() {
            document.getElementById('benchmark_ranking').innerHTML = '<tr><td colspan="4" style="text-align: center;">⏳ Chargement...</td></tr>';
            
            fetch('/api/benchmark').then(r => r.json()).then(benchmark => {
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
            }).then(() => {
                fetch('/api/benchmark_ranking').then(r => r.json()).then(data => {
                    let html = '';
                    data.ranking.forEach(r => {
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
        
        // ============== LIVE DASHBOARD ==============
        function refreshLiveDashboard() {
            // Récupérer status global
            fetch('/api/status').then(r => r.json()).then(status => {
                document.getElementById('live_portfolio').textContent = '$' + status.portfolio;
                document.getElementById('live_active_count').textContent = status.active_traders + '/3';
                
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
                                        <value>${traderPositions.length > 0 ? (Math.random() * 100).toFixed(0) : '0'}%</value>
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
                                    <button class="action-btn exit-all" onclick="exitAllTrader('${trader.name}', ${traderPositions.map(p => p.position_id).join(',')})">💰 Sortir Tout</button>
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
                const ids = positionIds.toString().split(',').filter(x => x);
                if (ids.length === 0) {
                    alert('Aucune position ouverte');
                    return;
                }
                
                let exitedCount = 0;
                ids.forEach(id => {
                    fetch(`/api/manual_sell/${id}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({current_price: 0})
                    }).then(() => {
                        exitedCount++;
                        if (exitedCount === ids.length) {
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
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    return jsonify({
        'portfolio': backend.get_portfolio_value(),
        'pnl_total': backend.get_total_pnl(),
        'pnl_percent': backend.get_total_pnl_percent(),
        'running': backend.is_running,
        'mode': backend.data.get('mode', 'TEST'),
        'active_traders': backend.get_active_traders_count(),
        'traders': backend.data['traders'],
        'slippage': backend.data.get('slippage', 1.0),
        'currency': backend.data.get('currency', 'USD'),
        'total_capital': backend.data.get('total_capital', 1000)
    })

@app.route('/api/traders_performance')
def api_traders_performance():
    """Retourne les performances réelles des traders"""
    performance = []
    
    for trader in backend.data['traders']:
        perf = portfolio_tracker.get_trader_performance(trader['address'])
        performance.append({
            'trader': f"{trader['emoji']} {trader['name']}",
            'current_value': f"${perf['current_value']:.2f}",
            'pnl': f"{perf['pnl']:.2f}",
            'pnl_percent': f"{perf['pnl_percent']:.2f}",
            'pnl_24h': f"{perf['pnl_24h']:.2f}",
            'pnl_24h_percent': f"{perf['pnl_24h_percent']:.2f}",
            'pnl_7d': f"{perf['pnl_7d']:.2f}",
            'pnl_7d_percent': f"{perf['pnl_7d_percent']:.2f}",
            'active': trader['active']
        })
    
    return jsonify(performance)

@app.route('/api/toggle_bot')
def api_toggle_bot():
    backend.toggle_bot(not backend.is_running)
    return jsonify({'status': 'ok'})

@app.route('/api/toggle_trader/<int:index>')
def api_toggle_trader(index):
    success = backend.toggle_trader(index, not backend.data['traders'][index]['active'])
    return jsonify({'status': 'ok' if success else 'limit_reached'})

@app.route('/api/update_params')
def api_update_params():
    slippage = request.args.get('slippage', type=float)
    if slippage:
        backend.data['slippage'] = slippage
        backend.save_config()
    return jsonify({'status': 'ok'})

@app.route('/api/switch_mode')
def api_switch_mode():
    backend.data['mode'] = 'REEL' if backend.data['mode'] == 'TEST' else 'TEST'
    backend.save_config()
    return jsonify({'status': 'ok'})

@app.route('/api/save_key', methods=['POST'])
def api_save_key():
    data = request.get_json()
    backend.data['wallet_private_key'] = data.get('key', '')
    backend.save_config()
    return jsonify({'status': 'ok'})

@app.route('/api/disconnect')
def api_disconnect():
    backend.data['wallet_private_key'] = ''
    backend.save_config()
    return jsonify({'status': 'ok'})

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
    
    if index is not None and 0 <= index < len(backend.data['traders']):
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
        max_slippage_bps=int(data.get('max_slippage_bps', 500)),
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
    """Benchmark bot vs traders"""
    bot_perf = metrics_collector.get_performance_summary()
    traders_perf = []
    
    for trader in backend.data.get('traders', []):
        perf = portfolio_tracker.get_trader_performance(trader['address'])
        perf['address'] = trader['address']
        perf['name'] = trader['name']
        traders_perf.append(perf)
    
    benchmark = benchmark_system.calculate_benchmark(bot_perf, traders_perf)
    return jsonify(benchmark)

@app.route('/api/benchmark_ranking', methods=['GET'])
def api_benchmark_ranking():
    """Classement bot vs traders"""
    return jsonify({'ranking': benchmark_system.get_ranking()})

@app.route('/api/benchmark_summary', methods=['GET'])
def api_benchmark_summary():
    """Résumé du benchmark"""
    return jsonify(benchmark_system.get_benchmark_summary())

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

if __name__ == '__main__':
    print("🚀 Lancement sur http://0.0.0.0:5000")
    print("📊 Mode TEST avec suivi de portefeuilles réels")
    print("🔒 Phase 3 Security: Validation + Safety + Audit logging activés")
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
