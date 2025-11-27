# Phase 9 - Routes API à Ajouter dans bot.py

## Routes à intégrer (copier-coller dans bot.py)

```python
# ============================================
# PHASE 9: ROUTES API OPTIMISATIONS
# ============================================

@app.route('/api/phase9/health', methods=['GET'])
def get_system_health():
    """Retourne la santé de tous les services"""
    try:
        from integration_phase9 import phase9
        health_data = phase9.check_system_health()
        return jsonify({
            'success': True,
            'data': health_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/phase9/stats', methods=['GET'])
def get_phase9_stats():
    """Retourne toutes les stats Phase 9"""
    try:
        from integration_phase9 import phase9
        stats = phase9.get_all_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/phase9/performance/logs', methods=['GET'])
def get_performance_logs():
    """Retourne les derniers logs de performance"""
    try:
        from performance_logger import performance_logger
        
        # Lire les derniers logs (fichier JSONL)
        logs = []
        try:
            with open('performance_metrics.jsonl', 'r') as f:
                lines = f.readlines()
                # Derniers 50 logs
                for line in lines[-50:]:
                    logs.append(json.loads(line.strip()))
        except FileNotFoundError:
            pass
        
        return jsonify({
            'success': True,
            'data': {
                'logs': logs,
                'stats': performance_logger.get_stats()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

## Comment les intégrer dans bot.py:

1. Ouvrir bot.py
2. Chercher la section avec les autres routes API
3. Copier-coller les 3 routes ci-dessus
4. Sauvegarder le fichier
5. Redémarrer le bot

## Tests des routes:

```bash
# Test health check
curl http://localhost:5000/api/phase9/health

# Test stats
curl http://localhost:5000/api/phase9/stats

# Test performance logs
curl http://localhost:5000/api/phase9/performance/logs
```
