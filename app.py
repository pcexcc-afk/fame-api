"""Pepegram backend. Запуск: pip install flask && python app.py  ->  http://localhost:5000"""
import sqlite3, secrets, os
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'pepegram.db')
app = Flask(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, token TEXT UNIQUE, name TEXT, bio TEXT DEFAULT '',
  stars INTEGER DEFAULT 1000, ton REAL DEFAULT 0, gram REAL DEFAULT 0, is_admin INTEGER DEFAULT 0,
  frozen INTEGER DEFAULT 0, name_color TEXT DEFAULT '#1c2733', frame TEXT DEFAULT 'none', bg TEXT DEFAULT 'blue');
CREATE TABLE IF NOT EXISTS gifts(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, emoji TEXT, price INTEGER,
  gift_type TEXT DEFAULT 'regular', supply INTEGER DEFAULT 0, minted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, gift_id INTEGER,
  number INTEGER, showcase INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, text TEXT,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP);
"""
SEED = [('Мишка', '🧸', 50, 'regular', 0), ('Роза', '🌹', 100, 'regular', 0), ('Торт', '🎂', 150, 'regular', 0),
        ('Кубок', '🏆', 250, 'regular', 0), ('Ракета', '🚀', 300, 'regular', 0),
        ('Алмаз', '💎', 500, 'market', 100), ('Пепе', '🐸', 1000, 'market', 50), ('Корона', '👑', 2500, 'market', 10)]


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop('db', None)
    if d:
        d.close()


def q(sql, a=(), one=False):
    r = db().execute(sql, a).fetchall()
    return (r[0] if r else None) if one else r


def x(sql, a=()):
    c = db().execute(sql, a)
    db().commit()
    return c.lastrowid


def init():
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    if not con.execute('SELECT 1 FROM gifts').fetchone():
        con.executemany('INSERT INTO gifts(name,emoji,price,gift_type,supply) VALUES(?,?,?,?,?)', SEED)
    con.commit()
    con.close()


def err(m, c=400):
    return jsonify(success=False, error=m), c


@app.after_request
def cors(r):  # нужно, если фронтенд открыт не с этого же сервера (например, в APK)
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,OPTIONS'
    return r


def auth(admin=False):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            u = q('SELECT * FROM users WHERE token=?', (request.headers.get('Authorization', ''),), one=True)
            if not u:
                return err('Не авторизован', 401)
            if admin and not u['is_admin']:
                return err('Нет прав', 403)
            g.u = u
            return f(*a, **k)
        return w
    return deco


def body():
    return request.get_json(silent=True) or {}


def user_json(u):
    d = dict(u)
    d.pop('token', None)
    return d


def gift_json(r):
    d = dict(r)
    if d['supply'] and d['minted'] >= d['supply']:
        d['gift_type'] = 'sold'
    return d


@app.route('/')
def index():
    return send_from_directory(BASE, 'index.html')


@app.route('/api/<path:_>', methods=['OPTIONS'])
def opts(_):
    return '', 204


@app.post('/api/register')
def register():
    name = (body().get('name') or '').strip()[:32]
    if not name:
        return err('Введи имя')
    first = q('SELECT 1 FROM users LIMIT 1', one=True) is None  # первый пользователь = админ
    uid, token = str(secrets.randbelow(9 * 10 ** 8) + 10 ** 8), secrets.token_hex(24)
    x('INSERT INTO users(id,token,name,is_admin) VALUES(?,?,?,?)', (uid, token, name, int(first)))
    return jsonify(success=True, id=uid, token=token)


@app.get('/api/me')
@auth()
def me():
    return jsonify(user_json(g.u))


@app.put('/api/me')
@auth()
def update_me():
    b, allowed = body(), {'name': 32, 'bio': 140, 'name_color': 9, 'frame': 12, 'bg': 12}
    for k, n in allowed.items():
        if k in b:
            v = str(b[k]).strip()[:n]
            if k == 'name' and not v:
                continue
            x(f'UPDATE users SET {k}=? WHERE id=?', (v, g.u['id']))
    return jsonify(success=True)


@app.get('/api/gifts')
@auth()
def gifts():
    return jsonify([gift_json(r) for r in q('SELECT * FROM gifts ORDER BY id')])


def inv_rows(uid):
    return q('''SELECT i.id,i.number,i.showcase,i.gift_id,g.name,g.emoji,g.supply,g.gift_type
                FROM inventory i JOIN gifts g ON g.id=i.gift_id WHERE i.user_id=? ORDER BY i.id DESC''', (uid,))


@app.get('/api/inventory')
@auth()
def inventory():
    return jsonify([dict(r) for r in inv_rows(g.u['id'])])


@app.post('/api/buy_gift')
@auth()
def buy_gift():
    u = g.u
    if u['frozen']:
        return err('Аккаунт заморожен', 403)
    gf = q('SELECT * FROM gifts WHERE id=?', (body().get('gift_id'),), one=True)
    if not gf or gf['gift_type'] == 'sold':
        return err('Недоступен')
    if gf['supply'] and gf['minted'] >= gf['supply']:
        return err('Распродан')
    if u['stars'] < gf['price']:
        return err('Не хватает звёзд')
    n = gf['minted'] + 1
    x('UPDATE users SET stars=stars-? WHERE id=?', (gf['price'], u['id']))
    x('UPDATE gifts SET minted=? WHERE id=?', (n, gf['id']))
    x('INSERT INTO inventory(user_id,gift_id,number) VALUES(?,?,?)', (u['id'], gf['id'], n))
    return jsonify(success=True, new_balance=u['stars'] - gf['price'], number=n)


@app.post('/api/send_gift')
@auth()
def send_gift():
    b = body()
    if g.u['frozen']:
        return err('Аккаунт заморожен', 403)
    to = str(b.get('to_user', '')).strip()
    it = q('SELECT * FROM inventory WHERE id=? AND user_id=?', (b.get('inventory_id'), g.u['id']), one=True)
    if not it:
        return err('Подарок не найден')
    if to == g.u['id'] or not q('SELECT 1 FROM users WHERE id=?', (to,), one=True):
        return err('Получатель не найден')
    x('UPDATE inventory SET user_id=?, showcase=0 WHERE id=?', (to, it['id']))
    return jsonify(success=True)


@app.post('/api/showcase')
@auth()
def showcase():
    b = body()
    it = q('SELECT * FROM inventory WHERE id=? AND user_id=?', (b.get('inventory_id'), g.u['id']), one=True)
    if not it:
        return err('Подарок не найден')
    on = int(bool(b.get('on')))
    if on and q('SELECT COUNT(*) c FROM inventory WHERE user_id=? AND showcase=1', (g.u['id'],), one=True)['c'] >= 6:
        return err('В витрине максимум 6 подарков')
    x('UPDATE inventory SET showcase=? WHERE id=?', (on, it['id']))
    return jsonify(success=True)


@app.get('/api/messages')
@auth()
def messages():
    after = request.args.get('after', type=int, default=0)
    rows = q('''SELECT * FROM (SELECT m.id,m.text,m.ts,u.id uid,u.name,u.name_color FROM messages m
                JOIN users u ON u.id=m.user_id WHERE m.id>? ORDER BY m.id DESC LIMIT 50) ORDER BY id''', (after,))
    return jsonify([dict(r) for r in rows])


@app.post('/api/messages')
@auth()
def send_message():
    if g.u['frozen']:
        return err('Аккаунт заморожен', 403)
    t = (body().get('text') or '').strip()[:1000]
    if not t:
        return err('Пустое сообщение')
    return jsonify(success=True, id=x('INSERT INTO messages(user_id,text) VALUES(?,?)', (g.u['id'], t)))


# ---------- админка ----------
@app.post('/api/admin/give_stars')
@auth(admin=True)
def give_stars():
    b = body()
    cur = b.get('currency', 'stars')
    if cur not in ('stars', 'ton', 'gram'):
        return err('Неверная валюта')
    if not q('SELECT 1 FROM users WHERE id=?', (b.get('target_id'),), one=True):
        return err('Пользователь не найден')
    x(f'UPDATE users SET {cur}={cur}+? WHERE id=?', (float(b.get('amount', 0)), b.get('target_id')))
    return jsonify(success=True)


@app.post('/api/admin/give_gift')
@auth(admin=True)
def give_gift():
    b = body()
    gf = q('SELECT * FROM gifts WHERE id=?', (b.get('gift_id'),), one=True)
    if not gf or not q('SELECT 1 FROM users WHERE id=?', (b.get('target_id'),), one=True):
        return err('Подарок или пользователь не найден')
    n = gf['minted'] + 1
    x('UPDATE gifts SET minted=? WHERE id=?', (n, gf['id']))
    x('INSERT INTO inventory(user_id,gift_id,number) VALUES(?,?,?)', (b['target_id'], gf['id'], n))
    return jsonify(success=True)


@app.post('/api/admin/freeze')
@auth(admin=True)
def freeze():
    b = body()
    if b.get('target_id') == g.u['id']:
        return err('Нельзя заморозить себя')
    x('UPDATE users SET frozen=? WHERE id=?', (int(bool(b.get('frozen'))), b.get('target_id')))
    return jsonify(success=True)


@app.post('/api/admin/add_gift')
@auth(admin=True)
def add_gift():
    b = body()
    name, emoji = (b.get('name') or '').strip()[:40], (b.get('emoji') or '').strip()[:8]
    if not name or not emoji:
        return err('Заполни название и символ')
    t = b.get('gift_type') if b.get('gift_type') in ('regular', 'market') else 'regular'
    x('INSERT INTO gifts(name,emoji,price,gift_type,supply) VALUES(?,?,?,?,?)',
      (name, emoji, int(b.get('price') or 100), t, int(b.get('supply') or 0)))
    return jsonify(success=True)


init()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
