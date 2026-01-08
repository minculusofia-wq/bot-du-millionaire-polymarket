/**
 * insider.js - Insider Tracker Frontend Logic
 * Gere l'interface utilisateur pour la detection de wallets suspects sur Polymarket
 */

// ============ SCANNER CONTROL ============

function toggleInsiderScanner() {
    const enabled = document.getElementById('insider-scanner-toggle').checked;

    fetch('/api/insider/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateInsiderStatus(data.running);
                console.log('Scanner:', data.running ? 'Started' : 'Stopped');
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
                // Reset toggle
                document.getElementById('insider-scanner-toggle').checked = !enabled;
            }
        })
        .catch(e => {
            console.error('Toggle scanner error:', e);
            document.getElementById('insider-scanner-toggle').checked = !enabled;
        });
}

function updateInsiderStatus(running) {
    const statusEl = document.getElementById('insider-status');
    if (statusEl) {
        statusEl.textContent = running ? 'Running' : 'Stopped';
        statusEl.style.color = running ? '#00E676' : '#FF5252';
    }
}

function triggerManualScan() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Scanning...';

    fetch('/api/insider/scan_now', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert(`Scan termine: ${data.alerts_found} alerte(s) trouvee(s)`);
                loadInsiderAlerts();
                loadInsiderStats();
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        })
        .catch(e => {
            console.error('Manual scan error:', e);
            alert('Erreur de scan');
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Scan Manuel';
        });
}

// ============ CONFIGURATION ============

function onInsiderPresetChange() {
    const preset = document.getElementById('insider-preset').value;
    const customSection = document.getElementById('custom-weights-section');

    if (preset === 'custom') {
        customSection.style.display = 'block';
    } else {
        customSection.style.display = 'none';
    }
}

function toggleCategory(el) {
    el.classList.toggle('active');
}

function updateWeightDisplay() {
    const unlikely = parseInt(document.getElementById('weight-unlikely').value) || 0;
    const abnormal = parseInt(document.getElementById('weight-abnormal').value) || 0;
    const profile = parseInt(document.getElementById('weight-profile').value) || 0;

    document.getElementById('weight-unlikely-val').textContent = unlikely;
    document.getElementById('weight-abnormal-val').textContent = abnormal;
    document.getElementById('weight-profile-val').textContent = profile;
    document.getElementById('weights-total').textContent = unlikely + abnormal + profile;
}

function saveInsiderConfig() {
    // Collecter les categories actives
    const activeCategories = [];
    document.querySelectorAll('.category-toggle.active').forEach(el => {
        activeCategories.push(el.dataset.category);
    });

    // Collecter la config
    const config = {
        scoring_preset: document.getElementById('insider-preset').value,
        alert_threshold: parseInt(document.getElementById('insider-threshold').value) || 60,
        categories: activeCategories,

        // Seuils avances
        min_bet_amount: parseFloat(document.getElementById('insider-min-bet').value) || 1000,
        max_odds_threshold: parseFloat(document.getElementById('insider-max-odds').value) || 10,
        dormant_days: parseInt(document.getElementById('insider-dormant-days').value) || 30,
        dormant_min_bet: parseFloat(document.getElementById('insider-dormant-bet').value) || 500,
        max_tx_count: parseInt(document.getElementById('insider-max-tx').value) || 15,
        new_wallet_min_bet: parseFloat(document.getElementById('insider-new-bet').value) || 500
    };

    // Si mode custom, ajouter les poids
    if (config.scoring_preset === 'custom') {
        config.custom_weights = {
            unlikely_bet: parseInt(document.getElementById('weight-unlikely').value) || 35,
            abnormal_behavior: parseInt(document.getElementById('weight-abnormal').value) || 35,
            suspicious_profile: parseInt(document.getElementById('weight-profile').value) || 30
        };
    }

    fetch('/api/insider/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('Configuration sauvegardee!');
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        })
        .catch(e => {
            console.error('Save config error:', e);
            alert('Erreur de sauvegarde');
        });
}

// ============ LOAD DATA ============

function loadInsiderConfig() {
    fetch('/api/insider/config')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            const config = data.config;

            // Toggle scanner
            const toggle = document.getElementById('insider-scanner-toggle');
            if (toggle) toggle.checked = config.running;

            // Preset
            const preset = document.getElementById('insider-preset');
            if (preset) preset.value = config.scoring_preset || 'balanced';

            // Threshold
            const threshold = document.getElementById('insider-threshold');
            if (threshold) threshold.value = config.alert_threshold || 60;

            // Categories
            const categories = config.enabled_categories || config.categories || [];
            document.querySelectorAll('.category-toggle').forEach(el => {
                if (categories.includes(el.dataset.category)) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            });

            // Status
            updateInsiderStatus(config.running);

            // Custom weights section visibility
            onInsiderPresetChange();
        });
}

