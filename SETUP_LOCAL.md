# Configuration Bot du Millionnaire - Ordinateur Local

## 🚀 Installation Rapide

### 1. Prérequis
- Python 3.9+
- pip (gestionnaire de paquets Python)

### 2. Installer les dépendances
```bash
pip install flask requests websockets
```

### 3. Configurer HELIUS_API_KEY

#### Option A: Fichier `.env` (RECOMMANDÉ)
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env et ajouter votre clé Helius
# HELIUS_API_KEY=votre_cle_helius_ici
```

#### Option B: Variable d'environnement système
**Sur Windows (PowerShell):**
```powershell
$env:HELIUS_API_KEY="votre_cle_helius_ici"
python bot.py
```

**Sur macOS/Linux:**
```bash
export HELIUS_API_KEY="votre_cle_helius_ici"
python bot.py
```

### 4. Lancer le bot
```bash
python bot.py
```

Vous verrez:
```
============================================================
✅ BOT PRÊT À DÉMARRER
Mode: TEST
Helius API Key: ✅ Configurée
Traders actifs: 3
Bot activé: ❌ NON
============================================================
```

### 5. Accéder au dashboard
- Ouvrez: **http://localhost:5000**
- Cliquez sur **"Activer/Désactiver Bot"** pour démarrer la détection des trades

---

## 🔧 Obtenir votre HELIUS_API_KEY

1. Allez sur: https://dashboard.helius.dev/
2. Créez un compte gratuit
3. Créez une nouvelle clé API
4. Copiez la clé dans `.env`

---

## 📊 En mode TEST

- Le bot simule les trades avec capital fictif
- Les trades réels de vos traders Axiom Pro sont téléchargés via Helius
- Les positions ouvertes sont trackées dans le portfolio
- Aucune vraie transaction ne sera exécutée

---

## ❌ Dépannage

### "Helius API Key: ❌ NON configurée"
- Vérifiez que vous avez défini `HELIUS_API_KEY` correctement
- Sur Windows: utilisez PowerShell (pas Command Prompt)
- Redémarrez le terminal après le `set`

### "Traders actifs: 0"
- Vérifiez `config.json`: les traders doivent avoir `"active": true`

### "Bot activé: ❌ NON"
- Cliquez sur le bouton **"Activer/Désactiver Bot"** dans le dashboard

### "0 trades détectés"
- Attendre 5-10 secondes (le bot vérifie toutes les 5 secondes)
- Vérifier que vos traders ont des trades récents sur Axiom Pro
- Vérifier la console pour les messages d'erreur

---

## 📍 Fichiers de configuration

- `config.json`: Paramètres du bot, traders, TP/SL
- `portfolio_tracker.json`: Portfolio et PnL
- `simulated_trades.json`: Historique des trades simulés
- `bot_data.db`: Base de données SQLite (historique complet)
