@app.route('/api/customize', methods=['POST'])
def customize():
    data = request.json or {}
    conn = from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3

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
        stars INTEGER DEFAULT 1000,
        is_admin INTEGER DEFAULT 0,
        is_frozen INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        emoji TEXT,
        price INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        gift_id INTEGER
    )""")
    
    c.execute("SELECT COUNT(*) FROM gifts")
    if c.fetchone()[0] == 0:
        gifts = [
            ("Сердце", "❤️", 15), ("Мишка", "🧸", 50), 
            ("Ракета", "🚀", 50), ("Кубок", "🏆", 100), 
            ("Кольцо", "💍", 100), ("Алмаз", "💎", 100)
        ]
        c.executemany("INSERT INTO gifts (name, emoji, price) VALUES (?, ?, ?)", gifts)
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "API работает!"

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("SELECT COUNT(*) FROM users")
        is_admin = 1 if c.fetchone()[0] == 0 else 0
        c.execute("INSERT INTO users (id, name, is_admin) VALUES (?, ?, ?)", (user_id, "Игрок", is_admin))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
    conn.close()
    return jsonify(dict(user))

@app.route('/api/gifts', methods=['GET'])
def get_gifts():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM gifts")
    gifts = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(gifts)

@app.route('/api/buy_gift', methods=['POST'])
def buy_gift():
    data = request.json
    user_id = data.get('user_id')
    gift_id = data.get('gift_id')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM gifts WHERE id = ?", (gift_id,))
    gift = c.fetchone()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    
    if not user or not gift:
        conn.close()
        return jsonify({"success": False, "error": "Данные не найдены"}), 404

    if user['is_frozen'] == 1:
        conn.close()
        return jsonify({"success": False, "error": "Ваш аккаунт заморожен"}), 403

    if user['stars'] >= gift['price']:
        new_balance = user['stars'] - gift['price']
        c.execute("UPDATE users SET stars = ? WHERE id = ?", (new_balance, user_id))
        c.execute("INSERT INTO user_gifts (user_id, gift_id) VALUES (?, ?)", (user_id, gift_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "new_balance": new_balance})
    else:
        conn.close()
        return jsonify({"success": False, "error": "Недостаточно звезд"}), 400

@app.route('/api/admin/give_stars', methods=['POST'])
def give_stars():
    data = request.json
    admin_id = data.get('admin_id')
    target_id = data.get('target_id')
    amount = data.get('amount')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE id = ?", (admin_id,))
    admin = c.fetchone()
    
    if admin and admin['is_admin'] == 1:
        c.execute("UPDATE users SET stars = stars + ? WHERE id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    conn.close()
    return jsonify({"success": False, "error": "Доступ запрещен"}), 403

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    c = conn.cursor()
    c.execute("UPDATE users SET name_color = ?, avatar_frame = ? WHERE user_id = ?", 
              (data.get('color', '#ffffff'), data.get('frame', 'none'), data.get('user_id')))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})
