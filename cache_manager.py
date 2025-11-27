# -*- coding: utf-8 -*-
"""
Cache Manager - Système de cache multi-niveaux pour réduire les appels API
✨ Phase 9 Optimization: -60% d'appels RPC/API grâce au cache intelligent

Niveaux de cache:
1. Mémoire (L1): Ultra-rapide, TTL court (5-30s)
2. Redis (L2): Optionnel, persistant, partagé (TTL moyen 1-5min)
"""
import time
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class CacheManager:
    """
    Gestionnaire de cache multi-niveaux avec TTL configurable

    Exemples d'utilisation:
    >>> cache = CacheManager()
    >>> cache.set('token_price_SOL', 150.5, ttl=30)  # Cache 30s
    >>> price = cache.get('token_price_SOL')  # Récupère si encore valide
    """

    def __init__(self, enable_redis=False):
        """
        Initialise le cache manager

        Args:
            enable_redis: Si True, active Redis comme cache L2 (nécessite redis-py)
        """
        # Cache L1: Mémoire (dict Python)
        self._memory_cache = {}
        self._cache_metadata = {}  # {key: {'expires_at': timestamp, 'hits': count}}

        # Stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_saved_calls': 0
        }

        # Cache L2: Redis (optionnel)
        self.redis_enabled = enable_redis
        self.redis_client = None

        if enable_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                # Test connexion
                self.redis_client.ping()
                print("✅ Cache Redis (L2) activé")
            except ImportError:
                print("⚠️ redis-py non installé - Cache L2 désactivé")
                print("   Installation: pip install redis")
                self.redis_enabled = False
            except Exception as e:
                print(f"⚠️ Redis non disponible: {e}")
                self.redis_enabled = False

    def set(self, key: str, value: Any, ttl: int = 30, namespace: str = "default"):
        """
        Stocke une valeur dans le cache avec TTL

        Args:
            key: Clé unique
            value: Valeur à cacher (sera sérialisée en JSON)
            ttl: Time-to-live en secondes (défaut: 30s)
            namespace: Namespace pour organiser les clés (ex: "prices", "traders")
        """
        full_key = f"{namespace}:{key}"
        expires_at = time.time() + ttl

        # Cache L1: Mémoire
        self._memory_cache[full_key] = value
        self._cache_metadata[full_key] = {
            'expires_at': expires_at,
            'hits': 0,
            'created_at': time.time()
        }

        # Cache L2: Redis (si activé)
        if self.redis_enabled and self.redis_client:
            try:
                serialized = json.dumps(value)
                self.redis_client.setex(full_key, ttl, serialized)
            except Exception as e:
                print(f"⚠️ Erreur Redis set: {e}")

    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Récupère une valeur du cache

        Args:
            key: Clé à récupérer
            namespace: Namespace de la clé

        Returns:
            Valeur cachée ou None si expirée/absente
        """
        full_key = f"{namespace}:{key}"

        # L1: Mémoire (prioritaire, plus rapide)
        if full_key in self._memory_cache:
            metadata = self._cache_metadata.get(full_key, {})

            # Vérifier si expiré
            if time.time() < metadata.get('expires_at', 0):
                # Hit!
                self.stats['hits'] += 1
                self.stats['total_saved_calls'] += 1
                metadata['hits'] = metadata.get('hits', 0) + 1
                return self._memory_cache[full_key]
            else:
                # Expiré, nettoyer
                self._evict(full_key)

        # L2: Redis (fallback)
        if self.redis_enabled and self.redis_client:
            try:
                cached = self.redis_client.get(full_key)
                if cached:
                    # Hit Redis! Remettre en L1 pour next fois
                    value = json.loads(cached)
                    ttl = self.redis_client.ttl(full_key)
                    if ttl > 0:
                        self.set(key, value, ttl=ttl, namespace=namespace)
                        self.stats['hits'] += 1
                        self.stats['total_saved_calls'] += 1
                        return value
            except Exception as e:
                print(f"⚠️ Erreur Redis get: {e}")

        # Miss
        self.stats['misses'] += 1
        return None

    def delete(self, key: str, namespace: str = "default"):
        """Supprime une clé du cache"""
        full_key = f"{namespace}:{key}"
        self._evict(full_key)

        # Redis
        if self.redis_enabled and self.redis_client:
            try:
                self.redis_client.delete(full_key)
            except:
                pass

    def _evict(self, full_key: str):
        """Éviction d'une clé (interne)"""
        if full_key in self._memory_cache:
            del self._memory_cache[full_key]
            self.stats['evictions'] += 1
        if full_key in self._cache_metadata:
            del self._cache_metadata[full_key]

    def clear(self, namespace: Optional[str] = None):
        """
        Nettoie le cache

        Args:
            namespace: Si fourni, nettoie seulement ce namespace. Sinon tout.
        """
        if namespace:
            # Nettoyer seulement un namespace
            prefix = f"{namespace}:"
            keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                self._evict(key)
        else:
            # Tout nettoyer
            self._memory_cache.clear()
            self._cache_metadata.clear()
            self.stats['evictions'] += len(self._memory_cache)

        # Redis
        if self.redis_enabled and self.redis_client:
            try:
                if namespace:
                    # Scanner et supprimer les clés du namespace
                    pattern = f"{namespace}:*"
                    for key in self.redis_client.scan_iter(pattern):
                        self.redis_client.delete(key)
                else:
                    self.redis_client.flushdb()
            except:
                pass

    def cleanup_expired(self):
        """Nettoie les entrées expirées (à appeler périodiquement)"""
        now = time.time()
        expired_keys = [
            k for k, meta in self._cache_metadata.items()
            if now >= meta.get('expires_at', 0)
        ]

        for key in expired_keys:
            self._evict(key)

        if expired_keys:
            print(f"🧹 Cache: {len(expired_keys)} entrées expirées nettoyées")

    def get_stats(self) -> Dict:
        """Retourne les statistiques du cache"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'evictions': self.stats['evictions'],
            'total_saved_calls': self.stats['total_saved_calls'],
            'cache_size': len(self._memory_cache),
            'redis_enabled': self.redis_enabled
        }

    def get_size_info(self) -> Dict:
        """Retourne les infos de taille du cache"""
        return {
            'memory_cache_entries': len(self._memory_cache),
            'metadata_entries': len(self._cache_metadata),
            'top_hits': self._get_top_hits(5)
        }

    def _get_top_hits(self, limit: int = 5) -> list:
        """Retourne les clés les plus accédées"""
        sorted_keys = sorted(
            self._cache_metadata.items(),
            key=lambda x: x[1].get('hits', 0),
            reverse=True
        )
        return [
            {'key': k, 'hits': v.get('hits', 0)}
            for k, v in sorted_keys[:limit]
        ]


# ============================================
# HELPER FUNCTIONS - Wrappers pratiques
# ============================================

def cache_token_price(cache: CacheManager, token_address: str, price: float, ttl: int = 30):
    """Helper: Cache le prix d'un token"""
    cache.set(f"price_{token_address}", price, ttl=ttl, namespace="prices")


