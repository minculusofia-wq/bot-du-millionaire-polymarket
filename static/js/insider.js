/**
 * insider.js - Insider Tracker Frontend Logic
 * Gere l'interface utilisateur pour la detection de wallets suspects sur Polymarket
 */

// ============ STATE ============
// Stocke les alertes en mémoire pour distinguer pending vs saved
let pendingAlerts = [];
let dismissedAlertIds = new Set(); // Alertes ignorées (par ID si dispo, ou signature)

// Charger les IDs ignorés
function loadDismissedAlerts() {
    try {
        const stored = localStorage.getItem('dismissedInsiderAlertIds');
        if (stored) {
            dismissedAlertIds = new Set(JSON.parse(stored));
        }
    } catch (e) {
        console.error('Error loading dismissed alerts:', e);
    }
}

function saveDismissedAlerts() {
    try {
        localStorage.setItem('dismissedInsiderAlertIds', JSON.stringify([...dismissedAlertIds]));
    } catch (e) {
        console.error('Error saving dismissed alerts:', e);
    }
}

// ============ SCANNER CONTROL ============

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
                loadPendingAndSavedWallets();
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
            btn.textContent = '🔍 Scan Manuel';
        });
}

// ============ CONFIGURATION ============

function toggleCategory(el) {
    el.classList.toggle('active');
}

