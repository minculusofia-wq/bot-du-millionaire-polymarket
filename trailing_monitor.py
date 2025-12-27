# -*- coding: utf-8 -*-
"""
Trailing Stop Monitor
Surveille les positions ouvertes et déclenche la vente si le Trailing Stop est touché.
"""
import time
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TrailingStopMonitor:
    def __init__(self, db_manager, executor, poll_interval=10):
        self.db_manager = db_manager
        self.executor = executor
        self.poll_interval = poll_interval
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self):
        """Démarre le moniteur en arrière-plan"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("🛡️ Trailing Stop Monitor démarré")

    def stop(self):
        """Arrête le moniteur"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("🛡️ Trailing Stop Monitor arrêté")

    def _monitor_loop(self):
        """Boucle principale de surveillance"""
        while self.running:
            try:
                self._check_positions()
            except Exception as e:
                logger.error(f"❌ Erreur dans Trailing Monitor: {e}")
            
            time.sleep(self.poll_interval)

    def _check_positions(self):
        """Vérifie toutes les positions avec Trailing Stop actif"""
        # Récupérer positions OPEN avec use_trailing=1
        # Note: On suppose que db_manager.get_active_positions peut filtrer ou on filtre ici
        positions = self.db_manager.get_bot_positions(status='OPEN')
        
        for pos in positions:
            if not pos.get('use_trailing'):
                continue

            pos_id = pos['id']
            token_id = pos['token_id']
            sl_percent = pos.get('sl_percent') # ex: 10 pour 10%
            highest_price = pos.get('highest_price', 0) or pos['entry_price']

            if not sl_percent:
                continue

            # Récupérer prix actuel (SELL price car on veut vendre)
            # On utilise le cache de l'executor ou appel direct
            current_price = self.executor.get_market_price(token_id, side='SELL')
            
            if not current_price:
                continue

            # 1. Mise à jour du Highest Price
            if current_price > highest_price:
                new_highest = current_price
                self.db_manager.update_position_highest_price(pos_id, new_highest)
                logger.info(f"📈 Position #{pos_id}: Nouveau sommet ${new_highest:.4f} (Ancien: ${highest_price:.4f})")
                highest_price = new_highest

            # 2. Vérification du Trailing Stop
            # Seuil de vente = Highest * (1 - SL%)
            trailing_threshold = highest_price * (1 - (sl_percent / 100))
            
            if current_price < trailing_threshold:
                logger.warning(f"🛡️ TRAILING STOP DÉCLENCHÉ pour #{pos_id} !")
                logger.warning(f"   Prix: ${current_price:.4f} < Seuil: ${trailing_threshold:.4f} (High: ${highest_price:.4f}, SL: {sl_percent}%)")

                # Exécuter la vente via l'executor
                try:
                    result = self.executor.sell_position(
                        position_id=pos_id,
                        amount=None  # Tout vendre
                    )
                    if result.get('success'):
                        logger.info(f"✅ Position #{pos_id} vendue (Trailing Stop) - PnL: ${result.get('pnl', 0):.2f}")
                    else:
                        logger.error(f"❌ Échec vente position #{pos_id}: {result.get('error')}")
                except Exception as e:
                    logger.error(f"❌ Erreur vente Trailing Stop #{pos_id}: {e}")

    def get_stats(self):
        """Retourne les statistiques du moniteur"""
        return {
            'running': self.running,
            'poll_interval': self.poll_interval
        }


# Instance globale (optionnelle, créée dans bot.py)
trailing_monitor = None
