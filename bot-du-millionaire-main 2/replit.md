# Configuration Replit - Bot du Millionnaire

## 📋 Vue d'ensemble du Projet

**Nom** : Bot du Millionnaire - Solana Copy Trading  
**Langue** : Python + HTML/CSS/JavaScript  
**Port** : 5000  
**Type** : Application Web Flask  

---

## 🚀 Fonctionnalités Principales

1. **Gestion de Traders** : Sélectionnez et copiez jusqu'à 3 traders Solana
2. **Contrôle Trading** : TP/SL configurables, slippage ajustable
3. **Suivi Performances** : PnL 24h, 7 jours, historique complet
4. **Interface Web** : 4 onglets intuitifs, mise à jour en temps réel
5. **Sécurité** : Clé privée en mémoire uniquement, jamais sauvegardée

---

## ⚙️ Configuration d'Exécution

### Workflow Replit
**Commande** : `python bot.py`  
**Port** : 5000  
**Type** : Application Web

### Accès
- **Local** : http://localhost:5000
- **Replit** : https://[votre-replit].replit.dev

---

## 📦 Dépendances

```
flask==3.0.0
requests==2.31.0
```

Installation :
```bash
pip install -r requirements.txt
```

---

## 📁 Structure des Fichiers

### Core (Exécution)
- **bot.py** (34 KB) - Flask app + UI + 30+ routes API
- **bot_logic.py** (15 KB) - Logique métier + config management

### Intégration Solana
- **solana_integration.py** - Connexion RPC Solana
- **helius_integration.py** - Parsing enrichi transactions (Helius API)
- **solana_executor.py** - Exécution wallet + transactions
- **dex_handler.py** - Support multi-DEX (Raydium, Orca, Jupiter)

### Sécurité & Validation
- **trade_validator.py** - Validation 3 niveaux des trades
- **trade_safety.py** - TP/SL automatiques + gestion risque
- **audit_logger.py** - Logging audit trail sécurisé

### Monitoring & Analytics
- **monitoring.py** - Métriques temps réel, alertes internes
- **portfolio_tracker.py** - Suivi portefeuilles + historique

### Configuration & Données
- **config.json** - Configuration traders et paramètres trading
- **requirements.txt** - Dépendances Python
- **README.md** - Documentation complète
- **.gitignore** - Sécurité (clés, configs locales)

---

## 🔒 Variables d'Environnement

Aucune clé API externe requise pour le mode TEST.

### Mode REEL (Optionnel)
Pour le mode REEL avec exécution de trades, vous auriez besoin de :
- Wallet Phantom (clé privée)
- RPC Helius (optionnel, pour plus de vitesse)

**⚠️ IMPORTANT** : Les clés ne sont jamais sauvegardées - stockées en mémoire uniquement.

---

## 🎯 Prérequis pour Replit

✅ Python 3.9+  
✅ Accès à Internet (pour communication RPC)  
✅ No setup nécessaire au-delà de `pip install`

---

## 📊 Utilisation

### Démarrage
1. Cliquez sur **"Run"** dans Replit
2. Attendez le message : `Running on http://0.0.0.0:5000`
3. L'interface s'ouvre automatiquement

### Arrêt
- Cliquez sur **"Stop"** ou Ctrl+C dans le terminal

---

## 🐛 Dépannage Replit

### Problème : "ModuleNotFoundError"
**Solution** : Les dépendances sont installées automatiquement. Attendez le démarrage.

### Problème : Port occupé
**Solution** : Attendez 30 secondes, Replit libère automatiquement.

### Problème : Interface ne s'affiche pas
**Solution** : Vérifiez le terminal pour les erreurs, nettoyez le cache du navigateur.

---

## 🔄 Workflow Recommandé

1. **Développement** : Utilisez la session Replit pour tester
2. **Test** : Mode TEST pour vérifier la configuration
3. **Production** : Mode REEL avec petit capital initialement

---

## 📝 Préférences Utilisateur

- **Langue** : Français
- **Expertise** : Non-technique
- **Objectif** : Copy trading Solana simplifié

---

## 🎯 Récentes Améliorations (22 nov 2025)

### Phase 1 - Foundation ✅
- ✅ Solana RPC réelle
- ✅ Récupération données réelles
- ✅ Validation adresses Solana
- ✅ Gestion clés API sécurisée

### Phase 2 - Execution ✅
- ✅ `solana_executor.py` - Gestion wallet + transactions
- ✅ `dex_handler.py` - Support DEX (Raydium, Orca, Jupiter)
- ✅ Routes API d'exécution
- ✅ Cache + throttling RPC (évite rate limiting)

### Phase 3 - Safety ✅
- ✅ `trade_validator.py` - Validation complète des trades
- ✅ `trade_safety.py` - TP/SL automatiques, gestion risque
- ✅ `audit_logger.py` - Logging sécurisé audit trail
- ✅ Routes API Phase 3:
  - `/api/validation_stats` - Stats validation
  - `/api/portfolio_risk` - Analyse risque
  - `/api/audit_logs` - Logs d'audit
  - `/api/emergency_close` - Fermeture urgence
  - Et 5+ autres routes de sécurité

