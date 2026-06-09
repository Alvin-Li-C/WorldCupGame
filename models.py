import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'draft.db')


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
#   conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
        DROP TABLE IF EXISTS selections;
        DROP TABLE IF EXISTS preselect_queues;
        DROP TABLE IF EXISTS game_state;
        DROP TABLE IF EXISTS players;
        DROP TABLE IF EXISTS teams;
        DROP TABLE IF EXISTS participants;

        CREATE TABLE teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            group_name TEXT NOT NULL,
            flag_emoji TEXT NOT NULL
        );

        CREATE TABLE players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_cn TEXT NOT NULL DEFAULT '',
            jersey_number INTEGER NOT NULL,
            team_id INTEGER NOT NULL REFERENCES teams(id),
            position TEXT NOT NULL
        );

        CREATE TABLE participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            draft_order INTEGER NOT NULL UNIQUE
        );

        CREATE TABLE selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_number INTEGER NOT NULL,
            pick_number INTEGER NOT NULL,
            participant_id INTEGER NOT NULL REFERENCES participants(id),
            player_id INTEGER NOT NULL UNIQUE REFERENCES players(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE preselect_queues (
            participant_name TEXT PRIMARY KEY,
            pin_hash TEXT NOT NULL,
            queue_data TEXT NOT NULL DEFAULT '[]',
            auto_draft INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE game_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_key TEXT NOT NULL UNIQUE,
            state_value TEXT NOT NULL
        );
    ''')

    # Initialize game state
    cur.executemany(
        'INSERT OR IGNORE INTO game_state (state_key, state_value) VALUES (?, ?)',
        [
            ('current_round', '1'),
            ('current_pick', '1'),
            ('status', 'waiting'),
            ('last_participant_id', '0'),
        ]
    )
    conn.commit()
    conn.close()


def migrate_briefing_tables():
    """Additive migration for briefing; does not touch draft tables."""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS team_ownership (
            team_id INTEGER PRIMARY KEY REFERENCES teams(id),
            participant_id INTEGER NOT NULL REFERENCES participants(id)
        );

        CREATE TABLE IF NOT EXISTS match_results (
            fixture_id INTEGER PRIMARY KEY,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT NOT NULL DEFAULT 'scheduled',
            played_date TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS match_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fixture_id INTEGER NOT NULL,
            player_id INTEGER REFERENCES players(id),
            player_name_cn TEXT NOT NULL,
            team_name TEXT NOT NULL,
            minute INTEGER,
            UNIQUE(fixture_id, player_id, minute)
        );
    ''')
    conn.commit()
    conn.close()
