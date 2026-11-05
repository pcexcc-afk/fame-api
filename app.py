"""from flask import Flask, request, jsonify
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
    # Юзеры
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT, username TEXT,
        stars INTEGER DEFAULT 1000, ton REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0, is_frozen INTEGER DEFAULT 0,
        anon_number TEXT DEFAULT NULL, labels TEXT DEFAULT 'Нет'
    )""")
    # Подарки
    c.execute("""CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, emoji TEXT, price INTEGER,
        gift_type TEXT DEFAULT 'regular',
        upgrade_cost INTEGER DEFAULT 0
    )""")
    # Инвентарь
    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, gift_id INTEGER,
        is_upgraded INTEGER DEFAULT 0,
        gift_number INTEGER
    )""")
    # Коды для входа
    c.execute("""CREATE TABLE IF NOT EXISTS auth_codes (
        phone TEXT PRIMARY KEY, code TEXT
    )""")
    
    # Добавляем стартовые подарки, если пусто
    c.execute("SELECT COUNT(*) FROM gifts")
    if c.fetchone()[0] == 0:
        gifts = [
            # --- ОБЫЧНЫЕ (Regular) ---
            ("Сердце с бантом","❤️",15,"regular",0),
            ("Подарочная коробка","🎁",25,"regular",0),
            ("Роза","🌹",25,"regular",0),
            ("Шампанское","🍾",50,"regular",0),
            ("Мишка с тыквой","🐻",50,"regular",0),
            ("Торт","🎂",50,"regular",0),
            ("Букет","💐",50,"regular",0),
            ("Ракета","🚀",50,"regular",0),
            ("Кубок","🏆",100,"regular",0),
            ("Кольцо с бриллиантом","💍",100,"regular",0),
            ("Бриллиант","💎",100,"regular",0),
            
            # --- МАРКЕТ (Market) ---
            ("Мороженое рожок","🍦",300,"market",100),
            ("Статуя Свободы","🗽",565,"market",200),
            ("Фонарь","🏮",499,"market",200),
            ("Собака-рэпер","🐕",565,"market",200),
            ("Лапша","🍜",438,"market",150),
            ("Радужный леденец","🍭",450,"market",150),
            ("Эскимо","🍫",464,"market",150),
            ("Фламинго-круг","🦩",460,"market",150),
            ("Рюкзак","🎒",526,"market",200),
            ("Какашка","💩",500,"market",200),
            ("2025 год","🎊",399,"market",100),
            ("Корона шута","🎭",470,"market",150),
            ("Пряничное сердце","🍪",565,"market",200),
            ("Пасхальный кролик","🐣",565,"market",200),
            ("Медаль","🥇",532,"market",200),
            ("Световой меч","⚔️",565,"market",200),
            ("Котик в сердце","🐱",1451,"market",500),
            ("Пепе","🐸",626336,"market",100000),
            ("Маска Джейсона","😨",4030993,"market",500000),
            ("Кулон-луна","🌙",565,"market",200),
            ("Пионы","🌸",564,"market",200),
            ("Гриб","🍄",565,"market",200),
            ("Глинтвейн","🍷",500,"market",200),
            ("Доска для сёрфинга","🏄",643,"market",250),
            ("Шляпа ведьмы","🧙",770,"market",300),
            ("Сакура","🌸",1016,"market",400),
            ("Рождественский венок","🎄",530,"market",200),
            ("Клубника в коробке","🍓",852,"market",350),
            ("Снежный шар","❄️",624,"market",250),
            
            # --- ПРОДАННЫЕ (Sold) ---
            ("Конь","🐴",0,"sold",0),
            ("Надгробие RIP","🪦",15000,"sold",0),
            ("Гроб","⚰️",5000,"sold",0),
            ("Персонаж","🦸",41000,"sold",0),
            ("Кроссовки","👟",10000,"sold",0),
            ("Портфель","💼",5000,"sold",0)
        ]
        c.executemany("INSERT INTO gifts (name, emoji, price, gift_type, upgrade_cost) VALUES (?, ?, ?, ?, ?)", gifts)
    conn.commit()
    conn.close()

init_db()

# --- АВТОРИЗАЦИЯ ---
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
        
    c.execute("SELECT * FROM users WHERE id = ?", (phone,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (id, name) VALUES (?, ?)", (phone, "Игрок"))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id = ?", (phone,))
        user = c.fetchone()
        
    c.execute("DELETE FROM auth_codes WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "user": dict(user)})

# --- ЮЗЕР ---
@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify(dict(user))
    return jsonify({"error": "Не найден"}), 404

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
    
    if user['is_frozen'] == 1:
        conn.close()
        return jsonify({"success": False, "error": "Аккаунт заморожен"}), 403
        
    if user['stars'] < gift['price']:
        conn.close()
        return jsonify({"success": False, "error": "Недостаточно звезд"}), 400
        
    new_balance = user['stars'] - gift['price']
    c.execute("UPDATE users SET stars = ? WHERE id = ?", (new_balance, user_id))
    
    # Генерируем номер подарка
    c.execute("SELECT COUNT(*) FROM inventory WHERE gift_id = ?", (gift_id,))
    gift_num = c.fetchone()[0] + 1
    
    c.execute("INSERT INTO inventory (user_id, gift_id, gift_number) VALUES (?, ?, ?)", (user_id, gift_id, gift_num))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "new_balance": new_balance})

# --- УЛУЧШЕНИЕ ---
@app.route('/api/upgrade_gift', methods=['POST'])
def upgrade_gift():
    data = request.json
    user_id = data.get('user_id')
    inv_id = data.get('inv_id')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT i.id, g.upgrade_cost, i.is_upgraded 
                 FROM inventory i JOIN gifts g ON i.gift_id = g.id 
                 WHERE i.id = ? AND i.user_id = ?""", (inv_id, user_id))
    item = c.fetchone()
    
    if not item:
        conn.close()
        return jsonify({"success": False, "error": "Подарок не найден"}), 404
        
    if item['is_upgraded'] == 1:
        conn.close()
        return jsonify({"success": False, "error": "Уже улучшен"}), 400
        
    c.execute("SELECT stars FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    
    if user['stars'] < item['upgrade_cost']:
        conn.close()
        return jsonify({"success": False, "error": "Недостаточно звезд"}), 400
        
    c.execute("UPDATE users SET stars = stars - ? WHERE id = ?", (item['upgrade_cost'], user_id))
    c.execute("UPDATE inventory SET is_upgraded = 1 WHERE id = ?", (inv_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- АДМИНКА ---
@app.route('/api/admin/give', methods=['POST'])
def admin_give():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE id = ?", (data.get('admin_id'),))
    admin = c.fetchone()
    
    if not admin or admin['is_admin'] != 1:
        conn.close()
        return jsonify({"success": False, "error": "Нет прав"}), 403
        
    c.execute("UPDATE users SET stars = stars + ? WHERE id = ?", (data.get('amount', 0), data.get('target_id')))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
