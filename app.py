from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import random

app = Flask(__name__)
CORS(app)

def get_db():
    conn = sqlite3.connect('gifts.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Добавили user_id и is_premium (по умолчанию 1 - Премиум включен)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        display_name TEXT,
        user_id TEXT,
        anon_number TEXT DEFAULT 'Не задан',
        grams INTEGER DEFAULT 0,
        tons INTEGER DEFAULT 0,
        stars INTEGER DEFAULT 1000,
        is_premium INTEGER DEFAULT 1,
        nft_username TEXT DEFAULT 'Не куплен'
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
    
    # Создаем юзера с ID и Премиумом
    c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    existing = c.fetchone()
    
    if not existing:
        new_id = str(random.randint(100000000, 999999999))
        c.execute("INSERT INTO users (username, display_name, user_id, stars) VALUES (?, ?, ?, 1000)", (username, username, new_id))
    
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.commit()
    conn.close()
    
    return jsonify({
        "username": user["username"], 
        "user_id": user["user_id"],
        "anon_number": user["anon_number"],
        "grams": user["grams"], 
        "tons": user["tons"], 
        "stars": user["stars"], 
        "is_premium": user["is_premium"],
        "nft_username": user["nft_username"]
    })

# АДМИН: Получить список всех игроков
@app.route('/api/admin/get_all_users', methods=['GET'])
def get_all_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(users)

# АДМИН: Выдать валюту
@app.route('/api/admin/give_currency', methods=['POST'])
def give_currency():
    data = request.json or {}
    username = data.get('username', '').lower()
    ctype = data.get('type') # 'stars', 'grams', 'tons'
    amount = int(data.get('amount', 0))
    
    if not username or amount == 0: return jsonify({"error": "Ошибка"}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (username, display_name) VALUES (?, ?)", (username, username))
    
    if ctype in ['stars', 'grams', 'tons']:
        c.execute(f"UPDATE users SET {ctype} = {ctype} + ? WHERE username = ?", (amount, username))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "msg": f"Выдано {amount} {ctype} для @{username}"})
    
    conn.close()
    return jsonify({"error": "Неверный тип валюты"}), 400

# КАЗИНО (оставляем как было)
@app.route('/api/casino/upgrader', methods=['POST'])
def casino_upgrader():
    data = request.json or {}
    username = data.get('username', '').lower()
    amount = int(data.get('amount', 0))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT stars FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    if not user or user["stars"] < amount:
        conn.close()
        return jsonify({"error": "Недостаточно звезд"}), 403
    c.execute("UPDATE users SET stars = stars - ? WHERE username = ?", (amount, username))
    win = random.choice([True, False])
    if win:
        c.execute("UPDATE users SET stars = stars + ? WHERE username = ?", (amount * 2, username))
        msg = f"Выигрыш! +{amount * 2} ⭐"
    else:
        msg = f"Проигрыш. -{amount} ⭐"
    conn.commit()
    conn.close()
    return jsonify({"win": win, "message": msg})

@app.route('/api/casino/rocket', methods=['POST'])
def casino_rocket():
    data = request.json or {}
    username = data.get('username', '').lower()
    amount = int(data.get('amount', 0))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT stars FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    if not user or user["stars"] < amount:
        conn.close()
        return jsonify({"error": "Недостаточно звезд"}), 403
    c.execute("UPDATE users SET stars = stars - ? WHERE username = ?", (amount, username))
    win = random.choice([True, False, False])
    if win:
        c.execute("UPDATE users SET stars = stars + ? WHERE username = ?", (amount * 3, username))
        msg = f"Ракета взлетела! +{amount * 3} ⭐"
    else:
        msg = f"Ракета упала. -{amount} ⭐"
    conn.commit()
    conn.close()
    return jsonify({"win": win, "message": msg})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