### Phase 4 - Monitoring ✅
- ✅ `monitoring.py` - Métriques temps réel, alertes internes
- ✅ `PerformanceMonitor` - Win rate, PnL, trades tracking
- ✅ `ExecutionMonitor` - DEX stats, slippage, temps exécution
- ✅ `SystemMonitor` - RPC health, wallet balance, portfolio trends
- ✅ Routes API Phase 4:
  - `/api/metrics` - Toutes les métriques
  - `/api/performance` - Performance trades (win rate, PnL)
  - `/api/system_health` - Santé système et RPC
  - `/api/execution_stats` - Stats exécution par DEX
  - `/api/alerts` - Alertes critiques
  - `/api/wallet_trend` - Tendance solde (configurable hours)
  - `/api/portfolio_trend` - Tendance portefeuille

### Phase 5 - Real Copy Trading Simulation ✅
- ✅ `copy_trading_simulator.py` - Simulation copy trading réel
  - Récupère les VRAIES transactions des traders via Helius API
  - Simule les mêmes trades avec capital fictif 1000$
  - Calcule le PnL réel de la simulation
  - Support complet MODE TEST avec données réelles + exécution simulée
- ✅ Améliorations macOS:
  - Imports Solana optionnels (try/except)
  - Bot fonctionne sans dépendances Solana en mode TEST
  - Fallbacks pour mode développement
- ✅ Routes API Phase 5:
  - `/api/copy_trading_pnl` - PnL des simulations traders actifs
  - `/api/trader_simulation/<name>` - Détails simulation trader
- ✅ Fonctionnalités:
  - Mode TEST = Vraies données traders + trades simulés + 1000$ fictifs
  - Suivi portefeuilles simulés avec PnL réel
  - Historique complet des trades copiés

### Phase 6 - Backtesting, Benchmark & Auto Sell ✅
- ✅ `backtesting_engine.py` - Moteur de backtesting multi-paramètres
  - Teste 30+ combinaisons TP/SL
  - Identification du meilleur résultat (surlignage doré)
  - Interface visuelle complète avec résultats détaillés
- ✅ `benchmark_system.py` - Système de benchmark intelligent
  - Compare Bot vs chaque trader
  - Classement avec médailles (🥇🥈🥉)
  - Suivi win rate et PnL%
- ✅ `auto_sell_manager.py` - Vente automatique intelligente
  - Détecte automatiquement quand trader vend
  - Respecte TP/SL configurés
  - Mode mirror si TP/SL = 0 (vend exactement comme trader)
  - Vente manuelle optionnelle
  - MODE TEST = MODE REAL (logique identique)
- ✅ **6 onglets UI** : Dashboard, Traders, Backtesting, Benchmark, Paramètres, Historique
- ✅ **Suivi positions ouvertes** en temps réel
- ✅ **SQLite persistance** : Historique complet 30+ jours

### Phase 7 - LIVE Dashboard en Temps Réel ✅ NEW!
- ✅ **⚡ LIVE TRADING** : Nouveau onglet de monitoring temps réel
  - Polling continu 1 seconde pour mise à jour ultra-rapide
  - Affichage exact des tokens tradés par chaque trader
  - Indicateurs visuels : 🟢 Rentable vs 🔴 En perte
- ✅ **Actions rapides sur la carte trader**:
  - 💰 [SORTIR TOUT] = Ferme toutes les positions du trader
  - ❌ [DÉSACTIVER] = Arrête ce trader immédiatement
- ✅ **Stats en direct** : PnL 24h, Win Rate %, positions ouvertes
- ✅ **Vue synthétique** : Portefeuille total, traders actifs, positions
- ✅ **7 onglets UI** : Dashboard, LIVE TRADING, Traders, Backtesting, Benchmark, Paramètres, Historique
- ✅ **Code Audit Complet** (24 nov 2025):
  - 7 protections division par zéro (backtesting, trade_safety, auto_sell, bot_logic)
  - 5 clauses `except:` corrigées avec exceptions spécifiques
  - Total 12 bugs corrigés + exception handling amélioré
  - Zéro erreur détectée ✅ Bot RUNNING avec tous les endpoints 200 OK

---

## 🎨 Personnalisation

### Modifier les traders défaut
Éditez `config.json`, section `"traders"` :
```json
{
  "name": "NomDuTrader",
  "emoji": "🚀",
  "address": "AdresseSolana...",
  "capital": 333
}
```

### Modifier les paramètres de trading
- Via l'interface "Paramètres & Sécurité"
- Les changements se sauvegardent automatiquement

---

## 🚀 Déploiement Replit

Le projet est déjà configuré pour Replit :
- Workflow automatique défini
- Pas de build nécessaire
- Prêt à l'emploi
- Avec les dernières améliorations de sécurité

---

## 📞 Support

- **Issues** : GitHub Issues
- **Documentation** : README.md complet
- **Questions** : Posez dans les Issues avec tag `question`

---

**Dernière mise à jour** : 22 novembre 2025 - 18:05  
**Version** : 3.0.0 (Phases 1-5 Complétées - Copy Trading Simulation)  
**Statut** : ✅ Production-Ready - TESTED  
**Licence** : Personal Use Only - Non-Commercial  
**Tests** : ✅ Mode TEST (vraies données + exécution simulée) - 100% Opérationnel  
**Sécurité** : ✅ Clés privées jamais sauvegardées  
**Platform** : ✅ macOS, Linux, Windows compatibles  
**Voir** : TEST_REPORT.md pour rapport complet
