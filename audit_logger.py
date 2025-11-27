# -*- coding: utf-8 -*-
"""
Audit Logger - Logging sécurisé et audit trail
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional, List
from enum import Enum

class LogLevel(Enum):
    """Niveaux de log"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"

class AuditLogger:
    """Logger sécurisé pour audit trail"""
    
    def __init__(self, log_dir: str = "audit_logs"):
        self.log_dir = log_dir
        self.ensure_log_dir()
        self.in_memory_logs = []
        self.in_memory_limit = 1000  # Garder les 1000 derniers logs en mémoire
        
    def ensure_log_dir(self):
        """Crée le répertoire de logs s'il n'existe pas"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
    
    def log(self, 
            level: LogLevel,
            message: str,
            data: Dict = None,
            action: str = None,
            actor: str = None) -> Dict:
        """
        Crée une entrée de log
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level.value,
            'message': message,
            'action': action,
            'actor': actor,
            'data': data or {}
        }
        
        # Garder en mémoire
        self.in_memory_logs.append(log_entry)
        if len(self.in_memory_logs) > self.in_memory_limit:
            self.in_memory_logs = self.in_memory_logs[-self.in_memory_limit:]
        
        # Écrire dans un fichier
        self._write_to_file(log_entry)
        
        # Print si critique
        if level in [LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.SECURITY]:
            prefix = "🔒" if level == LogLevel.SECURITY else "❌"
            print(f"{prefix} [{level.value}] {message}")
        
        return log_entry
    
    def _write_to_file(self, log_entry: Dict):
        """Écrit le log dans un fichier"""
        # Fichier du jour
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"audit_{date_str}.log")
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"❌ Erreur écriture log: {e}")
    
    def log_trade_execution(self, trade_data: Dict, status: str, trader: str = None):
        """Log l'exécution d'une trade"""
        self.log(
            LogLevel.INFO,
            f"Trade executed: {status}",
            data=trade_data,
            action='TRADE_EXECUTION',
            actor=trader
        )
    
    def log_trade_validation(self, trade_data: Dict, is_valid: bool, reason: str):
        """Log la validation d'une trade"""
        level = LogLevel.INFO if is_valid else LogLevel.WARNING
        action = 'TRADE_APPROVED' if is_valid else 'TRADE_REJECTED'
        
        self.log(
            level,
            f"Trade validation: {reason}",
            data=trade_data,
            action=action
        )
    
    def log_security_event(self, event_type: str, details: Dict, severity: str = "MEDIUM"):
        """Log un événement de sécurité"""
        self.log(
            LogLevel.SECURITY,
            f"Security event: {event_type} ({severity})",
            data=details,
            action=f'SECURITY_{event_type.upper()}'
        )
    
    def log_wallet_action(self, action: str, wallet: str, status: str, details: Dict = None):
        """Log une action sur un wallet"""
        self.log(
            LogLevel.SECURITY,
            f"Wallet action: {action} - {status}",
            data={'wallet': wallet, **(details or {})},
            action=f'WALLET_{action.upper()}'
        )
    
    def log_error(self, message: str, error: Exception, context: Dict = None):
        """Log une erreur"""
        self.log(
            LogLevel.ERROR,
            message,
            data={
                'error_type': type(error).__name__,
                'error_message': str(error),
                **(context or {})
            }
        )
    
    def log_rate_limit(self, service: str, limit: int, reset_time: str):
        """Log un rate limit"""
        self.log(
            LogLevel.WARNING,
            f"Rate limit reached on {service}",
            data={
                'service': service,
                'limit': limit,
                'reset_time': reset_time
            },
            action='RATE_LIMIT'
        )
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Récupère les logs récents en mémoire"""
        return self.in_memory_logs[-limit:]
    
    def get_logs_by_level(self, level: LogLevel, limit: int = 100) -> List[Dict]:
        """Récupère les logs d'un certain niveau"""
        logs = [l for l in self.in_memory_logs if l['level'] == level.value]
        return logs[-limit:]
    
    def get_logs_by_action(self, action: str, limit: int = 100) -> List[Dict]:
        """Récupère les logs d'une certaine action"""
        logs = [l for l in self.in_memory_logs if l['action'] == action]
        return logs[-limit:]
    
    def search_logs(self, query: str, limit: int = 100) -> List[Dict]:
        """Recherche dans les logs"""
        query_lower = query.lower()
        matching = [
            l for l in self.in_memory_logs
            if query_lower in l['message'].lower() or 
               query_lower in json.dumps(l.get('data', {})).lower()
        ]
        return matching[-limit:]
    
    def export_logs(self, filename: str = None) -> str:
        """Exporte les logs en JSON"""
        if filename is None:
            filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.log_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.in_memory_logs, f, indent=2)
            return filepath
        except Exception as e:
            print(f"❌ Erreur export logs: {e}")
            return None
    
    def get_security_summary(self) -> Dict:
        """Résumé des événements de sécurité"""
        security_logs = self.get_logs_by_level(LogLevel.SECURITY)
        errors = self.get_logs_by_level(LogLevel.ERROR)
        
        return {
            'total_security_events': len(security_logs),
            'total_errors': len(errors),
            'recent_security_events': security_logs[-10:],
            'last_security_event': security_logs[-1] if security_logs else None,
            'export_ready': True
        }

# Instance globale
audit_logger = AuditLogger()
