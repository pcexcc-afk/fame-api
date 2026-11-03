from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import time

app = Flask(__name__)
CORS(app)

def get_db():
    conn = sqlite3.connect('pepegram.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT,
        username TEXT,
        stars INTEGER DEFAULT 1000,
        tons REAL DEFAULT 0,
        is_premium INTEGER DEFAULT 1,
        is_frozen INTEGER DEFAULT 0,
        role TEXT DEFAULT 'user',
        bio TEXT DEFAULT '',
        nick_color TEXT DEFAULT '#ffffff',
        frame TEXT DEFAULT 'transparent',
        avatar TEXT DEFAULT ''
    )""")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "Pepegram API работает!"

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (id, name, username) VALUES (?, ?, ?)", (user_id, "Игрок", "user" + user_id[-4:]))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
    conn.close()
    return jsonify(dict(user))

@app.route('/api/user/update', methods=['POST'])
def update_user():
    data = request.json or {}
    conn = get_db()
    c = conn.cursor()
    c.execute("""UPDATE users SET 
        name = ?, bio = ?, nick_color = ?, frame = ? 
        WHERE id = ?""", 
        (data['name'], data['bio'], data['nick_color'], data['frame'], data['id']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
