# -*- coding: utf-8 -*-
"""
Health Checker - Monitoring santé de tous les services du bot
"""
import os
import time
import requests
from typing import Dict
from datetime import datetime

class ServiceHealth:
    """Représente la santé d'un service"""
    def __init__(self, name: str):
        self.name = name
        self.is_healthy = True
        self.last_check = None
        self.consecutive_failures = 0
        self.total_checks = 0
        self.total_failures = 0
    
    def record_success(self):
        self.is_healthy = True
        self.last_check = datetime.now().isoformat()
        self.consecutive_failures = 0
        self.total_checks += 1
    
    def record_failure(self, error_msg: str):
        self.consecutive_failures += 1
        self.total_failures += 1
        self.total_checks += 1
        self.last_check = datetime.now().isoformat()
        if self.consecutive_failures >= 3:
            self.is_healthy = False

class HealthChecker:
    """Gestionnaire de health checks"""
    
    def __init__(self):
        self.services: Dict[str, ServiceHealth] = {}
        self._init_services()
    
    def _init_services(self):
        """Initialise les services à monitorer"""
        self.services["Solana Public RPC"] = ServiceHealth("Solana Public RPC")
        self.services["SQLite Database"] = ServiceHealth("SQLite Database")
        if os.getenv('HELIUS_API_KEY'):
            self.services["Helius API"] = ServiceHealth("Helius API")
        print(f"✅ Health Checker initialisé avec {len(self.services)} services")
    
    def check_rpc_health(self, name: str, rpc_url: str) -> bool:
        """Vérifie la santé d'un RPC"""
        try:
            response = requests.post(rpc_url, json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"}, timeout=5)
            if response.status_code == 200:
                self.services[name].record_success()
                return True
            else:
                self.services[name].record_failure(f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.services[name].record_failure(str(e)[:100])
            return False
    
    def check_database_health(self) -> bool:
        """Vérifie la santé de la base de données"""
        try:
            from db_manager import db_manager
            cursor = db_manager.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            self.services["SQLite Database"].record_success()
            return True
        except Exception as e:
            self.services["SQLite Database"].record_failure(str(e)[:100])
            return False
    
    def perform_all_checks(self) -> Dict[str, bool]:
        """Effectue tous les health checks"""
        results = {}
        results["Solana Public RPC"] = self.check_rpc_health("Solana Public RPC", "https://api.mainnet-beta.solana.com")
        results["SQLite Database"] = self.check_database_health()
        return results
    
    def get_overall_health(self) -> Dict:
        """Retourne la santé globale"""
        total_services = len(self.services)
        healthy_services = sum(1 for s in self.services.values() if s.is_healthy)
        return {
            'overall_healthy': healthy_services == total_services,
            'healthy_count': healthy_services,
            'total_services': total_services,
            'timestamp': datetime.now().isoformat()
        }

health_checker = HealthChecker()