function loadInsiderStats() {
    fetch('/api/insider/stats')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            const stats = data.stats;

            const alertsCount = document.getElementById('insider-alerts-count');
            if (alertsCount) alertsCount.textContent = stats.alerts_generated || 0;

            const marketsCount = document.getElementById('insider-markets-count');
            if (marketsCount) marketsCount.textContent = stats.markets_scanned || 0;

            const lastScan = document.getElementById('insider-last-scan');
            if (lastScan) {
                lastScan.textContent = stats.last_scan
                    ? new Date(stats.last_scan).toLocaleTimeString()
                    : 'Never';
            }

            updateInsiderStatus(stats.running);
        });
}

function loadInsiderAlerts() {
    fetch('/api/insider/alerts?limit=50')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            renderAlertFeed(data.alerts);
        });
}

function renderAlertFeed(alerts) {
    const container = document.getElementById('insider-alert-feed');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <p style="color: #888; text-align: center; padding: 40px;">
                Aucune alerte detectee. Activez le scanner pour commencer.
            </p>
        `;
        return;
    }

    container.innerHTML = alerts.map(alert => {
        const scoreClass = alert.suspicion_score >= 80 ? 'high' :
            alert.suspicion_score >= 60 ? 'medium' : 'low';

        const criteriaHtml = (alert.criteria_matched || []).map(c =>
            `<span class="criteria-badge ${c}">${formatCriteria(c)}</span>`
        ).join('');

        const stats = alert.wallet_stats || {};
        const pnlClass = (stats.pnl || 0) >= 0 ? 'positive' : 'negative';

        return `
        <div class="insider-alert-card score-${scoreClass}">
            <div class="alert-header">
                <div class="alert-wallet">
                    ${alert.nickname ? `<span class="alert-nickname">${escapeHtml(alert.nickname)}</span>` : ''}
                    <span class="alert-wallet-address">${truncateAddress(alert.wallet_address)}</span>
                </div>
                <div class="suspicion-score ${scoreClass}">${alert.suspicion_score}</div>
            </div>

            <div class="alert-market">${escapeHtml(alert.market_question || 'Unknown Market')}</div>

            <div class="alert-bet-details">
                <div>
                    <label>Bet Amount</label>
                    <span class="value">$${(alert.bet_amount || 0).toFixed(2)}</span>
                </div>
                <div>
                    <label>Outcome</label>
                    <span class="value">${alert.bet_outcome || 'N/A'}</span>
                </div>
                <div>
                    <label>Odds</label>
                    <span class="value">${((alert.outcome_odds || 0) * 100).toFixed(1)}%</span>
                </div>
            </div>

            <div class="alert-criteria">${criteriaHtml}</div>

            <div class="alert-stats">
                <div>
                    <label>PnL</label>
                    <span class="${pnlClass}">$${(stats.pnl || 0).toFixed(2)}</span>
                </div>
                <div>
                    <label>Win Rate</label>
                    <span>${(stats.win_rate || 0).toFixed(1)}%</span>
                </div>
                <div>
                    <label>ROI</label>
                    <span>${(stats.roi || 0).toFixed(1)}%</span>
                </div>
                <div>
                    <label>Trades</label>
                    <span>${stats.total_trades || 0}</span>
                </div>
            </div>

            <div class="alert-actions">
                <button class="btn btn-secondary btn-sm" onclick="followInsiderWallet('${alert.wallet_address}')">
                    Follow
                </button>
                <button class="btn btn-primary btn-sm" onclick="saveInsiderWallet('${alert.wallet_address}')">
                    Save
                </button>
            </div>

            <div class="alert-time">${formatTime(alert.timestamp)}</div>
        </div>
        `;
    }).join('');
}

// ============ WALLET ACTIONS ============

function followInsiderWallet(address) {
    // Utiliser la modale de config wallet existante
    if (typeof openWalletConfigModal === 'function') {
        // Creer une entree temporaire dans walletsData si necessaire
        if (!window.walletsData) window.walletsData = {};
        if (!window.walletsData[address]) {
            window.walletsData[address] = {
                address: address,
                name: 'Insider ' + address.slice(0, 8),
                capital_allocated: 0,
                percent_per_trade: 0,
                active: false
            };
        }
        openWalletConfigModal(address);
    } else {
        alert('Modal de configuration non disponible');
    }
}

function saveInsiderWallet(address) {
    const nickname = prompt('Nickname pour ce wallet (optionnel):');

    fetch('/api/insider/save_wallet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address: address,
            nickname: nickname || ''
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('Wallet sauvegarde!');
                loadSavedWallets();
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        })
        .catch(e => {
            console.error('Save wallet error:', e);
            alert('Erreur de sauvegarde');
        });
}

// ============ SAVED WALLETS ============

function loadSavedWallets() {
    fetch('/api/insider/saved')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;

            renderSavedWallets(data.wallets);
        });
}

function renderSavedWallets(wallets) {
    const container = document.getElementById('saved-wallets-list');
    if (!container) return;

    if (!wallets || wallets.length === 0) {
        container.innerHTML = `
            <p style="color: #888; text-align: center; padding: 20px;">
                Aucun wallet sauvegarde. Utilisez le bouton "Save" sur une alerte pour ajouter.
            </p>
        `;
        return;
    }

    container.innerHTML = wallets.map(w => {
        const sourceBadge = w.source === 'MANUAL'
            ? '<span class="source-badge manual">MANUAL</span>'
            : '<span class="source-badge scanner">SCANNER</span>';

        const pnlClass = (w.pnl || 0) >= 0 ? 'positive' : 'negative';

        return `
        <div class="saved-wallet-card">
            <div class="saved-wallet-info">
                <div class="saved-wallet-header" style="display: flex; align-items: center; gap: 8px;">
                    <div class="saved-wallet-nickname">${escapeHtml(w.nickname) || 'Unnamed Wallet'}</div>
                    ${sourceBadge}
                </div>
                <div class="saved-wallet-address">${w.address}</div>
                <div class="saved-wallet-stats-brief" style="display: flex; gap: 15px; margin-top: 5px; font-size: 0.9em;">
                    <span class="${pnlClass}">$${(w.pnl || 0).toFixed(2)}</span>
                    <span style="color: #888;">${(w.win_rate || 0).toFixed(1)}% WR</span>
                </div>
                <div class="saved-wallet-meta">
                    Saved: ${formatTime(w.saved_at)} |
                    Alerts: ${w.total_alerts || 0}
                </div>
            </div>
            <div class="saved-wallet-actions">
                <button class="btn btn-secondary btn-sm" onclick="viewWalletStats('${w.address}')">
                    Refresh
                </button>
                <button class="btn btn-primary btn-sm" onclick="followInsiderWallet('${w.address}')">
                    Follow
                </button>
                <button class="btn btn-danger btn-sm" onclick="removeSavedWallet('${w.address}')">
                    Remove
                </button>
            </div>
        </div>
    `}).join('');
}

function viewWalletStats(address) {
    fetch(`/api/insider/wallet_stats/${address}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const stats = data.stats;
                alert(`
Wallet: ${truncateAddress(address)}

PnL: $${(stats.pnl || 0).toFixed(2)}
Win Rate: ${(stats.win_rate || 0).toFixed(1)}%
ROI: ${(stats.roi || 0).toFixed(1)}%
Total Trades: ${stats.total_trades || 0}

Alertes enregistrees: ${data.alerts_count || 0}
            `);
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        });
}

