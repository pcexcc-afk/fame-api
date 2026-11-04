from flask import Flask, request, jsonify
from flask_cors import CORS
import os, sqlite3

app = Flask(__name__)
CORS(app)
DB = 'pepegram.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT, bio TEXT DEFAULT '',
        stars INTEGER DEFAULT 1000, tons REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0, is_frozen INTEGER DEFAULT 0,
        avatar_url TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, emoji TEXT, price INTEGER,
        gift_type TEXT DEFAULT 'regular'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id TEXT, gift_id INTEGER,
        from_user TEXT DEFAULT NULL,
        received_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id TEXT, to_id TEXT, amount INTEGER, type TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # Migration: add gift_type if missing
    try:
        c.execute("ALTER TABLE gifts ADD COLUMN gift_type TEXT DEFAULT 'regular'")
    except: pass
    try:
        c.execute("ALTER TABLE user_gifts ADD COLUMN from_user TEXT DEFAULT NULL")
    except: pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")
    except: pass
    c.execute("SELECT COUNT(*) FROM gifts")
    if c.fetchone()[0] == 0:
        gifts = [
            # --- ОБЫЧНЫЕ ---
            ("Сердце с бантом","💗",15,"regular"),
            ("Подарочная коробка","🎁",25,"regular"),
            ("Роза","🌹",25,"regular"),
            ("Шампанское","🍾",50,"regular"),
            ("Мишка с тыквой","🐻",50,"regular"),
            ("Торт","🎂",50,"regular"),
            ("Букет","💐",50,"regular"),
            ("Ракета","🚀",50,"regular"),
            ("Кубок","🏆",100,"regular"),
            ("Кольцо с бриллиантом","💍",100,"regular"),
            ("Бриллиант","💎",100,"regular"),
            # --- МАРКЕТ ---
            ("Мороженое рожок","🍦",300,"market"),
            ("Статуя Свободы","🗽",565,"market"),
            ("Фонарь","🏮",499,"market"),
            ("Собака-рэпер","🐕",565,"market"),
            ("Лапша","🍜",438,"market"),
            ("Радужный леденец","🍭",450,"market"),
            ("Эскимо","🍫",464,"market"),
            ("Фламинго-круг","🦩",460,"market"),
            ("Рюкзак","🎒",526,"market"),
            ("Пакет семечек","🌰",565,"market"),
            ("Какашка","💩",500,"market"),
            ("2025 год","🎊",399,"market"),
            ("Цифра 8","🎂",420,"market"),
            ("Рождественская конфета","🍬",399,"market"),
            ("Рождественский носок","🧦",399,"market"),
            ("Клевер","🍀",500,"market"),
            ("Подарок 2025","🎁",420,"market"),
            ("Носки","🧦",500,"market"),
            ("Змея-Санта","🐍",525,"market"),
            ("Торт с вишнями","🍰",550,"market"),
            ("Мечеть","🕌",550,"market"),
            ("Корона шута","🎭",470,"market"),
            ("Пряничное сердце","🍪",565,"market"),
            ("Happy B-Day","🎉",530,"market"),
            ("Пасхальный кролик","🐣",565,"market"),
            ("Медаль","🥇",532,"market"),
            ("Косяк","🌿",1366,"market"),
            ("Световой меч","⚔️",565,"market"),
            ("Букет с деньгами","💵",530,"market"),
            ("Волшебная палочка","✨",525,"market"),
            ("Ключ к сердцу","🗝️",565,"market"),
            ("Книга","📚",520,"market"),
            ("Календарь","📅",555,"market"),
            ("Котик в сердце","🐱",1451,"market"),
            ("Обезьянка","🐒",697,"market"),
            ("Ракета-корабль","🛸",450,"market"),
            ("Кулон-луна","🌙",565,"market"),
            ("Банка конфет","🍬",564,"market"),
            ("Торт на подставке","🎂",500,"market"),
            ("Имбирный человечек","🍪",549,"market"),
            ("Тамагочи","🎮",410,"market"),
            ("Белый зверёк","🐑",802,"market"),
            ("Пионы","🌸",564,"market"),
            ("Гриб","🍄",565,"market"),
            ("Красный глаз","👁️",798,"market"),
            ("Глинтвейн","🍷",500,"market"),
            ("2025 цветные","🎊",399,"market"),
            ("Доска для сёрфинга","🏄",643,"market"),
            ("Пасхальное яйцо","🥚",450,"market"),
            ("Love You подарок","🛍️",725,"market"),
            ("Какао с корицей","☕",455,"market"),
            ("Перо-ручка","🖊️",790,"market"),
            ("Шляпа ведьмы","🧙",770,"market"),
            ("Коричневый леденец","🍭",495,"market"),
            ("Блокнот","📓",500,"market"),
            ("Котёл с монетами","🪙",500,"market"),
            ("Сакура","🌸",1016,"market"),
            ("Галстук-бабочка","🎀",565,"market"),
            ("Чёртик в коробке","🎃",499,"market"),
            ("Рождественский венок","🎄",530,"market"),
            ("Зелёный котёл","🫕",490,"market"),
            ("Шапка Санты","🎅",499,"market"),
            ("Клубника в коробке","🍓",852,"market"),
            ("Снежный шар","❄️",624,"market"),
            ("Кекс с зайцем","🐰",798,"market"),
            ("Свеча","🕯️",565,"market"),
            ("Пушистая шапка","🎩",750,"market"),
            ("Звёздочка-брелок","⭐",937,"market"),
            ("Варежки","🧤",750,"market"),
            ("Цилиндр","🎩",957,"market"),
            ("Тыква Хэллоуин","🎃",1491,"market"),
            ("Рождественские колокола","🔔",1023,"market"),
            ("Розовые туфли","👠",1702,"market"),
            ("Хрустальный шар","🔮",1313,"market"),
            ("Коробка шоколада","🍫",1193,"market"),
            ("Розовое зелье","🧪",1433,"market"),
            ("Сердце-замок","🗝️",2092,"market"),
            ("Роза в колбе","🌹",2418,"market"),
            ("Бирюзовая шкатулка","📦",2902,"market"),
            ("Розовая свеча","🕯️",1083,"market"),
            ("Патефон","🎵",1111,"market"),
            ("Сердце с паутиной","🕸️",1552,"market"),
            ("Розовый медвежонок","🐻",3062,"market"),
            ("Цветок-череп","💀",1161,"market"),
            ("Фен с бантом","💇",1379,"market"),
            ("Золотой колокольчик","🔔",803,"market"),
            ("Кольцо Telegram","💍",2983,"market"),
            ("Белый голубь","🕊️",2619,"market"),
            ("Метла","🧹",1261,"market"),
            ("Сигара","🚬",3321,"market"),
            ("Кукла вуду","🧸",3783,"market"),
            ("Машина","🚗",5639,"market"),
            ("Золотые часы","⌚",5494,"market"),
            ("Among Us","👾",43535,"market"),
            ("Розовый шлем","🪖",3451,"market"),
            ("Белый череп","💀",2777,"market"),
            ("Золотая соска","🍼",2338,"market"),
            ("Кольцо-печатка","💍",4031,"market"),
            ("Вампирские губы","💋",4672,"market"),
            ("Духи №5","🧴",7417,"market"),
            ("Кольцо с камнем","💎",5963,"market"),
            ("Кристаллы","💎",11763,"market"),
            ("Лягушка","🐸",4747,"market"),
            ("Золотая рука","🤚",10077,"market"),
            ("Чёрная кошка","🐈",24992,"market"),
            ("Тёмные очки","🕶️",11529,"market"),
            ("Сумка Birkin","👜",12633,"market"),
            ("Яд","☠️",5877,"market"),
            ("Золотой браслет","📿",11121,"market"),
            ("Золотой шлем","⛑️",17500,"market"),
            ("Кирпич","🧱",7079,"market"),
            ("Слива","🫐",24097,"market"),
            ("Кепка","🧢",38601,"market"),
            ("Золотой кулак","💪",11202,"market"),
            ("Мозаичный кубок","🏆",125767,"market"),
            ("Ледяной кубок","🏆",161240,"market"),
            ("Маска Джейсона","😨",4030993,"market"),
            ("Лунное сердце","💜",116818,"market"),
            ("Пепе","🐸",626336,"market"),
            # --- ПРОДАН ---
            ("Конь","🐴",0,"sold"),
            ("Оригами-самолётик","✈️",0,"sold"),
            ("Надгробие RIP","🪦",15000,"sold"),
            ("Гроб","⚰️",5000,"sold"),
            ("Персонаж","🦸",41000,"sold"),
            ("Чёрная куртка","🧥",10000,"sold"),
            ("Кроссовки","👟",10000,"sold"),
            ("Портфель","💼",5000,"sold"),
            ("Замок из песка","🏰",500,"sold"),
            ("Кокос","🥥",150,"sold"),
            ("Мороженое-вазочка","🍨",150,"sold"),
            ("Красная звезда","⭐",100,"sold"),
            ("Голубь-марка","🕊️",150,"sold"),
            ("1 Мая","🌹",100,"sold"),
            ("Пасхальный кулич","🎂",75,"sold"),
            ("Восьмёрка из роз","🌹",200,"sold"),
        ]
        c.executemany("INSERT INTO gifts (name,emoji,price,gift_type) VALUES (?,?,?,?)", gifts)
    conn.commit()
    conn.close()

