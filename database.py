import sqlite3
import json
from datetime import datetime

DB_PATH = 'data/game.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS game_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT,
            final_safety INTEGER,
            final_willingness INTEGER,
            rounds_played INTEGER,
            result TEXT,
            tags TEXT,
            history TEXT,
            aar_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_game(player_name, final_safety, final_willingness, rounds_played, result, tags, history, aar_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO game_sessions (player_name, final_safety, final_willingness, rounds_played, result, tags, history, aar_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (player_name, final_safety, final_willingness, rounds_played, result, 
          json.dumps(tags, ensure_ascii=False), 
          json.dumps(history, ensure_ascii=False), 
          aar_text))
    conn.commit()
    game_id = c.lastrowid
    conn.close()
    return game_id

def get_all_games():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM game_sessions ORDER BY created_at DESC')
    games = [dict(row) for row in c.fetchall()]
    conn.close()
    return games

def get_game_by_id(game_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM game_sessions WHERE id = ?', (game_id,))
    game = c.fetchone()
    conn.close()
    return dict(game) if game else None
