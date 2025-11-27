# -*- coding: utf-8 -*-
"""
Integration Phase 9 - Connecte tous les nouveaux modules au bot
✨ Intègre: Jito, Retry, Health Checker, Performance Logger
"""

# Import des nouveaux modules
try:
    from jito_integration import jito_integration
    from retry_handler import default_retry_handler, retry
    from health_checker import health_checker
    from performance_logger import performance_logger
    print("✅ Tous les modules Phase 9 importés avec succès")
except ImportError as e:
    print(f"⚠️ Erreur import Phase 9: {e}")

class Phase9Integration:
    """Classe centrale pour utiliser tous les modules Phase 9"""
    
    def __init__(self):
        self.jito = jito_integration
        self.retry = default_retry_handler
        self.health = health_checker
        self.logger = performance_logger
        print("✅ Phase 9 Integration initialisée")
    
    def send_transaction_with_jito(self, signed_tx: str, urgency: str = 'normal'):
        """Envoie une transaction via Jito avec retry automatique"""
        
        def _send():
            return self.jito.send_transaction(signed_tx, urgency=urgency)
        
        # Utiliser retry handler
        try:
            result = self.retry.execute(_send)
            
            # Logger le résultat
            if result:
                self.logger.log_trade_execution({
                    'trader': 'bot',
                    'latency_ms': result.get('latency_ms', 0),
                    'success': True
                })
            return result
        except Exception as e:
            # Logger l'erreur
            self.logger.log_error({
                'module': 'integration_phase9',
                'error_message': str(e)
            })
            return None
    
    def check_system_health(self):
        """Vérifie la santé de tous les services"""
        results = self.health.perform_all_checks()
        overall = self.health.get_overall_health()
        return {
            'checks': results,
            'overall': overall,
            'jito_stats': self.jito.get_stats(),
            'retry_stats': self.retry.get_stats(),
            'logger_stats': self.logger.get_stats()
        }
    
    def get_all_stats(self):
        """Retourne toutes les statistiques Phase 9"""
        return {
            'jito': self.jito.get_stats(),
            'retry': self.retry.get_stats(),
            'health': self.health.get_overall_health(),
            'performance': self.logger.get_stats()
        }

# Instance globale
phase9 = Phase9Integration()
