from flask import Flask, render_template_string, jsonify, request
import webbrowser
import json
import time
import threading
from bot_logic import BotBackend
from portfolio_tracker import portfolio_tracker

app = Flask(__name__)
backend = BotBackend()

# Démarrer le thread de suivi des portefeuilles
def start_tracking():
    while True:
        if backend.is_running:
            portfolio_tracker.track_all_wallets()
            portfolio_tracker.update_bot_portfolio()
        time.sleep(30)  # Mettre à jour toutes les 30 secondes

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
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Bot du Millionnaire - Solana Copy Trading</h1>
        
        <div class="nav">
            <button class="nav-btn active" onclick="showSection('dashboard')">Tableau de Bord</button>
            <button class="nav-btn" onclick="showSection('traders')">Gestion Traders</button>
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
                <div id="traders_list"></div>
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
        <div style="background:#1a1a1a;margin:100px auto;padding:30px;width:500px;border-radius:12px;">
            <h3 style="color:#64B5F6;margin-bottom:20px;">Éditer Trader</h3>
            <input type="text" id="edit_name" placeholder="Nom" style="width:100%;padding:10px;margin:10px 0;">
            <input type="text" id="edit_emoji" placeholder="Emoji" style="width:100%;padding:10px;margin:10px 0;">
            <input type="text" id="edit_address" placeholder="Adresse Solana" style="width:100%;padding:10px;margin:10px 0;">
            <button class="btn" onclick="saveTraderEdit()">Sauvegarder</button>
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
                
                // Mettre à jour les performances des traders
                updateTradersPerformance();
                
                let html = '';
                data.traders.forEach((t,i) => {
                    const disabled = data.active_traders >= 3 && !t.active;
                    const activeClass = t.active ? 'active' : '';
                    html += `<div class="trader-item ${activeClass}">
                        <span>${t.emoji} ${t.name} (${t.address.slice(0,8)}...)</span>
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
                document.getElementById('editModal').style.display = 'block';
            });
        }
        
        function saveTraderEdit() {
            const name = document.getElementById('edit_name').value;
            const emoji = document.getElementById('edit_emoji').value;
            const address = document.getElementById('edit_address').value;
            
            fetch('/api/edit_trader', {
                method: 'POST',
                body: JSON.stringify({index: editingTraderIndex, name, emoji, address}),
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
        
        setInterval(updateUI, 1000);
        updateUI();
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
        'running': backend.is_running,
        'mode': backend.data.get('mode', 'TEST'),
        'active_traders': backend.get_active_traders_count(),
        'traders': backend.data['traders'],
        'slippage': backend.data.get('slippage', 1.0),
        'currency': backend.data.get('currency', 'USD')
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
    
    if index is not None and 0 <= index < len(backend.data['traders']):
        backend.update_trader(index, name, emoji, address)
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'})

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

if __name__ == '__main__':
    print("🚀 Lancement sur http://0.0.0.0:5000")
    print("📊 Mode TEST avec suivi de portefeuilles réels")
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
