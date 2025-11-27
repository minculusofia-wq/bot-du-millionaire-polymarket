# -*- coding: utf-8 -*-
"""
Simulateur de Copy Trading Réel
- Récupère les transactions VRAIES des traders via Helius API
- Simule les mêmes trades avec capital fictif 1000$
- Calcule les PnL reels de la simulation
"""
import json
import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from db_manager import db_manager
import uuid

class CopyTradingSimulator:
    """Simule le copy trading avec capital fictif"""
    
    def __init__(self):
        self.helius_api_key = os.getenv('HELIUS_API_KEY')
        self.rpc_url = "https://api.mainnet-beta.solana.com"
        self.simulated_trades = self._load_simulated_trades()
        self.trader_portfolios = self._load_trader_portfolios()
        self.max_slippage_allowed = 100  # Max 100% pour meme coins (configurable)
        
    def _load_simulated_trades(self) -> Dict:
        """Charge les trades simulés"""
        try:
            with open('simulated_trades.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_simulated_trades(self):
        """Sauvegarde les trades simulés"""
        with open('simulated_trades.json', 'w') as f:
            json.dump(self.simulated_trades, f, indent=2)
        
        # Synchroniser avec la DB
        for trade_id, trade_data in self.simulated_trades.items():
            db_manager.save_simulated_trade({
                'trade_id': trade_id,
                'trader_address': trade_data.get('trader_address', ''),
                'trader_name': trade_data.get('trader_name', ''),
                'signature': trade_data.get('signature', ''),
                'timestamp': trade_data.get('timestamp', datetime.now().isoformat()),
                'swap_type': 'SWAP',
                'input_mint': trade_data.get('input_mint', ''),
                'input_amount': trade_data.get('input_amount', 0),
                'output_mint': trade_data.get('output_mint', ''),
                'output_amount': trade_data.get('output_amount', 0),
                'entry_price_usd': trade_data.get('entry_price_usd', 0),
                'exit_price_usd': trade_data.get('exit_price_usd', 0),
                'status': trade_data.get('status', 'OPEN'),
                'pnl': trade_data.get('pnl', 0),
                'pnl_percent': trade_data.get('pnl_percent', 0)
            })
    
    def _load_trader_portfolios(self) -> Dict:
        """Charge les portefeuilles simulés des traders"""
        try:
            with open('trader_portfolios.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_trader_portfolios(self):
        """Sauvegarde les portefeuilles simulés"""
        with open('trader_portfolios.json', 'w') as f:
            json.dump(self.trader_portfolios, f, indent=2)
        
        # Synchroniser avec la DB
        for trader_name, portfolio in self.trader_portfolios.items():
            trades = portfolio.get('trades', [])
            total_pnl = portfolio.get('realized_pnl', 0)
            
            # Calculer PnL des positions ouvertes
            for pos in portfolio.get('positions', {}).values():
                total_pnl += pos.get('pnl', 0)
            
            # Sauvegarder dans la DB
            db_manager.update_trader_portfolio(
                trader_name,
                trader_name,
                portfolio.get('capital', 0),
                portfolio.get('available_balance', 0) + portfolio.get('capital', 0) - sum(
                    p.get('purchase_usd', 0) for p in portfolio.get('positions', {}).values()
                ),
                total_pnl,
                (total_pnl / portfolio.get('capital', 1) * 100) if portfolio.get('capital', 0) > 0 else 0
            )
    
    def get_trader_recent_trades(self, trader_address: str, limit: int = 10) -> List[Dict]:
        """Récupère les VRAIES transactions d'un trader via Helius (avec retry robuste)"""
        if not self.helius_api_key:
            print(f"⚠️ HELIUS_API_KEY non configurée pour {trader_address[:10]}...")
            return []
        
        # Retry logic robuste
        retry_count = 0
        max_retries = 2
        
        while retry_count < max_retries:
            try:
                # Appel Helius pour obtenir les transactions parsées
                url = f"https://api-mainnet.helius-rpc.com/v0/addresses/{trader_address}/transactions/?api-key={self.helius_api_key}&limit={limit}"
                response = requests.get(url, timeout=8)
                
                if response.status_code == 200:
                    result = response.json()
                    transactions = result if isinstance(result, list) else result.get('transactions', [])
                elif response.status_code == 429:
                    # Rate limited - attendre et retry
                    retry_count += 1
                    if retry_count < max_retries:
                        import time
                        time.sleep(1)
                        continue
                    else:
                        return []
                elif response.status_code == 404:
                    # Pas trouvé
                    return []
                else:
                    # Autre erreur - retry
                    retry_count += 1
                    if retry_count < max_retries:
                        import time
                        time.sleep(0.5)
                        continue
                    else:
                        return []
            
            except requests.Timeout:
                retry_count += 1
                if retry_count < max_retries:
                    import time
                    time.sleep(0.5)
                    continue
                else:
                    print(f"⚠️ Helius timeout pour {trader_address[:10]}...")
                    return []
            
            except Exception as e:
                print(f"⚠️ Helius error {trader_address[:10]}...: {str(e)[:50]}")
                retry_count += 1
                if retry_count < max_retries:
                    import time
                    time.sleep(0.5)
                    continue
                else:
                    return []
        
        # Si on arrive ici sans avoir returné, retourner les transactions traitées
        if 'transactions' not in locals():
            return []
        
        # Parser les transactions pour identifier les swaps
        trades = []
        for tx_data in transactions[:limit]:
            swap_data = self._parse_swap_transaction(tx_data)
            if swap_data:
                trades.append(swap_data)
        
        return trades[:limit]
    
    def _parse_swap_transaction(self, tx_data: Dict) -> Optional[Dict]:
        """Parse une transaction Solana pour extraire les infos de swap"""
        try:
            # Si c'est une chaîne (signature), la récupérer via l'API
            if isinstance(tx_data, str):
                url = f"https://api-mainnet.helius-rpc.com/v0/transactions/?api-key={self.helius_api_key}"
                response = requests.post(url, json={"transactions": [tx_data]}, timeout=10)
                result = response.json()
                
                if not result.get('transactions'):
                    return None
                
                tx_data = result['transactions'][0]
            
            # Vérifier que c'est un SWAP
            if tx_data.get('type') != 'SWAP':
                return None
            
            # Extraire les informations de swap
            # Note: Helius retourne "tokenTransfers" (camelCase), pas "token_transfers"
            token_transfers = tx_data.get('tokenTransfers', tx_data.get('token_transfers', []))
            
            # Si pas de token transfers, on ne peut pas extraire les infos (peut être SOL/Token swap)
            if len(token_transfers) < 1:
                return None
            
            # Pour un swap, on a au minimum 1 token transfer
            swap_token = token_transfers[0]
            
            # Récupérer les montants réels
            native_transfers = tx_data.get('nativeTransfers', [])
            in_amount = 0
            if native_transfers and native_transfers[0].get('amount'):
                in_amount = float(native_transfers[0].get('amount', 0)) / 1_000_000_000
            else:
                # Fallback: utiliser fee comme proxy
                in_amount = float(tx_data.get('fee', 0.1)) / 1_000_000_000
            
            # Ensure in_amount is at least 0.01 SOL (meme coin minimum)
            if in_amount < 0.01:
                in_amount = 0.01
            
            out_amount = float(swap_token.get('tokenAmount', 0))
            
            # Pour meme coins, les quantités peuvent être énormes. Limiter pour éviter e-24
            # Si out_amount est déjà énorme, diviser pour garder un prix raisonnable
            normalized_out_amount = out_amount
            if out_amount > 1_000_000_000:  # Si > 1 billion tokens
                normalized_out_amount = out_amount / 1_000_000  # Diviser par 1 million
            
            swap = {
                'signature': tx_data.get('signature', tx_data.get('description', 'unknown'))[:64],
                'timestamp': tx_data.get('timestamp', datetime.now().isoformat()),
                'type': 'SWAP',
                'source': tx_data.get('source', 'Unknown'),  # DEX (Raydium, Orca, Jupiter, PumpFun, etc)
                'in_mint': 'SOL',  # Assume SOL in by default (or could parse from nativeTransfers)
                'in_amount': in_amount,  # SOL amount réel
                'out_mint': swap_token.get('mint', ''),  # Token reçu
                'out_amount': normalized_out_amount,  # Quantité normalisée pour éviter e-24
                'fee': tx_data.get('fee', 0) / 1_000_000_000,  # Convert to SOL
                'status': 'success'
            }
            
            return swap
        except Exception as e:
            print(f"⚠️ Erreur parsing swap: {e}")
            return None
    
    def calculate_slippage_percent(self, trade: Dict) -> float:
        """
        Calcule le slippage réel d'un trade (%)
        Pour meme coins, peut être 0-100%+
        """
        try:
            in_amount = trade.get('in_amount', 0)
            out_amount = trade.get('out_amount', 0)
            
            if in_amount == 0 or out_amount == 0:
                return 0
            
            # Slippage = (théorique - réel) / théorique * 100
            theoretical_ratio = in_amount / out_amount if out_amount > 0 else 1
            slippage = (theoretical_ratio - 1) * 100
            return max(0, slippage)
        except Exception:
            return 0
    
    def apply_slippage_to_execution(self, trade: Dict, slippage_percent: float) -> Dict:
        """Applique le slippage à l'exécution du trade"""
        execution = trade.copy()
        if slippage_percent > 0:
            # Réduire la quantité reçue par le slippage
            out_amount_after_slippage = execution.get('out_amount', 0) * (1 - slippage_percent / 100)
            execution['out_amount_slipped'] = out_amount_after_slippage
            execution['slippage_applied_percent'] = slippage_percent
        else:
            execution['out_amount_slipped'] = execution.get('out_amount', 0)
            execution['slippage_applied_percent'] = 0
        
        return execution
    
    def simulate_trade_for_trader(self, trader_name: str, trade: Dict, capital_allocation: float) -> Dict:
        """Simule l'exécution d'un trade copié pour un trader avec capital fictif"""
        try:
            # Initialiser le portefeuille du trader s'il n'existe pas
            if trader_name not in self.trader_portfolios:
                self.trader_portfolios[trader_name] = {
                    'capital': capital_allocation,
                    'available_balance': capital_allocation,
                    'positions': {},  # {token_mint: {amount, entry_price}}
                    'realized_pnl': 0,
                    'trades': []
                }
            
            trader_portfolio = self.trader_portfolios[trader_name]
            trade_id = f"{trader_name}_{trade['signature']}"
            
            # Vérifier si ce trade a déjà été simulé
            if any(t.get('signature') == trade['signature'] for t in trader_portfolio['trades']):
                return {'status': 'duplicate', 'message': 'Trade already simulated'}
            
            # Calculer la proportion du trade basée sur le capital disponible
            available = trader_portfolio['available_balance']
            if available <= 0:
                return {'status': 'insufficient_balance', 'message': 'Solde insuffisant'}
            
            # Montant à investir (proportionnel au capital disponible)
            trade_amount_usd = available * 0.1  # Investir 10% du capital disponible par trade
            
            # Calculer et appliquer le slippage RÉEL
            real_slippage = self.calculate_slippage_percent(trade)
            trade_with_slippage = self.apply_slippage_to_execution(trade, real_slippage)
            
            # Créer l'exécution simulée avec slippage appliqué
            execution = {
                'id': trade_id,
                'timestamp': datetime.now().isoformat(),
                'trader_transaction': trade['signature'],
                'in_token': trade['in_mint'],
                'out_token': trade['out_mint'],
                'in_amount': trade['in_amount'],
                'out_amount': trade.get('out_amount', 0),
                'out_amount_after_slippage': trade_with_slippage.get('out_amount_slipped', 0),
                'slippage_percent': real_slippage,
                'simulated_amount_usd': trade_amount_usd,
                'status': 'executed',
                'pnl': 0,
                'pnl_percent': 0
            }
            
            # Ajouter le trade au portefeuille
            trader_portfolio['trades'].append(execution)
            trader_portfolio['available_balance'] -= trade_amount_usd
            
            # Ajouter à la position (en utilisant la quantité après slippage)
            token_key = trade['out_mint']
            out_amount_final = trade_with_slippage.get('out_amount_slipped', trade.get('out_amount', 0))
            
            if token_key not in trader_portfolio['positions']:
                trader_portfolio['positions'][token_key] = {
                    'amount': out_amount_final,
                    'entry_price_usd': trade_amount_usd / out_amount_final if out_amount_final > 0 else 0,
                    'purchase_usd': trade_amount_usd,
                    'purchase_timestamp': execution['timestamp'],
                    'slippage_incurred': real_slippage
                }
            else:
                # Augmenter la position
                pos = trader_portfolio['positions'][token_key]
                old_cost = pos['amount'] * pos['entry_price_usd']
                pos['amount'] += out_amount_final
                pos['entry_price_usd'] = (old_cost + trade_amount_usd) / pos['amount'] if pos['amount'] > 0 else 0
                pos['purchase_usd'] += trade_amount_usd
                pos['slippage_incurred'] = real_slippage
            
            self._save_trader_portfolios()
            
            return {
                'status': 'success',
                'execution': execution,
                'portfolio_update': {
                    'available_balance': trader_portfolio['available_balance'],
                    'positions': len(trader_portfolio['positions']),
                    'total_invested': capital_allocation - trader_portfolio['available_balance']
                }
            }
        except Exception as e:
            print(f"❌ Erreur simulation trade: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def calculate_trader_pnl(self, trader_name: str, current_prices: Dict[str, float]) -> Dict:
        """Calcule le PnL réel d'un trader basé sur les positions actuelles"""
        if trader_name not in self.trader_portfolios:
            return {'pnl': 0, 'pnl_percent': 0, 'positions': 0}
        
        portfolio = self.trader_portfolios[trader_name]
        total_pnl = portfolio['realized_pnl']
        total_investment = 0
        
        # Calculer le PnL des positions ouvertes
        for token_mint, position in portfolio['positions'].items():
            current_price = current_prices.get(token_mint, position['entry_price_usd'])
            position_value = position['amount'] * current_price
            position_pnl = position_value - position['purchase_usd']
            position['pnl'] = position_pnl
            position['pnl_percent'] = (position_pnl / position['purchase_usd'] * 100) if position['purchase_usd'] > 0 else 0
            
            total_pnl += position_pnl
            total_investment += position['purchase_usd']
        
        pnl_percent = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        return {
            'pnl': round(total_pnl, 2),
            'pnl_percent': round(pnl_percent, 2),
            'positions': len(portfolio['positions']),
            'available_balance': portfolio['available_balance'],
            'total_invested': total_investment,
            'trades_count': len(portfolio['trades'])
        }
    
    def get_trader_simulation_status(self, trader_name: str) -> Dict:
        """Retourne l'état complet de la simulation pour un trader"""
        if trader_name not in self.trader_portfolios:
            return {'status': 'not_started', 'message': 'No simulation for this trader'}
        
        portfolio = self.trader_portfolios[trader_name]
        return {
            'status': 'active',
            'trader': trader_name,
            'capital': portfolio['capital'],
            'available_balance': portfolio['available_balance'],
            'invested': portfolio['capital'] - portfolio['available_balance'],
            'positions': len(portfolio['positions']),
            'trades': len(portfolio['trades']),
            'latest_trades': portfolio['trades'][-5:] if portfolio['trades'] else []
        }

# Instance globale
copy_trading_simulator = CopyTradingSimulator()
