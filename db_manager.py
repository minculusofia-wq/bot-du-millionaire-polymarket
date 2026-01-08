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
                highest_price REAL DEFAULT 0,
                use_trailing INTEGER DEFAULT 0,
                exit_tiers TEXT, -- JSON pour paliers de sortie
                capital_recovered INTEGER DEFAULT 0, -- 1 si capital initial retiré
                UNIQUE(token_id, source_wallet)
            )
        ''')

        # Migration: Ajouter colonnes manquantes si elles n'existent pas (pour bases existantes)
        try:
            c.execute('ALTER TABLE bot_positions ADD COLUMN highest_price REAL DEFAULT 0')
        except:
            pass  # Colonne existe déjà
        try:
            c.execute('ALTER TABLE bot_positions ADD COLUMN use_trailing INTEGER DEFAULT 0')
        except:
            pass  # Colonne existe déjà

        # Index pour performances
        c.execute('CREATE INDEX IF NOT EXISTS idx_source_wallet ON bot_positions(source_wallet)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_status ON bot_positions(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_token_source ON bot_positions(token_id, source_wallet)')

        # ============ INSIDER TRACKER TABLES ============

        # Table: insider_alerts - Stocke les alertes de wallets suspects
        c.execute('''
            CREATE TABLE IF NOT EXISTS insider_alerts (
                id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                suspicion_score INTEGER NOT NULL,
                market_question TEXT,
                market_slug TEXT,
                token_id TEXT,
                bet_amount REAL,
                bet_outcome TEXT,
                outcome_odds REAL,
                criteria_matched TEXT,
                wallet_stats TEXT,
                scoring_mode TEXT,
                timestamp TEXT NOT NULL,
                dedup_key TEXT,
                nickname TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_insider_alerts_wallet ON insider_alerts(wallet_address)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_insider_alerts_score ON insider_alerts(suspicion_score DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_insider_alerts_ts ON insider_alerts(timestamp DESC)')

        # Table: saved_insider_wallets - Wallets sauvegardés par l'utilisateur
        c.execute('''
            CREATE TABLE IF NOT EXISTS saved_insider_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                nickname TEXT,
                notes TEXT,
                last_activity TEXT,
                total_alerts INTEGER DEFAULT 0,
                avg_suspicion_score REAL DEFAULT 0,
                pnl REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'SCANNER' -- 'SCANNER' or 'MANUAL'
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_saved_wallets_addr ON saved_insider_wallets(address)')

        # Migration: Ajouter colonnes manquantes
        migrations = [
            ('source', 'TEXT DEFAULT "SCANNER"'),
            ('pnl', 'REAL DEFAULT 0'),
            ('win_rate', 'REAL DEFAULT 0'),
            ('nickname', 'TEXT')
        ]
        for col, col_type in migrations:
            try:
                c.execute(f'ALTER TABLE saved_insider_wallets ADD COLUMN {col} {col_type}')
            except:
                pass  # Colonne existe déjà

        self.conn.commit()
        
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
             unrealized_pnl, status, opened_at, last_updated, highest_price, use_trailing,
             exit_tiers, capital_recovered)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            int(position_data.get('use_trailing', 0)),
            position_data.get('exit_tiers'), # Nouveau: JSON string
            int(position_data.get('capital_recovered', 0)) # Nouveau: 0 ou 1
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

    def update_position_capital_recovered(self, position_id: int, status: int = 1):
        """Marque le capital comme récupéré pour une position"""
        self._execute(
            "UPDATE bot_positions SET capital_recovered = ?, last_updated = ? WHERE id = ?",
            (status, datetime.now().isoformat(), position_id),
            commit=True
        )

    def update_position_exit_tiers(self, position_id: int, tiers_json: str):
        """Met à jour l'état des paliers de sortie (JSON)"""
        self._execute(
            "UPDATE bot_positions SET exit_tiers = ?, last_updated = ? WHERE id = ?",
            (tiers_json, datetime.now().isoformat(), position_id),
            commit=True
        )

    # ============ INSIDER TRACKER METHODS ============

    def save_insider_alert(self, alert_data: Dict) -> str:
        """Sauvegarde une alerte insider dans la base de données

        Args:
            alert_data: Dictionnaire contenant les données de l'alerte

        Returns:
            ID de l'alerte créée
        """
        self._execute('''
            INSERT OR REPLACE INTO insider_alerts
            (id, wallet_address, suspicion_score, market_question, market_slug,
             token_id, bet_amount, bet_outcome, outcome_odds, criteria_matched,
             wallet_stats, scoring_mode, timestamp, dedup_key, nickname)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert_data.get('id'),
            alert_data.get('wallet_address', '').lower(),
            int(alert_data.get('suspicion_score', 0)),
            alert_data.get('market_question'),
            alert_data.get('market_slug'),
            alert_data.get('token_id'),
            float(alert_data.get('bet_amount', 0)),
            alert_data.get('bet_outcome'),
            float(alert_data.get('outcome_odds', 0)),
            json.dumps(alert_data.get('criteria_matched', [])),
            json.dumps(alert_data.get('wallet_stats', {})),
            alert_data.get('scoring_mode', 'balanced'),
            alert_data.get('timestamp', datetime.now().isoformat()),
            alert_data.get('dedup_key'),
            alert_data.get('nickname', '')
        ), commit=True)

        # Mettre à jour les stats du wallet sauvegardé s'il existe
        self._update_saved_wallet_stats(alert_data.get('wallet_address', '').lower())

        return alert_data.get('id')

    def get_insider_alerts(self, limit: int = 100, min_score: int = 0) -> List[Dict]:
        """Récupère les alertes insider, triées par date décroissante

        Args:
            limit: Nombre max d'alertes à récupérer
            min_score: Score minimum pour filtrer

        Returns:
            Liste des alertes
        """
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM insider_alerts
            WHERE suspicion_score >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (min_score, limit))

        rows = c.fetchall()
        alerts = []
        for row in rows:
            alert = dict(row)
            # Parser les champs JSON
            try:
                alert['criteria_matched'] = json.loads(alert.get('criteria_matched', '[]'))
            except:
                alert['criteria_matched'] = []
            try:
                alert['wallet_stats'] = json.loads(alert.get('wallet_stats', '{}'))
            except:
                alert['wallet_stats'] = {}
            alerts.append(alert)
        return alerts

    def save_insider_wallet(self, wallet_data: Dict, source: str = 'SCANNER'):
        """Sauvegarde ou met à jour un wallet suspect"""
        self._execute('''
            INSERT INTO saved_insider_wallets (address, nickname, notes, source, pnl, win_rate)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                nickname = excluded.nickname,
                notes = excluded.notes,
                source = excluded.source,
                pnl = excluded.pnl,
                win_rate = excluded.win_rate
        ''', (
            wallet_data.get('address', '').lower(),
            wallet_data.get('nickname', ''),
            wallet_data.get('notes', ''),
            source,
            wallet_data.get('pnl', 0),
            wallet_data.get('win_rate', 0)
        ), commit=True)
        return wallet_data.get('address')

    def get_saved_insider_wallets(self) -> List[Dict]:
        """Récupère tous les wallets insider sauvegardés"""
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('SELECT * FROM saved_insider_wallets ORDER BY saved_at DESC')
        rows = c.fetchall()
        return [dict(row) for row in rows]

    def delete_insider_wallet(self, address: str):
        """Supprime un wallet sauvegardé"""
        self._execute(
            'DELETE FROM saved_insider_wallets WHERE address = ?',
            (address.lower(),),
            commit=True
        )

    def get_wallet_alerts_history(self, address: str, limit: int = 50) -> List[Dict]:
        """Récupère l'historique des alertes pour un wallet spécifique

        Args:
            address: Adresse du wallet
            limit: Nombre max d'alertes

        Returns:
            Liste des alertes pour ce wallet
        """
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM insider_alerts
            WHERE wallet_address = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (address.lower(), limit))

        rows = c.fetchall()
        alerts = []
        for row in rows:
            alert = dict(row)
            try:
                alert['criteria_matched'] = json.loads(alert.get('criteria_matched', '[]'))
            except:
                alert['criteria_matched'] = []
            try:
                alert['wallet_stats'] = json.loads(alert.get('wallet_stats', '{}'))
            except:
                alert['wallet_stats'] = {}
            alerts.append(alert)
        return alerts

    def _update_saved_wallet_stats(self, address: str):
        """Met à jour les statistiques d'un wallet sauvegardé (appelé après nouvelle alerte)"""
        if not address:
            return

        # Calculer les stats à partir des alertes
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('''
            SELECT COUNT(*) as total, AVG(suspicion_score) as avg_score, MAX(timestamp) as last_activity
            FROM insider_alerts
            WHERE wallet_address = ?
        ''', (address.lower(),))

        row = c.fetchone()
        if row and row['total'] > 0:
            self._execute('''
                UPDATE saved_insider_wallets
                SET total_alerts = ?, avg_suspicion_score = ?, last_activity = ?
                WHERE address = ?
            ''', (
                row['total'],
                row['avg_score'] or 0,
                row['last_activity'],
                address.lower()
            ), commit=True)

    def cleanup_old_insider_alerts(self, days: int = 30):
        """Nettoie les alertes anciennes pour éviter une base trop volumineuse

        Args:
            days: Nombre de jours à conserver
        """
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        self._execute(
            'DELETE FROM insider_alerts WHERE timestamp < ?',
            (cutoff,),
            commit=True
        )
        print(f"🧹 Alertes insider > {days} jours supprimées")

db_manager = DBManager()
