# -*- coding: utf-8 -*-
"""
Retry Handler - Système de retry intelligent avec exponential backoff
"""
import time
import random
from typing import Callable, Any
from functools import wraps

class RetryHandler:
    """Gestionnaire de retry intelligent"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.stats = {'total_executions': 0, 'successful_executions': 0, 'total_retries': 0}
    
    def calculate_delay(self, attempt: int) -> float:
        """Calcule le délai avant le prochain retry (exponential backoff)"""
        delay = self.base_delay * (2 ** attempt)
        delay = min(delay, self.max_delay)
        # Jitter +/- 20%
        jitter_range = delay * 0.2
        delay += random.uniform(-jitter_range, jitter_range)
        return max(0.1, delay)
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Exécute une fonction avec retry automatique"""
        self.stats['total_executions'] += 1
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)
                self.stats['successful_executions'] += 1
                if attempt > 0:
                    print(f"✅ Succès après {attempt + 1} tentatives")
                return result
            except Exception as e:
                last_exception = e
                if attempt == self.max_attempts - 1:
                    self.stats['total_retries'] += attempt
                    raise
                delay = self.calculate_delay(attempt)
                self.stats['total_retries'] += 1
                print(f"⏳ Retry dans {delay:.1f}s... (tentative {attempt + 2}/{self.max_attempts})")
                time.sleep(delay)
        raise last_exception
    
    def get_stats(self) -> dict:
        """Retourne les statistiques"""
        return self.stats

def retry(max_attempts: int = 3, base_delay: float = 1.0):
    """Décorateur pour ajouter retry automatique"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(max_attempts=max_attempts, base_delay=base_delay)
            return handler.execute(func, *args, **kwargs)
        return wrapper
    return decorator

default_retry_handler = RetryHandler(max_attempts=3, base_delay=1.0)
