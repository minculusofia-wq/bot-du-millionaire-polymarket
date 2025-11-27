# -*- coding: utf-8 -*-
"""
Analytics Export - Export des données et rapports
✨ Phase 9 Optimization: Export CSV/JSON pour analyse externe

Features:
- Export CSV des trades
- Export JSON des positions
- Génération de rapports de synthèse
"""
import json
import csv
from typing import List, Dict
from datetime import datetime


class AnalyticsExporter:
    """Export des données d'analytics"""

    def export_trades_csv(self, trades: List[Dict], filename: str = "trades_export.csv"):
        """
        Exporte les trades en CSV

        Args:
            trades: Liste des trades
            filename: Nom du fichier de sortie
        """
        if not trades:
            print("⚠️ Aucun trade à exporter")
            return

        # Définir les colonnes
        fieldnames = ['timestamp', 'trader', 'type', 'token', 'amount', 'price', 'pnl', 'pnl_percent']

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for trade in trades:
                    writer.writerow({
                        'timestamp': trade.get('timestamp', ''),
                        'trader': trade.get('trader_name', ''),
                        'type': trade.get('type', ''),
                        'token': trade.get('token_address', '')[:8],
                        'amount': trade.get('amount', 0),
                        'price': trade.get('price', 0),
                        'pnl': trade.get('pnl', 0),
                        'pnl_percent': trade.get('pnl_percent', 0)
                    })

            print(f"✅ Trades exportés vers {filename}")
        except Exception as e:
            print(f"❌ Erreur export CSV: {e}")

    def export_positions_json(self, positions: List[Dict], filename: str = "positions_export.json"):
        """
        Exporte les positions en JSON

        Args:
            positions: Liste des positions
            filename: Nom du fichier de sortie
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2, ensure_ascii=False)

            print(f"✅ Positions exportées vers {filename}")
        except Exception as e:
            print(f"❌ Erreur export JSON: {e}")

    def generate_summary_report(self, stats: Dict) -> str:
        """
        Génère un rapport de synthèse

        Args:
            stats: Statistiques globales

        Returns:
            Rapport formaté en texte
        """
        report = f"""
╔══════════════════════════════════════════════════════════╗
║          BOT DU MILLIONNAIRE - RAPPORT DE SYNTHÈSE        ║
╚══════════════════════════════════════════════════════════╝

📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 PERFORMANCE GLOBALE
──────────────────────────────────────────────────────────
  • PnL Total: ${stats.get('total_pnl', 0):,.2f}
  • PnL %: {stats.get('pnl_percent', 0):.2f}%
  • Win Rate: {stats.get('win_rate', 0):.2f}%

📈 STATISTIQUES DE TRADING
──────────────────────────────────────────────────────────
  • Trades totaux: {stats.get('total_trades', 0)}
  • Trades gagnants: {stats.get('winning_trades', 0)}
  • Trades perdants: {stats.get('losing_trades', 0)}
  • Trades actifs: {stats.get('active_positions', 0)}

👥 TRADERS
──────────────────────────────────────────────────────────
  • Traders actifs: {stats.get('active_traders', 0)}
  • Meilleur trader: {stats.get('best_trader', 'N/A')}

⚡ OPTIMISATIONS PHASE 9
──────────────────────────────────────────────────────────
  • Latence moyenne: {stats.get('avg_latency', 0):.0f}ms
  • Cache hit rate: {stats.get('cache_hit_rate', 0):.1f}%
  • RPC success rate: {stats.get('rpc_success', 0):.1f}%
  • Circuit breaker: {'🔴 OUVERT' if stats.get('circuit_open') else '🟢 FERMÉ'}

╚══════════════════════════════════════════════════════════╝
        """
        return report


# Instance globale
global_exporter = AnalyticsExporter()
