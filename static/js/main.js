// ============ NAVIGATION ============
function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    // Find the correct tab button assuming the event was triggered by onclick
    // If called programmatically, we might need a better way to highlight the tab
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        if (tab.textContent.includes(tabId === 'dashboard' ? 'Dashboard' :
            tabId === 'live' ? 'Flux' :
                tabId === 'wallets' ? 'Wallets' :
                    tabId === 'history' ? 'Historique' :

                        tabId === 'settings' ? 'Paramètres' : '')) {
            tab.classList.add('active');
        }
    });
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



// ============ WALLET CONFIG MODAL ============
function openWalletConfigModal(address) {
    // 1. Récupération depuis le store global
    const w = window.walletsData && window.walletsData[address];

    if (!w) {
        console.error('❌ ERREUR: Données wallet introuvables pour', address);
        console.log('Store actuel:', window.walletsData);
        alert("Erreur interne: Impossible de charger les données du wallet. Rechargez la page.");
        return;
    }

    // 2. Remplissage du formulaire
    document.getElementById('modal-wallet-address').value = w.address;

    const safeName = w.name || 'Wallet'; // Pas d'encodage nécessaire ici, c'est du texte DOM
    const shortAddress = w.address.slice(0, 10) + '...';
    document.getElementById('modal-wallet-name').textContent = `${safeName} - ${shortAddress}`;

    document.getElementById('modal-capital').value = w.capital_allocated || 0;
    document.getElementById('modal-percent').value = w.percent_per_trade || 0;
    document.getElementById('modal-sl').value = (w.sl_percent === null || w.sl_percent === undefined) ? '' : w.sl_percent;
    document.getElementById('modal-tp').value = (w.tp_percent === null || w.tp_percent === undefined) ? '' : w.tp_percent;
    document.getElementById('modal-use-kelly').checked = w.use_kelly || false;
    document.getElementById('modal-use-trailing').checked = w.use_trailing || false;

    // 3. Affichage
    document.getElementById('wallet-config-modal').classList.add('active');
}

function closeWalletConfigModal() {
    document.getElementById('wallet-config-modal').classList.remove('active');
}

// ... (skip lines)

function loadWallets() {
    fetch('/api/wallets').then(r => r.json()).then(data => {
        const container = document.getElementById('wallets-list');
        if (!data.wallets || data.wallets.length === 0) {
            container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">Aucun wallet suivi</p>';
            return;
        }

        // ✨ INITIALISATION DU STORE GLOBAL
        // C'est la clé pour éviter les problèmes de guillemets dans les attributs HTML
        window.walletsData = {};
        data.wallets.forEach(w => {
            window.walletsData[w.address] = w;
        });

        container.innerHTML = data.wallets.map(w => {
            const capital = w.capital_allocated || 0;
            const percent = w.percent_per_trade || 0;
            const sl = w.sl_percent;
            const tp = w.tp_percent;
            const useKelly = w.use_kelly || false;
            const useTrailing = w.use_trailing || false;
            const isActive = w.active !== false;

            // Config Summary
            let configParts = [];
            if (capital > 0) configParts.push(`Capital: <span>$${capital}</span>`);
            if (percent > 0) configParts.push(`Par trade: <span>${percent}%</span>`);
            if (sl !== null && sl !== undefined) configParts.push(`SL: <span style="color: #FF5252;">${sl}%</span>`);
            if (tp !== null && tp !== undefined) configParts.push(`TP: <span style="color: #00E676;">${tp}%</span>`);
            if (useKelly) configParts.push(`<span class="status-badge" style="background: #9C27B0; color: white;">🧠 Kelly</span>`);
            if (useTrailing) configParts.push(`<span class="status-badge" style="background: #FF9800; color: white;">🛡️ Trailing</span>`);

            const configInfo = configParts.length > 0
                ? `<div class="wallet-config-info">${configParts.join(' | ')}</div>`
                : `<div class="wallet-config-info">Non configuré</div>`;

            // Status Badge
            const statusBadge = isActive
                ? '<span class="status-badge status-on" style="font-size: 10px; padding: 2px 8px; margin-left: 8px;">ACTIF</span>'
                : '<span class="status-badge status-off" style="font-size: 10px; padding: 2px 8px; margin-left: 8px;">INACTIF</span>';

            // GENERATION DU BOUTON SÉCURISÉ
            // On ne passe plus que l'adresse (chaîne simple sans espaces ni guillemets bizarres)
            return `
            <div class="wallet-item" style="opacity: ${isActive ? '1' : '0.6'};">
                <div style="flex: 1;">
                    <div>
                        <strong>${w.name || 'Wallet'}</strong>
                        ${statusBadge}
                    </div>
                    <span class="address">${w.address.slice(0, 10)}...${w.address.slice(-8)}</span>
                    ${configInfo}
                </div>
                <div class="flex flex-center gap-10">
                    <label class="toggle-switch" style="transform: scale(0.8);">
                        <input type="checkbox" ${isActive ? 'checked' : ''} onchange="toggleWalletActive('${w.address}', ${isActive})">
                        <span class="toggle-slider"></span>
                    </label>
                    <button class="btn-config" onclick="openWalletConfigModal('${w.address}')">⚙️</button>
                    <button class="btn btn-danger" onclick="removeWallet('${w.address}')">✕</button>
                </div>
            </div>
        `}).join('');
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

            // Config values
            document.getElementById('pm-polling').value = pm.polling_interval || 30;
            document.getElementById('pm-max-position').value = pm.max_position_usd || 0;
            document.getElementById('pm-min-position').value = pm.min_position_usd || 0;
            document.getElementById('pm-copy-percent').value = pm.copy_percentage || 100;


            // Wallet addresses
            if (data.polymarket_wallet) {
                document.getElementById('pm-wallet-address').value = data.polymarket_wallet.address || '';
                // Afficher adresse sur dashboard
                const pmAddr = data.polymarket_wallet.address;
                if (pmAddr) {
                    document.getElementById('pm-wallet-addr').textContent = pmAddr.slice(0, 10) + '...' + pmAddr.slice(-8);
                } else {
                    document.getElementById('pm-wallet-addr').textContent = 'Non configuré';
                }
            }

        } catch (e) {
            console.error('Erreur updateUI:', e);
        }
    }).catch(e => console.error('Erreur fetch status:', e));

    // Load wallets
    loadWallets();

    // Load positions
    loadPositions();

    // Load balances
    loadBalances();
}

