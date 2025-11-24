# Bot du Millionnaire - Solana Copy Trading 🚀

**Bot de copy trading automatisé pour la blockchain Solana** avec interface graphique moderne et surveillance en temps réel des portefeuilles.

> **État du Projet** : ✅ Complet et Fonctionnel

---

## 📊 Fonctionnalités Principales

### 🎯 Gestion des Traders
- ✅ **10 traders pré-configurés** avec adresses Solana
- ✅ **Limite de 3 traders actifs** simultanément
- ✅ **Édition en temps réel** : Modifier Nom, Emoji et Adresse
- ✅ **Surbrillance visuelle** des traders sélectionnés
  - 🟢 Bordure verte sur la liste des traders
  - 🟢 Surlignage dans le tableau de bord avec indicateur ✅

### 🤖 Achat & Vente AUTOMATIQUE (Core du Bot)
- ✅ **Trader achète** → **Bot achète AUTOMATIQUEMENT** (capital alloué)
- ✅ **Trader vend** → **Bot vend AUTOMATIQUEMENT**
- ✅ **Respect TP/SL** : Si configurés, le bot applique les Take Profit/Stop Loss
- ✅ **Mode Mirror** : Si TP/SL = 0, bot vend exactement comme le trader
- ✅ **Vente manuelle** : Bonus optionnel - bouton 💰 Vendre par position
- ✅ **Mode TEST = MODE REAL** : Logique identique dans les deux modes

### 💰 Contrôle Trading Avancé
- ✅ **3 Take Profit configurables** (TP1, TP2, TP3)
  - TP1 : 33% de position à +10% de profit
  - TP2 : 33% de position à +25% de profit  
  - TP3 : 34% de position à +50% de profit

- ✅ **Stop Loss amélioré** (structure identique aux TP)
  - SL : 100% de position à -5% de perte
  - Configuration flexible

- ✅ **Slippage réglable** : 0.1% à 100%
- ✅ **Mode USD/SOL** : Changement instantané

### 🎮 Backtesting Avancé
- ✅ **Onglet Backtesting** complet avec interface visuelle
- ✅ **Tester tous les paramètres TP/SL** (30+ combinaisons)
- ✅ **Affichage résultats en temps réel** : Win Rate, PnL, Trades
- ✅ **Identification meilleur résultat** avec surlignage doré
- ✅ **Données réelles** : Backtesting basé sur les vraies transactions

### 🏆 Benchmark Intelligent
- ✅ **Onglet Benchmark** : Comparer Bot vs Traders
- ✅ **Classement complet** avec médailles 🥇🥈🥉
- ✅ **Performances détaillées** : PnL%, Win Rate, Classement
- ✅ **Identification meilleur trader** automatique
- ✅ **Mise à jour en temps réel**

### 📈 Tableau de Bord Complet
- **Performance en temps réel** avec PnL total
- **Graphique d'évolution** du portefeuille
- **4 statistiques clés** :
  - Trades détectés
  - PnL Total
  - Performance Bot (%)
  - Traders Actifs

### 📊 Suivi des Performances
- **PnL Total** : Performance globale depuis le début
- **PnL 24h** : Performance sur les dernières 24 heures
- **PnL 7j** : Performance sur 7 jours
- **Tableau détaillé** avec valeur actuelle de chaque trader
- **Historique automatique** : Nettoyage après 8 jours

### 🔒 Sécurité Renforcée
- ✅ **Clé privée** stockée en mémoire uniquement (session)
- ✅ **Jamais sauvegardée** sur le disque
- ✅ **Déconnexion sécurisée** avec effacement immédiat

### 🌐 Interface Web Moderne
- ✅ **6 onglets** : Tableau de Bord, Gestion Traders, 🎮 Backtesting, 🏆 Benchmark, Paramètres, Historique
- ✅ **Thème sombre** professionnel
- ✅ **Responsive** : Fonctionne sur desktop et mobile
- ✅ **Animations fluides** et navigation intuitive
- ✅ **Mise à jour en temps réel** (chaque seconde)
- ✅ **Suivi des positions ouvertes** en direct

