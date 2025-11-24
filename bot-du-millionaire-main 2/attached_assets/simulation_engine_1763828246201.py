import requests
import time
import json
import random
from bot_logic import BotBackend

class RealisticSimulation:
    def __init__(self, backend):
        self.backend = backend
        self.rpc_url = backend.data['rpc_url']
        
    def update_portfolio_value(self):
        """Met à jour la valeur du portefeuille basée sur les traders actifs"""
        if not self.backend.is_running:
            return self.backend.virtual_balance
        
        total_value = 1000
        
        for trader in self.backend.data['traders']:
            if trader['active']:
                performance = random.uniform(-2, 5)
                total_value += (1000 / self.backend.get_active_traders_count()) * (performance / 100)
        
        self.backend.virtual_balance = total_value
        return round(total_value, 2)
