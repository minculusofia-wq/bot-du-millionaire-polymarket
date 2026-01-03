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

// ============ WALLET MANAGEMENT ============
function addWallet() {
    const address = document.getElementById('new-wallet-address').value.trim();
    const name = document.getElementById('new-wallet-name').value.trim() || 'Wallet';

    if (!address) {
        alert('Veuillez entrer une adresse de wallet');
        return;
    }

    if (!address.startsWith('0x') || address.length !== 42) {
        alert('Adresse invalide. Format attendu: 0x... (42 caractères)');
        return;
    }

    fetch('/api/wallets/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, name })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('new-wallet-address').value = '';
                document.getElementById('new-wallet-name').value = '';
                loadWallets();
                alert('Wallet ajouté avec succès!');
            } else {
                alert('Erreur: ' + (data.error || 'Impossible d\'ajouter le wallet'));
            }
        })
        .catch(e => {
            console.error('Erreur addWallet:', e);
            alert('Erreur réseau');
        });
}

function removeWallet(address) {
    if (!confirm('Supprimer ce wallet de la liste de suivi?')) return;

    fetch('/api/wallets/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                loadWallets();
            } else {
                alert('Erreur: ' + (data.error || 'Impossible de supprimer'));
            }
        })
        .catch(e => console.error('Erreur removeWallet:', e));
}

function toggleWalletActive(address, currentlyActive) {
    const newState = !currentlyActive;

    fetch('/api/wallets/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, active: newState })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                loadWallets();
            }
        })
        .catch(e => console.error('Erreur toggleWalletActive:', e));
}

function saveWalletConfig() {
    const address = document.getElementById('modal-wallet-address').value;
    const capital = parseFloat(document.getElementById('modal-capital').value) || 0;
    const percent = parseFloat(document.getElementById('modal-percent').value) || 0;
    const slValue = document.getElementById('modal-sl').value;
    const tpValue = document.getElementById('modal-tp').value;
    const useKelly = document.getElementById('modal-use-kelly').checked;
    const useTrailing = document.getElementById('modal-use-trailing').checked;

    const sl = slValue !== '' ? parseFloat(slValue) : null;
    const tp = tpValue !== '' ? parseFloat(tpValue) : null;

    fetch('/api/wallets/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address,
            capital_allocated: capital,
            percent_per_trade: percent,
            sl_percent: sl,
            tp_percent: tp,
            use_kelly: useKelly,
            use_trailing: useTrailing
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeWalletConfigModal();
                loadWallets();
                alert('Configuration sauvegardée!');
            } else {
                alert('Erreur: ' + (data.error || 'Impossible de sauvegarder'));
            }
        })
        .catch(e => {
            console.error('Erreur saveWalletConfig:', e);
            alert('Erreur réseau');
        });
}

// ============ POSITIONS ============
function loadPositions() {
    fetch('/api/positions')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('active-positions');
            if (!data.success || !data.positions || data.positions.length === 0) {
                container.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">Aucune position active</p>';
                return;
            }

            container.innerHTML = data.positions.map(p => {
                const pnl = p.pnl || p.unrealized_pnl || 0;
                const pnlClass = pnl >= 0 ? 'positive' : 'negative';
                const pnlSign = pnl >= 0 ? '+' : '';
                const market = p.market || p.market_slug || 'Marché inconnu';
                const amount = p.amount || p.value_usd || 0;

                return `
            <div class="position-card">
                <div class="position-header">
                    <strong>${market}</strong>
                    <span class="side-badge ${(p.side || 'BUY').toLowerCase()}">${p.side || 'BUY'}</span>
                </div>
                <div class="position-details">
                    <div>
                        <span>Montant:</span>
                        <span class="value">$${amount.toFixed(2)}</span>
                    </div>
                    <div>
                        <span>Prix entrée:</span>
                        <span>$${(p.entry_price || 0).toFixed(4)}</span>
                    </div>
                    <div>
                        <span>Prix actuel:</span>
                        <span>$${(p.current_price || 0).toFixed(4)}</span>
                    </div>
                    <div>
                        <span>PnL:</span>
                        <span class="${pnlClass}">${pnlSign}$${pnl.toFixed(2)}</span>
                    </div>
                </div>
                <div class="position-actions">
                    <button class="btn btn-danger btn-sm" onclick="openSellModal(${p.id || p.position_id})">Vendre</button>
                </div>
            </div>
            `;
            }).join('');
        })
        .catch(e => {
            console.error('Erreur loadPositions:', e);
        });
}

