#!/bin/bash

# Bot du Millionnaire - Lancer sur macOS
# Version corrigée : Utilise un environnement virtuel (venv) pour éviter les erreurs de permissions.

# 1. Se placer dans le dossier du bot
cd "$(dirname "$0")"

# 2. Chercher Python 3
if command -v python3 &> /dev/null; then
    PYTHON=$(command -v python3)
else
    echo "❌ Erreur : Python 3 n'est pas installé"
    echo "📥 Installez Python depuis : https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python trouvé : $PYTHON"
echo "♻️  Initialisation de l'environnement virtuel (cela peut prendre quelques secondes la première fois)..."

# 3. Créer/Activer venv
if [ ! -d "venv" ]; then
    echo "📦 Création du dossier 'venv'..."
    $PYTHON -m venv venv
    
    echo "📥 Installation des dépendances..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
else
    # Mettre à jour si nécessaire
    ./venv/bin/pip install -r requirements.txt
    echo "✅ Environnement virtuel prêt."
fi

# 4. Lancer le serveur Flask via venv
echo ""
echo "=================================================="
echo "🚀 Démarrage du Bot du Millionnaire..."
echo "📱 L'application sera disponible à : http://localhost:5000"
echo "=================================================="
echo ""

# 5. Ouvrir le navigateur automatiquement après 3 secondes (en background)
(sleep 3 && open "http://localhost:5000") &

./venv/bin/python bot.py
