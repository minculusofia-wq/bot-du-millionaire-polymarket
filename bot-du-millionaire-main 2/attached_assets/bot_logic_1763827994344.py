import json
import random

class BotBackend:
    def __init__(self):
        self.config_file = "config.json"
        self.load_config()
        self.is_running = False
        self.virtual_balance = 1000.0
        
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
        except:
            self.data = {
                "mode": "TEST",
                "slippage": 1.0,
                "active_traders_limit": 3,
                "currency": "USD",
                "wallet_private_key": "",
                "tp1_percent": 33,
                "tp1_profit": 10,
                "tp2_percent": 33,
                "tp2_profit": 25,
                "tp3_percent": 34,
                "tp3_profit": 50,
                "sl_percent": 100,
                "sl_loss": 5,
                "traders": [
                    {"name": "AlphaMoon", "emoji": "🚀", "address": "EQaxqKT3N981QBmdSUGNzAGK5S26zUwAdRHhBCgn87zD", "active": False},
                    {"name": "DeFiKing", "emoji": "♛", "address": "2undvDBttb5ohSggdzEhGUq6mhNBf9JsiLTcsguPp51c", "active": False},
                    {"name": "SolShark", "emoji": "🦈", "address": "DfMxre4cKmvogbLrPigxmibVTTQDuzjdXojWzjCXXhzj", "active": False},
                    {"name": "Merlin", "emoji": "🧙", "address": "89HbgWduLwoxcofWpmn1EiF9wEdpgkNDEyPjzZ72mkDi", "active": False},
                    {"name": "Zap", "emoji": "⚡", "address": "BBPKQwYLyiPjAX2KTFxanR7vxwa7majAF7c7yoaRX8oR", "active": False},
                    {"name": "Dragon", "emoji": "🐉", "address": "CTC7HVkCkPuChSJjArVip375ogvMUtQLhdzLfiPizdEc", "active": False},
                    {"name": "Wisdom", "emoji": "🦉", "address": "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5", "active": False},
                    {"name": "Sniper", "emoji": "🎯", "address": "DmB4xRNaVH2Y2FVBFsJKYvdPDKYjx2sgC8aQFRBF4gB2", "active": False},
                    {"name": "Pirate", "emoji": "🏴‍☠️", "address": "EzLu595m6CRxPybAUjSser9FmjDvjS3d3vyX4CPiu8Xn", "active": False},
                    {"name": "ApeTrain", "emoji": "🚂", "address": "PMJA8UQDyWTFw2Smhyp9jGA6aTaP7jKHR7BPudrgyYN", "active": False}
                ]
            }
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_portfolio_value(self):
        if self.is_running and self.data.get("mode") == "TEST":
            self.virtual_balance += random.uniform(-5, 10)
            return round(self.virtual_balance, 2)
        return round(self.virtual_balance, 2)

    def get_active_traders_count(self):
        return sum(1 for t in self.data['traders'] if t['active'])

    def toggle_trader(self, index, state):
        current_active = self.get_active_traders_count()
        if state and current_active >= self.data['active_traders_limit'] and not self.data['traders'][index]['active']:
            return False
        self.data['traders'][index]['active'] = state
        self.save_config()
        return True

    def toggle_bot(self, status):
        self.is_running = status

    def update_trader(self, index, name, emoji, address):
        self.data['traders'][index]['name'] = name
        self.data['traders'][index]['emoji'] = emoji
        self.data['traders'][index]['address'] = address
        self.save_config()
    
    def update_take_profit(self, tp1_percent, tp1_profit, tp2_percent, tp2_profit, tp3_percent, tp3_profit, sl_percent, sl_loss):
        self.data['tp1_percent'] = tp1_percent
        self.data['tp1_profit'] = tp1_profit
        self.data['tp2_percent'] = tp2_percent
        self.data['tp2_profit'] = tp2_profit
        self.data['tp3_percent'] = tp3_percent
        self.data['tp3_profit'] = tp3_profit
        self.data['sl_percent'] = sl_percent
        self.data['sl_loss'] = sl_loss
        self.save_config()
