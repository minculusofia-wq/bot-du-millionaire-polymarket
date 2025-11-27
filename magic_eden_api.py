# -*- coding: utf-8 -*-
"""
Magic Eden API - Fallback indexer fiable
Utilisé si Helius failover
"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime


class MagicEdenAPI:
    """API Magic Eden pour transactions (fallback)"""
    
    def __init__(self):
        self.base_url = "https://api-mainnet.magiceden.dev/v2"
        self.timeout = 10
        self.max_retries = 2
    
    def get_wallet_transactions(self, wallet_address: str, limit: int = 10) -> List[Dict]:
        """Récupère les transactions d'un wallet via Magic Eden"""
        try:
            url = f"{self.base_url}/wallets/{wallet_address}/transactions"
            params = {
                "offset": 0,
                "limit": limit,
                "sort_by": "created_at",
                "sort_order": "DESC"
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                transactions = data.get('transactions', [])
                
                # Parser les swaps
                swaps = []
                for tx in transactions:
                    if self._is_swap(tx):
                        swaps.append({
                            'signature': tx.get('signature', ''),
                            'timestamp': tx.get('created_at', ''),
                            'type': 'SWAP',
                            'raw': tx
                        })
                
                return swaps
            
            return []
        
        except requests.Timeout:
            print(f"⚠️ Magic Eden timeout pour {wallet_address[:10]}...")
            return []
        
        except Exception as e:
            print(f"⚠️ Magic Eden error: {str(e)[:60]}")
            return []
    
    def _is_swap(self, transaction: Dict) -> bool:
        """Vérifie si c'est un swap"""
        try:
            tx_type = str(transaction.get('type', '')).upper()
            return 'SWAP' in tx_type or 'TRADE' in tx_type
        except:
            return False


# Instance globale
magic_eden_api = MagicEdenAPI()
