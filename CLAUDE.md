# CLAUDE.md - Guide pour Assistants IA

> Documentation complète du Bot du Millionnaire pour assistants IA (Claude, etc.)

## 📋 Table des Matières

1. [Vue d'Ensemble du Projet](#vue-densemble-du-projet)
2. [Architecture & Structure](#architecture--structure)
3. [Modules Principaux](#modules-principaux)
4. [Workflows de Développement](#workflows-de-développement)
5. [Configuration & Environnement](#configuration--environnement)
6. [Conventions de Code](#conventions-de-code)
7. [Sécurité & Bonnes Pratiques](#sécurité--bonnes-pratiques)
8. [Testing & Débogage](#testing--débogage)
9. [API & Routes](#api--routes)
10. [Base de Données](#base-de-données)

---

## 🎯 Vue d'Ensemble du Projet

### Description
**Bot du Millionnaire** est un bot de copy trading automatisé pour la blockchain Solana avec interface web moderne. Il permet de copier automatiquement les trades de traders sélectionnés avec gestion avancée du risque (TP/SL), backtesting et benchmarking.

### État Actuel
- **Version**: 4.0.0 (Phase 8 complétée)
- **Statut**: ✅ Production-Ready
- **Langage**: Python 3.9+
- **Framework Web**: Flask 3.0.0
- **Base de données**: SQLite
- **Blockchain**: Solana (via Helius API)

### Fonctionnalités Principales
- ✅ Copy trading automatique de 2 traders simultanément (limite configurable)
- ✅ Take Profit / Stop Loss automatiques
- ✅ Backtesting avec 30+ combinaisons de paramètres
- ✅ Benchmark: comparaison Bot vs Traders
- ✅ Auto-sell intelligent (mode mirror si TP/SL = 0)
- ✅ Mode TEST (simulation) et MODE REAL (transactions réelles)
- ✅ Monitoring en temps réel avec métriques
- ✅ Interface web responsive (6 onglets)
- ✅ Optimisations performance (Phase 8): Batch RPC, Workers, Smart TP/SL, Arbitrage

---

## 🏗️ Architecture & Structure

### Structure des Fichiers

```
bot-du-millionaire/
├── 📱 INTERFACE WEB & SERVEUR
│   ├── bot.py                          # ⭐ Application Flask principale (2400+ lignes)
│   │                                   # Routes API, HTML embarqué, WebSocket callbacks
│   └── bot_logic.py                    # Backend logique métier, gestion config
│
├── 🤖 CORE TRADING
│   ├── portfolio_tracker.py            # Suivi portefeuilles en temps réel
│   ├── copy_trading_simulator.py       # Simulation copy trading (MODE TEST)
│   ├── auto_sell_manager.py            # Vente automatique + Mode Mirror
│   ├── backtesting_engine.py           # Moteur de backtesting multi-paramètres
│   └── benchmark_system.py             # Système de benchmark Bot vs Traders
│
├── 🔗 BLOCKCHAIN & EXECUTION
│   ├── solana_executor.py              # Exécution transactions Solana réelles
│   ├── solana_integration.py           # Intégration Solana RPC
│   ├── helius_integration.py           # API Helius pour données enrichies
│   ├── helius_polling.py               # Polling transactions Helius
│   ├── helius_websocket.py             # WebSocket Helius (temps réel)
│   ├── dex_handler.py                  # Support multi-DEX (Raydium, Orca, Jupiter)
│   └── magic_eden_api.py               # API Magic Eden (NFTs)
│
├── 🛡️ SÉCURITÉ & VALIDATION
│   ├── trade_validator.py              # Validation 3 niveaux (STRICT/NORMAL/RELAXED)
│   ├── trade_safety.py                 # Gestion risque, TP/SL automatiques
│   ├── audit_logger.py                 # Logging audit trail sécurisé
│   └── advanced_risk_manager.py        # Gestionnaire de risque avancé (Phase 8)
│
├── 📊 MONITORING & ANALYTICS
│   ├── monitoring.py                   # Métriques temps réel + alertes
│   ├── advanced_analytics.py           # Analytics avancées (Phase 8)
│   └── db_manager.py                   # Gestionnaire base de données SQLite
│
├── ⚡ OPTIMISATIONS PERFORMANCE (Phase 8)
│   ├── worker_threads.py               # Pool de workers parallèles
│   ├── smart_strategy.py               # Stratégies TP/SL intelligentes
│   └── arbitrage_engine.py             # Détection opportunités d'arbitrage
│
├── 🔧 WEBSOCKETS & ASYNC
│   └── websockets_handler.py           # Gestionnaire WebSocket
│
├── 📝 CONFIGURATION
│   ├── config.json                     # ⚠️ Config principale (NE PAS COMMITER si clés privées)
│   ├── .env                            # ⚠️ Variables d'environnement (NE PAS COMMITER)
│   ├── .env.example                    # Template pour .env
│   └── requirements.txt                # Dépendances Python
│
├── 💾 DONNÉES & PERSISTENCE
│   ├── bot_data.db                     # Base SQLite (historique 30+ jours)
│   ├── portfolio_tracker.json          # Historique performances
│   ├── copied_trades_history.json      # Historique trades copiés
│   └── open_positions.json             # Positions ouvertes actives
│
├── 📚 DOCUMENTATION
│   ├── README.md                       # Documentation utilisateur
│   ├── CLAUDE.md                       # 👈 Ce fichier
│   ├── SETUP_LOCAL.md                  # Guide installation locale
│   ├── TEST_REPORT.md                  # Rapport de tests
│   └── replit.md                       # Configuration Replit
│
└── 🚀 SCRIPTS
    ├── Lancer le Bot.command           # Script lancement macOS
    ├── main.py                         # Point d'entrée alternatif
    └── push-to-github.sh               # Script déploiement Git
```

### Architecture Technique

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE WEB (Flask)                     │
│                  bot.py (Routes API + HTML)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────────┐ ┌───▼────────┐ ┌───▼──────────┐
│  bot_logic.py   │ │ Portfolio  │ │   DB Manager │
│  (Backend Core) │ │  Tracker   │ │   (SQLite)   │
└────────┬────────┘ └───┬────────┘ └───┬──────────┘
         │               │               │
┌────────▼───────────────▼───────────────▼──────────┐
│           TRADING ENGINE (Copy Trading)            │
│  • copy_trading_simulator.py (MODE TEST)          │
│  • auto_sell_manager.py (Vente auto)              │
│  • backtesting_engine.py (Backtesting)            │
│  • benchmark_system.py (Benchmark)                │
└────────┬───────────────────────────────────────────┘
         │
┌────────▼───────────────────────────────────────────┐
│        BLOCKCHAIN LAYER (Solana + Helius)          │
│  • helius_polling.py (Récupération transactions)  │
│  • helius_websocket.py (Temps réel ~100-200ms)   │
│  • solana_executor.py (Exécution trades réels)    │
│  • dex_handler.py (Multi-DEX: Raydium/Orca/Jupiter)│
└────────┬───────────────────────────────────────────┘
         │
┌────────▼───────────────────────────────────────────┐
│         SÉCURITÉ & VALIDATION                      │
│  • trade_validator.py (Validation 3 niveaux)      │
│  • trade_safety.py (TP/SL, Gestion risque)        │
│  • audit_logger.py (Audit trail)                  │
│  • advanced_risk_manager.py (Risque avancé)       │
└────────────────────────────────────────────────────┘
```

---

## 🔧 Modules Principaux

### 1. `bot.py` - Application Flask Principale ⭐
**Rôle**: Serveur web, routes API, interface utilisateur, orchestration

**Responsabilités**:
- Servir l'interface web (HTML/CSS/JS embarqué)
- 60+ routes API pour toutes les fonctionnalités
- Callbacks WebSocket pour détection rapide des trades
- Chargement des variables d'environnement (`.env`)
- Orchestration de tous les modules

**Routes API principales**:
- `/api/dashboard` - Données du tableau de bord
- `/api/traders` - Liste des traders
- `/api/toggle_trader` - Activer/désactiver un trader
- `/api/execute_trade` - Exécuter un trade
- `/api/backtest` - Lancer un backtesting
- `/api/benchmark` - Obtenir le classement benchmark
- `/api/positions` - Positions ouvertes
- `/api/sell_position` - Vendre une position (manuel)

**Points d'attention**:
- Fichier massif (2400+ lignes) - considérer la modularisation si modifications majeures
- HTML/CSS/JS embarqué dans le code Python (render_template_string)
- Gère les callbacks WebSocket pour détection ultra-rapide (~100-200ms)

### 2. `bot_logic.py` - Backend Logique Métier
**Rôle**: Gestion configuration, logique métier centrale, état du bot

**Responsabilités**:
- Charger/sauvegarder `config.json`
- Validation de la configuration
- Gestion du capital virtuel (MODE TEST)
- Cache du portfolio et du wallet balance
- Initialisation des prix simulés (MODE TEST)

**Méthodes clés**:
- `load_config()` - Charge la configuration
- `save_config()` - Sauvegarde la configuration
- `_validate_config()` - Valide les champs requis
- `initialize_test_prices()` - Prix simulés pour MODE TEST

### 3. `portfolio_tracker.py` - Suivi Portefeuilles
**Rôle**: Surveille les portefeuilles des traders en temps réel

**Responsabilités**:
- Polling régulier des adresses Solana
- Détection des nouveaux trades
- Calcul du PnL (Profit & Loss)
- Historique des performances (24h, 7j, 30j)

**Fonctionnalités**:
- Récupère les transactions via Helius API
- Parse les swaps et tokens achetés/vendus
- Calcule le PnL en temps réel
- Nettoie l'historique après 8 jours

### 4. `copy_trading_simulator.py` - Simulation Copy Trading
**Rôle**: Simule le copy trading en MODE TEST avec données réelles

**Responsabilités**:
- Récupère les VRAIES transactions des traders via Helius
- Simule les mêmes trades avec capital fictif (1000$)
- Calcule le PnL réel de la simulation
- Support complet MODE TEST

**Points d'attention**:
- Utilise les données réelles pour la simulation
- Capital fictif de 1000$ par défaut
- Permet de tester sans risque

### 5. `auto_sell_manager.py` - Vente Automatique
**Rôle**: Gère la vente automatique (principale) et manuelle (bonus)

**Responsabilités**:
- **Détecte AUTOMATIQUEMENT** les ventes du trader
- **Vend AUTOMATIQUEMENT** en respectant TP/SL
- **Mode Mirror**: Si TP/SL = 0, vend EXACTEMENT comme le trader
- Vente manuelle optionnelle (bonus)
- Identique en MODE TEST et MODE REAL

**Logique**:
```python
if TP/SL configurés:
    Vente automatique selon TP/SL
else:
    Mode Mirror: vendre exactement comme le trader
```

### 6. `backtesting_engine.py` - Backtesting
**Rôle**: Teste 30+ combinaisons de paramètres TP/SL sur données historiques

**Responsabilités**:
- Teste différentes combinaisons TP/SL
- Calcule Win Rate, PnL, nombre de trades
- Identifie le meilleur résultat
- Interface visuelle avec résultats détaillés

### 7. `benchmark_system.py` - Benchmark
**Rôle**: Compare les performances Bot vs chaque Trader

**Responsabilités**:
- Calcule le PnL% de chaque trader
- Calcule le Win Rate
- Classe les traders avec médailles (🥇🥈🥉)
- Identifie le meilleur trader automatiquement

### 8. `solana_executor.py` - Exécution Solana
**Rôle**: Exécute les transactions Solana réelles (MODE REAL uniquement)

**Responsabilités**:
- Signature et envoi des transactions
- Gestion du wallet (clé privée)
- Validation des transactions
- Retry en cas d'échec

**Sécurité**:
- Clé privée stockée en mémoire uniquement
- Jamais sauvegardée sur disque
- Validation avant chaque transaction

### 9. `trade_validator.py` - Validation
**Rôle**: Valide les trades avant exécution (3 niveaux)

**Niveaux de validation**:
- **STRICT**: Validation maximale (production)
- **NORMAL**: Validation standard (défaut)
- **RELAXED**: Validation minimale (développement)

**Vérifications**:
- Montants valides (> 0, <= capital disponible)
- Adresses Solana valides
- Slippage acceptable
- Limites de position respectées

### 10. `trade_safety.py` - Gestion Risque
**Rôle**: Gère les Take Profit, Stop Loss et le risque global

**Responsabilités**:
- Application automatique des TP/SL
- Calcul des niveaux de prix TP/SL
- Gestion du risk/reward ratio
- Protection contre les pertes excessives

**Niveaux de risque**:
- **LOW**: Risque minimal (SL serré)
- **MEDIUM**: Risque modéré (défaut)
- **HIGH**: Risque élevé (SL large)

### 11. `monitoring.py` - Monitoring
**Rôle**: Collecte des métriques en temps réel et alertes

**Métriques collectées**:
- **Performance**: Win Rate, PnL, Sharpe Ratio
- **Exécution**: Latence, slippage, DEX utilisés
- **Système**: Santé RPC, balance wallet, tendances

**Alertes**:
- Balance faible
- Santé RPC dégradée
- Slippage excessif

### 12. `db_manager.py` - Gestionnaire BDD
**Rôle**: Gestion de la base de données SQLite

**Tables**:
- `trades`: Historique des trades
- `positions`: Positions ouvertes
- `performance`: Métriques de performance
- `traders`: Données des traders

**Responsabilités**:
- CRUD operations (Create, Read, Update, Delete)
- Nettoyage automatique (données > 30 jours)
- Export/Import de données

### 13. Phase 8 - Optimisations Performance
**Nouveaux modules**:
- `worker_threads.py`: Pool de workers parallèles (4 threads)
- `smart_strategy.py`: Stratégies TP/SL intelligentes basées sur volatilité
- `arbitrage_engine.py`: Détection opportunités d'arbitrage multi-DEX
- `advanced_risk_manager.py`: Gestion risque avancée avec corrélations
- `advanced_analytics.py`: Analytics avancées avec ML

**Optimisations**:
- ✅ Batch RPC requests (réduction 60% latence)
- ✅ Workers parallèles (4 threads)
- ✅ Smart TP/SL adaptatifs
- ✅ Détection arbitrage multi-DEX
- ✅ Risk Manager avec analyse corrélations
- ✅ Analytics avancées
- ✅ Backtesting amélioré (10x plus rapide)

---

## 🔄 Workflows de Développement

### Workflow 1: Ajouter une Nouvelle Fonctionnalité

1. **Planification**
   - Lire ce fichier CLAUDE.md pour comprendre l'architecture
   - Identifier les modules impactés
   - Vérifier les conventions de code

2. **Développement**
   - Créer un nouveau module si nécessaire (ex: `nouvelle_feature.py`)
   - OU modifier un module existant
   - Ajouter la logique métier
   - Ajouter les routes API dans `bot.py` si besoin

3. **Intégration**
   - Importer le nouveau module dans `bot.py`
   - Créer les routes API
   - Mettre à jour l'interface web (HTML dans `bot.py`)
   - Ajouter au `requirements.txt` si nouvelles dépendances

4. **Testing**
   - Tester en MODE TEST d'abord
   - Vérifier les logs dans la console
   - Tester toutes les routes API
   - Valider l'interface web

5. **Documentation**
   - Mettre à jour README.md
   - Mettre à jour ce fichier CLAUDE.md
   - Ajouter des commentaires dans le code

### Workflow 2: Corriger un Bug

1. **Investigation**
   - Reproduire le bug
   - Consulter les logs (console + `audit_logger.py`)
   - Identifier le module responsable

2. **Fix**
   - Modifier le code
   - Ajouter des validations si nécessaire
   - Tester la correction

3. **Validation**
   - Tester en MODE TEST
   - Vérifier les effets de bord
   - Valider avec plusieurs scénarios

### Workflow 3: Modifier la Configuration

Les modifications de configuration se font via `config.json`:

```json
{
  "mode": "TEST",              // "TEST" ou "REAL"
  "slippage": 1.0,             // 0.1 à 100%
  "active_traders_limit": 2,   // Nombre de traders actifs max
  "currency": "USD",           // "USD" ou "SOL"
  "total_capital": 1000,       // Capital total
  "tp1_percent": 33,           // % position vendue au TP1
  "tp1_profit": 10,            // % profit cible TP1
  "sl_percent": 100,           // % position vendue au SL
  "sl_loss": 5,                // % perte cible SL
  "traders": [...]             // Liste des traders
}
```

**⚠️ Important**: Ne jamais commiter `config.json` si contient des clés privées!

### Workflow 4: Ajouter une Route API

1. **Dans `bot.py`**:
```python
@app.route('/api/nouvelle_route', methods=['POST', 'GET'])
def nouvelle_route():
    try:
        # Récupérer les données
        data = request.get_json()

        # Logique métier
        result = backend.faire_quelquechose(data)

        # Retour JSON
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

2. **Dans le frontend (HTML dans `bot.py`)**:
```javascript
async function appelNouvelleRoute() {
    try {
        const response = await fetch('/api/nouvelle_route', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ param: 'valeur' })
        });
        const data = await response.json();
        if (data.success) {
            // Traiter le succès
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}
```

---

## ⚙️ Configuration & Environnement

### Variables d'Environnement (`.env`)

```bash
# API Helius (OBLIGATOIRE pour données blockchain)
HELIUS_API_KEY=votre_cle_helius_ici

# RPC Solana (optionnel, défaut: api.mainnet-beta.solana.com)
RPC_URL=https://api.mainnet-beta.solana.com

# Port Flask (optionnel, défaut: 5000)
PORT=5000
```

**Comment obtenir une clé Helius**:
1. Aller sur https://helius.dev
2. Créer un compte gratuit
3. Créer un projet Solana
4. Copier la clé API dans `.env`

### Installation

```bash
# 1. Cloner le projet
git clone https://github.com/minculusofia-wq/bot-du-millionaire.git
cd bot-du-millionaire

# 2. Créer .env depuis .env.example
cp .env.example .env
# Éditer .env et ajouter votre HELIUS_API_KEY

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer le bot
python bot.py
# OU sur macOS:
./Lancer\ le\ Bot.command
```

### Dépendances Python

```
flask==3.0.0          # Framework web
requests==2.31.0      # Requêtes HTTP
```

**Note**: Les dépendances sont volontairement minimales. Les imports Solana (`solders`, `solana`) sont optionnels et gérés avec des try/except.

---

## 📐 Conventions de Code

### Style Python
- **PEP 8**: Suivre les conventions Python standard
- **Indentation**: 4 espaces (pas de tabs)
- **Encodage**: UTF-8
- **Line length**: Max 120 caractères (flexible)

### Nommage

```python
# Modules et fichiers: snake_case
portfolio_tracker.py
auto_sell_manager.py

# Classes: PascalCase
class BotBackend:
class AutoSellManager:

# Fonctions et méthodes: snake_case
def load_config():
def get_wallet_balance():

# Constantes: UPPER_SNAKE_CASE
MAX_TRADERS = 10
DEFAULT_SLIPPAGE = 1.0

# Variables privées: _underscore_prefix
def _load_open_positions():
self._cache = {}
```

### Commentaires et Documentation

```python
# ✅ BON: Docstrings pour toutes les classes et fonctions publiques
class AutoSellManager:
    """Gère la vente automatique (principale) et manuelle (bonus)"""

    def execute_sell(self, position_id: str, amount: float) -> bool:
        """
        Exécute une vente pour une position donnée

        Args:
            position_id: ID unique de la position
            amount: Montant à vendre

        Returns:
            True si succès, False sinon
        """
        pass

# ✅ BON: Commentaires pour expliquer la logique complexe
# Vérifier si déjà copié pour éviter les doublons
trader_key = f"{trader_name}_{signature}"
if trader_key in copied_trades_history:
    return  # Déjà copié, ignorer

# ❌ MAUVAIS: Commentaires évidents
x = x + 1  # Incrémenter x
```

### Emojis dans les Messages Console

Le projet utilise des emojis pour rendre les logs plus lisibles:

```python
print("✅ Configuration chargée")      # Succès
print("⚠️ Avertissement: ...")        # Warning
print("❌ Erreur: ...")                # Erreur
print("🚀 Bot démarré")                # Action importante
print("💰 Trade exécuté")              # Trading
print("📊 Statistiques: ...")          # Données/Stats
print("🔒 Sécurité: ...")              # Sécurité
print("⚡ Optimisation: ...")          # Performance
```

### Gestion des Erreurs

```python
# ✅ BON: Try/except avec logging approprié
try:
    result = execute_dangerous_operation()
    print("✅ Opération réussie")
    return result
except SpecificException as e:
    print(f"❌ Erreur spécifique: {e}")
    return None
except Exception as e:
    print(f"❌ Erreur inattendue: {e}")
    return None

# ❌ MAUVAIS: Catch all sans logging
try:
    result = execute_dangerous_operation()
except:
    pass
```

### Retours de Fonctions

```python
# ✅ BON: Typage avec type hints
def get_trader_balance(address: str) -> Optional[float]:
    """Retourne le balance du trader ou None si erreur"""
    pass

# ✅ BON: Dictionnaires pour retours complexes
def execute_trade(params: Dict) -> Dict:
    """Retourne un dictionnaire avec success, data et éventuellement error"""
    return {
        'success': True,
        'data': {'signature': 'abc123...'},
        'timestamp': datetime.now().isoformat()
    }
```

---

## 🔒 Sécurité & Bonnes Pratiques

### Règles de Sécurité CRITIQUES ⚠️

1. **NE JAMAIS commiter de secrets**
   ```bash
   # ❌ NE JAMAIS COMMITER
   config.json           # Peut contenir wallet_private_key
   .env                  # Contient HELIUS_API_KEY
   *.db                  # Base de données (peut contenir données sensibles)

   # ✅ Vérifier .gitignore
   __pycache__/
   *.py[oc]
   .venv
   ```

2. **Clés privées en mémoire uniquement**
   ```python
   # ✅ BON: Jamais sauvegardé sur disque
   self.wallet_keypair = Keypair.from_secret_key(bytes.fromhex(private_key))

   # ❌ MAUVAIS: Sauvegarder clé privée
   with open('wallet.key', 'w') as f:
       f.write(private_key)  # NE JAMAIS FAIRE ÇA
   ```

3. **Validation systématique des inputs**
   ```python
   # ✅ BON: Toujours valider
   if not address or len(address) < 32:
       return {'success': False, 'error': 'Adresse invalide'}

   if amount <= 0 or amount > max_capital:
       return {'success': False, 'error': 'Montant invalide'}
   ```

4. **Mode TEST par défaut**
   ```python
   # ✅ BON: Toujours démarrer en MODE TEST
   "mode": "TEST"  # Défaut dans config.json
   ```

5. **Confirmation pour actions destructives**
   ```python
   # ✅ BON: Demander confirmation en MODE REAL
   if mode == "REAL":
       if not user_confirmed:
           print("⚠️ Confirmation requise pour MODE REAL")
           return
   ```

### Audit Trail

Le projet utilise `audit_logger.py` pour tracer toutes les actions:

```python
from audit_logger import audit_logger, LogLevel

# Tracer une action importante
audit_logger.log(
    level=LogLevel.INFO,
    event_type='TRADE_EXECUTED',
    message='Trade exécuté avec succès',
    metadata={
        'trader': 'AlphaMoon',
        'amount': 100,
        'signature': 'abc123...'
    }
)
```

**Niveaux de log**:
- `DEBUG`: Détails techniques
- `INFO`: Actions normales
- `WARNING`: Situations inhabituelles
- `ERROR`: Erreurs récupérables
- `CRITICAL`: Erreurs critiques

### Validation Multi-Niveaux

```python
from trade_validator import trade_validator, TradeValidationLevel

# STRICT: Production, validation maximale
result = trade_validator.validate(trade_params, TradeValidationLevel.STRICT)

# NORMAL: Défaut, validation standard
result = trade_validator.validate(trade_params, TradeValidationLevel.NORMAL)

# RELAXED: Développement uniquement
result = trade_validator.validate(trade_params, TradeValidationLevel.RELAXED)
```

---

## 🧪 Testing & Débogage

### Mode TEST vs REAL

**MODE TEST** (recommandé pour développement):
- ✅ Simulation complète sans transactions réelles
- ✅ Données réelles des traders (via Helius)
- ✅ Capital fictif de 1000$
- ✅ Pas de risque financier
- ✅ Logique identique au MODE REAL

**MODE REAL** (production uniquement):
- ⚠️ Exécution de vraies transactions Solana
- ⚠️ Risque de perte financière
- ⚠️ Nécessite une clé privée
- ⚠️ À utiliser avec extrême prudence

### Tester une Modification

```bash
# 1. Lancer en MODE TEST
python bot.py

# 2. Accéder à l'interface
# Ouvrir http://localhost:5000 dans le navigateur

# 3. Vérifier les logs dans la console
# Tous les print() s'affichent dans le terminal

# 4. Tester les routes API avec curl ou Postman
curl -X GET http://localhost:5000/api/dashboard
```

### Logs et Débogage

```python
# Console standard (pour développement)
print(f"🔍 DEBUG: variable = {variable}")
print(f"📊 État actuel: {json.dumps(state, indent=2)}")

# Audit logger (pour production)
audit_logger.log(
    level=LogLevel.DEBUG,
    event_type='DEBUG_INFO',
    message='État du système',
    metadata={'state': state}
)
```

### Points de Contrôle Importants

**À vérifier après chaque modification**:
1. Le bot démarre sans erreur
2. L'interface web s'affiche correctement
3. Les traders peuvent être activés/désactivés
4. Les métriques s'affichent dans le dashboard
5. Les logs sont clairs et informatifs
6. Pas de fuite mémoire (vérifier avec long running)

---

## 🌐 API & Routes

### Routes API Principales

#### Dashboard & Monitoring
```
GET  /                          # Interface web principale
GET  /api/dashboard             # Données tableau de bord
GET  /api/bot_status            # Statut du bot
POST /api/toggle_bot            # Activer/désactiver bot
```

#### Gestion des Traders
```
GET  /api/traders               # Liste des traders
POST /api/toggle_trader         # Activer/désactiver un trader
POST /api/edit_trader           # Modifier un trader
GET  /api/trader_performance    # Performance d'un trader
```

#### Trading
```
POST /api/execute_trade         # Exécuter un trade
GET  /api/positions             # Positions ouvertes
POST /api/sell_position         # Vendre une position (manuel)
GET  /api/trading_history       # Historique des trades
```

#### Backtesting & Benchmark
```
POST /api/backtest              # Lancer un backtesting
GET  /api/backtest_results      # Résultats backtesting
GET  /api/benchmark             # Classement benchmark
GET  /api/benchmark_details     # Détails benchmark
```

#### Configuration
```
GET  /api/config                # Configuration actuelle
POST /api/update_config         # Mettre à jour config
POST /api/update_tp_sl          # Mettre à jour TP/SL
POST /api/toggle_mode           # Basculer TEST/REAL
```

#### Monitoring & Metrics
```
GET  /api/metrics               # Métriques système
GET  /api/performance           # Métriques de performance
GET  /api/health                # Santé du système
GET  /api/alerts                # Alertes actives
```

#### Sécurité & Wallet
```
POST /api/set_wallet            # Configurer wallet (MODE REAL)
POST /api/disconnect_wallet     # Déconnecter wallet
GET  /api/wallet_balance        # Balance du wallet
```

### Format des Réponses API

**Succès**:
```json
{
  "success": true,
  "data": {
    "key": "value"
  },
  "timestamp": "2025-11-26T10:30:00Z"
}
```

**Erreur**:
```json
{
  "success": false,
  "error": "Message d'erreur descriptif",
  "timestamp": "2025-11-26T10:30:00Z"
}
```

---

## 💾 Base de Données

### Schema SQLite (`bot_data.db`)

**Table `trades`**:
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trader_name TEXT NOT NULL,
    trader_address TEXT NOT NULL,
    signature TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,              -- 'BUY' ou 'SELL'
    token_address TEXT NOT NULL,
    amount REAL NOT NULL,
    price REAL,
    pnl REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    mode TEXT NOT NULL                -- 'TEST' ou 'REAL'
);
```

**Table `positions`**:
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id TEXT UNIQUE NOT NULL,
    trader_name TEXT NOT NULL,
    token_address TEXT NOT NULL,
    entry_price REAL NOT NULL,
    current_price REAL,
    amount REAL NOT NULL,
    pnl REAL,
    status TEXT NOT NULL,            -- 'OPEN', 'CLOSED', 'PARTIAL'
    opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME
);
```

**Table `performance`**:
```sql
CREATE TABLE performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trader_name TEXT NOT NULL,
    date DATE NOT NULL,
    pnl_daily REAL,
    pnl_total REAL,
    win_rate REAL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER
);
```

### Utilisation de `db_manager.py`

```python
from db_manager import db_manager

# Ajouter un trade
db_manager.add_trade({
    'trader_name': 'AlphaMoon',
    'trader_address': 'EQax...',
    'signature': 'abc123...',
    'type': 'BUY',
    'token_address': 'So11...',
    'amount': 100.0,
    'price': 1.23,
    'mode': 'TEST'
})

# Récupérer les positions ouvertes
positions = db_manager.get_open_positions()

# Récupérer les performances
performance = db_manager.get_performance('AlphaMoon')

# Nettoyage automatique (données > 30 jours)
db_manager.cleanup_old_data(days=30)
```

---

## 🎯 Recommandations pour Assistants IA

### Avant de Modifier le Code

1. **Lire ce fichier CLAUDE.md en entier**
2. **Consulter README.md** pour comprendre les fonctionnalités utilisateur
3. **Identifier les modules impactés** par la modification
4. **Vérifier les dépendances** entre modules
5. **Planifier les tests** en MODE TEST

### Pendant le Développement

1. **Respecter l'architecture existante** - Ne pas créer de nouvelles dépendances circulaires
2. **Suivre les conventions de code** - Style, nommage, commentaires
3. **Ajouter des logs appropriés** - Avec emojis pour la lisibilité
4. **Valider tous les inputs** - Sécurité avant tout
5. **Tester en MODE TEST d'abord** - Pas de surprises en production

### Après la Modification

1. **Tester toutes les fonctionnalités** - Pas seulement la nouvelle
2. **Vérifier les logs** - Pas d'erreurs ou warnings suspects
3. **Mettre à jour la documentation** - README.md et CLAUDE.md
4. **Commiter avec message clair** - Emoji + description
   ```bash
   git commit -m "✨ Ajout: Nouvelle fonctionnalité XYZ"
   git commit -m "🐛 Fix: Correction bug dans module ABC"
   git commit -m "📝 Docs: Mise à jour CLAUDE.md"
   ```

### Emojis pour Commits Git

```
✨ Nouvelle fonctionnalité
🐛 Correction de bug
📝 Documentation
🎨 Amélioration UI/UX
⚡ Optimisation performance
🔒 Sécurité
🧪 Tests
🔧 Configuration
♻️ Refactoring
🚀 Déploiement
```

### Cas d'Usage Fréquents

**Ajouter un nouveau trader**:
- Modifier directement `config.json` (section `traders`)
- OU utiliser l'interface web (onglet Gestion Traders)

**Modifier les paramètres TP/SL**:
- Onglet Paramètres de l'interface web
- OU modifier `config.json` (sections `tp*_percent`, `tp*_profit`, `sl_*`)

**Ajouter une nouvelle métrique de monitoring**:
- Modifier `monitoring.py`
- Ajouter la route API dans `bot.py`
- Mettre à jour l'interface web

**Supporter un nouveau DEX**:
- Modifier `dex_handler.py`
- Ajouter la logique de parsing des transactions
- Tester en MODE TEST

---

## 📊 État Actuel du Projet (Phase 8)

### Phases Complétées

#### Phase 1 - Foundation ✅
- Intégration Solana RPC réelle
- API Helius pour parsing enrichi
- Validation adresses Solana
- Gestion sécurisée des clés API

#### Phase 2 - Execution ✅
- Gestion wallet + transactions
- Support multi-DEX (Raydium, Orca, Jupiter)
- Routes API d'exécution
- Cache + throttling RPC

#### Phase 3 - Safety ✅
- Validation 3 niveaux (STRICT/NORMAL/RELAXED)
- TP/SL automatiques, gestion risque
- Logging audit trail sécurisé
- Routes API de sécurité

#### Phase 4 - Monitoring ✅
- Métriques temps réel + alertes
- Performance tracking (win rate, PnL)
- Santé système et RPC
- Statistiques DEX

#### Phase 5 - Real Copy Trading Simulation ✅
- Simulation copy trading avec vraies données
- Capital fictif 1000$
- Calcul PnL réel
- Support complet MODE TEST

#### Phase 6 - Backtesting, Benchmark & Auto Sell ✅
- Backtesting 30+ combinaisons TP/SL
- Benchmark Bot vs Traders avec classement
- Auto-sell automatique + Mode Mirror
- 6 onglets UI intégrés
- SQLite persistence 30+ jours

#### Phase 7 - Performance Optimizations ✅
- Batch RPC requests (-60% latence)
- Workers parallèles (4 threads)
- Smart TP/SL adaptatifs
- Détection arbitrage multi-DEX

#### Phase 8 - Advanced Features ✅
- Risk Manager avec analyse corrélations
- Analytics avancées avec ML
- Backtesting amélioré (10x plus rapide)
- Dashboard analytics enrichi

### Roadmap Future (Possibilités)

#### Phase 9+ (À Discuter)
- [ ] Prédictions ML / Trading signals
- [ ] Support multiples blockchains (Ethereum, BSC)
- [ ] Intégrations alertes (Telegram, Discord)
- [ ] Dashboard d'analyse approfondie
- [ ] Export PDF/CSV rapports
- [ ] Mode Paper Trading avancé
- [ ] API publique pour développeurs tiers

---

## 🤝 Support & Questions

### Pour les Utilisateurs
- 📧 Issues GitHub: https://github.com/minculusofia-wq/bot-du-millionaire/issues
- 📖 Documentation: README.md

### Pour les Développeurs / Assistants IA
- 📚 Architecture: Ce fichier (CLAUDE.md)
- 🔧 Setup local: SETUP_LOCAL.md
- 🧪 Tests: TEST_REPORT.md
- 💬 Configuration Replit: replit.md

---

## 📜 Licence & Avertissement

**Licence**: Usage Personnel - Non-Commercial

### ⚠️ DISCLAIMER IMPORTANT

1. **Aucune Garantie**
   - Ce projet est fourni "tel quel" sans garantie d'aucune sorte
   - L'auteur n'est pas responsable des pertes financières

2. **Risques Financiers**
   - Le trading comporte des risques de perte en capital
   - Ne tradez que ce que vous pouvez vous permettre de perdre
   - Testez TOUJOURS en MODE TEST avant MODE REAL

3. **Usage Éducatif**
   - Projet à but éducatif et personnel
   - Pas de droits commerciaux
   - Ne pas revendre ou commercialiser

---

## 📅 Dernière Mise à Jour

**Date**: 26 novembre 2025
**Version**: 4.0.0 (Phase 8 complétée)
**Auteur**: Bot du Millionnaire Team
**Status**: ✅ Production-Ready

---

**Fait avec ❤️ pour la communauté Solana**

---

*Ce fichier CLAUDE.md est conçu pour être lu par des assistants IA (Claude, GPT, etc.) afin de comprendre rapidement la structure, l'architecture et les conventions du projet Bot du Millionnaire.*
