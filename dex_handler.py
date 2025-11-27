# -*- coding: utf-8 -*-
"""
Gestion des DEX Solana (Raydium, Orca, Jupiter, etc)
Construction et exécution des transactions de swap
"""
from typing import Dict, Optional, List
from enum import Enum
import requests
import json
from datetime import datetime
from trade_validator import trade_validator
from trade_safety import trade_safety, RiskLevel
from audit_logger import audit_logger, LogLevel

class DEXType(Enum):
    """Types de DEX supportés"""
    RAYDIUM = "raydium"
    ORCA = "orca"
    JUPITER = "jupiter"
    MAGIC_EDEN = "magic_eden"
    UNKNOWN = "unknown"

class SwapDetails:
    """Détails d'un swap"""
    def __init__(self, 
                 input_mint: str,
                 output_mint: str,
                 input_amount: float,
                 slippage_bps: int = 100):
        self.input_mint = input_mint
        self.output_mint = output_mint
        self.input_amount = input_amount
        self.slippage_bps = slippage_bps
        self.timestamp = datetime.now().isoformat()

class DEXHandler:
    """Gestionnaire des swaps DEX"""
    
    def __init__(self):
        self.dex_type = DEXType.UNKNOWN
        self.swaps_executed = []
        self.price_cache = {}
    
    def identify_dex(self, transaction_source: str) -> DEXType:
        """Identifie le DEX à partir du source"""
        source_lower = transaction_source.lower()
        
        if 'raydium' in source_lower:
            return DEXType.RAYDIUM
        elif 'orca' in source_lower:
            return DEXType.ORCA
        elif 'jupiter' in source_lower:
            return DEXType.JUPITER
        elif 'magic' in source_lower:
            return DEXType.MAGIC_EDEN
        
        return DEXType.UNKNOWN
    
    def get_token_price(self, mint: str) -> Optional[float]:
        """Récupère le prix d'un token"""
        try:
            if mint in self.price_cache:
                return self.price_cache[mint]
            
            # API pour les prix (simplifié)
            sol_address = 'So11111111111111111111111111111111111111112'
            if mint == sol_address:
                # Récupérer prix SOL
                response = requests.get(
                    'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd',
                    timeout=5
                )
                price = response.json().get('solana', {}).get('usd', 100)
                self.price_cache[mint] = price
                return price
            
            return None
        except Exception as e:
            print(f"❌ Erreur get_token_price: {e}")
            return None
    
    def calculate_output_amount(self, 
                                input_amount: float,
                                input_price: float,
                                output_price: float,
                                slippage_bps: int) -> float:
        """Calcule le montant output après slippage"""
        try:
            # Calcul basique
            output_amount = (input_amount * input_price) / output_price
            
            # Appliquer slippage
            slippage_ratio = slippage_bps / 10000
            output_with_slippage = output_amount * (1 - slippage_ratio)
            
            return output_with_slippage
        except Exception as e:
            print(f"❌ Erreur calculate_output: {e}")
            return 0
    
    def build_swap_instruction(self, swap_details: SwapDetails, dex: DEXType) -> Optional[Dict]:
        """Construit une instruction de swap pour un DEX"""
        try:
            instruction = {
                'type': 'swap',
                'dex': dex.value,
                'input_mint': swap_details.input_mint,
                'output_mint': swap_details.output_mint,
                'input_amount': swap_details.input_amount,
                'slippage_bps': swap_details.slippage_bps,
                'timestamp': swap_details.timestamp
            }
            
            # Logique spécifique par DEX à étendre
            if dex == DEXType.RAYDIUM:
                instruction['program'] = 'raydium_program_id'
            elif dex == DEXType.ORCA:
                instruction['program'] = 'orca_program_id'
            elif dex == DEXType.JUPITER:
                instruction['aggregator'] = 'jupiter'
            
            return instruction
        except Exception as e:
            print(f"❌ Erreur build_swap_instruction: {e}")
            return None
    
    def execute_swap(self, swap_details: SwapDetails, dex: DEXType) -> Optional[Dict]:
        """Exécute un swap"""
        try:
            # Construire l'instruction
            instruction = self.build_swap_instruction(swap_details, dex)
            if not instruction:
                audit_logger.log(LogLevel.ERROR, "Impossible construire instruction swap")
                return None
            
            # Calculer montant output
            input_price = self.get_token_price(swap_details.input_mint)
            output_price = self.get_token_price(swap_details.output_mint)
            
            if not input_price or not output_price:
                audit_logger.log(LogLevel.WARNING, "Impossible obtenir les prix tokens")
                return None
            
            output_amount = self.calculate_output_amount(
                swap_details.input_amount,
                input_price,
                output_price,
                swap_details.slippage_bps
            )
            
            # Créer un trade de sécurité avec TP/SL
            trade_id = f"swap_{datetime.now().timestamp()}"
            entry_price = input_price
            trade = trade_safety.create_trade_with_safety(
                trade_id=trade_id,
                entry_price=entry_price,
                amount=swap_details.input_amount,
                risk_level=RiskLevel.MEDIUM,
                sl_percent=5,
                tp_percent=10
            )
            
            swap_result = {
                'status': 'executed',
                'dex': dex.value,
                'input_amount': swap_details.input_amount,
                'output_amount': output_amount,
                'slippage': swap_details.slippage_bps,
                'timestamp': datetime.now().isoformat(),
                'instruction': instruction,
                'trade_id': trade_id,
                'sl_price': trade.get('sl_price'),
                'tp_price': trade.get('tp_price')
            }
            
            self.swaps_executed.append(swap_result)
            audit_logger.log_trade_execution(swap_result, 'EXECUTED', dex.value)
            return swap_result
            
        except Exception as e:
            audit_logger.log_error("Erreur execute_swap", e, {'dex': dex.value})
            return None
    
    def get_swap_history(self) -> List[Dict]:
        """Récupère l'historique des swaps"""
        return self.swaps_executed

# Instance globale
dex_handler = DEXHandler()
