#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot du Millionnaire - Polymarket Copy Trading + Solana Arbitrage
================================================================
Bot de copy trading sur Polymarket avec arbitrage Solana.
"""

import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request

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
from arbitrage_engine import ArbitrageEngine
from db_manager import db_manager
from audit_logger import audit_logger

# Imports Polymarket (avec fallback)
try:
    from polymarket_tracking import PolymarketTracker
    from polymarket_executor import PolymarketExecutor
    polymarket_tracker = PolymarketTracker()
    polymarket_executor = PolymarketExecutor()
except ImportError as e:
    print(f"⚠️ Modules Polymarket non disponibles: {e}")
    polymarket_tracker = None
    polymarket_executor = None

# ============================================================================
# INITIALISATION
# ============================================================================

app = Flask(__name__)
backend = BotBackend()
arbitrage_engine = ArbitrageEngine()

# Historique des trades Polymarket
polymarket_trades_history = []
polymarket_positions = []

print("=" * 60)
print("🎯 BOT DU MILLIONNAIRE - POLYMARKET COPY TRADING")
print("=" * 60)
print(f"✅ Configuration chargée")
print(f"📊 Polymarket: {'Activé' if backend.data.get('polymarket', {}).get('enabled') else 'Désactivé'}")
print(f"⚡ Arbitrage: {'Activé' if backend.data.get('arbitrage', {}).get('enabled') else 'Désactivé'}")
print("=" * 60)

# ============================================================================
# TEMPLATE HTML - INTERFACE COMPLÈTE
# ============================================================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot du Millionnaire - Polymarket Copy Trading</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3a 100%);
            color: #fff;
            min-height: 100vh;
        }

        /* HEADER */
        .header {
            background: rgba(0,0,0,0.3);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .header h1 {
            font-size: 24px;
            background: linear-gradient(90deg, #00E676, #00B0FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-status {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .status-on { background: rgba(0, 230, 118, 0.2); color: #00E676; border: 1px solid #00E676; }
        .status-off { background: rgba(255, 82, 82, 0.2); color: #FF5252; border: 1px solid #FF5252; }

        /* NAVIGATION */
        .nav-tabs {
            display: flex;
            background: rgba(0,0,0,0.2);
            padding: 10px 30px;
            gap: 10px;
            flex-wrap: wrap;
        }
        .nav-tab {
            padding: 12px 24px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #aaa;
            cursor: pointer;
            transition: all 0.3s;
        }
        .nav-tab:hover { background: rgba(255,255,255,0.1); color: #fff; }
        .nav-tab.active {
            background: linear-gradient(135deg, #00E676, #00B0FF);
            color: #000;
            font-weight: bold;
            border: none;
        }

        /* CONTAINER */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }

        /* TAB CONTENT */
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* CARDS */
        .card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .card h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #00E676;
        }

        /* STATS GRID */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .stat-card h3 { color: #888; font-size: 14px; margin-bottom: 10px; }
        .stat-card .value { font-size: 28px; font-weight: bold; color: #00E676; }
        .stat-card .value.negative { color: #FF5252; }

        /* BUTTONS */
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #00E676, #00B0FF);
            color: #000;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0,230,118,0.3); }
        .btn-danger { background: #FF5252; color: #fff; }
        .btn-secondary { background: rgba(255,255,255,0.1); color: #fff; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* FORMS */
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #aaa; }
        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #00E676;
        }

        /* TABLES */
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th { color: #888; font-weight: normal; }

        /* WALLET LIST */
        .wallet-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .wallet-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 8px;
        }
        .wallet-item .address {
            font-family: monospace;
            color: #00B0FF;
        }

        /* TOGGLE SWITCH */
        .toggle-switch {
            position: relative;
            width: 60px;
            height: 30px;
        }
        .toggle-switch input { display: none; }
        .toggle-slider {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(255,255,255,0.1);
            border-radius: 30px;
            cursor: pointer;
            transition: 0.3s;
        }
        .toggle-slider:before {
            content: '';
            position: absolute;
            width: 24px;
            height: 24px;
            left: 3px;
            bottom: 3px;
            background: #fff;
            border-radius: 50%;
            transition: 0.3s;
        }
        input:checked + .toggle-slider { background: #00E676; }
        input:checked + .toggle-slider:before { transform: translateX(30px); }

        /* TWO COLUMNS */
        .two-columns {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }
        @media (max-width: 900px) {
            .two-columns { grid-template-columns: 1fr; }
        }

        /* FLEX UTILITIES */
        .flex { display: flex; }
        .flex-between { justify-content: space-between; }
        .flex-center { align-items: center; }
        .gap-10 { gap: 10px; }
        .gap-20 { gap: 20px; }
    </style>
</head>
<body>
    <!-- HEADER -->
    <div class="header">
        <h1>🎯 Bot du Millionnaire</h1>
        <div class="header-status">
            <span id="bot-status" class="status-badge status-off">BOT DÉSACTIVÉ</span>
            <button id="toggle-bot-btn" class="btn btn-primary" onclick="toggleBot()">Activer le Bot</button>
        </div>
    </div>

    <!-- NAVIGATION -->
    <div class="nav-tabs">
        <div class="nav-tab active" onclick="showTab('dashboard')">📊 Dashboard</div>
        <div class="nav-tab" onclick="showTab('live')">🔴 Live Trading</div>
        <div class="nav-tab" onclick="showTab('wallets')">👛 Wallets Suivis</div>
        <div class="nav-tab" onclick="showTab('history')">📜 Historique</div>
        <div class="nav-tab" onclick="showTab('arbitrage')">⚡ Arbitrage</div>
        <div class="nav-tab" onclick="showTab('settings')">⚙️ Paramètres</div>
    </div>

    <div class="container">
        <!-- ============ DASHBOARD ============ -->
        <div id="tab-dashboard" class="tab-content active">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>📡 Signaux Détectés</h3>
                    <div class="value" id="signals-count">0</div>
                </div>
                <div class="stat-card">
                    <h3>📈 Trades Copiés</h3>
                    <div class="value" id="trades-copied">0</div>
                </div>
                <div class="stat-card">
                    <h3>💰 Profit Total</h3>
                    <div class="value" id="total-profit">$0.00</div>
                </div>
                <div class="stat-card">
                    <h3>🎯 Win Rate</h3>
                    <div class="value" id="win-rate">0%</div>
                </div>
            </div>

            <div class="two-columns">
                <div class="card">
                    <h2>📊 Polymarket Copy Trading</h2>
                    <div class="flex flex-between flex-center" style="margin-bottom: 15px;">
                        <span>Status</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="polymarket-toggle" onchange="togglePolymarket()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="flex flex-between flex-center" style="margin-bottom: 15px;">
                        <span>Mode Dry Run (Simulation)</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="dryrun-toggle" onchange="toggleDryRun()" checked>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <p style="color: #888; font-size: 12px;">
                        Dry Run = Simulation sans exécution réelle des trades
                    </p>
                </div>

                <div class="card">
                    <h2>⚡ Arbitrage Solana</h2>
                    <div class="flex flex-between flex-center" style="margin-bottom: 15px;">
                        <span>Status</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="arbitrage-toggle" onchange="toggleArbitrage()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div id="arbitrage-stats">
                        <p>Opportunités: <span id="arb-opportunities">0</span></p>
                        <p>Profit Arbitrage: <span id="arb-profit">$0.00</span></p>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>📈 Positions Actives</h2>
                <div id="active-positions">
                    <p style="color: #888; text-align: center; padding: 20px;">Aucune position active</p>
                </div>
            </div>
        </div>

        <!-- ============ LIVE TRADING ============ -->
        <div id="tab-live" class="tab-content">
            <div class="card">
                <h2>🔴 Trading en Temps Réel</h2>
                <div id="live-feed" style="max-height: 500px; overflow-y: auto;">
                    <p style="color: #888; text-align: center; padding: 20px;">
                        En attente de signaux...
                    </p>
                </div>
            </div>

            <div class="card">
                <h2>📊 Derniers Trades Copiés</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Marché</th>
                            <th>Position</th>
                            <th>Montant</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="recent-trades">
                        <tr><td colspan="5" style="text-align: center; color: #888;">Aucun trade récent</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ============ WALLETS SUIVIS ============ -->
        <div id="tab-wallets" class="tab-content">
            <div class="card">
                <h2>👛 Ajouter un Wallet à Suivre</h2>
                <div class="form-group">
                    <label>Adresse du Wallet Polymarket</label>
                    <input type="text" id="new-wallet-address" placeholder="0x...">
                </div>
                <div class="form-group">
                    <label>Nom (optionnel)</label>
                    <input type="text" id="new-wallet-name" placeholder="Whale #1">
                </div>
                <button class="btn btn-primary" onclick="addWallet()">+ Ajouter Wallet</button>
            </div>

            <div class="card">
                <h2>📋 Wallets Suivis</h2>
                <div id="wallets-list" class="wallet-list">
                    <p style="color: #888; text-align: center; padding: 20px;">Aucun wallet suivi</p>
                </div>
            </div>

            <div class="card">
                <h2>🏆 Benchmark des Wallets</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rang</th>
                            <th>Wallet</th>
                            <th>Win Rate</th>
                            <th>PnL</th>
                            <th>Trades</th>
                        </tr>
                    </thead>
                    <tbody id="benchmark-table">
                        <tr><td colspan="5" style="text-align: center; color: #888;">Pas de données</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ============ HISTORIQUE ============ -->
        <div id="tab-history" class="tab-content">
            <div class="card">
                <h2>📜 Historique des Trades</h2>
                <div class="flex gap-10" style="margin-bottom: 15px;">
                    <button class="btn btn-secondary" onclick="filterHistory('all')">Tous</button>
                    <button class="btn btn-secondary" onclick="filterHistory('won')">Gagnés</button>
                    <button class="btn btn-secondary" onclick="filterHistory('lost')">Perdus</button>
                    <button class="btn btn-secondary" onclick="filterHistory('pending')">En cours</button>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Marché</th>
                            <th>Position</th>
                            <th>Prix Entrée</th>
                            <th>Prix Sortie</th>
                            <th>PnL</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="history-table">
                        <tr><td colspan="7" style="text-align: center; color: #888;">Aucun historique</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ============ ARBITRAGE ============ -->
        <div id="tab-arbitrage" class="tab-content">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>🔍 Opportunités Détectées</h3>
                    <div class="value" id="arb-opp-count">0</div>
                </div>
                <div class="stat-card">
                    <h3>✅ Arbitrages Exécutés</h3>
                    <div class="value" id="arb-executed">0</div>
                </div>
                <div class="stat-card">
                    <h3>💰 Profit Arbitrage</h3>
                    <div class="value" id="arb-total-profit">$0.00</div>
                </div>
                <div class="stat-card">
                    <h3>📊 ROI Moyen</h3>
                    <div class="value" id="arb-avg-roi">0%</div>
                </div>
            </div>

            <div class="card">
                <h2>⚡ Opportunités en Cours</h2>
                <div id="arb-opportunities-list">
                    <p style="color: #888; text-align: center; padding: 20px;">
                        Recherche d'opportunités...
                    </p>
                </div>
            </div>

            <div class="card">
                <h2>📜 Historique Arbitrage</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Token</th>
                            <th>Achat (DEX)</th>
                            <th>Vente (DEX)</th>
                            <th>Profit</th>
                        </tr>
                    </thead>
                    <tbody id="arb-history">
                        <tr><td colspan="5" style="text-align: center; color: #888;">Aucun arbitrage</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ============ PARAMÈTRES ============ -->
        <div id="tab-settings" class="tab-content">
            <div class="two-columns">
                <!-- WALLET POLYMARKET -->
                <div class="card">
                    <h2>👛 Wallet Polymarket (Polygon)</h2>
                    <div class="form-group">
                        <label>Adresse du Wallet</label>
                        <input type="text" id="pm-wallet-address" placeholder="0x...">
                    </div>
                    <div class="form-group">
                        <label>Clé Privée</label>
                        <input type="password" id="pm-wallet-key" placeholder="Clé privée (stockée en mémoire uniquement)">
                    </div>
                    <button class="btn btn-primary" onclick="savePolymarketWallet()">Sauvegarder</button>
                    <p style="color: #888; font-size: 11px; margin-top: 10px;">
                        ⚠️ La clé privée n'est jamais sauvegardée sur disque
                    </p>
                </div>

                <!-- WALLET SOLANA -->
                <div class="card">
                    <h2>⚡ Wallet Solana (Arbitrage)</h2>
                    <div class="form-group">
                        <label>Adresse du Wallet</label>
                        <input type="text" id="sol-wallet-address" placeholder="Adresse Solana...">
                    </div>
                    <div class="form-group">
                        <label>Clé Privée</label>
                        <input type="password" id="sol-wallet-key" placeholder="Clé privée (stockée en mémoire uniquement)">
                    </div>
                    <div class="form-group">
                        <label>RPC URL</label>
                        <input type="text" id="sol-rpc-url" value="https://api.mainnet-beta.solana.com">
                    </div>
                    <button class="btn btn-primary" onclick="saveSolanaWallet()">Sauvegarder</button>
                </div>
            </div>

            <div class="two-columns">
                <!-- CONFIG POLYMARKET -->
                <div class="card">
                    <h2>📊 Configuration Polymarket</h2>
                    <div class="form-group">
                        <label>Intervalle de Polling (secondes)</label>
                        <input type="number" id="pm-polling" value="30" min="10">
                    </div>
                    <div class="form-group">
                        <label>Position Maximum ($)</label>
                        <input type="number" id="pm-max-position" value="0" min="0">
                    </div>
                    <div class="form-group">
                        <label>Position Minimum ($)</label>
                        <input type="number" id="pm-min-position" value="0" min="0">
                    </div>
                    <div class="form-group">
                        <label>Pourcentage à copier (%)</label>
                        <input type="number" id="pm-copy-percent" value="100" min="1" max="100">
                    </div>
                    <button class="btn btn-primary" onclick="savePolymarketConfig()">Sauvegarder Config</button>
                </div>

                <!-- CONFIG ARBITRAGE -->
                <div class="card">
                    <h2>⚡ Configuration Arbitrage</h2>
                    <div class="form-group">
                        <label>Capital Dédié ($)</label>
                        <input type="number" id="arb-capital" value="0" min="0">
                    </div>
                    <div class="form-group">
                        <label>% par Trade</label>
                        <input type="number" id="arb-percent" value="0" min="0" max="100">
                    </div>
                    <div class="form-group">
                        <label>Profit Minimum (%)</label>
                        <input type="number" id="arb-min-profit" value="0.5" min="0" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>Cooldown (secondes)</label>
                        <input type="number" id="arb-cooldown" value="60" min="10">
                    </div>
                    <button class="btn btn-primary" onclick="saveArbitrageConfig()">Sauvegarder Config</button>
                </div>
            </div>

            <div class="card">
                <h2>🔧 Actions</h2>
                <div class="flex gap-10">
                    <button class="btn btn-secondary" onclick="exportData()">📤 Exporter Données</button>
                    <button class="btn btn-danger" onclick="resetStats()">🗑️ Reset Statistiques</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // ============ NAVIGATION ============
        function showTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            event.target.classList.add('active');
        }

        // ============ BOT CONTROL ============
        function toggleBot() {
            fetch('/api/toggle_bot', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    updateBotStatus(data.is_running);
                })
                .catch(e => console.error('Erreur toggle bot:', e));
        }

        function updateBotStatus(running) {
            const badge = document.getElementById('bot-status');
            const btn = document.getElementById('toggle-bot-btn');
            if (running) {
                badge.textContent = 'BOT ACTIVÉ';
                badge.className = 'status-badge status-on';
                btn.textContent = 'Désactiver le Bot';
            } else {
                badge.textContent = 'BOT DÉSACTIVÉ';
                badge.className = 'status-badge status-off';
                btn.textContent = 'Activer le Bot';
            }
        }

        // ============ TOGGLES ============
        function togglePolymarket() {
            const enabled = document.getElementById('polymarket-toggle').checked;
            fetch('/api/polymarket/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            }).then(r => r.json()).then(data => {
                console.log('Polymarket:', data);
            });
        }

        function toggleDryRun() {
            const dryRun = document.getElementById('dryrun-toggle').checked;
            fetch('/api/polymarket/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dry_run: dryRun })
            });
        }

        function toggleArbitrage() {
            const enabled = document.getElementById('arbitrage-toggle').checked;
            fetch('/api/arbitrage/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
        }

        // ============ WALLETS ============
        function addWallet() {
            const address = document.getElementById('new-wallet-address').value;
            const name = document.getElementById('new-wallet-name').value || 'Wallet';
            if (!address) return alert('Adresse requise');

            fetch('/api/wallets/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address, name })
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    document.getElementById('new-wallet-address').value = '';
                    document.getElementById('new-wallet-name').value = '';
                    loadWallets();
                } else {
                    alert(data.error || 'Erreur');
                }
            });
        }

        function removeWallet(address) {
            if (!confirm('Supprimer ce wallet ?')) return;
            fetch('/api/wallets/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address })
            }).then(() => loadWallets());
        }

        function loadWallets() {
            fetch('/api/wallets').then(r => r.json()).then(data => {
                const container = document.getElementById('wallets-list');
                if (!data.wallets || data.wallets.length === 0) {
                    container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">Aucun wallet suivi</p>';
                    return;
                }
                container.innerHTML = data.wallets.map(w => `
                    <div class="wallet-item">
                        <div>
                            <strong>${w.name || 'Wallet'}</strong><br>
                            <span class="address">${w.address.slice(0,10)}...${w.address.slice(-8)}</span>
                        </div>
                        <button class="btn btn-danger" onclick="removeWallet('${w.address}')">✕</button>
                    </div>
                `).join('');
            });
        }

        // ============ SAVE CONFIGS ============
        function savePolymarketWallet() {
            const address = document.getElementById('pm-wallet-address').value;
            const key = document.getElementById('pm-wallet-key').value;
            fetch('/api/wallet/polymarket', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address, private_key: key })
            }).then(r => r.json()).then(data => {
                alert(data.success ? 'Wallet Polymarket sauvegardé' : 'Erreur');
            });
        }

        function saveSolanaWallet() {
            const address = document.getElementById('sol-wallet-address').value;
            const key = document.getElementById('sol-wallet-key').value;
            const rpc = document.getElementById('sol-rpc-url').value;
            fetch('/api/wallet/solana', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address, private_key: key, rpc_url: rpc })
            }).then(r => r.json()).then(data => {
                alert(data.success ? 'Wallet Solana sauvegardé' : 'Erreur');
            });
        }

        function savePolymarketConfig() {
            fetch('/api/polymarket/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    polling_interval: parseInt(document.getElementById('pm-polling').value),
                    max_position_usd: parseFloat(document.getElementById('pm-max-position').value),
                    min_position_usd: parseFloat(document.getElementById('pm-min-position').value),
                    copy_percentage: parseInt(document.getElementById('pm-copy-percent').value)
                })
            }).then(r => r.json()).then(data => {
                alert(data.success ? 'Configuration sauvegardée' : 'Erreur');
            });
        }

        function saveArbitrageConfig() {
            fetch('/api/arbitrage/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    capital_dedicated: parseFloat(document.getElementById('arb-capital').value),
                    percent_per_trade: parseFloat(document.getElementById('arb-percent').value),
                    min_profit_threshold: parseFloat(document.getElementById('arb-min-profit').value),
                    cooldown_seconds: parseInt(document.getElementById('arb-cooldown').value)
                })
            }).then(r => r.json()).then(data => {
                alert(data.success ? 'Configuration sauvegardée' : 'Erreur');
            });
        }

        // ============ UTILITIES ============
        function filterHistory(filter) {
            console.log('Filter:', filter);
        }

        function exportData() {
            window.open('/api/export', '_blank');
        }

        function resetStats() {
            if (!confirm('Êtes-vous sûr de vouloir reset toutes les statistiques ?')) return;
            fetch('/api/reset_stats', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        alert('Statistiques réinitialisées');
                        updateUI();
                    }
                });
        }

        // ============ UPDATE UI ============
        function updateUI() {
            fetch('/api/status').then(r => r.json()).then(data => {
                try {
                    // Bot status
                    updateBotStatus(data.is_running);

                    // Polymarket stats
                    const pm = data.polymarket || {};
                    document.getElementById('signals-count').textContent = pm.signals_detected || 0;
                    document.getElementById('trades-copied').textContent = pm.trades_copied || 0;
                    const profit = pm.total_profit || 0;
                    const profitEl = document.getElementById('total-profit');
                    profitEl.textContent = (profit >= 0 ? '+' : '') + '$' + profit.toFixed(2);
                    profitEl.className = 'value' + (profit < 0 ? ' negative' : '');
                    document.getElementById('win-rate').textContent = (pm.win_rate || 0) + '%';

                    // Toggles
                    document.getElementById('polymarket-toggle').checked = pm.enabled || false;
                    document.getElementById('dryrun-toggle').checked = pm.dry_run !== false;

                    // Arbitrage
                    const arb = data.arbitrage || {};
                    document.getElementById('arbitrage-toggle').checked = arb.enabled || false;

                    // Config values
                    document.getElementById('pm-polling').value = pm.polling_interval || 30;
                    document.getElementById('pm-max-position').value = pm.max_position_usd || 0;
                    document.getElementById('pm-min-position').value = pm.min_position_usd || 0;
                    document.getElementById('pm-copy-percent').value = pm.copy_percentage || 100;

                    document.getElementById('arb-capital').value = arb.capital_dedicated || 0;
                    document.getElementById('arb-percent').value = arb.percent_per_trade || 0;
                    document.getElementById('arb-min-profit').value = arb.min_profit_threshold || 0.5;
                    document.getElementById('arb-cooldown').value = arb.cooldown_seconds || 60;

                    // Wallet addresses
                    if (data.polymarket_wallet) {
                        document.getElementById('pm-wallet-address').value = data.polymarket_wallet.address || '';
                    }
                    if (data.solana_wallet) {
                        document.getElementById('sol-wallet-address').value = data.solana_wallet.address || '';
                        document.getElementById('sol-rpc-url').value = data.solana_wallet.rpc_url || 'https://api.mainnet-beta.solana.com';
                    }
                } catch (e) {
                    console.error('Erreur updateUI:', e);
                }
            }).catch(e => console.error('Erreur fetch status:', e));

            // Load wallets
            loadWallets();
        }

        // ============ INIT ============
        setInterval(updateUI, 5000);
        updateUI();
    </script>
</body>
</html>
'''

# ============================================================================
# ROUTES API
# ============================================================================

@app.route('/')
def index():
    """Page principale"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    """Status complet du bot"""
    return jsonify({
        'is_running': backend.is_running,
        'polymarket': backend.data.get('polymarket', {}),
        'arbitrage': backend.data.get('arbitrage', {}),
        'polymarket_wallet': {
            'address': backend.data.get('polymarket_wallet', {}).get('address', '')
        },
        'solana_wallet': {
            'address': backend.data.get('solana_wallet', {}).get('address', ''),
            'rpc_url': backend.data.get('solana_wallet', {}).get('rpc_url', '')
        }
    })

@app.route('/api/toggle_bot', methods=['POST'])
def api_toggle_bot():
    """Activer/désactiver le bot"""
    backend.toggle_bot(not backend.is_running)
    return jsonify({
        'success': True,
        'is_running': backend.is_running
    })

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
        if 'dry_run' in data:
            pm['dry_run'] = bool(data['dry_run'])

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

@app.route('/api/wallet/polymarket', methods=['POST'])
def api_wallet_polymarket():
    """Configurer le wallet Polymarket"""
    try:
        data = request.get_json()

        backend.data['polymarket_wallet'] = {
            'address': data.get('address', ''),
            'private_key': ''  # Ne pas sauvegarder la clé privée sur disque
        }
        backend.save_config_sync()

        # Stocker la clé en mémoire uniquement
        if data.get('private_key') and polymarket_executor:
            polymarket_executor.set_wallet(data['private_key'])

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wallet/solana', methods=['POST'])
def api_wallet_solana():
    """Configurer le wallet Solana pour l'arbitrage"""
    try:
        data = request.get_json()

        backend.data['solana_wallet'] = {
            'address': data.get('address', ''),
            'private_key': '',  # Ne pas sauvegarder
            'rpc_url': data.get('rpc_url', 'https://api.mainnet-beta.solana.com')
        }
        backend.save_config_sync()

        # Stocker la clé en mémoire
        if data.get('private_key'):
            arbitrage_engine.set_wallet(data['private_key'])

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# ARBITRAGE ROUTES
# ============================================================================

