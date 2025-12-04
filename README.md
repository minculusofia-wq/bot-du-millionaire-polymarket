# Bot du Millionnaire - Polymarket Copy Trading + Solana Arbitrage 🚀

**Bot de copy trading automatisé pour Polymarket** avec **arbitrage multi-DEX Solana** et interface graphique moderne.

> **État du Projet** : ✅ Complet et Fonctionnel (Refonte v5.0)

---

## 📊 Fonctionnalités Principales

### 🎯 Polymarket Copy Trading
- ✅ **Suivi de wallets Polymarket** (Polygon)
- ✅ **Copie automatique des trades** des wallets suivis
- ✅ **Dry Run mode** : Simulation sans risque
- ✅ **Gestion des positions** : Min/Max USD configurables
- ✅ **Pourcentage de copie** : Ajustable (1-100%)
- ✅ **Statistiques en temps réel** : Signaux détectés, trades copiés, profit total, win rate

### 💰 Arbitrage Multi-DEX Solana
- ✅ **3 DEX supportés** : Jupiter, Raydium, Orca
- ✅ **Détection automatique** des opportunités d'arbitrage
- ✅ **Capital dédié séparé** du copy trading
- ✅ **Configuration avancée** :
  - Seuil de profit minimum (%)
  - Montant min/max par trade
  - Cooldown entre trades
  - Max trades simultanés
  - Blacklist de tokens
- ✅ **Statistiques live** : Opportunités trouvées, win rate, profit total

### 🌐 Interface Web Moderne (6 Onglets)

1. **Dashboard** - Vue d'ensemble Polymarket + Arbitrage
2. **Live Trading** - Trades Polymarket en temps réel
3. **Wallets Suivis** - Gestion des wallets à copier
4. **Historique** - Historique complet des trades
5. **Arbitrage** - Stats et opportunités Solana
6. **Paramètres** - Configuration wallets et options

### 🔐 Double Wallet System
- **Wallet Polymarket** (Polygon) : Pour le copy trading sur Polymarket
- **Wallet Solana** : Exclusivement pour l'arbitrage multi-DEX

---

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- macOS, Linux ou Windows
- pip (gestionnaire de paquets Python)

### Étape 1 : Télécharger le projet
```bash
git clone https://github.com/votre-repo/bot-du-millionaire.git
cd bot-du-millionaire
```

### Étape 2 : Installer les dépendances
```bash
pip install -r requirements.txt
```

### Étape 3 : Configurer l'environnement
```bash
cp .env.example .env
# Éditez .env avec vos clés API
```

### Étape 4 : Lancer l'application

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

### 1️⃣ Dashboard
- **Activez le bot** avec le toggle principal
- **Visualisez** les stats Polymarket et Arbitrage
- **Surveillez** les performances en temps réel

### 2️⃣ Wallets Suivis (Polymarket)
- **Ajoutez** des adresses de wallets Polymarket à suivre
- **Donnez un nom** à chaque wallet pour l'identifier
- **Supprimez** les wallets que vous ne souhaitez plus suivre

### 3️⃣ Paramètres
- **Wallet Polymarket** : Configurez votre adresse Polygon
- **Wallet Solana** : Configurez votre adresse pour l'arbitrage
- **Polymarket Config** :
  - Dry Run (simulation)
  - Intervalle de polling
  - Position min/max USD
  - Pourcentage de copie
- **Arbitrage Config** :
  - Capital dédié
  - Seuil de profit minimum
  - Montants min/max par trade
  - Cooldown et limites

### 4️⃣ Arbitrage
- **Activez/Désactivez** l'arbitrage Solana
- **Consultez** les opportunités détectées
- **Suivez** les statistiques de performance

---

## 📁 Structure du Projet

```
bot-du-millionaire/
├── bot.py                      # Application Flask principale + Interface UI
├── bot_logic.py                # Logique métier et gestion config
├── config.json                 # Configuration principale
├── arbitrage_engine.py         # Moteur d'arbitrage multi-DEX
├── polymarket_bot.py           # Bot Polymarket copy trading
├── polymarket_executor.py      # Exécuteur d'ordres Polymarket
├── polymarket_tracking.py      # Tracking des wallets Polymarket
├── polymarket_wrapper.py       # Wrapper API Polymarket
├── solana_executor.py          # Exécution transactions Solana
├── solana_integration.py       # Intégration Solana RPC
├── dex_handler.py              # Handler multi-DEX
├── db_manager.py               # Gestionnaire SQLite
├── requirements.txt            # Dépendances Python
├── .env.example                # Template variables d'environnement
├── Lancer le Bot.command       # Script de lancement macOS
└── README.md                   # Documentation
```

