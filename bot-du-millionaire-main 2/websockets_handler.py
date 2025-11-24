"""
WebSockets Handler
Updates en temps réel du dashboard
"""
from flask import emit
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
from typing import Dict, Optional

class WebSocketsHandler:
    """Gère les WebSockets pour les updates temps réel"""
    
    def __init__(self, socketio: Optional[SocketIO] = None):
        self.socketio = socketio
        self.connected_clients = set()
        self.last_update = {}
        
    def init_app(self, app, socketio):
        """Initialise les WebSockets"""
        self.socketio = socketio
        
        @socketio.on('connect')
        def handle_connect():
            self.connected_clients.add(id)
            emit('status', {'data': 'Connected'})
        
        @socketio.on('disconnect')
        def handle_disconnect():
            self.connected_clients.discard(id)
            
    def broadcast_portfolio_update(self, portfolio_data: Dict):
        """Broadcast update du portefeuille"""
        if self.socketio:
            self.socketio.emit('portfolio_update', portfolio_data, broadcast=True)
            
    def broadcast_trade_executed(self, trade_data: Dict):
        """Broadcast execution de trade"""
        if self.socketio:
            self.socketio.emit('trade_executed', trade_data, broadcast=True)
            
    def broadcast_trader_update(self, trader_data: Dict):
        """Broadcast update d'un trader"""
        if self.socketio:
            self.socketio.emit('trader_update', trader_data, broadcast=True)
            
    def broadcast_alert(self, alert_data: Dict):
        """Broadcast une alerte"""
        if self.socketio:
            self.socketio.emit('alert', alert_data, broadcast=True)
            
    def broadcast_performance(self, performance_data: Dict):
        """Broadcast les performances"""
        if self.socketio:
            self.socketio.emit('performance', performance_data, broadcast=True)
            
    def get_connected_count(self) -> int:
        """Retourne le nombre de clients connectés"""
        return len(self.connected_clients)

ws_handler = WebSocketsHandler()
