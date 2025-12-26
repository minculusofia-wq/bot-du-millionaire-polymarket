#!/bin/bash
echo "🚀 Démarrage du Bot du Millionnaire..."

# 1. Vérifier si venv existe
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel (une seule fois)..."
    python3 -m venv venv
    echo "📥 Installation des dépendances..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
else
    echo "✅ Environnement virtuel détecté."
fi

# 2. Vérifier les mises à jour de dépendances (rapide)
# echo "🔄 Vérification des dépendances..."
# ./venv/bin/pip install -r requirements.txt

# 3. Lancer le bot
echo "🟢 Lancement du bot !"
echo "👉 Accédez à http://localhost:5000"
./venv/bin/python bot.py