---

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- macOS, Linux ou Windows
- pip (gestionnaire de paquets Python)

### Étape 1 : Télécharger le projet
```bash
# Option 1 : Cloner depuis GitHub
git clone https://github.com/minculusofia-wq/bot-du-millionaire.git
cd bot-du-millionaire

# Option 2 : Télécharger le ZIP
# Accédez à https://github.com/minculusofia-wq/bot-du-millionaire
# Cliquez sur "Code" → "Download ZIP"
# Décompressez et ouvrez le dossier
```

### Étape 2 : Installer les dépendances
```bash
pip install -r requirements.txt
```

### Étape 3 : Lancer l'application

#### Sur macOS
```bash
chmod +x "Lancer le Bot.command"
./"Lancer le Bot.command"
```

#### Sur Linux/Windows
```bash
python bot.py
```

L'application s'ouvrira à : **http://localhost:5000**

---

## 📖 Mode d'Emploi

### 1️⃣ Tableau de Bord
- **Activez le bot** avec le bouton "Activer/Désactiver Bot"
- **Visualisez** le PnL en temps réel
- **Consultez** les statistiques : trades, performance, traders actifs
- **Surveillez** l'évolution avec le graphique

### 2️⃣ Gestion des Traders
- **Cochez** jusqu'à 3 traders pour les activer
- **Observez** la surbrillance verte quand un trader est sélectionné
- **Éditez** les traders avec le bouton ✏️
  - Changez le nom, emoji ou adresse
  - Les modifications se sauvegardent automatiquement

### 3️⃣ Paramètres & Sécurité
- **Slippage** : Ajustez avec le curseur (0.1% - 100%)
- **Take Profit** : 3 niveaux configurables
  - % de position à vendre
  - % de profit cible
- **Stop Loss** : Configuration flexible
  - % de position à vendre en cas de perte
  - % de perte à laquelle déclencher le SL
- **Clé Privée** : Collez uniquement en mode REEL
  - Stockée en mémoire uniquement (jamais sauvegardée)
  - Déconnexion sécurisée disponible

### 4️⃣ Historique
- **Tous les trades** détectés avec horodatage
- **Performances** : PnL et % par trade
- **Signatures** : Pour vérification sur l'explorateur

---

## 📁 Structure du Projet

```
bot-du-millionaire/
├── bot.py                      # Application Flask principale + Interface UI
├── bot_logic.py               # Logique métier et gestion des configurations
├── portfolio_tracker.py       # Suivi des portefeuilles en temps réel
├── config.json                # Configuration (traders, TP/SL, etc.)
├── config_tracker.json        # Données de suivi des portefeuilles
├── portfolio_tracker.json     # Historique des performances
├── requirements.txt           # Dépendances Python
├── Lancer le Bot.command      # Script de lancement macOS
├── .gitignore                 # Fichiers ignorés par Git
├── README.md                  # Documentation
└── replit.md                  # Configuration Replit
```

---

## ⚙️ Configuration

### `config.json`
Les paramètres principaux sont sauvegardés automatiquement :

```json
{
  "mode": "TEST",
  "slippage": 1.0,
  "active_traders_limit": 3,
  "currency": "USD",
  "tp1_percent": 33,
  "tp1_profit": 10,
  "tp2_percent": 33,
  "tp2_profit": 25,
  "tp3_percent": 34,
  "tp3_profit": 50,
  "sl_percent": 100,
  "sl_loss": 5,
  "traders": [...]
}
```

---

## 🔒 Sécurité - IMPORTANT ⚠️

### ✅ À FAIRE
- ✅ Utiliser un wallet dédié au copy trading (pas le wallet principal)
- ✅ Copiez uniquement les traders de confiance
- ✅ Testez d'abord en mode TEST

