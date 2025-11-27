#!/bin/bash
# Script automatisé pour pusher vers GitHub avec le token Replit

cd "$(dirname "$0")"

echo "🚀 Configuration du remote GitHub..."
git remote set-url origin "https://${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/minculusofia-wq/bot-du-millionaire.git" 2>/dev/null

echo "📤 Push vers GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ PUSH RÉUSSI SUR GITHUB!"
else
    echo "❌ Erreur lors du push"
    exit 1
fi
