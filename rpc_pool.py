# -*- coding: utf-8 -*-
"""
RPC Pool Manager - Pool de connexions RPC avec load balancing et fallback
✨ Phase 9 Optimization: Haute disponibilité et réduction de latence

Features:
- Pool de plusieurs RPC endpoints
- Load balancing (round-robin, least-latency)
- Fallback automatique si un RPC est down
- Health checks périodiques
- Circuit breaker pour éviter les RPC lents
"""
import requests
import time
import threading
from typing import List, Dict, Optional, Any
from enum import Enum
import random


class LoadBalancingStrategy(Enum):
    """Stratégies de load balancing"""
    ROUND_ROBIN = "round_robin"  # Tour à tour
    LEAST_LATENCY = "least_latency"  # RPC le plus rapide
    RANDOM = "random"  # Aléatoire


class RPCEndpoint:
    """Représente un endpoint RPC avec ses stats"""

    def __init__(self, url: str, name: str = None):
        self.url = url
        self.name = name or url
        self.is_healthy = True
        self.latency = 0.0  # ms
        self.total_requests = 0
        self.failed_requests = 0
        self.last_check = time.time()
        self.circuit_breaker_open = False
        self.circuit_breaker_fail_count = 0

    def record_success(self, latency: float):
        """Enregistre une requête réussie"""
        self.total_requests += 1
        self.latency = latency
        self.is_healthy = True
        self.circuit_breaker_fail_count = 0
        self.circuit_breaker_open = False

    def record_failure(self):
        """Enregistre une requête échouée"""
        self.total_requests += 1
        self.failed_requests += 1
        self.circuit_breaker_fail_count += 1

        # Circuit breaker: après 3 échecs consécutifs, ouvrir le circuit
        if self.circuit_breaker_fail_count >= 3:
            self.circuit_breaker_open = True
            self.is_healthy = False
            print(f"⚠️ Circuit breaker ouvert pour {self.name}")

    def get_success_rate(self) -> float:
        """Retourne le taux de succès (0-1)"""
        if self.total_requests == 0:
            return 1.0
        return 1.0 - (self.failed_requests / self.total_requests)

    def reset_circuit_breaker(self):
        """Reset le circuit breaker"""
        self.circuit_breaker_open = False
        self.circuit_breaker_fail_count = 0
        self.is_healthy = True