### ❌ NE PAS FAIRE
- ❌ **NE JAMAIS** commiter `config.json` sur GitHub
- ❌ **NE JAMAIS** partager votre clé privée
- ❌ **NE JAMAIS** utiliser votre wallet principal
- ❌ **NE JAMAIS** laisser le bot sans surveillance en mode REEL

---

## 🛠️ Mode TEST vs REEL

### Mode TEST
- **Simulation** des trades basée sur les portefeuilles réels
- **Pas de transactions réelles**
- **Parfait pour tester** la configuration
- **Activation** : Onglet "Paramètres" → "Basculer Mode TEST/REEL"

### Mode REEL
- **Exécution de vrais trades**
- **Risque de perte réelle**
- **Nécessite une clé privée**
- ⚠️ À utiliser avec prudence

---

## 📈 Améliorations Récentes (Phase 1-6)

### Phase 1: Foundation ✅
- ✅ Intégration Solana RPC réelle
- ✅ API Helius pour parsing enrichi des transactions
- ✅ Validation adresses Solana
- ✅ Gestion sécurisée des clés API

### Phase 2: Execution ✅
- ✅ `solana_executor.py` - Gestion wallet + transactions
- ✅ `dex_handler.py` - Support multi-DEX (Raydium, Orca, Jupiter)
- ✅ Routes API pour exécution trades
- ✅ Cache + throttling RPC (évite rate limiting)

### Phase 3: Safety ✅
- ✅ `trade_validator.py` - Validation 3 niveaux (STRICT/NORMAL/RELAXED)
- ✅ `trade_safety.py` - TP/SL automatiques + gestion risque
- ✅ `audit_logger.py` - Logging audit trail sécurisé
- ✅ 9 routes API sécurité avancée

### Phase 4: Monitoring ✅
- ✅ `monitoring.py` - Métriques temps réel + alertes
- ✅ PerformanceMonitor - Win rate, PnL, tracking trades
- ✅ ExecutionMonitor - Stats DEX, slippage, timing
- ✅ SystemMonitor - RPC health, wallet balance trends
- ✅ 7 routes API métriques + tendances

### Phase 5: Real Copy Trading Simulation ✅
- ✅ **copy_trading_simulator.py** : Simulation copy trading réel
- ✅ Récupère les **VRAIES transactions** des traders via Helius API
- ✅ Simule les mêmes trades avec capital fictif **1000$**
- ✅ Calcule le **PnL réel** de la simulation
- ✅ Support complet **MODE TEST** avec données réelles + exécution simulée
- ✅ Routes API : `/api/copy_trading_pnl` et `/api/trader_simulation/<name>`

### Phase 6: Backtesting, Benchmark & Auto Sell ✅ NEW!
- ✅ **backtesting_engine.py** : Moteur de backtesting multi-paramètres
  - Teste 30+ combinaisons TP/SL
  - Identification du meilleur résultat
  - Interface visuelle avec résultats détaillés
  
- ✅ **benchmark_system.py** : Système de benchmark intelligent
  - Compare Bot vs chaque trader
  - Classement avec médailles (🥇🥈🥉)
  - Suivi win rate et PnL%
  
- ✅ **auto_sell_manager.py** : Vente automatique intelligente
  - Détecte automatiquement quand trader vend
  - Respecte TP/SL configurés
  - Mode mirror si TP/SL = 0 (vend exactement comme trader)
  - Vente manuelle optionnelle
  - MODE TEST = MODE REAL (logique identique)

- ✅ **6 onglets UI** : Dashboard, Traders, Backtesting, Benchmark, Paramètres, Historique
- ✅ **Suivi positions ouvertes** en temps réel
- ✅ **SQLite persistance** : 30+ jours historique

---

## 🐛 Dépannage

### Problème : "ModuleNotFoundError: No module named 'flask'"
**Solution** : 
```bash
pip install flask requests
```

### Problème : Port 5000 déjà utilisé
**Solution** : Modifiez le port dans `bot.py` à la dernière ligne