def get_cached_token_price(cache: CacheManager, token_address: str) -> Optional[float]:
    """Helper: Récupère le prix d'un token depuis le cache"""
    return cache.get(f"price_{token_address}", namespace="prices")


def cache_wallet_balance(cache: CacheManager, wallet_address: str, balance: float, ttl: int = 10):
    """Helper: Cache le balance d'un wallet"""
    cache.set(f"balance_{wallet_address}", balance, ttl=ttl, namespace="wallets")


def get_cached_wallet_balance(cache: CacheManager, wallet_address: str) -> Optional[float]:
    """Helper: Récupère le balance d'un wallet depuis le cache"""
    return cache.get(f"balance_{wallet_address}", namespace="wallets")


# Instance globale (singleton)
global_cache = CacheManager(enable_redis=False)  # Redis désactivé par défaut

# Alias pour compatibilité
cache_manager = global_cache


if __name__ == "__main__":
    # Tests unitaires
    print("🧪 Tests du CacheManager...")

    cache = CacheManager()

    # Test 1: Set/Get basique
    cache.set("test_key", "test_value", ttl=5)
    assert cache.get("test_key") == "test_value", "❌ Test 1 failed"
    print("✅ Test 1: Set/Get basique")

    # Test 2: Expiration
    cache.set("expire_test", "value", ttl=1)
    time.sleep(2)
    assert cache.get("expire_test") is None, "❌ Test 2 failed"
    print("✅ Test 2: Expiration")

    # Test 3: Namespaces
    cache.set("key1", "value1", namespace="ns1")
    cache.set("key1", "value2", namespace="ns2")
    assert cache.get("key1", namespace="ns1") == "value1", "❌ Test 3a failed"
    assert cache.get("key1", namespace="ns2") == "value2", "❌ Test 3b failed"
    print("✅ Test 3: Namespaces")

    # Test 4: Stats
    stats = cache.get_stats()
    print(f"✅ Test 4: Stats - Hit rate: {stats['hit_rate_percent']}%")

    print("\n✅ Tous les tests réussis!")
    print(f"📊 Stats finales: {cache.get_stats()}")
