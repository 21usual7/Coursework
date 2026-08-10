import sqlite3

conn = sqlite3.connect("example.db")

db = conn.cursor()

db.execute("""
    CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, password_hash TEXT UNIQUE, created_at TEXT UNIQUE)
""")