function saveInsiderConfig() {
    // Collecter les categories actives
    const activeCategories = [];
    document.querySelectorAll('.category-toggle.active').forEach(el => {
        activeCategories.push(el.dataset.category);
    });

    // Construire la config structurée
    const config = {
        categories: activeCategories,

        risky_bet: {
            enabled: document.getElementById('trigger-risky-enabled').checked,
            min_amount: parseFloat(document.getElementById('trigger-risky-min').value) || 50,
            max_odds: (parseFloat(document.getElementById('trigger-risky-odds').value) || 35) / 100
        },

        whale_wakeup: {
            enabled: document.getElementById('trigger-whale-enabled').checked,
            min_amount: parseFloat(document.getElementById('trigger-whale-min').value) || 100,
            dormant_days: parseInt(document.getElementById('trigger-whale-days').value) || 30
        },

        fresh_wallet: {
            enabled: document.getElementById('trigger-fresh-enabled').checked,
            min_amount: parseFloat(document.getElementById('trigger-fresh-min').value) || 500,
            max_tx: parseInt(document.getElementById('trigger-fresh-tx').value) || 5
        }
    };

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

            // Toggle scanner status
            const toggle = document.getElementById('insider-scanner-toggle');
            if (toggle) toggle.checked = config.running;

            // Categories
            const categories = config.enabled_categories || config.categories || [];
            document.querySelectorAll('.category-toggle').forEach(el => {
                if (categories.includes(el.dataset.category)) {
                    el.classList.add('active');
                } else {
                    el.classList.remove('active');
                }
            });

            // Config Triggers
            if (config.risky_bet) {
                document.getElementById('trigger-risky-enabled').checked = config.risky_bet.enabled;
                document.getElementById('trigger-risky-min').value = config.risky_bet.min_amount;
                document.getElementById('trigger-risky-odds').value = (config.risky_bet.max_odds * 100).toFixed(0);
            }

            if (config.whale_wakeup) {
                document.getElementById('trigger-whale-enabled').checked = config.whale_wakeup.enabled;
                document.getElementById('trigger-whale-min').value = config.whale_wakeup.min_amount;
                document.getElementById('trigger-whale-days').value = config.whale_wakeup.dormant_days;
            }

            if (config.fresh_wallet) {
                document.getElementById('trigger-fresh-enabled').checked = config.fresh_wallet.enabled;
                document.getElementById('trigger-fresh-min').value = config.fresh_wallet.min_amount;
                document.getElementById('trigger-fresh-tx').value = config.fresh_wallet.max_tx;
            }

            // Status display
            updateInsiderStatus(config.running);
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
    const container = document.getElementById('insider-alerts-feed');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#888;">Aucune alerte pour le moment.</p>';
        return;
    }

    // Filtrer les alertes ignorées
    const visibleAlerts = alerts.filter(a => !dismissedAlertIds.has(String(a.id || a.timestamp)));

    if (visibleAlerts.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#888;">Toutes les alertes ont été ignorées.</p>';
        return;
    }

    container.innerHTML = visibleAlerts.map(alert => {
        // Mapping des types d'alerte pour badge CSS
        const typeClass = (alert.alert_type || '').toLowerCase();
        const typeLabel = (alert.alert_type || 'UNKNOWN').replace('_', ' ');

        const stats = alert.wallet_stats || {};
        const pnlClass = (stats.pnl || 0) >= 0 ? 'positive' : 'negative';

        // ID unique pour suppression
        const alertId = alert.id || alert.timestamp;
        const marketName = alert.market_question || 'Marché Inconnu';
        const marketUrl = alert.market_url || (alert.market_slug ? `https://polymarket.com/event/${alert.market_slug}` : '#');

        return `
            <div id="alert-${alertId}" class="insider-alert-card type-${typeClass}" style="position: relative; transition: opacity 0.3s;">
                <button onclick="dismissAlert('${alertId}')" style="position: absolute; top: 10px; right: 10px; background: none; border: none; color: #666; cursor: pointer; font-size: 16px; z-index: 10;" title="Ignorer cette alerte">🗑️</button>
                
                <div class="alert-header" style="margin-right: 25px;">
                    <div>
                        <span class="alert-type-badge ${typeClass}">${typeLabel}</span>
                        <span class="alert-wallet-address">${truncateAddress(alert.wallet_address)}</span>
                        ${alert.nickname ? `<span class="alert-nickname">(${escapeHtml(alert.nickname)})</span>` : ''}
                    </div>
                    <div class="alert-time">${formatTime(alert.timestamp)}</div>
                </div>

                <div class="alert-market">
                    <a href="${marketUrl}" target="_blank" style="color: #fff; text-decoration: none;">
                        📊 ${escapeHtml(marketName)} <span style="color: #00B0FF;">↗️</span>
                    </a>
                </div>

                <!-- Details precis du Trigger -->
                <div class="alert-trigger-info" style="background: rgba(255, 255, 255, 0.05); padding: 8px; border-radius: 4px; margin: 10px 0; border-left: 3px solid #00B0FF;">
                    <div style="font-weight: bold; font-size: 0.9em; color: #fff;">💡 ${escapeHtml(alert.trigger_details || '')}</div>
                    <div style="font-size: 1.1em; color: #00E676; margin-top: 4px;">💰 ${escapeHtml(alert.bet_details || '')}</div>
                </div>

                <div class="alert-stats-row" style="display: flex; gap: 15px; font-size: 0.8em; color: #888; margin-bottom: 10px;">
                    <span>PnL: <span class="${pnlClass}">$${(stats.pnl || 0).toFixed(0)}</span></span>
                    <span>WinRate: ${(stats.win_rate || 0).toFixed(0)}%</span>
                    <span>Trades: ${stats.total_trades || 0}</span>
                </div>

                <div class="alert-actions" style="display: flex; gap: 10px;">
                    <a href="${marketUrl}" target="_blank" class="btn btn-primary btn-sm" style="flex: 2; text-decoration: none; text-align: center; display: flex; align-items: center; justify-content: center; background-color: #2D9CDB;">
                        📂 Ouvrir le Marché
                    </a>
                    <button class="btn btn-secondary btn-sm" onclick="followInsiderWallet('${alert.wallet_address}')" style="flex: 1;">
                        Follow
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="saveInsiderWallet('${alert.wallet_address}')" style="flex: 1;">
                        Save
                    </button>
                </div>
            </div>
            `;
    }).join('');
}

