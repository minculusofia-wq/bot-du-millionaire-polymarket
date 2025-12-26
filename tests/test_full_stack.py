# -*- coding: utf-8 -*-
"""
Test d'intégration Full Stack
Vérifie que le Backend (Flask) et le Frontend (HTML/JS) fonctionnent ensemble.
"""
import sys
import os
import unittest
import json

# Ajouter le répertoire parent au path pour importer bot.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import app
from db_manager import db_manager

class TestFullStack(unittest.TestCase):
    def setUp(self):
        """Configuration initiale avant chaque test"""
        self.app = app.test_client()
        self.app.testing = True 
        
        # Initialiser la DB de test si nécessaire
        db_manager.init_db()

    def test_01_homepage_serving(self):
        """Vérifie que la page d'accueil (Frontend) est servie correctement"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        
        # Vérifier la présence d'éléments clés du nouveau UI "Pure Copy Trader"
        self.assertIn('Bot du Millionnaire', content)
        self.assertIn('Flux Trades', content)  # Le nouvel onglet
        self.assertNotIn('Live Trading', content)  # L'ancien onglet ne doit plus être là
        print("✅ Frontend: Page d'accueil chargée et éléments d'interface validés.")

    def test_02_api_status(self):
        """Vérifie que l'API de statut backend répond"""
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('is_running', data)
        self.assertIn('polymarket', data)
        print(f"✅ Backend: API Status OK (Running: {data['is_running']})")

    def test_03_wallet_management(self):
        """Vérifie l'ajout et la récupération de wallets"""
        
        # 1. Ajouter un wallet
        test_wallet = "0x1234567890123456789012345678901234567890"
        payload = {
            "address": test_wallet,
            "name": "Test Whale"
        }
        
        response = self.app.post('/api/wallets/add', 
                               json=payload,
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # 2. Vérifier qu'il est dans la liste
        response = self.app.get('/api/wallets')
        data = json.loads(response.data)
        
        wallets_addresses = [w['address'] for w in data['wallets']]
        self.assertIn(test_wallet.lower(), [w.lower() for w in wallets_addresses])
        print("✅ Base de données: Ajout et lecture de wallet validés.")
        
        # 3. Supprimer le wallet (Clean up)
        response = self.app.post('/api/wallets/remove',
                               json={"address": test_wallet},
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
