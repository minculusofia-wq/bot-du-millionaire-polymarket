# -*- coding: utf-8 -*-
"""
Cache Manager - Système de cache simple en mémoire avec TTL
Réduit les appels API répétés et améliore les performances
"""
import time
import logging
from functools import wraps
from typing import Any, Callable, Optional
from threading import Lock

logger = logging.getLogger("CacheManager")


class SimpleCache:
    """Cache simple en mémoire avec expiration (TTL)"""
    
    def __init__(self):
        self._cache = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        logger.info("✅ Cache Manager initialisé")
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache si elle existe et n'est pas expirée"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    self._hits += 1
                    logger.debug(f"Cache HIT: {key}")
                    return value
                else:
                    # Clé expirée, la supprimer
                    del self._cache[key]
                    logger.debug(f"Cache EXPIRED: {key}")
            
            self._misses += 1
            logger.debug(f"Cache MISS: {key}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 60):
        """Stocke une valeur dans le cache avec un TTL en secondes"""
        with self._lock:
            expiry = time.time() + ttl
            self._cache[key] = (value, expiry)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
    
    def delete(self, key: str):
        """Supprime une clé du cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache DELETE: {key}")
    
    def clear(self):
        """Vide complètement le cache"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info(f"Cache CLEARED: {count} entrées supprimées")
    
    def get_stats(self) -> dict:
        """Retourne les statistiques du cache"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                'size': len(self._cache),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 2),
                'total_requests': total
            }
    
    def cleanup_expired(self):
        """Nettoie les entrées expirées du cache"""
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if now >= expiry
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cache cleanup: {len(expired_keys)} entrées expirées supprimées")


def cached(ttl: int = 60, key_prefix: str = ""):
    """
    Decorator pour cacher automatiquement les résultats d'une fonction
    
    Args:
        ttl: Durée de vie du cache en secondes (défaut: 60s)
        key_prefix: Préfixe optionnel pour la clé de cache
    
    Usage:
        @cached(ttl=30)
        def get_price(token_id):
            return expensive_api_call(token_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Construire la clé de cache
            # Format: prefix:function_name:args:kwargs
            args_str = ':'.join(str(arg) for arg in args)
            kwargs_str = ':'.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = f"{key_prefix}{func.__name__}:{args_str}:{kwargs_str}"
            
            # Essayer de récupérer depuis le cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Exécuter la fonction et cacher le résultat
            result = func(*args, **kwargs)
            
            # Ne cacher que si le résultat n'est pas None
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        
        # Ajouter une méthode pour invalider le cache de cette fonction
        wrapper.invalidate_cache = lambda *args, **kwargs: cache.delete(
            f"{key_prefix}{func.__name__}:{':'.join(str(arg) for arg in args)}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
        )
        
        return wrapper
    return decorator


# Instance globale du cache
cache = SimpleCache()


# Fonction utilitaire pour nettoyer périodiquement
def start_cleanup_scheduler(interval: int = 300):
    """
    Démarre un thread qui nettoie le cache périodiquement
    
    Args:
        interval: Intervalle de nettoyage en secondes (défaut: 5 minutes)
    """
    import threading
    
    def cleanup_loop():
        while True:
            time.sleep(interval)
            cache.cleanup_expired()
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info(f"🧹 Cache cleanup scheduler démarré (intervalle: {interval}s)")


if __name__ == '__main__':
    # Tests basiques
    print("=== Tests Cache Manager ===")
    
    # Test 1: Set et Get
    cache.set('test_key', 'test_value', ttl=5)
    assert cache.get('test_key') == 'test_value', "Test 1 failed"
    print("✅ Test 1: Set/Get OK")
    
    # Test 2: Expiration
    cache.set('expire_key', 'expire_value', ttl=1)
    time.sleep(2)
    assert cache.get('expire_key') is None, "Test 2 failed"
    print("✅ Test 2: Expiration OK")
    
    # Test 3: Decorator
    @cached(ttl=5)
    def expensive_function(x):
        return x * 2
    
    result1 = expensive_function(5)
    result2 = expensive_function(5)  # Devrait venir du cache
    assert result1 == result2 == 10, "Test 3 failed"
    print("✅ Test 3: Decorator OK")
    
    # Test 4: Stats
    stats = cache.get_stats()
    print(f"✅ Test 4: Stats OK - {stats}")
    
    print("\n🎉 Tous les tests passés!")