function dismissAlert(id) {
    if (!id) return;
    console.log('Dismissing alert:', id);
    dismissedAlertIds.add(String(id));
    saveDismissedAlerts();

    // Supprimer visuellement
    const el = document.getElementById(`alert-${id}`);
    if (el) {
        el.style.opacity = '0';
        el.style.transform = 'translateX(-20px)';
        setTimeout(() => el.remove(), 400);
    }
}

// ============ PENDING & SAVED WALLETS ============

function loadPendingAndSavedWallets() {
    // Charger les alertes et les wallets sauvegardés
    Promise.all([
        fetch('/api/insider/alerts?limit=50').then(r => r.json()).catch(e => ({ success: false, error: e })),
        fetch('/api/insider/saved').then(r => r.json()).catch(e => ({ success: false, error: e }))
    ]).then(([alertsData, savedData]) => {
        // Handle partial success
        const alerts = (alertsData && alertsData.success) ? (alertsData.alerts || []) : [];
        const savedWallets = (savedData && savedData.success) ? (savedData.wallets || []) : [];

        if (savedData && !savedData.success) {
            console.warn('Error loading saved wallets:', savedData.error);
        }

        // Créer un Set des adresses sauvegardées pour filtrage rapide
        const savedAddresses = new Set(savedWallets.map(w => (w.address || '').toLowerCase()));

        // Filtrer les alertes: exclure celles déjà sauvegardées et celles ignorées
        pendingAlerts = alerts.filter(a => {
            const addr = (a.wallet_address || '').toLowerCase();
            return !savedAddresses.has(addr) && !dismissedAlertIds.has(String(a.id || a.timestamp));
        });

        // Mettre à jour les compteurs
        const pendingCount = document.getElementById('pending-count');
        if (pendingCount) pendingCount.textContent = pendingAlerts.length;

        const savedCount = document.getElementById('saved-count');
        if (savedCount) savedCount.textContent = savedWallets.length;

        // Render
        renderPendingAlerts(pendingAlerts);
        renderSavedWallets(savedWallets);
    });
}

function renderPendingAlerts(alerts) {
    const container = document.getElementById('pending-alerts-list');
    if (!container) return;

    if (!alerts || alerts.length === 0) {
        container.innerHTML = `
            <p style="color: #888; text-align: center; padding: 20px;">
                Aucune alerte en attente. Le scanner cherche des wallets suspects...
            </p>
        `;
        return;
    }

    container.innerHTML = alerts.map(alert => {
        const typeClass = (alert.alert_type || '').toLowerCase();
        const typeLabel = (alert.alert_type || 'UNKNOWN').replace('_', ' ');
        const stats = alert.wallet_stats || {};
        const pnlClass = (stats.pnl || 0) >= 0 ? 'positive' : 'negative';

        return `
        <div class="pending-alert-card" data-alert-id="${alert.id || alert.wallet_address}">
            <div class="pending-alert-header">
                <div>
                    <span class="alert-type-badge ${typeClass}">${typeLabel}</span>
                    <span class="pending-alert-wallet">${truncateAddress(alert.wallet_address)}</span>
                    ${alert.nickname ? `<span class="alert-nickname">(${escapeHtml(alert.nickname)})</span>` : ''}
                </div>
                <div class="pending-alert-time">${formatTime(alert.timestamp)}</div>
            </div>

            <div class="pending-alert-market">📊 ${escapeHtml(alert.market_question || 'Marché inconnu')}</div>

            <div class="pending-alert-details">
                <div class="pending-alert-trigger">💡 ${escapeHtml(alert.trigger_details || 'Trigger détecté')}</div>
                <div class="pending-alert-bet">💰 ${escapeHtml(alert.bet_details || '')}</div>
            </div>

            <div class="pending-alert-stats">
                <span>PnL: <span class="${pnlClass}">$${(stats.pnl || 0).toFixed(0)}</span></span>
                <span>WinRate: ${(stats.win_rate || 0).toFixed(0)}%</span>
                <span>Trades: ${stats.total_trades || 0}</span>
                <a href="${alert.market_url || '#'}" target="_blank" style="color: #00B0FF; text-decoration: none;">↗ Marché</a>
                <a href="https://polymarket.com/profile/${alert.wallet_address}" target="_blank" style="color: #00E676; text-decoration: none;">👤 Profil</a>
            </div>

            <div class="pending-alert-actions">
                <button class="btn btn-save btn-sm" onclick="saveAlertWallet('${alert.wallet_address}', '${escapeHtml(alert.nickname || '')}', '${alert.id || alert.wallet_address}')">
                    💾 Sauvegarder
                </button>
                <button class="btn btn-primary btn-sm" onclick="viewWalletTrades('${alert.wallet_address}')" style="background: #9C27B0;">
                    📊 Voir Trades
                </button>
                <button class="btn btn-primary btn-sm" onclick="followInsiderWallet('${alert.wallet_address}')" style="background: #2D9CDB;">
                    📋 Follow
                </button>
                <button class="btn btn-dismiss btn-sm" onclick="dismissAlert('${alert.id || alert.wallet_address}')">
                    ✕
                </button>
            </div>
        </div>
        `;
    }).join('');
}

