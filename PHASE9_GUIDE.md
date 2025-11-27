# 📘 Guide d'Utilisation - Phase 9 Optimisations

## 🎯 Vue d'Ensemble

Phase 9 ajoute 5 nouveaux fichiers au bot pour des optimisations **100% GRATUITES** :

1. `jito_integration.py` - Protection MEV gratuite
2. `retry_handler.py` - Retry intelligent
3. `health_checker.py` - Monitoring services
4. `performance_logger.py` - Logs métriques
5. `integration_phase9.py` - Orchestration de tout

## 🚀 Utilisation

### 1. Utiliser Jito pour les Transactions

```python
from integration_phase9 import phase9

# Envoyer une transaction avec protection MEV
result = phase9.send_transaction_with_jito(
    signed_tx="votre_transaction_signée",
    urgency="high"  # low, normal, high, critical
)

if result:
    print(f"✅ Transaction envoyée: {result['signature']}")
    print(f"   Latence: {result['latency_ms']}ms")
```

**Urgences disponibles**:
- `low`: Priority fee 80% du median (économique)
- `normal`: Priority fee 120% du median (défaut)
- `high`: Priority fee 200% du median (rapide)
- `critical`: Priority fee 300% du median (ultra-rapide)

### 2. Vérifier la Santé du Système

```python
from integration_phase9 import phase9

# Check santé complète
health = phase9.check_system_health()

print(f"Santé globale: {health['overall']['overall_healthy']}")
print(f"Services OK: {health['overall']['healthy_count']}/{health['overall']['total_services']}")

# Détails par service
for service, status in health['checks'].items():
    print(f"  {service}: {'✅' if status else '❌'}")
```

**Services monitorés**:
- Solana Public RPC
- SQLite Database  
- Helius API (si clé configurée)

### 3. Logger les Performances

```python
from performance_logger import performance_logger

# Logger un trade
performance_logger.log_trade_execution({
    'trader': 'AlphaMoon',
    'latency_ms': 450,
    'slippage_percent': 0.8,
    'success': True
})

# Logger une erreur
performance_logger.log_error({
    'module': 'solana_executor',
    'error_message': 'RPC timeout'
})

# Récupérer les stats
stats = performance_logger.get_stats()
print(f"Success rate: {stats['success_rate_percent']}%")
print(f"Latence moyenne: {stats['avg_latency_ms']}ms")
```

### 4. Utiliser le Retry Handler

```python
from retry_handler import retry, default_retry_handler

# Méthode 1: Avec décorateur
@retry(max_attempts=3, base_delay=1.0)
def ma_fonction_risquee():
    # Code qui peut échouer
    return risky_operation()

# Méthode 2: Avec handler direct
def operation():
    return quelque_chose()

result = default_retry_handler.execute(operation)
```

### 5. Obtenir Toutes les Stats Phase 9

```python
from integration_phase9 import phase9

stats = phase9.get_all_stats()

print("📊 Stats Jito:")
print(f"  Transactions: {stats['jito']['total_transactions']}")
print(f"  Succès: {stats['jito']['successful_transactions']}")

print("\n🔄 Stats Retry:")
print(f"  Exécutions: {stats['retry']['total_executions']}")
print(f"  Retries: {stats['retry']['total_retries']}")

print("\n🏥 Health:")
print(f"  Services OK: {stats['health']['healthy_count']}/{stats['health']['total_services']}")

print("\n📈 Performance:")
print(f"  Trades: {stats['performance']['total_trades']}")
print(f"  Success rate: {stats['performance']['success_rate_percent']}%")
```

## 🌐 Routes API (à ajouter dans bot.py)

### GET /api/phase9/health
Retourne la santé de tous les services

**Réponse**:
```json
{
  "success": true,
  "data": {
    "checks": {
      "Solana Public RPC": true,
      "SQLite Database": true
    },
    "overall": {
      "overall_healthy": true,
      "healthy_count": 2,
      "total_services": 2
    },
    "jito_stats": {...},
    "retry_stats": {...}
  }
}
```

### GET /api/phase9/stats
Retourne toutes les statistiques Phase 9

**Réponse**:
```json
{
  "success": true,
  "data": {
    "jito": {
      "total_transactions": 0,
      "successful_transactions": 0
    },
    "retry": {
      "total_executions": 0,
      "total_retries": 0
    },
    "health": {...},
    "performance": {...}
  }
}
```

### GET /api/phase9/performance/logs
Retourne les derniers logs de performance (50 derniers)

## 📊 Fichiers de Logs

### performance_metrics.jsonl
Format JSONL (1 JSON par ligne), facile à parser.

**Exemple d'entrée**:
```json
{"timestamp": "2025-11-27T19:30:00", "type": "trade_execution", "trader": "AlphaMoon", "latency_ms": 450, "slippage_percent": 0.8, "success": true}
```

**Lire les logs**:
```python
import json

with open('performance_metrics.jsonl', 'r') as f:
    for line in f:
        entry = json.loads(line)
        print(entry)
```

## 🔧 Configuration

### Changer la région Jito préférée

```python
from jito_integration import jito_integration, JitoRegion

# Changer pour Tokyo
jito_integration.preferred_region = JitoRegion.TOKYO
```

**Régions disponibles**:
- `AMSTERDAM` - Europe
- `FRANKFURT` - Europe (défaut)
- `NEW_YORK` - USA
- `TOKYO` - Asie

### Ajuster les paramètres de retry

```python
from retry_handler import RetryHandler

# Créer un handler personnalisé
custom_retry = RetryHandler(
    max_attempts=5,        # 5 tentatives max
    base_delay=0.5,        # Délai de base 0.5s
    max_delay=20.0         # Délai max 20s
)

result = custom_retry.execute(ma_fonction)
```

## 🎯 Cas d'Usage Recommandés

### 1. Envoyer toutes les transactions via Jito
Protection MEV automatique pour tous les trades

### 2. Logger tous les trades
Analyse post-mortem complète avec métriques détaillées

### 3. Health check toutes les 30s
Monitoring proactif pour détecter les problèmes avant crash

### 4. Retry sur tous les appels RPC
Résilience automatique face aux erreurs réseau

## ⚠️ Notes Importantes

1. **Jito**: Endpoints publics GRATUITS, pas besoin de compte
2. **Logs**: Le fichier JSONL grossit, penser à nettoyer régulièrement
3. **Health checks**: Ne pas faire trop souvent (max 1x/30s) pour éviter rate limiting
4. **Retry**: Attention aux opérations non-idempotentes (éviter double envoi)

## 💡 Exemples Complets

Voir `integration_phase9.py` pour des exemples d'intégration complète.

---

**Phase 9 - Optimisations 100% GRATUITES** 🚀
