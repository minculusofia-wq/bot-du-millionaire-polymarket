# -*- coding: utf-8 -*-
"""
Intégration Helius - Parser enrichi des transactions Solana
Identifie automatiquement les swaps, DEX et montants
Inclut support pour slippage dynamique et meilleure exécution
"""
import requests
import os
from datetime import datetime
from typing import Optional, List, Dict

class HeliumsAPI:
    """Client Helius pour parser les transactions"""
    
    def __init__(self):
        self.api_key = os.getenv('HELIUS_API_KEY')
        self.base_url = "https://api-mainnet.helius-rpc.com/v0"
        self.timeout = 10
        self.slippage_cache = {}  # Cache slippage calculations
        
        if not self.api_key:
            print("⚠️ HELIUS_API_KEY non définie - utilisation du mode RPC standard")
    
    def get_parsed_transactions(self, signatures: List[str]) -> List[Dict]:
        """Récupère les transactions parsées par Helius"""
        if not self.api_key or not signatures:
            return []
        
        try:
            url = f"{self.base_url}/transactions/?api-key={self.api_key}"
            payload = {"transactions": signatures}
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            result = response.json()
            
            if 'transactions' not in result:
                return []
            
            return result['transactions']
        except Exception as e:
            print(f"❌ Erreur Helius: {e}")
            return []
    
    def parse_swap_from_helius(self, tx_data: Dict) -> Optional[Dict]:
        """Parse un swap à partir des données Helius enrichies"""
        try:
            # Helius fournit une description parsée
            description = tx_data.get('description', '')
            tx_type = tx_data.get('type', '')
            
            if tx_type != 'SWAP':
                return None
            
            # Extraire les informations du swap
            token_transfers = tx_data.get('token_transfers', [])
            source = tx_data.get('source', 'Unknown')  # DEX identifier
            fee = tx_data.get('fee', 0) / 1_000_000_000  # Convert lamports to SOL
            
            if len(token_transfers) < 2:
                return None
            
            # Token in (ce qu'on envoie)
            in_token = token_transfers[0]
            in_amount = float(in_token.get('tokenAmount', 0)) / (10 ** in_token.get('decimals', 9))
            in_mint = in_token.get('mint', '')
            
            # Token out (ce qu'on reçoit)
            out_token = token_transfers[1]
            out_amount = float(out_token.get('tokenAmount', 0)) / (10 ** out_token.get('decimals', 9))
            out_mint = out_token.get('mint', '')
            
            return {
                'type': 'SWAP',
                'description': description,
                'source': source,  # ✅ DEX identifier
                'fee_sol': fee,
                'in_amount': in_amount,
                'in_mint': in_mint,
                'out_amount': out_amount,
                'out_mint': out_mint,
                'timestamp': tx_data.get('timestamp', datetime.now().isoformat()),
                'status': 'success',
                'raw_data': tx_data
            }
        except Exception as e:
            print(f"❌ Erreur parsing swap: {e}")
            return None
    
    def get_wallet_recent_trades(self, address: str, limit: int = 20) -> List[Dict]:
        """Récupère les derniers trades d'un wallet"""
        if not self.api_key:
            return []
        
        try:
            # Récupérer les transactions du wallet
            url = f"{self.base_url}/addresses/{address}/transactions/?api-key={self.api_key}"
            response = requests.get(url, timeout=self.timeout)
            result = response.json()
            
            signatures = result.get('transactions', [])[:limit]
            if not signatures:
                return []
            
            # Parser les transactions
            parsed_txs = self.get_parsed_transactions(signatures)
            
            trades = []
            for tx in parsed_txs:
                trade = self.parse_swap_from_helius(tx)
                if trade:
                    trades.append(trade)
            
            return trades
        except Exception as e:
            print(f"❌ Erreur get_wallet_recent_trades: {e}")
            return []

class HeliumsTradeAnalyzer:
    """Analyse les trades parsés par Helius"""
    
    def __init__(self):
        self.helius = HeliumsAPI()
    
    def calculate_trade_value(self, trade: Dict, sol_price: float = 100) -> float:
        """Calcule la valeur USD d'un trade"""
        try:
            in_mint = trade.get('in_mint', '')
            sol_address = 'So11111111111111111111111111111111111111112'
            
            # Si le trade est en SOL
            if in_mint == sol_address:
                return trade.get('in_amount', 0) * sol_price
            
            return 0
        except Exception:
            return 0
    
    def identify_dex(self, trade: Dict) -> str:
        """Identifie le DEX utilisé"""
        source = trade.get('source', 'Unknown')
        
        dex_map = {
            'Raydium': '🔄 Raydium',
            'Orca': '🐋 Orca',
            'Jupiter': '🪐 Jupiter',
            'Magic Eden': '✨ Magic Eden',
            'Phantom': '👻 Phantom'
        }
        
        for key, emoji in dex_map.items():
            if key.lower() in source.lower():
                return emoji
        
        return f"📊 {source}"
    
    def calculate_slippage_percent(self, trade: Dict) -> float:
        """
        Calcule le slippage réel d'un trade (%)
        Pour meme coins, le slippage peut être 0-100%+
        """
        try:
            in_amount = trade.get('in_amount', 0)
            out_amount = trade.get('out_amount', 0)
            
            if in_amount == 0 or out_amount == 0:
                return 0
            
            # Ratio sans slippage = 1:1 (approximation)
            # Slippage = (prix attendu - prix réel) / prix attendu * 100
            theoretical_out = in_amount  # Pour 1:1 (simplifié)
            if theoretical_out == 0:
                return 0
            
            slippage = ((theoretical_out - out_amount) / theoretical_out) * 100
            return max(0, slippage)  # Pas de slippage négatif
        
        except Exception as e:
            print(f"⚠️ Erreur calcul slippage: {e}")
            return 0
    
    def analyze_trader_activity(self, address: str) -> Dict:
        """Analyse complète de l'activité d'un trader"""
        trades = self.helius.get_wallet_recent_trades(address, limit=30)
        
        if not trades:
            return {
                'address': address,
                'trades_count': 0,
                'activity': 'No recent trades',
                'dex_usage': {}
            }
        
        # Compter par DEX
        dex_usage = {}
        total_value = 0
        
        for trade in trades:
            dex = self.identify_dex(trade)
            if dex not in dex_usage:
                dex_usage[dex] = 0
            dex_usage[dex] += 1
            total_value += self.calculate_trade_value(trade)
        
        return {
            'address': address,
            'trades_count': len(trades),
            'dex_usage': dex_usage,
            'recent_trades': trades[:5],
            'total_volume_estimated': total_value,
            'activity': 'Active' if trades else 'Inactive'
        }

# Instance globale
helius_api = HeliumsAPI()
helius_analyzer = HeliumsTradeAnalyzer()
