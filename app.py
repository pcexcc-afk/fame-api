from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import random
import time

app = Flask(__name__)
CORS(app)

# Твой ник и ID (Владелец)
OWNER_USERNAME = "doctor" 

def get_db():
    conn = sqlite3.connect('gifts.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        display_name TEXT,
        user_id TEXT,
        anon_number TEXT DEFAULT 'Не задан',
        grams INTEGER DEFAULT 0,
        tons INTEGER DEFAULT 0,
        stars INTEGER DEFAULT 1000,
        is_premium INTEGER DEFAULT 1,
        last_bonus INTEGER DEFAULT 0,
        subscribed_chat INTEGER DEFAULT 1,
        subscribed_channel INTEGER DEFAULT 1,
        nft_username TEXT DEFAULT 'Не куплен',
        name_color TEXT DEFAULT '#ffffff',
        avatar_frame TEXT DEFAULT 'none',
        role TEXT DEFAULT 'user'
    )""")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "Pepegram API работает!"

# 1. Получить профиль
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

# 2. Кастомизация профиля (Цвет и Рамка)
@app.route('/api/customize', methods=['POST'])
def customize():
    data = request.json or {}
    username = data.get('username', '').lower()
    color = data.get('color', '#ffffff')
    frame = data.get('frame', 'none')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET name_color = ?, avatar_frame = ? WHERE username = ?", (color, frame, username))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "msg": "Профиль обновлен!"})

# 3. Выдача ролей (Админы)
@app.route('/api/admin/set_role', methods=['POST'])
def set_role():
    data = request.json or {}
    requester = data.get('requester', '').lower() # Кто запрашивает
    target = data.get('target', '').lower()       # Кому выдают
    new_role = data.get('role')                   # 'head_admin', 'admin', 'user'
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username = ?", (requester,))
    req_user = c.fetchone()
    
    if not req_user: return jsonify({"error": "Нет доступа"}), 403
    
    req_role = req_user["role"]
    
    # Права: Владелец может всех. Главный админ только простых админов.
    allowed = False
    if req_role == 'owner':
        allowed = True
    elif req_role == 'head_admin' and new_role in ['admin', 'user'] and target != OWNER_USERNAME:
        allowed = True
        
    if not allowed:
        conn.close()
        return jsonify({"error": "Недостаточно прав"}), 403
        
    c.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, target))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "msg": f"Роль @{target} изменена на {new_role}"})

# 4. Получить всех (для админки)
@app.route('/api/admin/get_all', methods=['GET'])
def get_all():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, user_id, stars, role, subscribed_chat, subscribed_channel FROM users")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(users)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
