# -*- coding: utf-8 -*-
"""
Trade Validator - Valide les trades avant exécution
Réduit les trades non-rentables et protège le capital
"""
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("TradeValidator")


class TradeValidator:
    """Valide les trades selon plusieurs critères de risque"""
    
    def __init__(self, config: Dict = None):
        """
        Initialise le validateur avec une configuration
        
        Args:
            config: Configuration Polymarket du backend
        """
        self.config = config or {}
        
        # Paramètres par défaut
        self.max_position_usd = self.config.get('max_position_usd', 100)
        self.min_position_usd = self.config.get('min_position_usd', 5)
        self.max_open_positions = self.config.get('max_open_positions', 10)
        self.max_per_market = self.config.get('max_per_market', 500)
        self.min_market_liquidity = self.config.get('min_market_liquidity', 5000)
        
        logger.info(f"✅ Trade Validator initialisé")
        logger.info(f"   Max position: ${self.max_position_usd}")
        logger.info(f"   Min position: ${self.min_position_usd}")
        logger.info(f"   Max positions ouvertes: {self.max_open_positions}")
    
    def validate(self, signal: Dict, current_positions: List[Dict]) -> Tuple[bool, str]:
        """
        Valide un signal de trading
        
        Args:
            signal: Signal de trading à valider
            current_positions: Liste des positions actuellement ouvertes
        
        Returns:
            (is_valid, reason): True si valide, False sinon avec la raison
        """
        # 1. Vérifier la taille de la position
        position_size = signal.get('value_usd', 0)
        if position_size > self.max_position_usd:
            return False, f"Position trop grande: ${position_size:.2f} > ${self.max_position_usd}"
        
        if position_size < self.min_position_usd:
            return False, f"Position trop petite: ${position_size:.2f} < ${self.min_position_usd}"
        
        # 2. Vérifier la liquidité du marché
        market = signal.get('market', {})
        liquidity = market.get('liquidity', 0)
        if liquidity < self.min_market_liquidity:
            return False, f"Liquidité insuffisante: ${liquidity:.0f} < ${self.min_market_liquidity}"
        
        # 3. Vérifier le nombre de positions ouvertes
        open_positions = [p for p in current_positions if p.get('status') == 'OPEN']
        if len(open_positions) >= self.max_open_positions:
            return False, f"Nombre max de positions atteint: {len(open_positions)}/{self.max_open_positions}"
        
        # 4. Vérifier l'exposition par marché
        market_slug = market.get('slug', '')
        if market_slug:
            existing_exposure = sum(
                p.get('value_usd', 0) for p in open_positions
                if p.get('market_slug') == market_slug
            )
            total_exposure = existing_exposure + position_size
            
            if total_exposure > self.max_per_market:
                return False, f"Exposition max sur '{market_slug}' atteinte: ${total_exposure:.2f} > ${self.max_per_market}"
        
        # 5. Vérifier le volume du marché (optionnel)
        volume = market.get('volume', 0)
        if volume > 0 and volume < 1000:
            logger.warning(f"⚠️ Volume faible sur {market_slug}: ${volume:.0f}")
        
        # Tous les critères sont OK
        return True, "OK"
    
    def validate_with_details(self, signal: Dict, current_positions: List[Dict]) -> Dict:
        """
        Valide un signal et retourne des détails complets
        
        Returns:
            {
                'valid': bool,
                'reason': str,
                'checks': {
                    'position_size': {'passed': bool, 'message': str},
                    'liquidity': {'passed': bool, 'message': str},
                    ...
                }
            }
        """
        checks = {}
        
        # Check 1: Taille de position
        position_size = signal.get('value_usd', 0)
        if self.min_position_usd <= position_size <= self.max_position_usd:
            checks['position_size'] = {
                'passed': True,
                'message': f"${position_size:.2f} dans les limites"
            }
        else:
            checks['position_size'] = {
                'passed': False,
                'message': f"${position_size:.2f} hors limites (${self.min_position_usd}-${self.max_position_usd})"
            }
        
        # Check 2: Liquidité
        market = signal.get('market', {})
        liquidity = market.get('liquidity', 0)
        checks['liquidity'] = {
            'passed': liquidity >= self.min_market_liquidity,
            'message': f"${liquidity:.0f} (min: ${self.min_market_liquidity})"
        }
        
        # Check 3: Nombre de positions
        open_positions = [p for p in current_positions if p.get('status') == 'OPEN']
        checks['open_positions'] = {
            'passed': len(open_positions) < self.max_open_positions,
            'message': f"{len(open_positions)}/{self.max_open_positions} positions"
        }
        
        # Check 4: Exposition par marché
        market_slug = market.get('slug', '')
        if market_slug:
            existing_exposure = sum(
                p.get('value_usd', 0) for p in open_positions
                if p.get('market_slug') == market_slug
            )
            total_exposure = existing_exposure + position_size
            checks['market_exposure'] = {
                'passed': total_exposure <= self.max_per_market,
                'message': f"${total_exposure:.2f}/${self.max_per_market} sur {market_slug}"
            }
        
        # Résultat global
        all_passed = all(check['passed'] for check in checks.values())
        failed_checks = [name for name, check in checks.items() if not check['passed']]
        
        return {
            'valid': all_passed,
            'reason': "OK" if all_passed else f"Échecs: {', '.join(failed_checks)}",
            'checks': checks
        }
    
    def update_config(self, new_config: Dict):
        """Met à jour la configuration du validateur"""
        self.config.update(new_config)
        self.max_position_usd = self.config.get('max_position_usd', self.max_position_usd)
        self.min_position_usd = self.config.get('min_position_usd', self.min_position_usd)
        self.max_open_positions = self.config.get('max_open_positions', self.max_open_positions)
        self.max_per_market = self.config.get('max_per_market', self.max_per_market)
        self.min_market_liquidity = self.config.get('min_market_liquidity', self.min_market_liquidity)
        logger.info("✅ Configuration du validateur mise à jour")