---

## ⚙️ Configuration

### `config.json`
```json
{
  "is_running": false,
  "params_saved": false,
  "polymarket_wallet": {
    "address": "",
    "private_key": ""
  },
  "solana_wallet": {
    "address": "",
    "private_key": "",
    "rpc_url": "https://api.mainnet-beta.solana.com"
  },
  "polymarket": {
    "enabled": false,
    "dry_run": true,
    "tracked_wallets": [],
    "polling_interval": 30,
    "max_position_usd": 0,
    "min_position_usd": 0,
    "copy_percentage": 100
  },
  "arbitrage": {
    "enabled": false,
    "capital_dedicated": 0,
    "percent_per_trade": 0,
    "min_profit_threshold": 0.5,
    "min_amount_per_trade": 0,
    "max_amount_per_trade": 0,
    "cooldown_seconds": 60,
    "max_concurrent_trades": 3,
    "dex_list": ["raydium", "orca", "jupiter"],
    "blacklist_tokens": []
  }
}
```

### Variables d'environnement (`.env`)
```bash
# API Polymarket (optionnel pour lecture seule)
POLYMARKET_API_KEY=your_key
POLYMARKET_SECRET=your_secret
POLYMARKET_PASSPHRASE=your_passphrase

# Helius API (pour Solana)
HELIUS_API_KEY=your_helius_key
```

---

## 🔒 Sécurité - IMPORTANT ⚠️

### ✅ À FAIRE
- ✅ Utiliser des wallets dédiés (pas vos wallets principaux)
- ✅ Tester d'abord en mode Dry Run
- ✅ Configurer des limites de position raisonnables
- ✅ Surveiller régulièrement les performances

### ❌ NE PAS FAIRE
- ❌ **NE JAMAIS** commiter `config.json` avec des clés privées
- ❌ **NE JAMAIS** partager vos clés privées
- ❌ **NE JAMAIS** utiliser vos wallets principaux
- ❌ **NE JAMAIS** laisser le bot sans surveillance

---

## 🐛 Dépannage

### Problème : Port 5000 déjà utilisé
**Solution** :
```bash
# Libérer le port
lsof -ti:5000 | xargs kill -9
# Ou utiliser un autre port dans bot.py
```

### Problème : "ModuleNotFoundError"
**Solution** :
```bash
pip install -r requirements.txt
```

### Problème : Erreur Polymarket API
**Solution** :
- Vérifiez vos identifiants dans `.env`
- Le mode lecture seule fonctionne sans identifiants

---

## 🤝 Contribution

Les contributions sont bienvenues ! Pour proposer une amélioration :

1. **Forkez** le projet
2. **Créez une branche** : `git checkout -b feature/ma-feature`
3. **Commitez** : `git commit -m "✨ Ajout de ma-feature"`
4. **Poussez** : `git push origin feature/ma-feature`
5. **Ouvrez une Pull Request**

---

## 📄 Licence

**Projet Personnel - Usage Personnel Uniquement**

- ✅ Usage personnel non-commercial uniquement
- ✅ Vous pouvez modifier le code pour vous-même
- ❌ Pas de commercialisation ou vente
- ❌ Aucune responsabilité de l'auteur

---

## ⚡ Roadmap Futur

- [ ] Alertes Telegram/Discord
- [ ] Support de plus de DEX Solana
- [ ] Analytics avancées
- [ ] Export CSV/PDF des rapports
- [ ] Interface mobile

---

**Dernière mise à jour** : 4 décembre 2025
**Version** : 5.0.0 (Refonte Polymarket + Arbitrage)
**Statut** : ✅ Production-Ready
**Polymarket** : ✅ Copy Trading + Dry Run
**Arbitrage** : ✅ Multi-DEX (Jupiter, Raydium, Orca)
**Plateforme** : ✅ macOS, Linux, Windows
**Licence** : Personnel - Non-Commercial

---

Made with ❤️ for the crypto community
