# -*- coding: utf-8 -*-
"""
Script de migration de la table bot_positions
Migre de l'ancien schéma vers le nouveau schéma avec source_wallet, sl_percent, tp_percent
"""
import sqlite3
from datetime import datetime

def migrate_bot_positions(db_path='bot_data.db'):
    """Migre la table bot_positions vers le nouveau schéma"""
    
    print("🔄 Début de la migration de la table bot_positions...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Vérifier si la table existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_positions'")
        if not cursor.fetchone():
            print("✅ Table bot_positions n'existe pas, rien à migrer")
            return
        
        # 2. Vérifier si la migration est nécessaire
        cursor.execute("PRAGMA table_info(bot_positions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'source_wallet' in columns:
            print("✅ Table bot_positions déjà migrée")
            return
        
        print("📋 Ancien schéma détecté, migration nécessaire...")
        
        # 3. Sauvegarder les données existantes
        cursor.execute("SELECT * FROM bot_positions")
        old_data = cursor.fetchall()
        
        print(f"💾 {len(old_data)} positions à migrer")
        
        # 4. Renommer l'ancienne table
        cursor.execute("ALTER TABLE bot_positions RENAME TO bot_positions_old")
        print("✅ Ancienne table renommée")
        
        # 5. Créer la nouvelle table avec le nouveau schéma
        cursor.execute('''
            CREATE TABLE bot_positions (
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
        print("✅ Nouvelle table créée")
        
        # 6. Créer les index
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_wallet ON bot_positions(source_wallet)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON bot_positions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_token_source ON bot_positions(token_id, source_wallet)')
        print("✅ Index créés")
        
        # 7. Migrer les données
        # Ancien schéma: token_id, market_slug, side, size, avg_entry_price, current_price, value_usd, pnl, updated_at
        for row in old_data:
            try:
                token_id = row[0]
                market_slug = row[1] if len(row) > 1 else 'unknown'
                side = row[2] if len(row) > 2 else 'BUY'
                size = row[3] if len(row) > 3 else 0
                avg_entry_price = row[4] if len(row) > 4 else 0
                current_price = row[5] if len(row) > 5 else avg_entry_price
                value_usd = row[6] if len(row) > 6 else 0
                pnl = row[7] if len(row) > 7 else 0
                updated_at = row[8] if len(row) > 8 else datetime.now().isoformat()
                
                # Insérer dans la nouvelle table avec source_wallet = 'LEGACY'
                cursor.execute('''
                    INSERT INTO bot_positions
                    (token_id, source_wallet, market_slug, outcome, side, shares, size,
                     avg_price, entry_price, current_price, value_usd, sl_percent, tp_percent,
                     unrealized_pnl, status, opened_at, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    token_id,
                    'LEGACY',  # Source wallet par défaut pour les anciennes positions
                    market_slug,
                    None,  # outcome
                    side,
                    size,
                    size,
                    avg_entry_price,
                    avg_entry_price,
                    current_price,
                    value_usd,
                    None,  # sl_percent
                    None,  # tp_percent
                    pnl,
                    'OPEN',
                    updated_at,
                    updated_at
                ))
            except Exception as e:
                print(f"⚠️ Erreur migration position {token_id}: {e}")
        
        print(f"✅ {len(old_data)} positions migrées")
        
        # 8. Supprimer l'ancienne table
        cursor.execute("DROP TABLE bot_positions_old")
        print("✅ Ancienne table supprimée")
        
        # 9. Commit
        conn.commit()
        print("✅ Migration terminée avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_bot_positions()