// ============ WALLET ACTIONS ============

function saveAlertWallet(address, nickname, alertId) {
    const finalNickname = nickname || prompt('Nickname pour ce wallet (optionnel):') || '';

    fetch('/api/insider/save_wallet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address: address,
            nickname: finalNickname,
            notes: 'Sauvegardé depuis alerte scanner'
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Retirer de la liste pending
                const card = document.querySelector(`[data-alert-id="${alertId}"]`);
                if (card) {
                    card.style.transition = 'all 0.3s';
                    card.style.opacity = '0';
                    card.style.transform = 'translateX(100px)';
                    setTimeout(() => {
                        loadPendingAndSavedWallets();
                    }, 300);
                } else {
                    loadPendingAndSavedWallets();
                }
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        })
        .catch(e => {
            console.error('Save wallet error:', e);
            alert('Erreur de sauvegarde');
        });
}

function dismissAlert(alertId) {
    // Ajouter à la liste des alertes ignorées
    dismissedAlerts.add(alertId);
    saveDismissedAlerts();

    // Animation de sortie
    const card = document.querySelector(`[data-alert-id="${alertId}"]`);
    if (card) {
        card.style.transition = 'all 0.3s';
        card.style.opacity = '0';
        card.style.transform = 'translateX(-100px)';
        setTimeout(() => {
            loadPendingAndSavedWallets();
        }, 300);
    } else {
        loadPendingAndSavedWallets();
    }
}

