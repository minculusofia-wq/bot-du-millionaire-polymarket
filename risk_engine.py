# -*- coding: utf-8 -*-
"""
Risk Engine - Moteur unifié haute fréquence (1s)
Gère le Stop Loss, Take Profit, Trailing Stop et les sorties partielles (Capital Recovery).
"""
import time
import threading
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from db_manager import db_manager

logger = logging.getLogger("RiskEngine")

class RiskEngine:
    def __init__(self, executor, client, poll_interval: float = 1.0):
        self.executor = executor
        self.client = client
        self.db = db_manager
        self.poll_interval = poll_interval
        self.running = False
        self.thread = None
        
        # Cache de prix partagé pour éviter les appels API redondants par seconde
        self.price_cache = {} # {token_id: (price, timestamp)}
        self.cache_ttl = 0.8 # Cache très court pour la réactivité
        
        logger.info("🛡️ Risk Engine Unifié initialisé (Intervalle: {}s)".format(poll_interval))

    def start(self):
        """Démarre le moteur de risque"""
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        logger.info("🚀 Risk Engine démarré")

    def stop(self):
        """Arrête le moteur"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("⏹️ Risk Engine arrêté")

    def _main_loop(self):
        """Boucle de surveillance ultra-rapide"""
        while self.running:
            try:
                start_time = time.time()
                self._process_cycle()
                
                # Calculer le temps d'attente pour rester à ~1s (soustraire le temps de traitement)
                elapsed = time.time() - start_time
                wait_time = max(0.1, self.poll_interval - elapsed)
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"❌ Erreur critique RiskEngine: {e}")
                time.sleep(1)

    def _process_cycle(self):
        """Un cycle complet de vérification de toutes les positions"""
        positions = self.db.get_bot_positions(status='OPEN')
        if not positions:
            return

        for pos in positions:
            try:
                self._check_position(pos)
            except Exception as e:
                logger.error(f"❌ Erreur position #{pos.get('id')}: {e}")

    def _get_price(self, token_id: str) -> Optional[float]:
        """Récupère le prix avec un cache très court"""
        now = time.time()
        if token_id in self.price_cache:
            price, ts = self.price_cache[token_id]
            if now - ts < self.cache_ttl:
                return price
        
        # Obtenir prix (SELL side car on veut sortir)
        try:
            price = self.executor.get_market_price(token_id, side='SELL')
            if price:
                self.price_cache[token_id] = (price, now)
                return price
        except:
            pass
        return None

    def _check_position(self, pos: Dict):
        """Logique de décision pour une position"""
        pos_id = pos['id']
        token_id = pos['token_id']
        entry_price = pos['entry_price']
        
        current_price = self._get_price(token_id)
        if not current_price: return

        # 1. Calculer PnL %
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        # 2. Mise à jour PnL non-réalisé et Highest Price (pour Trailing)
        highest_price = pos.get('highest_price', 0) or entry_price
        if current_price > highest_price:
            self.db.update_position_highest_price(pos_id, current_price)
            highest_price = current_price
            
        unrealized_pnl = (current_price - entry_price) * pos.get('shares', 0)
        self.db.update_position_price(pos_id, current_price, unrealized_pnl)

        # 3. Check STOP LOSS (Classique)
        sl_pct = pos.get('sl_percent')
        if sl_pct and pnl_pct <= -abs(sl_pct): # Supporte format -5 ou 5
            logger.warning(f"🛑 STOP LOSS touché pour #{pos_id} ({pnl_pct:.2f}%)")
            self._trigger_exit(pos, reason='STOP_LOSS')
            return

        # 4. Check TRAILING STOP
        if pos.get('use_trailing') and sl_pct:
            # Seuil de vente = Sommet * (1 - SL%)
            trailing_threshold = highest_price * (1 - (abs(sl_pct) / 100))
            if current_price < trailing_threshold:
                logger.warning(f"🛡️ TRAILING STOP touché pour #{pos_id} (Prix: {current_price} < Seuil: {trailing_threshold:.4f})")
                self._trigger_exit(pos, reason='TRAILING_STOP')
                return

        # 5. Check TAKE PROFIT (Classique ou Paliers)
        tp_pct = pos.get('tp_percent')
        if tp_pct and pnl_pct >= tp_pct:
            logger.info(f"🎯 TAKE PROFIT touché pour #{pos_id} (+{pnl_pct:.2f}%)")
            self._trigger_exit(pos, reason='TAKE_PROFIT')
            return

        # 6. Mode "Risk-Free" (Capital Recovery)
        # On vérifie si le capital a déjà été récupéré
        if not pos.get('capital_recovered') and tp_pct:
            # On déclenche si on a atteint le TP (ou un seuil dédié, ici on utilise TP comme déclencheur du risk-free)
            if pnl_pct >= tp_pct:
                logger.info(f"💰 Mode RISK-FREE déclenché pour #{pos_id} (+{pnl_pct:.2f}%)")
                
                # Calculer shares à vendre pour récupérer la mise initiale
                initial_investment = pos.get('size', 0) # 'size' stocke le montant USD investi
                if initial_investment > 0 and current_price > 0:
                    shares_to_sell = initial_investment / current_price
                    total_shares = pos.get('shares', 0)
                    
                    if shares_to_sell < total_shares:
                        logger.info(f"   Vente de {shares_to_sell:.4f} shares pour récupérer ${initial_investment:.2f}")
                        self._trigger_exit(pos, reason='CAPITAL_RECOVERY', amount_shares=shares_to_sell)
                        self.db.update_position_capital_recovered(pos_id, 1)
                        return # On s'arrête là pour ce cycle

        # 7. Paliers de sortie (Partial TP)
        exit_tiers_str = pos.get('exit_tiers')
        if exit_tiers_str:
            try:
                tiers = json.loads(exit_tiers_str)
                # Trier par profit croissant pour exécuter le premier atteint
                tiers.sort(key=lambda x: x['profit'])
                for tier in tiers:
                    if not tier.get('executed') and pnl_pct >= tier['profit']:
                        pct = tier['sell_pct']
                        logger.info(f"🎯 PALIER TP {tier['profit']}% atteint pour #{pos_id}")
                        
                        shares_to_sell = pos['shares'] * (pct / 100.0)
                        self._trigger_exit(pos, reason=f'PARTIAL_TP_{tier["profit"]}%', amount_shares=shares_to_sell)
                        
                        # Marquer le palier comme exécuté dans le JSON et update DB
                        tier['executed'] = True
                        self.db.update_position_exit_tiers(pos_id, json.dumps(tiers))
                        return
            except Exception as e:
                logger.error(f"❌ Erreur processing tiers #{pos_id}: {e}")

    def _trigger_exit(self, pos: Dict, reason: str, amount_usd: float = None, amount_shares: float = None):
        """Exécute l'ordre de sortie"""
        pos_id = pos['id']
        logger.info(f"🔻 Exécution sortie position #{pos_id} | Raison: {reason}")
        
        # Déterminer le slippage à appliquer selon la raison
        # Sorties d'urgence (SL, Trailing) = Slippage plus agressif (1%)
        # Sorties profitables (TP, Capital Recovery) = Slippage léger (0.2%)
        slippage = 0.2
        if reason in ['STOP_LOSS', 'TRAILING_STOP']:
            slippage = 1.0

        # Calculer amount_usd si amount_shares est fourni
        if amount_shares and not amount_usd:
            current_price = self._get_price(pos['token_id'])
            if current_price:
                amount_usd = amount_shares * current_price

        # Appel à l'executor
        result = self.executor.sell_position(
            position_id=pos_id,
            amount=amount_usd, # En USD
            market=pos.get('market_slug'),
            slippage=slippage
        )
        
        if result.get('success'):
            logger.info(f"✅ Position #{pos_id} clôturée via {reason}")
        else:
            logger.error(f"❌ Échec sortie #{pos_id}: {result.get('error')}")

# Instance globale
risk_engine = None

def init_risk_engine(executor, client):
    global risk_engine
    risk_engine = RiskEngine(executor, client)
    return risk_engine
