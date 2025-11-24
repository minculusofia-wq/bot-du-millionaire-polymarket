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
        
    def _load_simulated_trades(self) -> Dict:
        """Charge les trades simulés"""
        try:
            with open('simulated_trades.json', 'r') as f:
                return json.load(f)
        except:
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
        except:
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
        """Récupère les VRAIES transactions d'un trader via Helius"""
        if not self.helius_api_key:
            return []
        
        try:
            # Appel Helius pour obtenir les transactions parsées
            url = f"https://api-mainnet.helius-rpc.com/v0/addresses/{trader_address}/transactions/?api-key={self.helius_api_key}"
            response = requests.get(url, timeout=10)
            result = response.json()
            
            transactions = result.get('transactions', [])
            if not transactions:
                return []
            
            # Parser les transactions pour identifier les swaps
            trades = []
            for tx_sig in transactions[:limit]:
                swap_data = self._parse_swap_transaction(tx_sig)
                if swap_data:
                    trades.append(swap_data)
            
            return trades[:limit]
        except Exception as e:
            print(f"❌ Erreur récupération trades Helius: {e}")
            return []
    
    def _parse_swap_transaction(self, tx_signature: str) -> Optional[Dict]:
        """Parse une transaction Solana pour extraire les infos de swap"""
        try:
            # Récupérer la transaction via Helius
            url = f"https://api-mainnet.helius-rpc.com/v0/transactions/?api-key={self.helius_api_key}"
            response = requests.post(url, json={"transactions": [tx_signature]}, timeout=10)
            result = response.json()
            
            if not result.get('transactions'):
                return None
            
            tx_data = result['transactions'][0]
            
            # Vérifier que c'est un SWAP
            if tx_data.get('type') != 'SWAP':
                return None
            
            # Extraire les informations de swap
            token_transfers = tx_data.get('token_transfers', [])
            if len(token_transfers) < 2:
                return None
            
            in_token = token_transfers[0]
            out_token = token_transfers[1]
            
            swap = {
                'signature': tx_signature,
                'timestamp': tx_data.get('timestamp', datetime.now().isoformat()),
                'type': 'SWAP',
                'source': tx_data.get('source', 'Unknown'),  # DEX (Raydium, Orca, Jupiter, etc)
                'in_mint': in_token.get('mint', ''),
                'in_amount': float(in_token.get('tokenAmount', 0)),
                'out_mint': out_token.get('mint', ''),
                'out_amount': float(out_token.get('tokenAmount', 0)),
                'fee': tx_data.get('fee', 0) / 1_000_000_000,  # Convert to SOL
                'status': 'success'
            }
            
            return swap
        except Exception as e:
            print(f"⚠️ Erreur parsing swap {tx_signature}: {e}")
            return None
    
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
            
            # Créer l'exécution simulée
            execution = {
                'id': trade_id,
                'timestamp': datetime.now().isoformat(),
                'trader_transaction': trade['signature'],
                'in_token': trade['in_mint'],
                'out_token': trade['out_mint'],
                'in_amount': trade['in_amount'],
                'out_amount': trade['out_amount'],
                'simulated_amount_usd': trade_amount_usd,
                'status': 'executed',
                'pnl': 0,
                'pnl_percent': 0
            }
            
            # Ajouter le trade au portefeuille
            trader_portfolio['trades'].append(execution)
            trader_portfolio['available_balance'] -= trade_amount_usd
            
            # Ajouter à la position
            token_key = trade['out_mint']
            if token_key not in trader_portfolio['positions']:
                trader_portfolio['positions'][token_key] = {
                    'amount': 0,
                    'entry_price_usd': trade_amount_usd / trade['out_amount'] if trade['out_amount'] > 0 else 0,
                    'purchase_usd': trade_amount_usd,
                    'purchase_timestamp': execution['timestamp']
                }
            else:
                # Augmenter la position
                pos = trader_portfolio['positions'][token_key]
                old_cost = pos['amount'] * pos['entry_price_usd']
                pos['amount'] += trade['out_amount']
                pos['entry_price_usd'] = (old_cost + trade_amount_usd) / pos['amount'] if pos['amount'] > 0 else 0
                pos['purchase_usd'] += trade_amount_usd
            
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
