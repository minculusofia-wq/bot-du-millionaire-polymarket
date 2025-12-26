#!/bin/bash
echo "🧪 Lancement de la suite de tests Bot du Millionnaire..."

# Définir le PYTHONPATH pour inclure le dossier racine
export PYTHONPATH=$PYTHONPATH:.

# Lancer les tests avec unittest
python3 -m unittest discover tests -p "test_*.py" -v

echo "✅ Tests terminés."