if __name__ == '__main__':
    # Tests basiques
    print("=== Tests Trade Validator ===")
    
    validator = TradeValidator({
        'max_position_usd': 100,
        'min_position_usd': 5,
        'max_open_positions': 10,
        'min_market_liquidity': 5000
    })
    
    # Test 1: Signal valide
    signal1 = {
        'value_usd': 50,
        'market': {
            'slug': 'test-market',
            'liquidity': 10000
        }
    }
    is_valid, reason = validator.validate(signal1, [])
    assert is_valid, f"Test 1 failed: {reason}"
    print("✅ Test 1: Signal valide OK")
    
    # Test 2: Position trop grande
    signal2 = {
        'value_usd': 200,
        'market': {'liquidity': 10000}
    }
    is_valid, reason = validator.validate(signal2, [])
    assert not is_valid, "Test 2 failed"
    assert "trop grande" in reason, f"Test 2 failed: {reason}"
    print("✅ Test 2: Position trop grande rejetée OK")
    
    # Test 3: Liquidité insuffisante
    signal3 = {
        'value_usd': 50,
        'market': {'liquidity': 1000}
    }
    is_valid, reason = validator.validate(signal3, [])
    assert not is_valid, "Test 3 failed"
    assert "Liquidité" in reason, f"Test 3 failed: {reason}"
    print("✅ Test 3: Liquidité insuffisante rejetée OK")
    
    # Test 4: Trop de positions ouvertes
    positions = [{'status': 'OPEN', 'value_usd': 10} for _ in range(10)]
    is_valid, reason = validator.validate(signal1, positions)
    assert not is_valid, "Test 4 failed"
    assert "max de positions" in reason, f"Test 4 failed: {reason}"
    print("✅ Test 4: Trop de positions rejetée OK")
    
    # Test 5: Validation avec détails
    result = validator.validate_with_details(signal1, [])
    assert result['valid'], f"Test 5 failed: {result}"
    assert all(check['passed'] for check in result['checks'].values())
    print(f"✅ Test 5: Validation détaillée OK - {result}")
    
    print("\n🎉 Tous les tests passés!")
