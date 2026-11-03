from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import random
import time

app = Flask(__name__)
CORS(app)

OWNER_ID = 1780245651 

def get_db():
    conn = sqlite3.connect('gifts.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Пользователи (с добавленными полями)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT,
        username TEXT,
        phone TEXT,
        stars INTEGER DEFAULT 1000,
        grams INTEGER DEFAULT 0,
        role TEXT DEFAULT 'user',
        is_frozen INTEGER DEFAULT 0
    )""")
    # Сообщения
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT,
        sender TEXT,
        text TEXT,
        time TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "Pepegram API работает!"

# --- ПОЛЬЗОВАТЕЛИ ---
@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        # Если новый, даем 1000 звезд и роль owner (если это твой ID)
        role = 'owner' if int(user_id) == OWNER_ID else 'user'
        c.execute("INSERT INTO users (user_id, name, stars, role) VALUES (?, ?, 1000, ?)", (user_id, 'Новый игрок', role))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
    conn.close()
    return jsonify(dict(user))

# --- АДМИНКА ---
@app.route('/api/admin/get_all', methods=['GET'])
def get_all():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/admin/action', methods=['POST'])
def admin_action():
    data = request.json or {}
    action = data.get('action')
    target = data.get('target')
    value = data.get('value', 0)

    conn = get_db()
    c = conn.cursor()

    if action == 'freeze':
        c.execute("UPDATE users SET is_frozen = 1 WHERE user_id = ?", (target,))
    elif action == 'unfreeze':
        c.execute("UPDATE users SET is_frozen = 0 WHERE user_id = ?", (target,))
    elif action == 'give_stars':
        c.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (int(value), target))
    elif action == 'take_stars':
        c.execute("UPDATE users SET stars = stars - ? WHERE user_id = ?", (int(value), target))
    elif action == 'set_role':
        c.execute("UPDATE users SET role = ? WHERE user_id = ?", (value, target))

    conn.commit()
    conn.close()
    return jsonify({"msg": "Успешно"})

# --- ЧАТЫ ---
@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json or {}
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO messages (chat_id, sender, text, time) VALUES (?, ?, ?, ?)",
              (data['chat_id'], data['sender'], data['text'], time.strftime("%H:%M")))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/get_messages/<chat_id>', methods=['GET'])
def get_messages(chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
    messages = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(messages)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
