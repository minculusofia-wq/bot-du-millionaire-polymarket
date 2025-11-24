import requests
import time
import json
import threading
from bot_logic import BotBackend

class RealisticTestEngine:
    def __init__(self):
        self.backend = BotBackend()
        self.rpc_url = self.backend.data['rpc_url']
        self.last_signatures = {}
        self.running = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Démarre la surveillance des wallets en arrière-plan"""
        if self.running:
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("🔍 Surveillance blockchain démarrée")
        
    def stop_monitoring(self):
        """Arrête la surveillance"""
        self.running = False
        print("🔍 Surveillance blockchain arrêtée")
        
    def _monitor_loop(self):
        """Boucle de surveillance continue"""
        while self.running:
            try:
                self._check_all_wallets()
                time.sleep(3)  # Vérifier toutes les 3 secondes
            except Exception as e:
                print(f"❌ Erreur surveillance: {e}")
                time.sleep(5)
                
    def _check_all_wallets(self):
        """Vérifie tous les wallets actifs pour détecter des swaps"""
        if not self.backend.is_running:
            return
            
        for trader in self.backend.data['traders']:
            if trader['active']:
                self._check_wallet_for_swaps(trader)
                
    def _check_wallet_for_swaps(self, trader):
        """Vérifie un wallet spécifique pour les swaps"""
        wallet = trader['address']
        
        # Récupérer les signatures récentes
        signatures = self._get_recent_signatures(wallet, limit=5)
        if not signatures:
            return
            
        # Stocker la dernière signature pour éviter les doublons
        if wallet not in self.last_signatures:
            self.last_signatures[wallet] = signatures[0]['signature']
            return
            
        for sig_data in signatures:
            signature = sig_data['signature']
            
            # Si on a déjà vu cette signature, passer
            if signature == self.last_signatures[wallet]:
                continue
                
            self.last_signatures[wallet] = signature
            
            # Vérifier si c'est un swap
            swap = self._analyze_transaction(signature, wallet, trader)
            if swap:
                print(f"🚀 SWAP DÉTECTÉ: {trader['name']} - {swap['platform']}")
                self._simulate_trade_execution(swap, trader)
                break
                
    def _get_recent_signatures(self, wallet_address, limit=5):
        """Récupère les signatures récentes via Helius"""
        payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getSignaturesForAddress",
            "params": [wallet_address, {"limit": limit}]
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            return response.json().get('result', [])
        except Exception as e:
            print(f"❌ Erreur RPC: {e}")
            return []
            
    def _analyze_transaction(self, signature, wallet, trader):
        """Analyse une transaction pour détecter un swap"""
        payload = {
            "jsonrpc": "2.0",
            "id": "my-id",
            "method": "getTransaction",
            "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=10)
            tx = response.json().get('result')
            
            if not tx or not tx.get('transaction'):
                return None
                
            # Vérifier les instructions
            instructions = tx['transaction']['message'].get('instructions', [])
            
            for ix in instructions:
                if isinstance(ix, dict) and 'programId' in ix:
                    program = ix['programId']
                    
                    # Jupiter v6
                    if 'JUP6LkbZbjS5' in program:
                        return {
                            'type': 'SWAP',
                            'platform': 'Jupiter',
                            'signature': signature,
                            'timestamp': tx.get('blockTime'),
                            'trader': trader
                        }
                    
                    # Raydium
                    if '675kPX9MHT' in program:
                        return {
                            'type': 'SWAP',
                            'platform': 'Raydium',
                            'signature': signature,
                            'timestamp': tx.get('blockTime'),
                            'trader': trader
                        }
            return None
        except Exception as e:
            print(f"❌ Erreur analyse: {e}")
            return None
            
    def _simulate_trade_execution(self, swap, trader):
        """Simule l'exécution du trade copié"""
        # Calculer performance basée sur le trader
        performance = random.uniform(-2, 5)  # -2% à +5%
        
        # Mettre à jour le portefeuille virtuel
        if self.backend.get_active_traders_count() > 0:
            capital_par_trader = 1000 / self.backend.get_active_traders_count()
            gain_perte = capital_par_trader * (performance / 100)
            self.backend.virtual_balance += gain_perte
            
        # Ajouter à l'historique
        trade = {
            'time': time.strftime('%H:%M:%S'),
            'trader': f"{trader['emoji']} {trader['name']}",
            'platform': swap['platform'],
            'signature': swap['signature'][:8] + '...',
            'pnl': round(gain_perte, 2),
            'performance': round(performance, 2)
        }
        
        print(f"📊 Trade simulé: {trade}")
        
        # Sauvegarder dans un fichier d'historique
        try:
            with open('trades_history.json', 'r') as f:
                history = json.load(f)
        except:
            history = []
            
        history.insert(0, trade)
        if len(history) > 100:
            history.pop()
            
        with open('trades_history.json', 'w') as f:
            json.dump(history, f, indent=2)

# Instance globale
test_engine = RealisticTestEngine()
