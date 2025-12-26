# Bot du Millionnaire - Polymarket Copy Trading 🚀

**Bot de copy trading automatisé pour Polymarket** (Polygon).

> **État du Projet** : ✅ Fonctionnel - Mode Réel Uniquement

---

## 📊 Fonctionnalités Principales

### 🎯 Polymarket Copy Trading
- ✅ **Suivi de wallets Polymarket** (Polygon)
- ✅ **Copie automatique des trades** des wallets suivis
- ✅ **Exécution Réelle** : Trades placés directement sur le CLOB (Central Limit Order Book)
- ✅ **Gestion des positions** : Min/Max USD configurables
- ✅ **Pourcentage de copie** : Ajustable (1-100%)
- ✅ **Statistiques en temps réel** : Signaux détectés, trades copiés, profit total, win rate
- ✅ **Vente de positions** : Interface pour revendre partiellement ou totalement ses positions


### 🌐 Interface Web Moderne
1. **Dashboard** - Vue d'ensemble, status et graphiques PnL
2. **Live Trading** - Flux des trades en temps réel
3. **Wallets Suivis** - Gestion des "Whales" à copier (avec configs individuelles)
4. **Historique** - Historique complet des trades et PnL
5. **Paramètres** - Configuration API et gestion des risques

### ✨ Nouveautés v2
- **🧠 Kelly Criterion** : Gestion automatique de la taille de position basée sur la performance du trader.
- **🛡️ Trailing Stop** : Sécurisation des gains avec un SL dynamique qui suit le prix.
- **⚡ WebSocket Alchemy** : Détection ultra-rapide (<1s) des trades sur la blockchain.
- **📈 Graphiques PnL** : Visualisation de la performance sur 30 jours.
- **🔒 Sécurité** : Stockage chiffré des clés (plus de re-saisie à chaque lancement).

---

## 🚀 Installation

### Prérequis
- Python 3.9 ou supérieur
- Compte Polymarket avec clés API (pour le trading réel)
- Wallet Polygon (USDC)

### Installation
```bash
git clone https://github.com/votre-repo/bot-du-millionaire.git
cd bot-du-millionaire
pip install -r requirements.txt
```

### Configuration
1. Copiez le fichier d'exemple :
   ```bash
   cp .env.example .env
   ```
2. Configurez vos clés dans `.env` :
   ```bash
   # API Polymarket (Requis pour placer des ordres)
   POLYMARKET_API_KEY=votre_clé
   POLYMARKET_SECRET=votre_secret
   POLYMARKET_PASSPHRASE=votre_passphrase
   
   # Clé privée Polygon (Requis pour signer les tx)
   POLYGON_PRIVATE_KEY=votre_clé_privée
   ```

### Lancement
```bash
python bot.py
```
Accédez à l'interface sur : **http://localhost:5000**

---

## 🔒 Sécurité
- ⚠️ **Vos clés privées restent sur votre machine**. Elles ne sont jamais envoyées ailleurs que sur les serveurs de Polymarket/Polygon pour signer.
- ✅ Il est recommandé d'utiliser un wallet dédié au bot, et non votre wallet principal.
- ✅ Commencez avec de petits montants.

## ⚠️ Avertissement
Ce logiciel est fourni à titre expérimental. Le trading de crypto-monnaies et les marchés de prédiction comportent des risques financiers importants. L'auteur n'est pas responsable des pertes potentielles. Usez de prudence.
