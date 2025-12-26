import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ajouter le dossier parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trailing_monitor import TrailingStopMonitor

class TestTrailingStop(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_executor = MagicMock()
        self.monitor = TrailingStopMonitor(self.mock_db, self.mock_executor, poll_interval=0)

    def test_update_highest_price(self):
        """Doit mettre à jour highest_price si prix monte"""
        # Context: Position ouverte, use_trailing=True, High=1.0
        pos = {
            'id': 1, 'token_id': 'tok1', 'use_trailing': 1, 'sl_percent': 10,
            'highest_price': 1.0, 'entry_price': 1.0
        }
        self.mock_db.get_bot_positions.return_value = [pos]
        
        # Action: Prix actuel = 1.2
        self.mock_executor.get_market_price.return_value = 1.2
        
        # Run
        self.monitor._check_positions()
        
        # Verify: DB update called with 1.2
        self.mock_db.update_position_highest_price.assert_called_with(1, 1.2)

    def test_trigger_sell(self):
        """Doit vendre si prix passe sous le seuil"""
        # Context: High=2.0, SL=10% => Seuil = 1.8
        pos = {
            'id': 2, 'token_id': 'tok2', 'use_trailing': 1, 'sl_percent': 10,
            'highest_price': 2.0, 'entry_price': 1.0
        }
        self.mock_db.get_bot_positions.return_value = [pos]
        
        # Action: Prix actuel = 1.7 (Sous 1.8)
        self.mock_executor.get_market_price.return_value = 1.7
        
        # Run
        self.monitor._check_positions()
        
        # Verify: Sell triggered
        self.mock_executor.sell_position.assert_called_once()
        call_args = self.mock_executor.sell_position.call_args[1]
        self.assertEqual(call_args['reason'], "TRAILING_STOP_HIT")

    def test_no_trigger_if_safe(self):
        """Ne doit PAS vendre si prix au dessus du seuil"""
        # Context: High=2.0, SL=10% => Seuil = 1.8
        pos = {
            'id': 3, 'token_id': 'tok3', 'use_trailing': 1, 'sl_percent': 10,
            'highest_price': 2.0
        }
        self.mock_db.get_bot_positions.return_value = [pos]
        
        # Action: Prix actuel = 1.9 (Au dessus 1.8)
        self.mock_executor.get_market_price.return_value = 1.9
        
        # Run
        self.monitor._check_positions()
        
        # Verify: Sell NOT triggered
        self.mock_executor.sell_position.assert_not_called()

if __name__ == '__main__':
    unittest.main()
