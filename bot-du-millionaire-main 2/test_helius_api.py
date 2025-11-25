#!/usr/bin/env python3
"""
🔍 Diagnostic Helius API - Teste si le bot peut récupérer les trades
Lance ce script pour voir EXACTEMENT ce qui se passe
"""

import os
import json
import requests
from pathlib import Path

print("="*70)
print("🔍 DIAGNOSTIC HELIUS API - Bot du Millionnaire")
print("="*70)

# 1️⃣ Charger .env
print("\n1️⃣ Chargement variables d'environnement...")
env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"\'')
    print("✅ .env chargé")
else:
    print("⚠️ Aucun fichier .env trouvé - cherche dans les variables système")

# 2️⃣ Vérifier HELIUS_API_KEY
print("\n2️⃣ Vérification HELIUS_API_KEY...")
helius_key = os.getenv('HELIUS_API_KEY')
if not helius_key:
    print("❌ HELIUS_API_KEY NON CONFIGURÉE !")
    print("   → Créez un fichier .env avec: HELIUS_API_KEY=votre_cle_ici")
    print("   → Ou: export HELIUS_API_KEY='votre_cle_ici'")
    exit(1)
print(f"✅ HELIUS_API_KEY trouvée: {helius_key[:10]}...***")

# 3️⃣ Charger les traders depuis config.json
print("\n3️⃣ Chargement des traders...")
try:
    with open('config.json') as f:
        config = json.load(f)
    traders = config.get('traders', [])
    print(f"✅ {len(traders)} traders trouvés:")
    for t in traders:
        active = "✅" if t.get('active') else "❌"
        print(f"   {active} {t['name']}: {t['address'][:10]}... (capital: ${t.get('capital', 0)})")
except Exception as e:
    print(f"❌ Erreur lecture config.json: {e}")
    exit(1)

# 4️⃣ Tester chaque trader
print("\n4️⃣ Test API Helius pour chaque trader...")
print("-"*70)

for trader in traders:
    if not trader.get('active'):
        continue
    
    name = trader['name']
    address = trader['address']
    
    print(f"\n📍 Trader: {name}")
    print(f"   Adresse: {address}")
    
    # Récupérer les transactions
    try:
        url = f"https://api-mainnet.helius-rpc.com/v0/addresses/{address}/transactions/?api-key={helius_key}"
        print(f"   → Appel API: {url[:80]}...")
        
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if response.status_code != 200:
            print(f"   ❌ Erreur HTTP {response.status_code}: {result}")
            continue
        
        # L'API retourne directement une LISTE
        transactions = result if isinstance(result, list) else result.get('transactions', [])
        print(f"   ✅ {len(transactions)} transactions trouvées")
        
        if len(transactions) == 0:
            print(f"   ⚠️ Aucune transaction - ce trader n'a peut-être pas acheté/vendu récemment")
            continue
        
        # Parser les 3 premières transactions
        print(f"   → Analyse des 3 premières transactions:")
        
        for i, tx in enumerate(transactions[:3]):
            # Les transactions viennent déjà parsées de l'API
            tx_data = tx if isinstance(tx, dict) else None
            if not tx_data:
                print(f"\n      Transaction #{i+1}: ❌ Erreur - pas un dict")
                continue
                
            print(f"\n      Transaction #{i+1}: {tx_data.get('description', '?')[:30]}...")
            tx_type = tx_data.get('type', 'UNKNOWN')
            
            print(f"         Type: {tx_type}")
            
            if tx_type == 'SWAP':
                token_transfers = tx_data.get('token_transfers', [])
                print(f"         Tokens transférés: {len(token_transfers)}")
                
                for j, transfer in enumerate(token_transfers[:2]):
                    mint = transfer.get('mint', '?')[:10]
                    amount = transfer.get('tokenAmount', 0)
                    print(f"           [{j+1}] {mint}... : {amount}")
                
                print(f"         ✅ SWAP DÉTECTÉ - Le bot devrait copier ce trade!")
            else:
                print(f"         ⚠️ Pas un SWAP (type: {tx_type}) - ignoré")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")

print("\n" + "="*70)
print("✅ Diagnostic terminé")
print("="*70)
print("\n📋 RÉSUMÉ:")
print("- Si vous voyez '✅ SWAP DÉTECTÉ', le bot PEUT copier ce trade")
print("- Si vous ne voyez que '❌', vérifier:")
print("  1. Les adresses des traders sont correctes dans config.json")
print("  2. Ces traders ont des trades récents")
print("  3. HELIUS_API_KEY est valide")