### Problème : L'interface ne s'affiche pas
**Solution** : 
- Vérifiez que le serveur démarre (look for "Running on http://")
- Accédez à http://localhost:5000 dans le navigateur
- Nettoyez le cache (Ctrl+Shift+Delete)

---

## 🤝 Contribution

Les contributions sont bienvenues ! Pour proposer une amélioration :

1. **Forkez** le projet
2. **Créez une branche** : `git checkout -b feature/ma-feature`
3. **Commitez** : `git commit -m "✨ Ajout de ma-feature"`
4. **Poussez** : `git push origin feature/ma-feature`
5. **Ouvrez une Pull Request**

---

## 📞 Support & Questions

- 📧 **Issues GitHub** : Signalez des bugs ou proposez des features
- 💬 **Discussions** : Posez vos questions

---

## 📄 Licence

**Projet Personnel - Usage Personnel Uniquement**

### ⚠️ Conditions :
- ✅ Usage personnel non-commercial uniquement
- ✅ Vous pouvez modifier le code pour vous-même
- ✅ Vous ne pouvez pas le commercialiser ou vendre
- ❌ Aucune responsabilité de l'auteur
- ❌ Pas de droits commerciaux

**Note** : Ce projet est un développement personnel et ne doit pas être utilisé à des fins commerciales.

---

## ✅ Phases Complétées

### Phase 1 - Foundation ✅
- Solana RPC réelle
- Récupération données réelles
- Validation adresses Solana
- Gestion clés API sécurisée

### Phase 2 - Execution ✅
- Gestion wallet + transactions
- Support DEX (Raydium, Orca, Jupiter)
- Routes API d'exécution
- Cache + throttling RPC

### Phase 3 - Safety ✅
- Validation complète des trades
- TP/SL automatiques, gestion risque
- Logging sécurisé audit trail
- Routes API de sécurité

### Phase 4 - Monitoring ✅
- Métriques temps réel
- Performance tracking (win rate, PnL)
- Santé système et RPC
- Statistiques DEX

### Phase 5 - Real Copy Trading Simulation ✅
- **copy_trading_simulator.py** : Simulation copy trading réel
- Récupère les **VRAIES transactions** des traders via Helius API
- Simule les mêmes trades avec capital fictif **1000$**
- Calcule le **PnL réel** de la simulation
- Support complet **MODE TEST** avec données réelles + exécution simulée

### Phase 6 - Backtesting, Benchmark & Auto Sell ✅ NEW!
- **backtesting_engine.py** : 30+ combinaisons TP/SL testables
- **benchmark_system.py** : Classement Bot vs Traders avec médailles
- **auto_sell_manager.py** : Vente automatique + Mode Mirror
- **6 onglets UI** : Interface complète intégrée
- **SQLite persistence** : Historique complet 30+ jours

## ⚡ Roadmap Futur

### Phase 7+ (Possibilités)
- [ ] Prédictions ML / Trading signals
- [ ] Support de multiples blockchains
- [ ] Intégrations API tierces (Telegram, Discord alertes)
- [ ] Dashboard d'analyse approfondie
- [ ] Export PDF/CSV rapports

---

## 🎯 Objectif du Projet

Créer un bot de copy trading simple et sécurisé pour débutants qui veulent automatiser leur trading Solana sans complexité excessive.

---

**Dernière mise à jour** : 24 novembre 2025  
**Version** : 4.0.0 (Phases 1-6 Complétées - Backtesting, Benchmark & Auto Sell)  
**Statut** : ✅ Production-Ready  
**Mode TEST** : ✅ Vraies données + Exécution simulée (1000$ fictifs)  
**Auto Sell** : ✅ Automatique + Respect TP/SL + Mode Mirror  
**Backtesting** : ✅ 30+ paramètres testables  
**Benchmark** : ✅ Classement Bot vs Traders  
**Plateforme** : ✅ macOS, Linux, Windows  
**Licence** : Personnel - Non-Commercial

---

Made with ❤️ for the Solana community
