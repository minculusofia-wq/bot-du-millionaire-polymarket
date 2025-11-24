#!/bin/bash

# Bot du Millionnaire - Lancer sur macOS
# Assurez-vous d'avoir installé Python 3 et les dépendances

# Se placer dans le dossier du bot
cd "$(dirname "$0")"

# Chercher Python 3 (essayer plusieurs emplacements)
if command -v python3 &> /dev/null; then
    PYTHON=$(command -v python3)
elif command -v python &> /dev/null; then
    PYTHON=$(command -v python)
else
    echo "❌ Erreur : Python 3 n'est pas installé"
    echo "📥 Installez Python depuis : https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python trouvé : $PYTHON"

# Vérifier si les dépendances sont installées
echo "🔍 Vérification des dépendances..."
$PYTHON -m pip install -r requirements.txt --quiet

# Lancer le serveur Flask
echo "🚀 Démarrage du Bot du Millionnaire..."
echo "📱 L'application sera disponible à : http://localhost:5000"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter le serveur"
echo ""

$PYTHON bot.py
