# database.py
import sqlite3
import json
from datetime import datetime
from config import Config

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    save_path TEXT NOT NULL,
                    category TEXT,
                    last_hash TEXT,
                    last_check TIMESTAMP,
                    last_update TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER,
                    action TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (topic_id) REFERENCES topics (id)
                )
            ''')

    def add_topic(self, topic_id, title, save_path, category=None):
        with self.get_connection() as conn:
            try:
                conn.execute('''
                    INSERT INTO topics (topic_id, title, save_path, category, last_check, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (topic_id, title, save_path, category, datetime.now(), datetime.now()))

                # Добавляем запись в историю
                conn.execute('''
                    INSERT INTO history (topic_id, action, details)
                    VALUES ((SELECT id FROM topics WHERE topic_id = ?), 'add', 'Топик добавлен')
                ''', (topic_id,))

                return True
            except sqlite3.IntegrityError:
                return False  # Топик уже существует

    def get_topics(self):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM topics WHERE is_active = 1 ORDER BY created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def get_topic(self, topic_id):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM topics WHERE topic_id = ?', (topic_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_topic(self, topic_id, **kwargs):
        with self.get_connection() as conn:
            fields = []
            values = []
            for key, value in kwargs.items():
                if value is not None:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if fields:
                values.append(topic_id)
                query = f"UPDATE topics SET {', '.join(fields)} WHERE topic_id = ?"
                conn.execute(query, values)

    def delete_topic(self, topic_id):
        with self.get_connection() as conn:
            # Мягкое удаление
            conn.execute('UPDATE topics SET is_active = 0 WHERE topic_id = ?', (topic_id,))

            # Добавляем запись в историю
            cursor = conn.execute('SELECT id FROM topics WHERE topic_id = ?', (topic_id,))
            row = cursor.fetchone()
            if row:
                conn.execute('''
                    INSERT INTO history (topic_id, action, details)
                    VALUES (?, 'delete', 'Топик удален')
                ''', (row[0],))

    def add_history(self, topic_id, action, details):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO history (topic_id, action, details)
                VALUES ((SELECT id FROM topics WHERE topic_id = ?), ?, ?)
            ''', (topic_id, action, details))

    def get_history(self, limit=100):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT h.*, t.title, t.topic_id 
                FROM history h
                JOIN topics t ON h.topic_id = t.id
                ORDER BY h.created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]