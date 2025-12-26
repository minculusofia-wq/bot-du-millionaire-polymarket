# -*- coding: utf-8 -*-
"""
Database Manager - SQLite pour persistance long-terme
Gère le stockage des données de trading, portfolios, historiques
"""
import sqlite3
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional

class DBManager:
    """Gère la persistance SQLite"""

    def __init__(self, db_path: str = 'bot_data.db'):
        self.db_path = db_path
        # ✅ Phase A2: Connection persistante au lieu de nouvelles connexions à chaque fois
        self.conn = None
        self.lock = threading.Lock() # 🔒 Sécurité thread-safety
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
        
        # 🔒 Acquérir le verrou pour éviter accès concurrents
        with self.lock:
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
                    # Si locked, on peut retenter. Si le lock python est acquis, c'est peut-être un autre processus ?
                    # Ou alors la connexion est mauvaise.
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

        # ✅ NEW: Table pour les trades réels Polymarket
        c.execute('''
            CREATE TABLE IF NOT EXISTS polymarket_trades (
                order_id TEXT PRIMARY KEY,
                timestamp TEXT,
                market_slug TEXT,
                token_id TEXT,
                side TEXT,
                price REAL,
                size REAL,
                value_usd REAL,
                status TEXT,
                pnl REAL DEFAULT 0,
                signal_type TEXT,
                tx_hash TEXT
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_poly_trades_ts ON polymarket_trades(timestamp DESC)')

        # ✅ NEW: Table pour les positions actives du bot (Version 2.0 - Positions séparées par trader)
        c.execute('''
            CREATE TABLE IF NOT EXISTS bot_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id TEXT NOT NULL,
                source_wallet TEXT NOT NULL,
                market_slug TEXT NOT NULL,
                outcome TEXT,
                side TEXT,
                shares REAL NOT NULL,
                size REAL NOT NULL,
                avg_price REAL NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL,
                value_usd REAL,
                sl_percent REAL,
                tp_percent REAL,
                unrealized_pnl REAL DEFAULT 0,
                realized_pnl REAL DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                last_updated TEXT NOT NULL,
                UNIQUE(token_id, source_wallet)
            )
        ''')
        
        # Index pour performances
        c.execute('CREATE INDEX IF NOT EXISTS idx_source_wallet ON bot_positions(source_wallet)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_status ON bot_positions(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_token_source ON bot_positions(token_id, source_wallet)')


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

    def save_polymarket_trade(self, trade_data: Dict):
        """Sauvegarde un trade Polymarket"""
        self._execute('''
            INSERT OR REPLACE INTO polymarket_trades
            (order_id, timestamp, market_slug, token_id, side, price, size, value_usd, status, pnl, signal_type, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('order_id', ''),
            trade_data.get('timestamp', datetime.now().isoformat()),
            trade_data.get('market_slug', ''),
            trade_data.get('token_id', ''),
            trade_data.get('side', ''),
            float(trade_data.get('price', 0)),
            float(trade_data.get('size', 0)),
            float(trade_data.get('value_usd', 0)),
            trade_data.get('status', 'EXECUTED'),
            float(trade_data.get('pnl', 0)),
            trade_data.get('signal_type', ''),
            trade_data.get('tx_hash', '')
        ), commit=True)

    def get_polymarket_trades(self, limit: int = 50) -> List[Dict]:
        """Récupère l'historique des trades Polymarket"""
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM polymarket_trades
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = c.fetchall()
        return [dict(row) for row in rows]

    def get_daily_pnl(self, days: int = 30) -> List[Dict]:
        """Aggrège le PnL journalier réalisé des 30 derniers jours"""
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT date(timestamp) as day, 
                   SUM(pnl) as daily_pnl,
                   COUNT(*) as trades_count,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades
            FROM polymarket_trades
            WHERE status IN ('EXECUTED', 'CLOSED') 
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
        ''', (days,))
        
        rows = c.fetchall()
        return [dict(row) for row in rows]

    def get_trader_performance(self, trader_address: str) -> Dict:
        """
        Calcule les performances agrégées d'un trader copié.
        Basé sur les positions fermées (CLOSED_MANUAL, CLOSED_TP, CLOSED_SL)
        """
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        
        # Récupérer toutes les positions fermées pour ce trader
        c.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losses,
                SUM(realized_pnl) as total_pnl,
                SUM(value_usd) as total_invested,
                SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END) as gross_profit,
                SUM(CASE WHEN realized_pnl < 0 THEN ABS(realized_pnl) ELSE 0 END) as gross_loss
            FROM bot_positions
            WHERE source_wallet = ? 
            AND status LIKE 'CLOSED%'
        ''', (trader_address,))
        
        row = c.fetchone()
        
        stats = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'total_pnl': 0.0,
            'total_invested': 0.0
        }
        
        if row and row['total_trades'] > 0:
            stats['total_trades'] = row['total_trades']
            stats['wins'] = row['wins']
            stats['losses'] = row['losses']
            stats['total_pnl'] = row['total_pnl'] or 0.0
            stats['total_invested'] = row['total_invested'] or 0.0
            
            # Win Rate
            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total_trades']) * 100
                
            # Profit Factor
            gross_loss = row['gross_loss'] or 0.0
            gross_profit = row['gross_profit'] or 0.0
            if gross_loss > 0:
                stats['profit_factor'] = gross_profit / gross_loss
            elif gross_profit > 0:
                stats['profit_factor'] = 99.0 # Infini (que des gains)
            else:
                stats['profit_factor'] = 0.0

        return stats

    def add_position(self, position_data: Dict) -> int:
        """Ajoute une nouvelle position (Version 2.0)
        
        Args:
            position_data: Dictionnaire avec les données de la position
            
        Returns:
            ID de la position créée
        """
        cursor = self._execute('''
            INSERT INTO bot_positions
            (token_id, source_wallet, market_slug, outcome, side, shares, size, 
             avg_price, entry_price, current_price, value_usd, sl_percent, tp_percent,
             unrealized_pnl, status, opened_at, last_updated, highest_price, use_trailing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position_data.get('token_id'),
            position_data.get('source_wallet'),
            position_data.get('market_slug'),
            position_data.get('outcome'),
            position_data.get('side', 'BUY'),
            float(position_data.get('shares', 0)),
            float(position_data.get('size', 0)),
            float(position_data.get('avg_price', 0)),
            float(position_data.get('entry_price', 0)),
            float(position_data.get('current_price', 0)),
            float(position_data.get('value_usd', 0)),
            position_data.get('sl_percent'),
            position_data.get('tp_percent'),
            float(position_data.get('unrealized_pnl', 0)),
            position_data.get('status', 'OPEN'),
            position_data.get('opened_at', datetime.now().isoformat()),
            datetime.now().isoformat(),
            float(position_data.get('entry_price', 0)), # Initial highest_price = entry_price
            int(position_data.get('use_trailing', 0))
        ), commit=True)
        
        return cursor.lastrowid
    
    def update_bot_position(self, position_data: Dict):
        """Met à jour une position active du bot (rétrocompatibilité)
        
        Note: Cette méthode est conservée pour rétrocompatibilité.
        Pour les nouvelles fonctionnalités, utiliser add_position() ou update_position_by_id()
        """
        # Convertir vers le nouveau format si nécessaire
        if 'source_wallet' not in position_data:
            position_data['source_wallet'] = 'LEGACY'
        
        # Si size ~ 0, on supprime la position
        if float(position_data.get('size', 0)) < 0.0001:
            self._execute(
                'DELETE FROM bot_positions WHERE token_id = ? AND source_wallet = ?',
                (position_data.get('token_id'), position_data.get('source_wallet'))
            )
        else:
            # Essayer d'insérer ou mettre à jour
            self._execute('''
                INSERT INTO bot_positions
                (token_id, source_wallet, market_slug, outcome, side, shares, size,
                 avg_price, entry_price, current_price, value_usd, unrealized_pnl,
                 status, opened_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token_id, source_wallet) DO UPDATE SET
                    shares = excluded.shares,
                    size = excluded.size,
                    avg_price = excluded.avg_price,
                    current_price = excluded.current_price,
                    value_usd = excluded.value_usd,
                    unrealized_pnl = excluded.unrealized_pnl,
                    last_updated = excluded.last_updated
            ''', (
                position_data.get('token_id'),
                position_data.get('source_wallet', 'LEGACY'),
                position_data.get('market_slug'),
                position_data.get('outcome'),
                position_data.get('side', 'BUY'),
                float(position_data.get('size', 0)),
                float(position_data.get('size', 0)),
                float(position_data.get('avg_entry_price', 0)),
                float(position_data.get('avg_entry_price', 0)),
                float(position_data.get('current_price', 0)),
                float(position_data.get('value_usd', 0)),
                float(position_data.get('pnl', 0)),
                'OPEN',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

    def get_bot_positions(self, status: str = 'OPEN') -> List[Dict]:
        """Récupère toutes les positions actives (Version 2.0)
        
        Args:
            status: Statut des positions ('OPEN', 'CLOSED_SL', 'CLOSED_TP', 'CLOSED_MANUAL', ou None pour toutes)
        """
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        
        if status:
            c.execute('SELECT * FROM bot_positions WHERE status = ? ORDER BY opened_at DESC', (status,))
        else:
            c.execute('SELECT * FROM bot_positions ORDER BY opened_at DESC')
        
        rows = c.fetchall()
        
        # Convertir en liste avec structure compatible frontend
        positions = []
        for row in rows:
            pos = dict(row)
            # Re-mapping pour compatibilité frontend bot.py
            positions.append({
                'id': pos['id'],  # ID unique de la position
                'position_id': pos['id'],
                'token_id': pos['token_id'],
                'source_wallet': pos['source_wallet'],
                'asset_id': pos['token_id'],
                'market': pos['market_slug'] or 'Unknown Market',
                'market_slug': pos['market_slug'],
                'outcome': pos.get('outcome'),
                'side': pos['side'],
                'amount': pos['value_usd'],
                'shares': pos['shares'],
                'size': pos['size'],
                'entry_price': pos['entry_price'],
                'avg_price': pos['avg_price'],
                'current_price': pos['current_price'],
                'pnl': pos['unrealized_pnl'],
                'unrealized_pnl': pos['unrealized_pnl'],
                'realized_pnl': pos.get('realized_pnl', 0),
                'sl_percent': pos.get('sl_percent'),
                'tp_percent': pos.get('tp_percent'),
                'status': pos['status'],
                'opened_at': pos['opened_at'],
                'closed_at': pos.get('closed_at'),
                'last_updated': pos['last_updated']
            })
        return positions
    
    def get_position_by_id(self, position_id: int) -> Optional[Dict]:
        """Récupère une position par son ID"""
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('SELECT * FROM bot_positions WHERE id = ?', (position_id,))
        row = c.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_positions_by_wallet(self, source_wallet: str, status: str = 'OPEN') -> List[Dict]:
        """Récupère toutes les positions d'un trader spécifique
        
        Args:
            source_wallet: Adresse du trader copié
            status: Statut des positions (None pour toutes)
        """
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        
        if status:
            c.execute(
                'SELECT * FROM bot_positions WHERE source_wallet = ? AND status = ? ORDER BY opened_at DESC',
                (source_wallet, status)
            )
        else:
            c.execute(
                'SELECT * FROM bot_positions WHERE source_wallet = ? ORDER BY opened_at DESC',
                (source_wallet,)
            )
        
        rows = c.fetchall()
        return [dict(row) for row in rows]
    
    def update_position_price(self, position_id: int, current_price: float, unrealized_pnl: float):
        """Met à jour le prix et PnL d'une position"""
        self._execute('''
            UPDATE bot_positions
            SET current_price = ?, unrealized_pnl = ?, last_updated = ?
            WHERE id = ?
        ''', (current_price, unrealized_pnl, datetime.now().isoformat(), position_id), commit=True)
    
    def update_position_highest_price(self, position_id: int, highest_price: float):
        """Met à jour le highest_price d'une position"""
        self._execute('''
            UPDATE bot_positions
            SET highest_price = ?, last_updated = ?
            WHERE id = ?
        ''', (highest_price, datetime.now().isoformat(), position_id))

    def update_position_shares(self, position_id: int, new_shares: float):
        """Met à jour le nombre de shares d'une position (fermeture partielle)"""
        self._execute('''
            UPDATE bot_positions
            SET shares = ?, size = ?, last_updated = ?
            WHERE id = ?
        ''', (new_shares, new_shares, datetime.now().isoformat(), position_id), commit=True)
    
    def close_position(self, position_id: int, realized_pnl: float, status: str = 'CLOSED_MANUAL'):
        """Ferme une position
        
        Args:
            position_id: ID de la position
            realized_pnl: PnL réalisé
            status: 'CLOSED_MANUAL', 'CLOSED_SL', 'CLOSED_TP'
        """
        self._execute('''
            UPDATE bot_positions
            SET status = ?, realized_pnl = ?, closed_at = ?, last_updated = ?
            WHERE id = ?
        ''', (status, realized_pnl, datetime.now().isoformat(), datetime.now().isoformat(), position_id), commit=True)
    
    def get_open_positions(self) -> List[Dict]:
        """Récupère uniquement les positions ouvertes"""
        return self.get_bot_positions(status='OPEN')

db_manager = DBManager()
