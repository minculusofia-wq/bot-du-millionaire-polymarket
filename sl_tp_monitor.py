# -*- coding: utf-8 -*-
"""
SL/TP Monitor - Surveillance automatique des Stop Loss et Take Profit
Surveille les positions ouvertes et déclenche automatiquement les SL/TP
"""
import threading
import time
from typing import Dict, List, Optional
from datetime import datetime
from db_manager import db_manager


class SLTPMonitor:
    """Surveille les positions et déclenche SL/TP automatiquement"""
    
    def __init__(self, executor, client, check_interval: int = 30):
        """
        Initialise le moniteur SL/TP
        
        Args:
            executor: Instance de PolymarketExecutor pour exécuter les ventes
            client: Instance de PolymarketClient pour récupérer les prix
            check_interval: Intervalle de vérification en secondes (défaut: 30s)
        """
        self.db = db_manager
        self.executor = executor
        self.client = client
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.price_cache = {}  # Cache des prix pour optimiser les appels API
        self.cache_ttl = 10  # TTL du cache en secondes
        
        print("✅ SL/TP Monitor initialisé")
    
    def start(self):
        """Démarre le monitoring en arrière-plan"""
        if self.running:
            print("⚠️ Monitoring SL/TP déjà en cours")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("✅ Monitoring SL/TP démarré (intervalle: {}s)".format(self.check_interval))
    
    def stop(self):
        """Arrête le monitoring"""
        if not self.running:
            return
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("⏹️ Monitoring SL/TP arrêté")
    
    def _monitor_loop(self):
        """Boucle de surveillance principale"""
        while self.running:
            try:
                self._check_all_positions()
            except Exception as e:
                print(f"❌ Erreur monitoring SL/TP: {e}")
            
            # Attendre avant la prochaine vérification
            time.sleep(self.check_interval)
    
    def _check_all_positions(self):
        """Vérifie toutes les positions ouvertes"""
        try:
            positions = self.db.get_open_positions()
            
            if not positions:
                return
            
            print(f"🔍 Vérification de {len(positions)} positions...")
            
            for position in positions:
                try:
                    self._check_position(position)
                except Exception as e:
                    print(f"❌ Erreur vérification position {position.get('id')}: {e}")
                    
        except Exception as e:
            print(f"❌ Erreur récupération positions: {e}")
    
    def _check_position(self, position: Dict):
        """Vérifie une position individuelle et déclenche SL/TP si nécessaire
        
        Args:
            position: Dictionnaire contenant les données de la position
        """
        position_id = position.get('id') or position.get('position_id')
        token_id = position.get('token_id')
        entry_price = position.get('entry_price')
        sl_percent = position.get('sl_percent')
        tp_percent = position.get('tp_percent')
        
        # Vérifier que la position a un SL ou TP configuré
        if not sl_percent and not tp_percent:
            return  # Pas de SL/TP configuré pour cette position
        
        # Récupérer le prix actuel (avec cache)
        current_price = self._get_cached_price(token_id)
        
        if not current_price or not entry_price or entry_price == 0:
            return
        
        # Calculer le PnL %
        pnl_percent = ((current_price - entry_price) / entry_price) * 100
        
        # Mettre à jour le prix et PnL dans la DB
        unrealized_pnl = (current_price - entry_price) * position.get('shares', 0)
        self.db.update_position_price(position_id, current_price, unrealized_pnl)
        
        # Vérifier Stop Loss
        if sl_percent and pnl_percent <= sl_percent:
            print(f"🛑 SL déclenché pour position {position_id} ({position.get('market_slug')})")
            print(f"   Prix entrée: {entry_price:.4f}, Prix actuel: {current_price:.4f}, PnL: {pnl_percent:.2f}%")
            self._trigger_sl(position, pnl_percent)
        
        # Vérifier Take Profit
        elif tp_percent and pnl_percent >= tp_percent:
            print(f"🎯 TP déclenché pour position {position_id} ({position.get('market_slug')})")
            print(f"   Prix entrée: {entry_price:.4f}, Prix actuel: {current_price:.4f}, PnL: {pnl_percent:.2f}%")
            self._trigger_tp(position, pnl_percent)
    
    def _get_cached_price(self, token_id: str) -> Optional[float]:
        """Récupère le prix avec cache pour optimiser les appels API
        
        Args:
            token_id: ID du token
            
        Returns:
            Prix actuel ou None
        """
        now = time.time()
        
        # Vérifier le cache
        if token_id in self.price_cache:
            cached_price, cached_time = self.price_cache[token_id]
            if now - cached_time < self.cache_ttl:
                return cached_price
        
        # Récupérer le prix via l'API
        try:
            price = self.client.get_token_price(token_id)
            if price:
                self.price_cache[token_id] = (price, now)
                return price
        except Exception as e:
            print(f"⚠️ Erreur récupération prix pour {token_id}: {e}")
        
        return None
    
    def _trigger_sl(self, position: Dict, pnl_percent: float):
        """Déclenche le Stop Loss pour une position
        
        Args:
            position: Données de la position
            pnl_percent: PnL en pourcentage
        """
        position_id = position.get('id') or position.get('position_id')
        
        try:
            # Exécuter la vente via l'executor
            result = self.executor.sell_position(position_id)
            
            if result.get('success'):
                realized_pnl = result.get('pnl', 0)
                
                # Fermer la position dans la DB
                self.db.close_position(position_id, realized_pnl, status='CLOSED_SL')
                
                print(f"✅ SL exécuté avec succès - PnL réalisé: {realized_pnl:.2f}")
            else:
                print(f"❌ Échec exécution SL: {result.get('error', 'Erreur inconnue')}")
                
        except Exception as e:
            print(f"❌ Erreur déclenchement SL: {e}")
    
    def _trigger_tp(self, position: Dict, pnl_percent: float):
        """Déclenche le Take Profit pour une position
        
        Args:
            position: Données de la position
            pnl_percent: PnL en pourcentage
        """
        position_id = position.get('id') or position.get('position_id')
        
        try:
            # Exécuter la vente via l'executor
            result = self.executor.sell_position(position_id)
            
            if result.get('success'):
                realized_pnl = result.get('pnl', 0)
                
                # Fermer la position dans la DB
                self.db.close_position(position_id, realized_pnl, status='CLOSED_TP')
                
                print(f"✅ TP exécuté avec succès - PnL réalisé: {realized_pnl:.2f}")
            else:
                print(f"❌ Échec exécution TP: {result.get('error', 'Erreur inconnue')}")
                
        except Exception as e:
            print(f"❌ Erreur déclenchement TP: {e}")
    
    def get_status(self) -> Dict:
        """Retourne le statut du monitoring
        
        Returns:
            Dictionnaire avec le statut
        """
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'cache_size': len(self.price_cache),
            'monitored_positions': len(self.db.get_open_positions())
        }


# Instance globale (sera initialisée dans bot.py)
sl_tp_monitor = None


def init_monitor(executor, client, check_interval: int = 30):
    """Initialise le moniteur SL/TP global
    
    Args:
        executor: Instance de PolymarketExecutor
        client: Instance de PolymarketClient
        check_interval: Intervalle de vérification en secondes
    """
    global sl_tp_monitor
    sl_tp_monitor = SLTPMonitor(executor, client, check_interval)
    return sl_tp_monitor
