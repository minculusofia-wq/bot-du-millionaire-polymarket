import requests
import time
import json
from bot_logic import BotBackend

class HeliusMonitor:
    def __init__(self, rpc_url):
        self.rpc_url = rpc_url
        self.backend = BotBackend()
        self.last_signatures = {}
        
    def get_recent_signatures(self, wallet_address, limit=10):
        """Récupère les signatures récentes d'un wallet"""
        payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": limit}]
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            result = response.json().get('result', [])
            return result
        except Exception as e:
            print(f"❌ Erreur RPC pour {wallet_address}: {e}")
            return []
    
    def get_transaction_details(self, signature):
        """Récupère les détails d'une transaction"""
        payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getTransaction",
            "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            return response.json().get('result')
        except Exception as e:
            print(f"❌ Erreur détails transaction: {e}")
            return None
    
    def detect_swap(self, wallet_address):
        """Détecte si un wallet a fait un swap récemment"""
        signatures = self.get_recent_signatures(wallet_address, 5)
        
        if not signatures:
            return None
            
        # Stocker la dernière signature pour éviter les doublons
        if wallet_address not in self.last_signatures:
            self.last_signatures[wallet_address] = signatures[0]['signature']
            return None
        
        for sig_data in signatures:
            signature = sig_data['signature']
            
            # Si on a déjà vu cette signature, passer
            if signature == self.last_signatures[wallet_address]:
                continue
                
            self.last_signatures[wallet_address] = signature
            
            tx = self.get_transaction_details(signature)
            if not tx:
                continue
            
            # Vérifier si c'est un swap
            if tx.get('transaction', {}).get('message', {}).get('instructions'):
                for ix in tx['transaction']['message']['instructions']:
                    if isinstance(ix, dict) and 'programId' in ix:
                        program = ix['programId']
                        
                        # Jupiter v6
                        if 'JUP6LkbZbjS5' in program:
                            return {
                                'type': 'SWAP',
                                'platform': 'Jupiter',
                                'signature': signature,
                                'timestamp': sig_data['blockTime'],
                                'wallet': wallet_address
                            }
                        
                        # Raydium
                        if '675kPX9MHT' in program:
                            return {
                                'type': 'SWAP',
                                'platform': 'Raydium',
                                'signature': signature,
                                'timestamp': sig_data['blockTime'],
                                'wallet': wallet_address
                            }
        return None

# Test rapide
if __name__ == "__main__":
    print("🔍 Test de surveillance blockchain...")
    
    # Clé RPC (récupérée depuis config.json)
    backend = BotBackend()
    rpc_url = backend.data.get('rpc_url', 'https://api.mainnet-beta.solana.com')
    
    monitor = HeliusMonitor(rpc_url)
    
    # Wallet de test (remplacez par une vraie adresse active)
    TEST_WALLET = "7x7aCTrEfAdm3Y5Tt3B2V8rZV3XqXqXqXqXqXqXqXqXq"  # À remplacer
    
    print(f"Surveillance de: {TEST_WALLET}")
    print("Appuyez sur Ctrl+C pour arrêter\n")
    
    try:
        while True:
            result = monitor.detect_swap(TEST_WALLET)
            if result:
                print(f"🚀 SWAP DÉTECTÉ !")
                print(f"Plateforme: {result['platform']}")
                print(f"Signature: {result['signature']}")
                print(f"Heure: {result['timestamp']}")
                print("-" * 50)
            
            time.sleep(2)  # Vérifier toutes les 2 secondes
            
    except KeyboardInterrupt:
        print("\n✅ Surveillance arrêtée")