function viewWalletTrades(address) {
    // Ouvrir la page profil Polymarket du wallet pour voir ses trades
    const profileUrl = `https://polymarket.com/profile/${address}`;
    window.open(profileUrl, '_blank');
}

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
                loadPendingAndSavedWallets();
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

    // Mettre à jour le compteur
    const savedCount = document.getElementById('saved-count');
    if (savedCount) savedCount.textContent = wallets ? wallets.length : 0;

    if (!wallets || wallets.length === 0) {
        container.innerHTML = `
            <p style="color: #888; text-align: center; padding: 20px;">
                Aucun wallet sauvegardé. Utilisez le bouton "💾 Sauvegarder" sur une alerte ci-dessus.
            </p>
        `;
        return;
    }

    container.innerHTML = wallets.map(w => {
        const sourceBadge = w.source === 'MANUAL'
            ? '<span class="source-badge manual">MANUAL</span>'
            : '<span class="source-badge scanner">SCANNER</span>';

        const pnlClass = (w.pnl || 0) >= 0 ? 'positive' : 'negative';
        const polymarketProfileUrl = `https://polymarket.com/@${encodeURIComponent(w.nickname || w.address)}`;

        return `
        <div class="saved-wallet-card">
            <div class="saved-wallet-info">
                <div class="saved-wallet-header" style="display: flex; align-items: center; gap: 8px;">
                    <div class="saved-wallet-nickname">${escapeHtml(w.nickname) || 'Unnamed Wallet'}</div>
                    ${sourceBadge}
                </div>
                <div class="saved-wallet-address">${w.address}</div>
                <div class="saved-wallet-stats-brief" style="display: flex; gap: 15px; margin-top: 5px; font-size: 0.9em;">
                    <span title="Valeur des positions actuelles (pas le PnL réel)" class="${pnlClass}">📊 $${(w.pnl || 0).toFixed(2)}</span>
                    <a href="${polymarketProfileUrl}" target="_blank" style="color: #00B0FF; text-decoration: none; font-size: 0.85em;" title="Voir le vrai PnL sur Polymarket">
                        ↗ Profil
                    </a>
                </div>
                <div class="saved-wallet-meta">
                    Saved: ${formatTime(w.saved_at)} |
                    Alerts: ${w.total_alerts || 0}
                </div>
            </div>
            <div class="saved-wallet-actions">
                <button class="btn btn-secondary btn-sm" onclick="viewWalletTrades('${w.address}')" title="Voir les trades sur Polymarket">
                    📊
                </button>
                <button class="btn btn-secondary btn-sm" onclick="viewWalletStats('${w.address}')" title="Rafraîchir les stats">
                    🔄
                </button>
                <button class="btn btn-primary btn-sm" onclick="followInsiderWallet('${w.address}')" title="Suivre ce wallet">
                    📋
                </button>
                <button class="btn btn-danger btn-sm" onclick="removeSavedWallet('${w.address}')" title="Supprimer">
                    🗑️
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
                // Recharger pour afficher les stats mises à jour
                loadPendingAndSavedWallets();
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
                loadPendingAndSavedWallets();
            } else {
                alert('Erreur: ' + (data.error || 'Unknown'));
            }
        });
}

// ============ WEBSOCKET ============

function playAlertSound() {
    const toggle = document.getElementById('insider-sound-toggle');
    if (toggle && !toggle.checked) return;

    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;

        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.connect(gain);
        gain.connect(ctx.destination);

        // Petit effet "Sonar"
        osc.type = 'sine';
        osc.frequency.setValueAtTime(600, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1000, ctx.currentTime + 0.1);

        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);

        osc.start();
        osc.stop(ctx.currentTime + 0.5);
    } catch (e) {
        console.error('Error playing sound:', e);
    }
}

function initInsiderWebSocket() {
    if (typeof socket !== 'undefined') {
        socket.on('insider_alert', (alert) => {
            console.log('New insider alert:', alert);

            // Jouer le son
            playAlertSound();

            // Recharger le feed et les pending
            loadInsiderAlerts();
            loadInsiderStats();
            loadPendingAndSavedWallets();

            // Notification optionnelle (si permissions accordees)
            if (Notification.permission === 'granted') {
                new Notification('🚨 Insider Alert!', {
                    body: `${alert.alert_type}: ${(alert.market_question || '').slice(0, 50)}...`,
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
    loadDismissedAlerts();
    loadInsiderConfig();
    loadInsiderStats();
    loadInsiderAlerts();
    loadPendingAndSavedWallets();
    initInsiderWebSocket();
}

// Export pour main.js
window.initInsiderTracker = initInsiderTracker;
window.toggleInsiderScanner = toggleInsiderScanner;
window.toggleCategory = toggleCategory;
window.saveInsiderConfig = saveInsiderConfig;
window.triggerManualScan = triggerManualScan;
window.followInsiderWallet = followInsiderWallet;
window.saveInsiderWallet = saveInsiderWallet;
window.saveAlertWallet = saveAlertWallet;
window.dismissAlert = dismissAlert;
window.viewWalletTrades = viewWalletTrades;
window.viewWalletStats = viewWalletStats;
window.removeSavedWallet = removeSavedWallet;
window.loadPendingAndSavedWallets = loadPendingAndSavedWallets;

