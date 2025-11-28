# -*- coding: utf-8 -*-
"""
Advanced Risk Manager - Gestion avancée du risque
Inclut circuit breaker, Kelly criterion, position sizing intelligent
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from db_manager import db_manager
import json
import os


class AdvancedRiskManager:
    """Gestionnaire de risque avancé avec circuit breaker"""

    # Valeurs par défaut (utilisées si pas de sauvegarde)
    # Par défaut tout à 0 = Protection désactivée (mode le plus sûr pour débutant)
    DEFAULT_PARAMS = {
        'circuit_breaker_threshold': 0,  # Désactivé (0 = pas de circuit breaker automatique)
        'circuit_breaker_cooldown': 3600,  # 1 heure
        'max_consecutive_losses': 0,  # Désactivé (0 = pas de limite)
        'max_position_size_percent': 0,  # Désactivé (0 = pas de limite)
        'max_daily_loss_percent': 0,  # Désactivé (0 = pas de limite)
        'max_drawdown_percent': 0,  # Désactivé (0 = pas de limite)
        'kelly_safety_factor': 0,  # Désactivé (0 = pas de Kelly Criterion)
        'save_params': False  # Pas de sauvegarde par défaut
    }

    def __init__(self, total_capital: float = None, config_path: str = 'config.json'):
        # MODE REAL: total_capital sera fourni par get_wallet_balance_dynamic()
        # Si None, on attend l'initialisation dynamique
        self.total_capital = total_capital if total_capital is not None else 0
        self.current_balance = self.total_capital
        self.peak_balance = self.total_capital
        self.config_path = config_path

        # Charger les paramètres (depuis config.json si sauvegarde activée, sinon défaut)
        params = self._load_params()

        # Circuit Breaker Configuration
        self.circuit_breaker_active = False
        self.circuit_breaker_threshold = params['circuit_breaker_threshold'] / 100  # Convertir en fraction
        self.circuit_breaker_cooldown = params['circuit_breaker_cooldown']
        self.circuit_breaker_triggered_at = None

        # Risk Limits
        self.max_position_size_percent = params['max_position_size_percent'] / 100
        self.max_daily_loss_percent = params['max_daily_loss_percent'] / 100
        self.max_drawdown_percent = params['max_drawdown_percent'] / 100

        # Kelly Criterion
        self.kelly_safety_factor = params['kelly_safety_factor']

        # Tracking
        self.consecutive_losses = 0
        self.max_consecutive_losses = params['max_consecutive_losses']
        self.daily_pnl = 0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Sauvegarde activée?
        self.save_params_enabled = params['save_params']

    def _load_params(self) -> Dict:
        """Charge les paramètres depuis config.json si sauvegarde activée"""
        params = self.DEFAULT_PARAMS.copy()

        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                    # Vérifier si save_params est activé
                    risk_config = config.get('advanced_risk_manager', {})
                    if risk_config.get('save_params', False):
                        # Charger les paramètres sauvegardés
                        for key in params.keys():
                            if key in risk_config:
                                params[key] = risk_config[key]
                        print("✅ Paramètres de risque chargés depuis config.json")
                    else:
                        print("ℹ️ Utilisation des paramètres de risque par défaut")
        except Exception as e:
            print(f"⚠️ Erreur chargement paramètres: {e}")

        return params

    def _save_params(self):
        """Sauvegarde les paramètres dans config.json si activé"""
        if not self.save_params_enabled:
            return

        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            config['advanced_risk_manager'] = {
                'circuit_breaker_threshold': self.circuit_breaker_threshold * 100,
                'circuit_breaker_cooldown': self.circuit_breaker_cooldown,
                'max_consecutive_losses': self.max_consecutive_losses,
                'max_position_size_percent': self.max_position_size_percent * 100,
                'max_daily_loss_percent': self.max_daily_loss_percent * 100,
                'max_drawdown_percent': self.max_drawdown_percent * 100,
                'kelly_safety_factor': self.kelly_safety_factor,
                'save_params': True
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print("✅ Paramètres de risque sauvegardés")
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde paramètres: {e}")

    def update_balance(self, new_balance: float):
        """Met à jour le balance actuel"""
        self.current_balance = new_balance
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance

    def calculate_drawdown(self) -> float:
        """Calcule le drawdown actuel en %"""
        if self.peak_balance == 0:
            return 0
        return ((self.current_balance - self.peak_balance) / self.peak_balance) * 100

    def check_circuit_breaker(self) -> bool:
        """Vérifie si le circuit breaker doit être activé"""
        # Vérifier drawdown
        drawdown = self.calculate_drawdown()
        if drawdown <= -(self.circuit_breaker_threshold * 100):
            if not self.circuit_breaker_active:
                self.circuit_breaker_active = True
                self.circuit_breaker_triggered_at = datetime.now()
                print(f"🔴 CIRCUIT BREAKER ACTIVÉ - Drawdown: {drawdown:.2f}%")
            return True

        # Vérifier perte journalière
        if self.total_capital > 0:
            daily_loss_percent = (self.daily_pnl / self.total_capital) * 100
            if daily_loss_percent <= -(self.max_daily_loss_percent * 100):
                if not self.circuit_breaker_active:
                    self.circuit_breaker_active = True
                    self.circuit_breaker_triggered_at = datetime.now()
                    print(f"🔴 CIRCUIT BREAKER ACTIVÉ - Perte journalière: {daily_loss_percent:.2f}%")
                return True

        # Vérifier pertes consécutives
        if self.consecutive_losses >= self.max_consecutive_losses:
            if not self.circuit_breaker_active:
                self.circuit_breaker_active = True
                self.circuit_breaker_triggered_at = datetime.now()
                print(f"🔴 CIRCUIT BREAKER ACTIVÉ - {self.consecutive_losses} pertes consécutives")
            return True

        # Vérifier si cooldown terminé
        if self.circuit_breaker_active and self.circuit_breaker_triggered_at:
            elapsed = (datetime.now() - self.circuit_breaker_triggered_at).total_seconds()
            if elapsed >= self.circuit_breaker_cooldown:
                self.circuit_breaker_active = False
                self.circuit_breaker_triggered_at = None
                print("🟢 Circuit breaker désactivé (cooldown terminé)")
                return False

        return self.circuit_breaker_active

    def calculate_kelly_position_size(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calcule la taille de position optimale selon le critère de Kelly

        Args:
            win_rate: Taux de réussite (0-1)
            avg_win: Gain moyen en %
            avg_loss: Perte moyenne en % (positif)

        Returns:
            Taille de position en % du capital
        """
        if avg_loss == 0 or win_rate == 0:
            return 0

        # Kelly Formula: f = (p * b - q) / b
        # p = win rate, q = 1 - p, b = avg_win / avg_loss
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly_percent = (win_rate * b - q) / b

        # Appliquer safety factor (demi-Kelly par défaut)
        kelly_percent = max(0, kelly_percent * self.kelly_safety_factor)

        # Limiter au max position size
        return min(kelly_percent * 100, self.max_position_size_percent * 100)

    def calculate_position_size(self, trader_data: Dict) -> float:
        """
        Calcule la taille de position recommandée pour un trader

        Args:
            trader_data: {
                'win_rate': float,
                'avg_win_percent': float,
                'avg_loss_percent': float,
                'trader_name': str
            }

        Returns:
            Taille de position en % du capital
        """
        if self.circuit_breaker_active:
            print("⚠️ Circuit breaker actif - Aucune nouvelle position autorisée")
            return 0

        win_rate = trader_data.get('win_rate', 0.5)
        avg_win = trader_data.get('avg_win_percent', 10)
        avg_loss = trader_data.get('avg_loss_percent', 5)

        kelly_size = self.calculate_kelly_position_size(win_rate, avg_win, avg_loss)

        # Réduire la taille si en drawdown
        drawdown = abs(self.calculate_drawdown())
        if drawdown > 10:
            reduction_factor = max(0.3, 1 - (drawdown / 50))  # Réduction progressive
            kelly_size *= reduction_factor
            print(f"📉 Taille de position réduite de {(1-reduction_factor)*100:.1f}% (drawdown: {drawdown:.2f}%)")

        return round(kelly_size, 2)

    def record_trade_result(self, pnl: float, is_win: bool):
        """Enregistre le résultat d'un trade"""
        self.daily_pnl += pnl

        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        # Reset journalier
        now = datetime.now()
        if now.date() > self.daily_reset_time.date():
            self.daily_pnl = pnl  # Nouveau jour
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_risk_metrics(self) -> Dict:
        """Retourne les métriques de risque actuelles"""
        return {
            'circuit_breaker_active': self.circuit_breaker_active,
            'current_drawdown': round(self.calculate_drawdown(), 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'consecutive_losses': self.consecutive_losses,
            'current_balance': round(self.current_balance, 2),
            'peak_balance': round(self.peak_balance, 2)
        }

    def get_correlation_matrix(self, traders: List[str]) -> Dict:
        """
        Calcule la matrice de corrélation entre les traders

        Args:
            traders: Liste des noms de traders

        Returns:
            Dictionnaire {trader1_trader2: correlation_coefficient}
        """
        correlations = {}

        try:
            for i, trader1 in enumerate(traders):
                for trader2 in traders[i+1:]:
                    # Récupérer les trades des 2 traders
                    trades1 = db_manager.get_trader_trades(trader1, limit=100)
                    trades2 = db_manager.get_trader_trades(trader2, limit=100)

                    if not trades1 or not trades2:
                        continue

                    # Calculer corrélation simplifiée (basée sur timing des trades)
                    # Idéalement: corrélation des rendements
                    common_tokens = set([t.get('token_address') for t in trades1]) & \
                                    set([t.get('token_address') for t in trades2])

                    if len(common_tokens) > 0:
                        correlation = len(common_tokens) / max(len(trades1), len(trades2))
                        correlations[f"{trader1}_{trader2}"] = round(correlation, 3)
                    else:
                        correlations[f"{trader1}_{trader2}"] = 0.0

        except Exception as e:
            print(f"⚠️ Erreur calcul corrélations: {e}")

        return correlations

    def assess_diversification(self, active_traders: List[Dict]) -> Dict:
        """
        Évalue la diversification du portefeuille

        Args:
            active_traders: [{name, capital_allocated}]

        Returns:
            {
                'is_diversified': bool,
                'concentration_risk': float (0-1),
                'recommendations': [str]
            }
        """
        if not active_traders:
            return {
                'is_diversified': False,
                'concentration_risk': 0,
                'recommendations': ["Aucun trader actif"]
            }

        total_capital = sum(t.get('capital_allocated', 0) for t in active_traders)
        if total_capital == 0:
            return {
                'is_diversified': False,
                'concentration_risk': 0,
                'recommendations': ["Aucun capital alloué"]
            }

        # Calculer la concentration (Herfindahl index)
        allocations = [t.get('capital_allocated', 0) / total_capital for t in active_traders]
        herfindahl = sum(a ** 2 for a in allocations)

        # 0.33 = parfaitement diversifié (3 traders égaux), 1.0 = tout sur 1 trader
        concentration_risk = herfindahl

        recommendations = []
        if concentration_risk > 0.5:
            recommendations.append("⚠️ Concentration élevée - Diversifier davantage")
        if len(active_traders) < 3:
            recommendations.append("💡 Activer plus de traders pour améliorer la diversification")

        # Vérifier corrélations
        trader_names = [t.get('name') for t in active_traders]
        correlations = self.get_correlation_matrix(trader_names)
        high_corr = [pair for pair, corr in correlations.items() if corr > 0.7]
        if high_corr:
            recommendations.append(f"⚠️ Corrélation élevée détectée: {', '.join(high_corr)}")

        return {
            'is_diversified': concentration_risk < 0.5 and len(active_traders) >= 2,
            'concentration_risk': round(concentration_risk, 3),
            'recommendations': recommendations if recommendations else ["✅ Diversification satisfaisante"]
        }


# Instance globale - Initialisée sans capital (sera mis à jour dynamiquement)
# MODE REAL: Le capital sera fourni par get_wallet_balance_dynamic()
risk_manager = AdvancedRiskManager(total_capital=None)
