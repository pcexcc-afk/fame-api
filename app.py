from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import os

app = Flask(__name__)
CORS(app)
DB_FILE = 'orbitagram.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 1. Таблица пользователей
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, 
        name TEXT, 
        stars INTEGER DEFAULT 1000, 
        ton REAL DEFAULT 0, 
        is_admin INTEGER DEFAULT 0, 
        is_frozen INTEGER DEFAULT 0
    )""")
    
    # 2. Таблица для кодов входа
    c.execute("""CREATE TABLE IF NOT EXISTS auth_codes (
        phone TEXT PRIMARY KEY, 
        code TEXT
    )""")
    
    # 3. Таблица подарков
    c.execute("""CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT, 
        emoji TEXT, 
        price INTEGER, 
        gift_type TEXT DEFAULT 'regular'
    )""")
    
    # 4. Таблица инвентаря (купленные подарки)
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id TEXT, 
        gift_id INTEGER, 
        is_upgraded INTEGER DEFAULT 0
    )""")
    
    # Заполняем магазин подарками, если он пустой
    c.execute("SELECT COUNT(*) FROM gifts")
    if c.fetchone()[0] == 0:
        gifts = [
            # Обычные
            ("Сердце", "❤️", 15, "regular"), 
            ("Мишка", "🧸", 50, "regular"),
            ("Ракета", "🚀", 50, "regular"), 
            ("Кубок", "🏆", 100, "regular"),
            ("Кольцо", "💍", 100, "regular"), 
            ("Алмаз", "💎", 100, "regular"),
            # Маркет (NFT)
            ("Пепе", "🐸", 1000, "market"), 
            ("Котик", "🐱", 1451, "market"),
            ("Световой меч", "⚔️", 565, "market")
        ]
        c.executemany("INSERT INTO gifts (name, emoji, price, gift_type) VALUES (?, ?, ?, ?)", gifts)
        
    conn.commit()
    conn.close()

init_db()

# --- АВТОРИЗАЦИЯ ---

@app.route('/api/auth/request_code', methods=['POST'])
def request_code():
    data = request.json
    phone = data.get('phone')
    if not phone: 
        return jsonify({"success": False, "error": "Введите номер"}), 400
        
    code = str(random.randint(1000, 9999))
    
    conn = get_db()
    c = conn.cursor()
    # Сохраняем код в базу
    c.execute("INSERT OR REPLACE INTO auth_codes (phone, code) VALUES (?, ?)", (phone, code))
    conn.commit()
    conn.close()
    
    # ВРЕМЕННО: возвращаем код на сайт, чтобы ты его увидел (потом уберем в бота)
    return jsonify({"success": True, "test_code": code})

@app.route('/api/auth/verify', methods=['POST'])
def verify_code():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT code FROM auth_codes WHERE phone = ?", (phone,))
    row = c.fetchone()
    
    if not row or row['code'] != code:
        conn.close()
        return jsonify({"success": False, "error": "Неверный код"}), 401
        
    # Проверяем, есть ли юзер, если нет - создаем
    c.execute("SELECT * FROM users WHERE id = ?", (phone,))
    user = c.fetchone()
    if not user:
        # Делаем первого зашедшего админом
        c.execute("SELECT COUNT(*) FROM users")
        is_admin = 1 if c.fetchone()[0] == 0 else 0
        c.execute("INSERT INTO users (id, name, is_admin) VALUES (?, ?, ?)", (phone, "Игрок", is_admin))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id = ?", (phone,))
        user = c.fetchone()
        
    # Удаляем использованный код
    c.execute("DELETE FROM auth_codes WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "user": dict(user)})

# --- МАГАЗИН ---

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
        return jsonify({"success": False, "error": "Ошибка данных"}), 404
        
    if user['is_frozen'] == 1:
        conn.close()
        return jsonify({"success": False, "error": "Аккаунт заморожен"}), 403
        
    if user['stars'] < gift['price']:
        conn.close()
        return jsonify({"success": False, "error": "Недостаточно звезд"}), 400
        
    # Списываем звезды и выдаем подарок
    new_balance = user['stars'] - gift['price']
    c.execute("UPDATE users SET stars = ? WHERE id = ?", (new_balance, user_id))
    c.execute("INSERT INTO inventory (user_id, gift_id) VALUES (?, ?)", (user_id, gift_id))
    
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_balance": new_balance})

# --- ИНВЕНТАРЬ ---

@app.route('/api/inventory/<user_id>', methods=['GET'])
def get_inventory(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT i.id, g.name, g.emoji, g.gift_type 
                 FROM inventory i 
                 JOIN gifts g ON i.gift_id = g.id 
                 WHERE i.user_id = ?""", (user_id,))
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(items)

# --- АДМИНКА ---

@app.route('/api/admin/give', methods=['POST'])
def admin_give():
    data = request.json
    admin_id = data.get('admin_id')
    target_id = data.get('target_id')
    amount = data.get('amount')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE id = ?", (admin_id,))
    admin = c.fetchone()
    
    if not admin or admin['is_admin'] != 1:
        conn.close()
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
        
    c.execute("UPDATE users SET stars = stars + ? WHERE id = ?", (amount, target_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
