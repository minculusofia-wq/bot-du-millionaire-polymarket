# -*- coding: utf-8 -*-
"""
Intégration Solana - Connexion réelle à la blockchain Solana
Récupération des transactions et trades réels des traders
"""
import requests
import json
try:
    import base58
except ImportError:
    base58 = None
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import os

class SolanaRPC:
    """Gestionnaire de connexion Solana RPC"""
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.getenv('RPC_URL', 'https://api.mainnet-beta.solana.com')
        self.timeout = 10
        
    def call(self, method: str, params: Optional[List] = None):
        """Appel RPC générique"""
        payload = {
            "jsonrpc": "2.0",
            "id": "py-rpc",
            "method": method,
            "params": params or []
        }
        try:
            response = requests.post(self.rpc_url, json=payload, timeout=self.timeout)
            result = response.json()
            if 'error' in result:
                print(f"❌ Erreur RPC: {result['error']}")
                return None
            return result.get('result')
        except Exception as e:
            print(f"❌ Erreur RPC {method}: {e}")
            return None

class SolanaValidator:
    """Validation des adresses et données Solana"""
    
    @staticmethod
    def is_valid_solana_address(address: str) -> bool:
        """Valide une adresse Solana"""
        if not isinstance(address, str) or len(address) < 32 or len(address) > 44:
            return False
        if base58 is None:
            return len(address) >= 32 and len(address) <= 44
        try:
            decoded = base58.b58decode(address)
            return len(decoded) == 32
        except Exception:
            return False
    
    @staticmethod
    def is_valid_private_key(private_key: str) -> bool:
        """Valide une clé privée Solana (base58)"""
        if not isinstance(private_key, str) or len(private_key) < 80 or len(private_key) > 90:
            return False
        if base58 is None:
            return len(private_key) >= 80 and len(private_key) <= 90
        try:
            decoded = base58.b58decode(private_key)
            return len(decoded) == 64
        except Exception:
            return False

class SolanaTradeTracker:
    """Suivi des trades réels d'un trader Solana"""
    
    def __init__(self, rpc_url: str = None):
        self.rpc = SolanaRPC(rpc_url)
        self.validator = SolanaValidator()
        self.trades_cache: Dict = {}
        self.cache_timeout = 300  # 5 minutes
        
    def get_wallet_balance(self, address: str) -> Dict:
        """Récupère le solde SOL d'un wallet"""
        if not self.validator.is_valid_solana_address(address):
            return {'error': 'Invalid address', 'sol_balance': 0}
        
        balance_lamports = self.rpc.call('getBalance', [address])
        if balance_lamports is None:
            return {'error': 'RPC call failed', 'sol_balance': 0}
        
        sol_balance = float(balance_lamports) / 1_000_000_000
        return {
            'address': address,
            'sol_balance': sol_balance,
            'lamports': balance_lamports,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_recent_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """Récupère les transactions récentes d'une adresse"""
        if not self.validator.is_valid_solana_address(address):
            return []
        
        signatures = self.rpc.call('getSignaturesForAddress', [address, {"limit": limit}])
        if not signatures:
            return []
        
        transactions = []
        for sig_info in signatures:
            signature = sig_info.get('signature')
            tx_data = self.rpc.call('getTransaction', [signature, {"encoding": "json"}])
            if tx_data:
                transactions.append({
                    'signature': signature,
                    'timestamp': sig_info.get('blockTime'),
                    'status': 'success' if sig_info.get('err') is None else 'failed',
                    'data': tx_data
                })
        
        return transactions
    
    def parse_swap_transaction(self, tx_data: Dict) -> Optional[Dict]:
        """Parse une transaction de swap (trade)"""
        if not tx_data or 'transaction' not in tx_data:
            return None
        
        try:
            tx = tx_data['transaction']
            meta = tx_data.get('meta', {})
            
            # Extraire les informations basiques
            trade_info = {
                'type': 'swap',
                'status': 'success' if meta.get('err') is None else 'failed',
                'fee': meta.get('fee', 0) / 1_000_000_000,  # Convert lamports to SOL
                'timestamp': tx_data.get('blockTime'),
                'slot': tx_data.get('slot'),
                'program_id': 'unknown',  # À identifier
                'in_amount': None,
                'out_amount': None
            }
            
            # Parsers pour différents DEX
            # À étendre selon les DEX utilisés
            
            return trade_info
        except Exception as e:
            print(f"❌ Erreur parsing transaction: {e}")
            return None
    
    def get_trader_activity(self, address: str, hours: int = 24) -> Dict:
        """Récupère l'activité d'un trader dans les dernières X heures"""
        if not self.validator.is_valid_solana_address(address):
            return {'error': 'Invalid address', 'trades': []}
        
        balance = self.get_wallet_balance(address)
        transactions = self.get_recent_transactions(address, limit=50)
        
        trades = []
        for tx in transactions:
            # Filtrer par timestamp
            if tx.get('timestamp'):
                tx_time = datetime.fromtimestamp(tx['timestamp'])
                if (datetime.now() - tx_time).total_seconds() / 3600 > hours:
                    continue
            
            # Parser le trade si c'est un swap
            if tx['status'] == 'success':
                trade = self.parse_swap_transaction(tx.get('data', {}))
                if trade:
                    trades.append(trade)
        
        return {
            'address': address,
            'current_balance': balance.get('sol_balance', 0),
            'trades_count': len(trades),
            'trades': trades,
            'timestamp': datetime.now().isoformat()
        }

def get_sol_price() -> float:
    """Récupère le prix actuel du SOL en USD"""
    try:
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd',
            timeout=5
        )
        data = response.json()
        return data.get('solana', {}).get('usd', 100)
    except Exception as e:
        print(f"⚠️ Erreur récupération prix SOL: {e}")
        return 100

# Instance globale
solana_tracker = SolanaTradeTracker()
