import sqlite3
from flask import g

DATABASE = 'my_database.db'


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None) -> None:
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('PRAGMA foreign_keys = ON;')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,    
            url TEXT NOT NULL,
            blocked INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("БД та таблиця створені!")


def add_user(username: str, hashed_password: str, email: str) -> None:
    db = get_db()  
    db.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (username, hashed_password, email))
    db.commit()    
    


def check_username(username: str) -> bool:
    db = get_db()
    result = db.execute('SELECT * FROM users WHERE username LIKE VALUES ?', (username,)).fetchone()
    
    return result


def get_user(email: str, hashed_password: str) -> bool:
    db = get_db()
    result = db.execute('SELECT * FROM users WHERE (username, password) LIKE values (?, ?)', (email, hashed_password))
    cursor = db.execute(
        'SELECT * FROM users WHERE email = ? AND password = ?', 
        (email, hashed_password)
    )
    user = cursor.fetchone()
    return user 

def delete_user_from_db(username: str):
    db = get_db()
    db.execute('DELETE FROM users WHERE username = like ? ', username) #TODO
    
    return "USER HAD BENN DELETED [200]" 
    
    
if __name__ == '__main__':
    init_db()