// ============ SELL MODAL ============
function openSellModal(positionId) {
    // Store positionId
    window.currentSellPositionId = positionId;
    document.getElementById('sell-position-id').value = positionId;

    // Fetch position details
    fetch('/api/positions')
        .then(r => r.json())
        .then(data => {
            const position = data.positions.find(p => (p.id || p.position_id) == positionId);
            if (position) {
                document.getElementById('sell-market-name').textContent = position.market || position.market_slug || 'Inconnu';
                document.getElementById('sell-position-side').textContent = position.side || 'BUY';
                document.getElementById('sell-position-amount').textContent = '$' + (position.amount || position.value_usd || 0).toFixed(2);
                const pnl = position.pnl || position.unrealized_pnl || 0;
                const pnlEl = document.getElementById('sell-position-pnl');
                pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
                pnlEl.className = 'value ' + (pnl >= 0 ? 'positive' : 'negative');
            }
        });

    // Reset percent selection
    selectSellPercent(100);

    // Show modal
    document.getElementById('sell-modal').classList.add('active');
}

function closeSellModal() {
    document.getElementById('sell-modal').classList.remove('active');
    window.currentSellPositionId = null;
}

function selectSellPercent(percent) {
    document.getElementById('sell-percent-value').value = percent;

    // Update button styles
    document.querySelectorAll('.sell-percent-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent === percent + '%') {
            btn.classList.add('active');
        }
    });
}

function executeSell() {
    const positionId = document.getElementById('sell-position-id').value;
    const percent = parseInt(document.getElementById('sell-percent-value').value);

    if (!positionId) {
        alert('Position non sélectionnée');
        return;
    }

    if (!confirm(`Confirmer la vente de ${percent}% de la position?`)) return;

    fetch('/api/positions/sell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            position_id: parseInt(positionId),
            percent: percent
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeSellModal();
                loadPositions();
                alert('Vente exécutée avec succès!');
            } else {
                alert('Erreur: ' + (data.error || 'Impossible de vendre'));
            }
        })
        .catch(e => {
            console.error('Erreur executeSell:', e);
            alert('Erreur réseau');
        });
}

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
function savePolymarketCredentials() {
    const address = document.getElementById('pm-wallet-address').value;
    const key = document.getElementById('pm-wallet-key').value;
    const apiKey = document.getElementById('pm-api-key').value;
    const apiSecret = document.getElementById('pm-api-secret').value;
    const apiPassphrase = document.getElementById('pm-api-passphrase').value;

    fetch('/api/polymarket/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address,
            private_key: key,
            api_key: apiKey,
            api_secret: apiSecret,
            api_passphrase: apiPassphrase
        })
    }).then(r => r.json()).then(data => {
        if (data.success) {
            alert('Identifiants Polymarket sauvegardés et chiffrés');
        } else {
            alert('Erreur: ' + (data.error || 'Inconnue'));
        }
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


            // Wallet & API addresses
            if (data.polymarket_wallet) {
                document.getElementById('pm-wallet-address').value = data.polymarket_wallet.address || '';
                // On ne remplit pas les mots de passe/clés pour la sécurité, 
                // mais si on veut montrer qu'ils existent:
                if (data.polymarket_wallet.has_key) document.getElementById('pm-wallet-key').placeholder = "••••••••••••••••";

                // Afficher adresse sur dashboard
                const pmAddr = data.polymarket_wallet.address;
                if (pmAddr) {
                    document.getElementById('pm-wallet-addr').textContent = pmAddr.slice(0, 10) + '...' + pmAddr.slice(-8);
                } else {
                    document.getElementById('pm-wallet-addr').textContent = 'Non configuré';
                }
            }

            // API Credentials placeholders
            if (data.polymarket_api) {
                if (data.polymarket_api.key) {
                    document.getElementById('pm-api-key').value = data.polymarket_api.key;
                }
                if (data.polymarket_api.has_secret) document.getElementById('pm-api-secret').placeholder = "••••••••••••••••";
                if (data.polymarket_api.has_passphrase) document.getElementById('pm-api-passphrase').placeholder = "••••••••••••••••";
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

    // Start polling (Reduced frequency as we have SocketIO)
    setInterval(updateUI, 10000);
    updateUI();

    // Charger le graphique
    loadPnLChart();
});