// ============ LOAD BALANCES ============
function loadBalances() {
    fetch('/api/balances').then(r => r.json()).then(data => {
        if (data.success) {
            // Polymarket (Polygon) balances
            const pm = data.polymarket || {};
            document.getElementById('pm-balance-usdc').textContent = '$' + (pm.usdc || 0).toFixed(2);
            document.getElementById('pm-balance-matic').textContent = (pm.matic || 0).toFixed(4) + ' MATIC';

            // Solana balances REMOVED
        }
    }).catch(e => console.error('Erreur chargement balances:', e));
}

// ============ INIT ============
// Initialisation WebSocket
const socket = io();

socket.on('connect', () => {
    console.log('✅ Connecté au WebSocket!');
    // On pourrait ajouter un indicateur visuel ici
});

socket.on('disconnect', () => {
    console.log('❌ Déconnecté du WebSocket');
});

// Écouter les mises à jour de position
socket.on('position_update', (data) => {
    console.log('🔄 Mise à jour position reçue:', data);
    // TODO: Mettre à jour l'UI spécifiquement
    loadPositions(); // Pour l'instant on recharge tout
});

// Écouter les nouveaux signaux
socket.on('new_signal', (data) => {
    console.log('🚨 Nouveau signal:', data);
    // Notification simple
    alert(`Nouveau signal détecté: ${data.market || 'Inconnu'}`);
});

// ============ CHART ============
let pnlChart = null;

function loadPnLChart() {
    const ctx = document.getElementById('pnlChart');
    if (!ctx) return;

    fetch('/api/stats/pnl_history?days=30')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            if (pnlChart) {
                pnlChart.destroy();
            }

            pnlChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'PnL Cumulé ($)',
                        data: data.cumulative_values,
                        borderColor: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
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
                            mode: 'index',
                            intersect: false
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#aaa'
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.1)'
                            },
                            ticks: {
                                color: '#aaa',
                                callback: function (value) {
                                    return '$' + value;
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(e => console.error('Erreur chargement chart:', e));
}

document.addEventListener('DOMContentLoaded', function () {
    // Initial call to set active tab correctly (already active in HTML but good for safety)
    if (!document.querySelector('.tab-content.active')) {
        showTab('dashboard');
    }

    // Start polling
    setInterval(updateUI, 5000);
    updateUI();

    // Charger le graphique
    loadPnLChart();
});
