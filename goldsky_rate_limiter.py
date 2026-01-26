# -*- coding: utf-8 -*-
"""
Goldsky Rate Limiter - Coordination des accès API Goldsky

Goldsky a un rate limit strict. Ce module coordonne les accès
entre l'Insider Scanner et le HFT Monitor pour éviter les erreurs 429.

Stratégie:
- Limite globale de requêtes par seconde
- Backoff exponentiel sur erreur 429
- File d'attente avec priorité (HFT > Insider pour latence)
"""
import threading
import time
import logging
from typing import Dict, Optional, Callable
from collections import deque
from dataclasses import dataclass
from enum import IntEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldskyRateLimiter")


class Priority(IntEnum):
    """Priorité des requêtes (plus bas = plus prioritaire)"""
    HFT = 1       # HFT a besoin de latence minimale
    INSIDER = 2   # Insider peut attendre un peu


@dataclass
class RateLimitStats:
    """Statistiques du rate limiter"""
    total_requests: int = 0
    rate_limited_requests: int = 0
    backoff_events: int = 0
    current_delay_ms: int = 0


class GoldskyRateLimiter:
    """
    Rate limiter global pour les appels Goldsky API.
    Thread-safe et partagé entre tous les composants.
    """

    # Singleton instance
    _instance = None
    _lock = threading.Lock()

    # Configuration
    DEFAULT_MIN_INTERVAL_MS = 200    # 5 requêtes/seconde max
    DEFAULT_BACKOFF_BASE_MS = 1000   # 1s backoff initial
    DEFAULT_BACKOFF_MAX_MS = 30000   # 30s backoff max

    def __new__(cls):
        """Singleton pattern - une seule instance partagée"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Timing
        self._last_request_time = 0
        self._min_interval_ms = self.DEFAULT_MIN_INTERVAL_MS

        # Backoff state
        self._current_backoff_ms = 0
        self._backoff_until = 0
        self._backoff_base_ms = self.DEFAULT_BACKOFF_BASE_MS
        self._backoff_max_ms = self.DEFAULT_BACKOFF_MAX_MS

        # Thread safety
        self._request_lock = threading.Lock()

        # Stats
        self.stats = RateLimitStats()

        logger.info(f"GoldskyRateLimiter initialisé (min_interval: {self._min_interval_ms}ms)")

    def wait_for_slot(self, priority: Priority = Priority.INSIDER) -> float:
        """
        Attend qu'un slot soit disponible pour faire une requête.
        Retourne le temps d'attente en secondes.

        Args:
            priority: Priorité de la requête (HFT = 1, INSIDER = 2)

        Returns:
            Temps attendu en secondes
        """
        with self._request_lock:
            self.stats.total_requests += 1
            now = time.time() * 1000  # en ms

            # Vérifier si on est en backoff
            if now < self._backoff_until:
                wait_ms = self._backoff_until - now
                # HFT peut réduire le backoff de 50%
                if priority == Priority.HFT:
                    wait_ms = wait_ms * 0.5
                self.stats.rate_limited_requests += 1
            else:
                # Calculer le temps depuis la dernière requête
                elapsed_ms = now - self._last_request_time
                wait_ms = max(0, self._min_interval_ms - elapsed_ms)

                # HFT a moins d'intervalle minimum
                if priority == Priority.HFT and wait_ms > 0:
                    wait_ms = wait_ms * 0.5

            # Attendre si nécessaire
            if wait_ms > 0:
                self.stats.current_delay_ms = int(wait_ms)
                time.sleep(wait_ms / 1000)
            else:
                self.stats.current_delay_ms = 0

            # Mettre à jour le timestamp
            self._last_request_time = time.time() * 1000

            return wait_ms / 1000

    def report_rate_limit(self):
        """
        Appelé quand une erreur 429 est reçue.
        Augmente le backoff exponentiellement.
        """
        with self._request_lock:
            self.stats.backoff_events += 1

            # Backoff exponentiel
            if self._current_backoff_ms == 0:
                self._current_backoff_ms = self._backoff_base_ms
            else:
                self._current_backoff_ms = min(
                    self._current_backoff_ms * 2,
                    self._backoff_max_ms
                )

            self._backoff_until = (time.time() * 1000) + self._current_backoff_ms

            logger.warning(
                f"Rate limit détecté! Backoff: {self._current_backoff_ms}ms "
                f"(total: {self.stats.backoff_events} events)"
            )

    def report_success(self):
        """
        Appelé quand une requête réussit.
        Réduit progressivement le backoff.
        """
        with self._request_lock:
            if self._current_backoff_ms > 0:
                # Réduire le backoff de 25%
                self._current_backoff_ms = int(self._current_backoff_ms * 0.75)
                if self._current_backoff_ms < self._backoff_base_ms:
                    self._current_backoff_ms = 0

    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return {
            'total_requests': self.stats.total_requests,
            'rate_limited_requests': self.stats.rate_limited_requests,
            'backoff_events': self.stats.backoff_events,
            'current_delay_ms': self.stats.current_delay_ms,
            'current_backoff_ms': self._current_backoff_ms,
            'min_interval_ms': self._min_interval_ms
        }

    def set_min_interval(self, interval_ms: int):
        """Configure l'intervalle minimum entre requêtes"""
        self._min_interval_ms = max(100, interval_ms)
        logger.info(f"Intervalle minimum mis à jour: {self._min_interval_ms}ms")


# Instance globale pour import facile
_rate_limiter = None

def get_goldsky_rate_limiter() -> GoldskyRateLimiter:
    """Retourne l'instance singleton du rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = GoldskyRateLimiter()
    return _rate_limiter