@app.route('/api/arbitrage/toggle', methods=['POST'])
def api_arbitrage_toggle():
    """Active/désactive l'arbitrage"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)

        if 'arbitrage' not in backend.data:
            backend.data['arbitrage'] = {}

        backend.data['arbitrage']['enabled'] = enabled
        backend.save_config_sync()

        return jsonify({
            'success': True,
            'enabled': enabled
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/arbitrage/config', methods=['GET', 'POST'])
def api_arbitrage_config():
    """Get/Set configuration arbitrage"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'config': backend.data.get('arbitrage', {})
        })

    try:
        data = request.get_json()
        arb = backend.data.get('arbitrage', {})

        if 'capital_dedicated' in data:
            arb['capital_dedicated'] = float(data['capital_dedicated'])
        if 'percent_per_trade' in data:
            arb['percent_per_trade'] = float(data['percent_per_trade'])
        if 'min_profit_threshold' in data:
            arb['min_profit_threshold'] = float(data['min_profit_threshold'])
        if 'cooldown_seconds' in data:
            arb['cooldown_seconds'] = int(data['cooldown_seconds'])

        backend.data['arbitrage'] = arb
        backend.save_config_sync()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/arbitrage/stats')
def api_arbitrage_stats():
    """Statistiques arbitrage"""
    stats = arbitrage_engine.get_stats()
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/api/arbitrage/opportunities')
def api_arbitrage_opportunities():
    """Opportunités d'arbitrage en cours"""
    opportunities = arbitrage_engine.get_opportunities()
    return jsonify({
        'success': True,
        'opportunities': opportunities
    })

# ============================================================================
# HISTORY & EXPORT
# ============================================================================

@app.route('/api/history')
def api_history():
    """Historique des trades"""
    return jsonify({
        'success': True,
        'trades': polymarket_trades_history
    })

@app.route('/api/positions')
def api_positions():
    """Positions actives"""
    return jsonify({
        'success': True,
        'positions': polymarket_positions
    })

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
    data = {
        'config': backend.data,
        'history': polymarket_trades_history,
        'positions': polymarket_positions,
        'exported_at': datetime.now().isoformat()
    }
    return jsonify(data)

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

        polymarket_trades_history.clear()
        polymarket_positions.clear()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🚀 Bot démarré sur http://localhost:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