init_db()

# ─── ROUTES ───────────────────────────────────────────

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("SELECT COUNT(*) FROM users")
        is_admin = 1 if c.fetchone()[0] == 0 else 0
        c.execute("INSERT INTO users (id,name,is_admin) VALUES (?,?,?)", (user_id, f"Игрок{user_id[-4:]}", is_admin))
        conn.commit()
        c.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = c.fetchone()
    conn.close()
    return jsonify(dict(user))

@app.route('/api/user/<user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    if 'name' in data:
        c.execute("UPDATE users SET name=? WHERE id=?", (data['name'][:32], user_id))
    if 'bio' in data:
        c.execute("UPDATE users SET bio=? WHERE id=?", (data['bio'][:128], user_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/gifts', methods=['GET'])
def get_gifts():
    gift_type = request.args.get('type')
    conn = get_db()
    c = conn.cursor()
    if gift_type:
        c.execute("SELECT * FROM gifts WHERE gift_type=? ORDER BY price", (gift_type,))
    else:
        c.execute("""SELECT * FROM gifts ORDER BY
            CASE gift_type WHEN 'regular' THEN 1 WHEN 'market' THEN 2 WHEN 'sold' THEN 3 END, price""")
    gifts = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(gifts)

@app.route('/api/user/<user_id>/inventory', methods=['GET'])
def get_inventory(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT ug.id, ug.received_at, ug.from_user,
                        g.name, g.emoji, g.price, g.gift_type
               FROM user_gifts ug JOIN gifts g ON ug.gift_id=g.id
               WHERE ug.owner_id=? ORDER BY ug.received_at DESC""", (user_id,))
    items = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/buy_gift', methods=['POST'])
def buy_gift():
    data = request.json
    user_id, gift_id = data.get('user_id'), data.get('gift_id')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM gifts WHERE id=?", (gift_id,))
    gift = c.fetchone()
    if not gift:
        conn.close(); return jsonify({"success":False,"error":"Подарок не найден"}), 404
    if gift['gift_type'] == 'sold':
        conn.close(); return jsonify({"success":False,"error":"Этот подарок распродан"}), 400
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    if not user:
        conn.close(); return jsonify({"success":False,"error":"Пользователь не найден"}), 404
    if user['is_frozen']:
        conn.close(); return jsonify({"success":False,"error":"Аккаунт заморожен"}), 403
    if user['stars'] < gift['price']:
        conn.close(); return jsonify({"success":False,"error":"Недостаточно звёзд"}), 400
    new_bal = user['stars'] - gift['price']
    c.execute("UPDATE users SET stars=? WHERE id=?", (new_bal, user_id))
    c.execute("INSERT INTO user_gifts (owner_id,gift_id) VALUES (?,?)", (user_id, gift_id))
    c.execute("INSERT INTO transactions (from_id,to_id,amount,type) VALUES (?,?,?,?)",
              (user_id,'shop',gift['price'],'purchase'))
    conn.commit()
    conn.close()
    return jsonify({"success":True,"new_balance":new_bal,"gift_name":gift['name']})

@app.route('/api/send_gift', methods=['POST'])
def send_gift():
    data = request.json
    from_user, to_user = data.get('from_user'), data.get('to_user')
    inv_id = data.get('inventory_id')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM user_gifts WHERE id=? AND owner_id=?", (inv_id, from_user))
    item = c.fetchone()
    if not item:
        conn.close(); return jsonify({"success":False,"error":"Подарок не найден"}), 403
    c.execute("SELECT id,name FROM users WHERE id=?", (to_user,))
    target = c.fetchone()
    if not target:
        conn.close(); return jsonify({"success":False,"error":"Получатель не найден"}), 404
    if from_user == to_user:
        conn.close(); return jsonify({"success":False,"error":"Нельзя отправить себе"}), 400
    c.execute("UPDATE user_gifts SET owner_id=?,from_user=? WHERE id=?", (to_user,from_user,inv_id))
    conn.commit()
    conn.close()
    return jsonify({"success":True,"to_name":target['name']})

# ─── ADMIN ────────────────────────────────────────────

def check_admin(admin_id, conn):
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE id=?", (admin_id,))
    row = c.fetchone()
    return row and row['is_admin'] == 1

@app.route('/api/admin/give_stars', methods=['POST'])
def give_stars():
    data = request.json
    conn = get_db()
    if not check_admin(data.get('admin_id'), conn):
        conn.close(); return jsonify({"success":False,"error":"Нет прав"}), 403
    c = conn.cursor()
    c.execute("UPDATE users SET stars=stars+? WHERE id=?", (data.get('amount',0), data.get('target_id')))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route('/api/admin/freeze', methods=['POST'])
def freeze_user():
    data = request.json
    conn = get_db()
    if not check_admin(data.get('admin_id'), conn):
        conn.close(); return jsonify({"success":False,"error":"Нет прав"}), 403
    c = conn.cursor()
    c.execute("UPDATE users SET is_frozen=? WHERE id=?", (data.get('frozen',1), data.get('target_id')))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route('/api/admin/add_gift', methods=['POST'])
def add_gift():
    data = request.json
    conn = get_db()
    if not check_admin(data.get('admin_id'), conn):
        conn.close(); return jsonify({"success":False,"error":"Нет прав"}), 403
    c = conn.cursor()
    c.execute("INSERT INTO gifts (name,emoji,price,gift_type) VALUES (?,?,?,?)",
              (data.get('name','Подарок'), data.get('emoji','🎁'),
               data.get('price',100), data.get('gift_type','regular')))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    admin_id = request.args.get('admin_id')
    conn = get_db()
    if not check_admin(admin_id, conn):
        conn.close(); return jsonify({"error":"Нет прав"}), 403
    c = conn.cursor()
    c.execute("SELECT id,name,stars,is_frozen,is_admin,created_at FROM users ORDER BY stars DESC")
    users = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(users)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