class RPCPool:
    """
    Pool de connexions RPC avec load balancing

    Exemples:
    >>> pool = RPCPool()
    >>> pool.add_endpoint("https://api.mainnet-beta.solana.com")
    >>> pool.add_endpoint("https://rpc.helius.xyz/?api-key=XXX")
    >>> result = pool.call("getBalance", ["address123"])
    """

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LATENCY):
        """
        Initialise le pool RPC

        Args:
            strategy: Stratégie de load balancing
        """
        self.endpoints: List[RPCEndpoint] = []
        self.strategy = strategy
        self.current_index = 0  # Pour round-robin
        self.lock = threading.Lock()

        # Stats globales
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'fallback_count': 0,
            'avg_latency': 0.0
        }

        # Health checker
        self.health_check_interval = 30  # 30s
        self.health_check_thread = None
        self.is_running = False

    def add_endpoint(self, url: str, name: str = None):
        """Ajoute un endpoint RPC au pool"""
        endpoint = RPCEndpoint(url, name)
        self.endpoints.append(endpoint)
        print(f"✅ RPC ajouté au pool: {endpoint.name}")

    def start_health_checks(self):
        """Démarre les health checks périodiques"""
        if self.is_running:
            return

        self.is_running = True

        def health_check_loop():
            while self.is_running:
                time.sleep(self.health_check_interval)
                self._perform_health_checks()

        self.health_check_thread = threading.Thread(target=health_check_loop, daemon=True)
        self.health_check_thread.start()
        print("✅ Health checks RPC démarrés")

    def stop_health_checks(self):
        """Arrête les health checks"""
        self.is_running = False

    def _perform_health_checks(self):
        """Effectue les health checks sur tous les endpoints"""
        print("🔍 Health check RPC...")

        for endpoint in self.endpoints:
            try:
                start = time.time()
                response = requests.post(
                    endpoint.url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                    timeout=5
                )
                latency = (time.time() - start) * 1000  # ms

                if response.status_code == 200:
                    endpoint.record_success(latency)
                    if endpoint.circuit_breaker_open:
                        endpoint.reset_circuit_breaker()
                        print(f"✅ Circuit breaker fermé pour {endpoint.name}")
                else:
                    endpoint.record_failure()
            except Exception as e:
                endpoint.record_failure()
                print(f"⚠️ Health check failed for {endpoint.name}: {e}")

    def _select_endpoint(self) -> Optional[RPCEndpoint]:
        """Sélectionne un endpoint selon la stratégie"""
        # Filtrer les endpoints sains
        healthy_endpoints = [e for e in self.endpoints if e.is_healthy and not e.circuit_breaker_open]

        if not healthy_endpoints:
            # Tous sont down, essayer de réinitialiser un circuit breaker
            print("⚠️ Tous les RPC sont down, tentative de reset...")
            for endpoint in self.endpoints:
                endpoint.reset_circuit_breaker()
            healthy_endpoints = self.endpoints

        if not healthy_endpoints:
            return None

        # Stratégie de sélection
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            with self.lock:
                selected = healthy_endpoints[self.current_index % len(healthy_endpoints)]
                self.current_index += 1
                return selected

        elif self.strategy == LoadBalancingStrategy.LEAST_LATENCY:
            # Choisir le RPC avec la latence la plus faible
            return min(healthy_endpoints, key=lambda e: e.latency if e.latency > 0 else 999)

        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(healthy_endpoints)

        return healthy_endpoints[0]

    def call(self, method: str, params: List[Any], timeout: int = 10) -> Optional[Dict]:
        """
        Appelle une méthode RPC avec fallback automatique

        Args:
            method: Méthode RPC (ex: "getBalance")
            params: Paramètres de la méthode
            timeout: Timeout en secondes

        Returns:
            Résultat de la méthode ou None si tous les RPC échouent
        """
        if not self.endpoints:
            print("❌ Aucun endpoint RPC configuré!")
            return None

        self.stats['total_calls'] += 1
        attempts = 0
        max_attempts = min(3, len(self.endpoints))  # Max 3 tentatives

        while attempts < max_attempts:
            endpoint = self._select_endpoint()
            if not endpoint:
                break

            try:
                start = time.time()
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
                }

                response = requests.post(endpoint.url, json=payload, timeout=timeout)
                latency = (time.time() - start) * 1000  # ms

                if response.status_code == 200:
                    data = response.json()

                    if 'result' in data:
                        # Succès!
                        endpoint.record_success(latency)
                        self.stats['successful_calls'] += 1
                        self._update_avg_latency(latency)
                        return data

                    elif 'error' in data:
                        # Erreur RPC
                        print(f"⚠️ RPC error from {endpoint.name}: {data['error']}")
                        endpoint.record_failure()
                else:
                    endpoint.record_failure()

            except requests.Timeout:
                print(f"⚠️ Timeout sur {endpoint.name}")
                endpoint.record_failure()
            except Exception as e:
                print(f"⚠️ Erreur RPC sur {endpoint.name}: {str(e)[:50]}")
                endpoint.record_failure()

            attempts += 1
            if attempts < max_attempts:
                self.stats['fallback_count'] += 1
                print(f"🔄 Fallback sur un autre RPC... (tentative {attempts + 1}/{max_attempts})")

        # Tous les endpoints ont échoué
        self.stats['failed_calls'] += 1
        print("❌ Tous les endpoints RPC ont échoué")
        return None

    def _update_avg_latency(self, latency: float):
        """Met à jour la latence moyenne"""
        total = self.stats['successful_calls']
        if total == 1:
            self.stats['avg_latency'] = latency
        else:
            # Moyenne mobile
            self.stats['avg_latency'] = (self.stats['avg_latency'] * (total - 1) + latency) / total

    def get_stats(self) -> Dict:
        """Retourne les statistiques du pool"""
        success_rate = 0
        if self.stats['total_calls'] > 0:
            success_rate = (self.stats['successful_calls'] / self.stats['total_calls']) * 100

        return {
            'total_calls': self.stats['total_calls'],
            'successful_calls': self.stats['successful_calls'],
            'failed_calls': self.stats['failed_calls'],
            'success_rate_percent': round(success_rate, 2),
            'fallback_count': self.stats['fallback_count'],
            'avg_latency_ms': round(self.stats['avg_latency'], 2),
            'endpoints_count': len(self.endpoints),
            'healthy_endpoints': sum(1 for e in self.endpoints if e.is_healthy)
        }

    def get_endpoints_status(self) -> List[Dict]:
        """Retourne le statut de tous les endpoints"""
        return [
            {
                'name': e.name,
                'url': e.url,
                'is_healthy': e.is_healthy,
                'latency_ms': round(e.latency, 2),
                'success_rate': round(e.get_success_rate() * 100, 2),
                'total_requests': e.total_requests,
                'circuit_breaker_open': e.circuit_breaker_open
            }
            for e in self.endpoints
        ]


# Instance globale (singleton)
global_rpc_pool = RPCPool(strategy=LoadBalancingStrategy.LEAST_LATENCY)


def initialize_default_pool():
    """Initialise le pool avec des RPCs publics Solana"""
    global_rpc_pool.add_endpoint("https://api.mainnet-beta.solana.com", "Solana Public")
    global_rpc_pool.add_endpoint("https://api.devnet.solana.com", "Solana Devnet")
    global_rpc_pool.start_health_checks()
    return global_rpc_pool


if __name__ == "__main__":
    # Tests unitaires
    print("🧪 Tests du RPCPool...")

    pool = RPCPool()
    pool.add_endpoint("https://api.mainnet-beta.solana.com", "Solana Public")

    # Test 1: Appel simple
    result = pool.call("getHealth", [])
    if result:
        print("✅ Test 1: Appel RPC réussi")
    else:
        print("⚠️ Test 1: Appel RPC échoué (normal si pas de connexion)")

    # Test 2: Stats
    stats = pool.get_stats()
    print(f"✅ Test 2: Stats - {stats}")

    print("\n📊 Stats finales:")
    print(pool.get_stats())
