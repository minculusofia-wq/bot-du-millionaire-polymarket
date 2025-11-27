# -*- coding: utf-8 -*-
"""
Database Manager - SQLite pour persistance long-terme
Gère le stockage des données de trading, portfolios, historiques
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional

class DBManager:
    """Gère la persistance SQLite"""

    def __init__(self, db_path: str = 'bot_data.db'):
        self.db_path = db_path
        # ✅ Phase A2: Connection persistante au lieu de nouvelles connexions à chaque fois
        self.conn = None
        self.pending_commits = []  # Pour batch commits
        self.max_batch_size = 10  # Commit tous les 10 ops
        self._connect()
        self.init_db()

    def _connect(self):
        """✅ Phase A2: Établit la connexion persistante"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
            # Optimisations SQLite
            self.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging (plus rapide)
            self.conn.execute("PRAGMA synchronous=NORMAL")  # Sync moins strict mais sûr
            print("✅ Connection SQLite persistante établie")
        except Exception as e:
            print(f"❌ Erreur connexion SQLite: {e}")
            self.conn = None

    def _reconnect(self):
        """✅ Phase A2: Reconnexion automatique en cas de déconnexion"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        self._connect()

    def _execute(self, query: str, params: tuple = (), commit: bool = True):
        """
        ✅ Phase A2: Exécute une requête avec reconnexion automatique

        Args:
            query: Requête SQL
            params: Paramètres de la requête
            commit: Si True, commit immédiatement. Sinon, batching.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not self.conn:
                    self._reconnect()

                cursor = self.conn.cursor()
                cursor.execute(query, params)

                if commit:
                    self.conn.commit()

                return cursor
            except sqlite3.OperationalError as e:
                print(f"⚠️ SQLite OperationalError (tentative {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    self._reconnect()
                else:
                    raise
            except Exception as e:
                print(f"❌ Erreur SQLite: {e}")
                raise

        return None

    def _batch_commit(self):
        """✅ Phase A2: Commit par batch pour optimiser les performances"""
        if self.conn:
            try:
                self.conn.commit()
                self.pending_commits.clear()
            except Exception as e:
                print(f"❌ Erreur batch commit: {e}")

    def init_db(self):
        """Initialise les tables"""
        # ✅ Phase A2: Utiliser la connexion persistante
        if not self.conn:
            self._connect()

        c = self.conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS wallet_history (
                id INTEGER PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sol_balance REAL,
                usd_value REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Index pour optimiser les recherches par wallet
        c.execute('CREATE INDEX IF NOT EXISTS idx_wallet_history_address ON wallet_history(wallet_address, timestamp DESC)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS trader_portfolio (
                id INTEGER PRIMARY KEY,
                trader_address TEXT UNIQUE NOT NULL,
                trader_name TEXT,
                initial_value REAL,
                current_value REAL,
                pnl REAL,
                pnl_percent REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Index pour optimiser les recherches par trader
        c.execute('CREATE INDEX IF NOT EXISTS idx_trader_portfolio_address ON trader_portfolio(trader_address)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY,
                trader_address TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                portfolio_value REAL,
                pnl REAL,
                pnl_percent REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(trader_address) REFERENCES trader_portfolio(trader_address)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS simulated_trades (
                id INTEGER PRIMARY KEY,
                trade_id TEXT UNIQUE NOT NULL,
                trader_address TEXT NOT NULL,
                trader_name TEXT,
                signature TEXT,
                timestamp TEXT,
                swap_type TEXT,
                input_mint TEXT,
                input_amount REAL,
                output_mint TEXT,
                output_amount REAL,
                entry_price_usd REAL,
                exit_price_usd REAL,
                status TEXT,
                pnl REAL,
                pnl_percent REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Indexes pour optimiser les recherches
        c.execute('CREATE INDEX IF NOT EXISTS idx_trades_trader ON simulated_trades(trader_address, timestamp DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON simulated_trades(status, timestamp DESC)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS backtesting_results (
                id INTEGER PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                trader_address TEXT NOT NULL,
                tp_percent REAL,
                sl_percent REAL,
                win_rate REAL,
                total_trades INTEGER,
                total_pnl REAL,
                total_pnl_percent REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS benchmark_data (
                id INTEGER PRIMARY KEY,
                bot_pnl REAL,
                bot_win_rate REAL,
                trader_address TEXT,
                trader_name TEXT,
                trader_pnl REAL,
                trader_win_rate REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()
        
    def save_wallet_history(self, wallet_address: str, sol_balance: float, usd_value: float, timestamp: str = None):
        """Sauvegarde l'historique du wallet"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # ✅ Phase A2: Utiliser connexion persistante + batch commit
        self._execute('''
            INSERT INTO wallet_history (wallet_address, timestamp, sol_balance, usd_value)
            VALUES (?, ?, ?, ?)
        ''', (wallet_address, timestamp, sol_balance, usd_value), commit=False)

        self.pending_commits.append('save_wallet_history')
        if len(self.pending_commits) >= self.max_batch_size:
            self._batch_commit()
        
    def get_wallet_history(self, wallet_address: str, days: int = 30) -> List[Dict]:
        """Récupère l'historique du wallet"""
        # ✅ Phase A2: Utiliser connexion persistante
        c = self.conn.cursor()
        c.execute('''
            SELECT timestamp, sol_balance, usd_value FROM wallet_history
            WHERE wallet_address = ? AND created_at > datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC
        ''', (wallet_address, days))
        rows = c.fetchall()

        return [{'timestamp': r[0], 'sol_balance': r[1], 'usd_value': r[2]} for r in rows]
        
    def update_trader_portfolio(self, trader_address: str, trader_name: str, initial_value: float,
                               current_value: float, pnl: float, pnl_percent: float):
        """Met à jour le portfolio d'un trader"""
        # ✅ Phase A2: Utiliser connexion persistante + batch commit
        self._execute('''
            INSERT OR REPLACE INTO trader_portfolio
            (trader_address, trader_name, initial_value, current_value, pnl, pnl_percent, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (trader_address, trader_name, initial_value, current_value, pnl, pnl_percent, datetime.now().isoformat()), commit=False)

        self.pending_commits.append('update_trader_portfolio')
        if len(self.pending_commits) >= self.max_batch_size:
            self._batch_commit()
        
    def get_trader_portfolio(self, trader_address: str) -> Optional[Dict]:
        """Récupère le portfolio d'un trader"""
        # ✅ Phase A2: Connexion persistante
        c = self.conn.cursor()
        c.execute('SELECT * FROM trader_portfolio WHERE trader_address = ?', (trader_address,))
        row = c.fetchone()

        if row:
            return {
                'id': row[0],
                'trader_address': row[1],
                'trader_name': row[2],
                'initial_value': row[3],
                'current_value': row[4],
                'pnl': row[5],
                'pnl_percent': row[6]
            }
        return None

    def save_portfolio_history(self, trader_address: str, portfolio_value: float,
                               pnl: float, pnl_percent: float, timestamp: str = None):
        """Sauvegarde l'historique du portfolio"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # ✅ Phase A2: Batch commit
        self._execute('''
            INSERT INTO portfolio_history (trader_address, timestamp, portfolio_value, pnl, pnl_percent)
            VALUES (?, ?, ?, ?, ?)
        ''', (trader_address, timestamp, portfolio_value, pnl, pnl_percent), commit=False)

        self.pending_commits.append('save_portfolio_history')
        if len(self.pending_commits) >= self.max_batch_size:
            self._batch_commit()

    def get_portfolio_history(self, trader_address: str, days: int = 30) -> List[Dict]:
        """Récupère l'historique du portfolio"""
        # ✅ Phase A2: Connexion persistante
        c = self.conn.cursor()
        c.execute('''
            SELECT timestamp, portfolio_value, pnl, pnl_percent FROM portfolio_history
            WHERE trader_address = ? AND created_at > datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC
        ''', (trader_address, days))
        rows = c.fetchall()

        return [{'timestamp': r[0], 'portfolio_value': r[1], 'pnl': r[2], 'pnl_percent': r[3]} for r in rows]

    def save_simulated_trade(self, trade_data: Dict):
        """Sauvegarde un trade simulé"""
        # ✅ Phase A2: Batch commit
        self._execute('''
            INSERT OR REPLACE INTO simulated_trades
            (trade_id, trader_address, trader_name, signature, timestamp, swap_type,
             input_mint, input_amount, output_mint, output_amount, entry_price_usd,
             exit_price_usd, status, pnl, pnl_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('trade_id', ''),
            trade_data.get('trader_address', ''),
            trade_data.get('trader_name', ''),
            trade_data.get('signature', ''),
            trade_data.get('timestamp', datetime.now().isoformat()),
            trade_data.get('swap_type', 'SWAP'),
            trade_data.get('input_mint', ''),
            trade_data.get('input_amount', 0),
            trade_data.get('output_mint', ''),
            trade_data.get('output_amount', 0),
            trade_data.get('entry_price_usd', 0),
            trade_data.get('exit_price_usd', 0),
            trade_data.get('status', 'OPEN'),
            trade_data.get('pnl', 0),
            trade_data.get('pnl_percent', 0)
        ), commit=False)

        self.pending_commits.append('save_simulated_trade')
        if len(self.pending_commits) >= self.max_batch_size:
            self._batch_commit()

    def get_simulated_trades(self, trader_address: str, limit: int = 50) -> List[Dict]:
        """Récupère les trades simulés d'un trader"""
        # ✅ Phase A2: Connexion persistante
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM simulated_trades
            WHERE trader_address = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (trader_address, limit))
        rows = c.fetchall()

        return [dict(row) for row in rows]

    def save_backtest_result(self, backtest_data: Dict):
        """Sauvegarde les résultats du backtest"""
        # ✅ Phase A2: Batch commit
        self._execute('''
            INSERT INTO backtesting_results
            (strategy_id, trader_address, tp_percent, sl_percent, win_rate, total_trades, total_pnl, total_pnl_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            backtest_data.get('strategy_id', ''),
            backtest_data.get('trader_address', ''),
            backtest_data.get('tp_percent', 0),
            backtest_data.get('sl_percent', 0),
            backtest_data.get('win_rate', 0),
            backtest_data.get('total_trades', 0),
            backtest_data.get('total_pnl', 0),
            backtest_data.get('total_pnl_percent', 0)
        ), commit=False)

        self.pending_commits.append('save_backtest_result')
        if len(self.pending_commits) >= self.max_batch_size:
            self._batch_commit()

    def get_backtest_results(self, trader_address: str, limit: int = 10) -> List[Dict]:
        """Récupère les résultats du backtest"""
        # ✅ Phase A2: Connexion persistante
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM backtesting_results
            WHERE trader_address = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (trader_address, limit))
        rows = c.fetchall()

        return [dict(row) for row in rows]

    def save_benchmark(self, benchmark_data: Dict):
        """Sauvegarde les données de benchmark"""
        # ✅ Phase A2: Batch commit
        self._execute('''
            INSERT INTO benchmark_data
            (bot_pnl, bot_win_rate, trader_address, trader_name, trader_pnl, trader_win_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            benchmark_data.get('bot_pnl', 0),
            benchmark_data.get('bot_win_rate', 0),
            benchmark_data.get('trader_address', ''),
            benchmark_data.get('trader_name', ''),
            benchmark_data.get('trader_pnl', 0),
            benchmark_data.get('trader_win_rate', 0)
        ), commit=False)

        self.pending_commits.append('save_benchmark')
        if len(self.pending_commits) >= self.max_batch_size:
            self._batch_commit()

    def get_benchmarks(self, limit: int = 50) -> List[Dict]:
        """Récupère les données de benchmark"""
        # ✅ Phase A2: Connexion persistante
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM benchmark_data
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        rows = c.fetchall()

        return [dict(row) for row in rows]

    def get_closed_trades(self, trader_name: str = None) -> List[Dict]:
        """
        Récupère les trades fermés (avec PnL calculé)

        Args:
            trader_name: Nom du trader (optionnel, None = tous les traders)

        Returns:
            Liste des trades fermés avec leurs données
        """
        # ✅ Phase A2: Connexion persistante
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()

        if trader_name:
            c.execute('''
                SELECT * FROM simulated_trades
                WHERE (status = 'CLOSED' OR exit_price_usd > 0)
                  AND trader_name = ?
                ORDER BY timestamp ASC
            ''', (trader_name,))
        else:
            c.execute('''
                SELECT * FROM simulated_trades
                WHERE (status = 'CLOSED' OR exit_price_usd > 0)
                ORDER BY timestamp ASC
            ''')

        rows = c.fetchall()

        trades = []
        for row in rows:
            trade = dict(row)
            # Ajouter opened_at et closed_at pour compatibilité
            trade['opened_at'] = trade.get('timestamp', datetime.now().isoformat())
            trade['closed_at'] = trade.get('timestamp', datetime.now().isoformat())
            trades.append(trade)

        return trades

db_manager = DBManager()