function removeSavedWallet(address) {
    if (!confirm('Retirer ce wallet de la liste?')) return;

    fetch(`/api/insider/saved/${address}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                loadSavedWallets();
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        });
}

// ============ WEBSOCKET ============

function initInsiderWebSocket() {
    if (typeof socket !== 'undefined') {
        socket.on('insider_alert', (alert) => {
            console.log('New insider alert:', alert);
            // Recharger le feed
            loadInsiderAlerts();
            loadInsiderStats();

            // Notification optionnelle (si permissions accordees)
            if (Notification.permission === 'granted') {
                new Notification('Insider Alert!', {
                    body: `Score ${alert.suspicion_score}: ${(alert.market_question || '').slice(0, 50)}...`,
                    icon: '/static/img/alert-icon.png'
                });
            }
        });
    }
}

// ============ UTILITIES ============

function formatCriteria(criteria) {
    const labels = {
        'unlikely_bet': 'Unlikely Bet',
        'abnormal_behavior': 'Abnormal',
        'suspicious_profile': 'New Wallet'
    };
    return labels[criteria] || criteria;
}

function truncateAddress(addr) {
    if (!addr) return 'Unknown';
    return addr.slice(0, 10) + '...' + addr.slice(-8);
}

function formatTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ INITIALIZATION ============

function initInsiderTracker() {
    loadInsiderConfig();
    loadInsiderStats();
    loadInsiderAlerts();
    loadSavedWallets();
    initInsiderWebSocket();
}

// Export pour main.js
window.initInsiderTracker = initInsiderTracker;
window.toggleInsiderScanner = toggleInsiderScanner;
window.onInsiderPresetChange = onInsiderPresetChange;
window.toggleCategory = toggleCategory;
window.updateWeightDisplay = updateWeightDisplay;
window.saveInsiderConfig = saveInsiderConfig;
window.triggerManualScan = triggerManualScan;
window.followInsiderWallet = followInsiderWallet;
window.saveInsiderWallet = saveInsiderWallet;
window.viewWalletStats = viewWalletStats;
window.removeSavedWallet = removeSavedWallet;
