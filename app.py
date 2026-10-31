from ffrom flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import random
import time

app = Flask(__name__)
CORS(app)

OWNER_USERNAME = "doctor"

def get_db():
    conn = sqlite3.connect('gifts.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Таблица пользователей (добавлены поля для всех функций)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        display_name TEXT,
        user_id TEXT,
        anon_number TEXT DEFAULT 'Нет',
        grams INTEGER DEFAULT 0,
        tons INTEGER DEFAULT 0,
        stars INTEGER DEFAULT 1000,
        is_premium INTEGER DEFAULT 1,
        is_frozen INTEGER DEFAULT 0,
        role TEXT DEFAULT 'user',
        nft_username TEXT DEFAULT 'Нет',
        last_bonus INTEGER DEFAULT 0
    )""")
    # Таблица сообщений
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        receiver TEXT,
        text TEXT,
        created_at TEXT
    )""")
    # Таблица подарков
    c.execute("""CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner TEXT,
        gift_name TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "Pepegram API работает!"

@app.route('/api/profile/<username>', methods=['GET'])
def get_profile(username):
    username = username.lower()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    if not user:
        new_id = str(random.randint(100000000, 999999999))
        role = 'owner' if username == OWNER_USERNAME else 'user'
        c.execute("INSERT INTO users (username, display_name, user_id, stars, role) VALUES (?, ?, ?, 1000, ?)", (username, username, new_id, role))
        conn.commit()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
    conn.close()
    return jsonify(dict(user))

# --- ЧАТЫ ---
@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json or {}
    sender = data.get('sender', '').lower()
    receiver = data.get('receiver', '').lower()
    text = data.get('text', '')
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender, receiver, text, created_at) VALUES (?, ?, ?, ?)",
              (sender, receiver, text, time.strftime("%H:%M")))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/get_messages', methods=['POST'])
def get_messages():
    data = request.json or {}
    user1 = data.get('user1', '').lower()
    user2 = data.get('user2', '').lower()
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT * FROM messages 
                 WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
                 ORDER BY id ASC""", (user1, user2, user2, user1))
    messages = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(messages)

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
    target = data.get('target', '').lower()
    value = data.get('value', 0)

    conn = get_db()
    c = conn.cursor()

    if action == 'freeze':
        c.execute("UPDATE users SET is_frozen = 1 WHERE username = ?", (target,))
        msg = f"Игрок @{target} заморожен"
    elif action == 'unfreeze':
        c.execute("UPDATE users SET is_frozen = 0 WHERE username = ?", (target,))
        msg = f"Игрок @{target} разморожен"
    elif action == 'give_stars':
        c.execute("UPDATE users SET stars = stars + ? WHERE username = ?", (int(value), target))
        msg = f"Выдано {value} звезд"
    elif action == 'take_stars':
        c.execute("UPDATE users SET stars = stars - ? WHERE username = ?", (int(value), target))
        msg = f"Забрано {value} звезд"
    elif action == 'give_gift':
        c.execute("INSERT INTO gifts (owner, gift_name) VALUES (?, ?)", (target, value))
        msg = f"Выдан подарок {value}"
    elif action == 'set_role':
        c.execute("UPDATE users SET role = ? WHERE username = ?", (value, target))
        msg = f"Роль изменена на {value}"
    elif action == 'give_anon':
        anon = f"+1 (202) {random.randint(100,999)}-{random.randint(1000,9999)}"
        c.execute("UPDATE users SET anon_number = ? WHERE username = ?", (anon, target))
        msg = f"Выдан номер {anon}"
    elif action == 'give_nft':
        c.execute("UPDATE users SET nft_username = ? WHERE username = ?", (value, target))
        msg = f"Выдан NFT-юзернейм @{value}"
    else:
        msg = "Неизвестное действие"
    
    conn.commit()
    conn.close()
    return jsonify({"msg": msg})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
