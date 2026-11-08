# -*- coding: utf-8 -*-
"""
AnoxGram — backend (Flask + SQLite/PostgreSQL) ИСПРАВЛЕННЫЙ
"""
import os, re, json, hmac, hashlib, secrets, sqlite3, datetime
from flask import Flask, request, jsonify, g
try:
    from flask_cors import CORS
except ImportError:
    CORS = None

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_PG = DATABASE_URL.startswith("postgres") 
try:
    import psycopg2, psycopg2.extras
except ImportError:
    USE_PG = False

ADMIN_KEY = os.environ.get("ADMIN_KEY", "anox-admin-change-me")
BOT_STAR_PRICE = 100  # 100 GRAM = 1 Telegram Star

app = Flask(__name__)
if CORS:
    CORS(app, resources={r"/api/*": {"origins": "*"}})
else:
    @app.after_request
    def _cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Key, X-Token"
        resp.headers["Access-Control-Allow-Methods"] = "*"
        return resp

def db():
    if "db" not in g:
        if USE_PG:
            g.db = psycopg2.connect(DATABASE_URL)
            g.db.cursor_factory = psycopg2.extras.RealDictCursor
        else:
            path = DATABASE_URL.replace("sqlite:///", "") if DATABASE_URL.startswith("sqlite") else "anoxgram.db"
            g.db = sqlite3.connect(path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(_=None):
    d = g.pop("db", None)
    if d is not None:
        d.close()

def Q(sql):
    return sql.replace("?", "%s") if USE_PG else sql

def run(sql, args=(), commit=False):
    c = db().cursor()
    c.execute(Q(sql), args)
    if commit:
        db().commit()
    return c

def one(sql, args=()):
    r = run(sql, args).fetchone()
    return dict(r) if r else None

def all_(sql, args=()):
    return [dict(r) for r in run(sql, args).fetchall()]

def init_db():
    # Упрощенная схема для совместимости
    schema = """
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE, pass_hash TEXT, salt TEXT,
      display_id INTEGER UNIQUE, nickname TEXT, bio TEXT DEFAULT '',
      avatar_color TEXT DEFAULT '#5a5ae6', avatar_emoji TEXT DEFAULT '',
      banner TEXT DEFAULT '', is_premium INTEGER DEFAULT 0,
      labels TEXT DEFAULT '[]', badges TEXT DEFAULT '[]',
      nick_color TEXT DEFAULT '#ffffff', nick_font TEXT DEFAULT 'Inter',
      stars INTEGER DEFAULT 100, gram INTEGER DEFAULT 100,
      level INTEGER DEFAULT 1, gift_level INTEGER DEFAULT 0,
      hidden_id INTEGER DEFAULT 0, frozen INTEGER DEFAULT 0,
      accent TEXT DEFAULT '#6c5ce7', effect TEXT DEFAULT '',
      clan_id INTEGER DEFAULT 0, clan_role TEXT DEFAULT '',
      created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS transactions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      from_id INTEGER, to_id INTEGER, amount INTEGER, currency TEXT,
      kind TEXT, note TEXT DEFAULT '', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS gifts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT, rarity TEXT DEFAULT 'common', model TEXT DEFAULT 'cube',
      bg TEXT DEFAULT 'linear-gradient(135deg,#667eea,#764ba2)',
      is_nft INTEGER DEFAULT 0, owner_id INTEGER, from_id INTEGER DEFAULT 0,
      price INTEGER DEFAULT 0, upgrade_level INTEGER DEFAULT 0,
      unique_key TEXT DEFAULT '', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS market(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      gift_id INTEGER, seller_id INTEGER, price INTEGER, sold INTEGER DEFAULT 0,
      created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS chats(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      type TEXT DEFAULT 'group', title TEXT, username TEXT DEFAULT '',
      owner_id INTEGER, admins TEXT DEFAULT '[]', public INTEGER DEFAULT 1,
      slow_mode INTEGER DEFAULT 0, pinned TEXT DEFAULT '', about TEXT DEFAULT '',
      boosts INTEGER DEFAULT 0, link_key TEXT DEFAULT '', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS chat_members(
      chat_id INTEGER, user_id INTEGER, muted INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      chat_id INTEGER, user_id INTEGER, text TEXT, kind TEXT DEFAULT 'text',
      created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS bots(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      owner_id INTEGER, name TEXT, username TEXT UNIQUE, token TEXT, about TEXT DEFAULT '',
      created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS clans(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT, tag TEXT, emblem TEXT, color TEXT, badge TEXT,
      owner_id INTEGER, members TEXT DEFAULT '{}', link_key TEXT UNIQUE,
      created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS numbers(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      display_id INTEGER UNIQUE, owner_id INTEGER, anonymous INTEGER DEFAULT 0,
      price INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS logs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      admin TEXT, action TEXT, detail TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS settings_kv(
      key TEXT PRIMARY KEY, value TEXT
    );
    """
    d = db()
    for stmt in schema.strip().split(";"):
        if stmt.strip():
            d.cursor().execute(stmt)
    d.commit()

with app.app_context():
    init_db()

NOW = lambda: datetime.datetime.utcnow().isoformat(timespec="seconds")

def h(pw, salt):
    return hashlib.sha256((salt + pw).encode()).hexdigest()

def new_display_id():
    while True:
        n = secrets.randbelow(900000) + 100000
        if not one("SELECT id FROM users WHERE display_id=?", (n,)):
            return n

def public_user(u, viewer=None):
    if not u: return None
    labels = json.loads(u.get("labels") or "[]")
    if u["hidden_id"] and (not viewer or viewer["id"] != u["id"]):
        labels = [l for l in labels if l not in ("id",)]
    return {
        "id": u["id"], "username": u["username"], "display_id": u["display_id"],
        "nickname": u["nickname"], "bio": u["bio"], "avatar_color": u["avatar_color"],
        "avatar_emoji": u["avatar_emoji"], "banner": u["banner"],
        "is_premium": bool(u["is_premium"]), "labels": labels,
        "badges": json.loads(u.get("badges") or "[]"),
        "nick_color": u["nick_color"], "nick_font": u["nick_font"],
        "level": u["level"], "gift_level": u["gift_level"],
        "accent": u["accent"], "effect": u["effect"],
        "clan_id": u["clan_id"], "clan_role": u["clan_role"],
        "created_at": u["created_at"], "frozen": bool(u["frozen"]),
    }

def get_user_by_token():
    t = request.headers.get("X-Token", "")
    if not t: return None, None
    uid = one("SELECT value FROM settings_kv WHERE key=?", ("tok:" + t,))
    if not uid: return None, None
    u = one("SELECT * FROM users WHERE id=?", (int(uid["value"]),))
    return (u, t) if u and not u["frozen"] else (None, t)

def tx(from_id, to_id, amount, currency, kind, note=""):
    run("INSERT INTO transactions(from_id,to_id,amount,currency,kind,note,created_at) VALUES(?,?,?,?,?,?,?)",
        (from_id, to_id, amount, currency, kind, note, NOW()), commit=True)

def change_balance(uid, currency, delta):
    col = "stars" if currency == "stars" else "gram"
    run(f"UPDATE users SET {col}={col}+? WHERE id=?", (delta, uid), commit=True)

def log(admin, action, detail=""):
    run("INSERT INTO logs(admin,action,detail,created_at) VALUES(?,?,?,?)",
        (admin, action, json.dumps(detail, ensure_ascii=False)[:500], NOW()), commit=True)

def require_admin():
    if request.headers.get("X-Admin-Key") != ADMIN_KEY:
        return jsonify({"error": "Доступ запрещён"}), 403
    return None

GIFT_MODELS = ["cube", "sphere", "pyramid", "heart", "star", "gem"]
GIFT_BGS = ["linear-gradient(135deg,#667eea,#764ba2)", "linear-gradient(135deg,#f093fb,#f5576c)",
            "linear-gradient(135deg,#4facfe,#00f2fe)", "linear-gradient(135deg,#43e97b,#38f9d7)",
            "linear-gradient(135deg,#fa709a,#fee140)", "linear-gradient(135deg,#30cfd0,#330867)"]

def make_gift(owner_id, from_id=0, name=None, rarity="common", is_nft=False, price=0):
    name = name or secrets.token_hex(2).upper()
    run("""INSERT INTO gifts(name,rarity,model,bg,is_nft,owner_id,from_id,price,unique_key,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (name, rarity, secrets.choice(GIFT_MODELS), secrets.choice(GIFT_BGS),
         1 if is_nft else 0, owner_id, from_id, price,
         "NFT-" + secrets.token_hex(6).upper() if is_nft else "", NOW()), commit=True)
    return one("SELECT * FROM gifts ORDER BY id DESC LIMIT 1")

# ---------------- AUTH ----------------
@app.post("/api/register")
def register():
    d = request.get_json(force=True)
    username = (d.get("username") or "").strip().lower()
    password = d.get("password") or ""
    nickname = (d.get("nickname") or username).strip()
    if not re.fullmatch(r"[a-z0-9_]{3,32}", username):
        return jsonify({"error": "Ник: 3–32 символа, a-z 0-9 _"}), 400
    if len(password) < 4:
        return jsonify({"error": "Пароль минимум 4 символа"}), 400
    if one("SELECT id FROM users WHERE username=?", (username,)):
        return jsonify({"error": "Ник занят"}), 409
    salt = secrets.token_hex(8)
    uid = new_display_id()
    run("""INSERT INTO users(username,pass_hash,salt,display_id,nickname,labels,stars,gram,created_at)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (username, h(password, salt), salt, uid, nickname,
         json.dumps(["Новичок"]), 100, 100, NOW()), commit=True)
    u = one("SELECT * FROM users WHERE username=?", (username,))
    token = secrets.token_hex(24)
    run("INSERT OR REPLACE INTO settings_kv(key,value) VALUES(?,?)", ("tok:" + token, str(u["id"])), commit=True)
    # автоподписка на официальный канал
    ch = one("SELECT id FROM chats WHERE username='anoxgram'")
    if ch:
        run("INSERT OR IGNORE INTO chat_members(chat_id,user_id) VALUES(?,?)", (ch["id"], u["id"]), commit=True)
    tx(0, u["id"], 100, "stars", "bonus", "Стартовый бонус")
    tx(0, u["id"], 100, "gram", "bonus", "Стартовый бонус")
    return jsonify({"token": token, "user": public_user(one("SELECT * FROM users WHERE id=?", (u["id"],)))})

@app.post("/api/login")
def login():
    d = request.get_json(force=True)
    u = one("SELECT * FROM users WHERE username=?", ((d.get("username") or "").strip().lower(),))
    if not u or not hmac.compare_digest(u["pass_hash"], h(d.get("password") or "", u["salt"])):
        return jsonify({"error": "Неверный ник или пароль"}), 401
    if u["frozen"]:
        return jsonify({"error": "Аккаунт заморожен"}), 403
    token = secrets.token_hex(24)
    run("INSERT OR REPLACE INTO settings_kv(key,value) VALUES(?,?)", ("tok:" + token, str(u["id"])), commit=True)
    return jsonify({"token": token, "user": public_user(u)})

@app.get("/api/me")
def me():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    full = dict(u); full.pop("pass_hash"); full.pop("salt")
    return jsonify({"user": full, "public": public_user(u, u)})

@app.post("/api/logout")
def logout():
    t = request.headers.get("X-Token", "")
    if t: run("DELETE FROM settings_kv WHERE key=?", ("tok:" + t,), commit=True)
    return jsonify({"ok": True})

# ---------------- PROFILE ----------------
@app.post("/api/profile")
def profile_update():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    allowed = ["nickname", "bio", "avatar_color", "avatar_emoji", "banner",
               "nick_color", "nick_font", "accent", "effect", "hidden_id"]
    for k in allowed:
        if k in d:
            v = d[k]
            if k in ("avatar_color", "nick_color", "accent") and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(v)):
                continue
            if k in ("hidden_id",): v = 1 if v else 0
            run(f"UPDATE users SET {k}=? WHERE id=?", (str(v)[:200], u["id"]))
    db().commit()
    return jsonify({"user": public_user(one("SELECT * FROM users WHERE id=?", (u["id"],)))})

@app.get("/api/user/<username>")
def user_page(username):
    viewer, _ = get_user_by_token()
    u = one("SELECT * FROM users WHERE username=? OR display_id=?",
            (username.lower(), username if username.isdigit() else -1))
    if not u: return jsonify({"error": "Не найден"}), 404
    gifts = all_("SELECT * FROM gifts WHERE owner_id=? ORDER BY id DESC LIMIT 12", (u["id"],))
    clan = one("SELECT * FROM clans WHERE id=?", (u["clan_id"],)) if u["clan_id"] else None
    return jsonify({"user": public_user(u, viewer), "gifts": gifts,
                    "clan": {k: clan[k] for k in ("name", "tag", "color", "badge")} if clan else None})

# ---------------- WALLET ----------------
@app.get("/api/wallet")
def wallet():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    t = all_("SELECT * FROM transactions WHERE from_id=? OR to_id=? ORDER BY id DESC LIMIT 50",
             (u["id"], u["id"]))
    return jsonify({"stars": u["stars"], "gram": u["gram"], "history": t})

@app.post("/api/transfer")
def transfer():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    to = one("SELECT * FROM users WHERE username=? OR display_id=?",
             ((d.get("to") or "").lower(), d.get("to") if str(d.get("to", "")).isdigit() else -1))
    if not to: return jsonify({"error": "Получатель не найден"}), 404
    if to["id"] == u["id"]: return jsonify({"error": "Нельзя перевести самому себе"}), 400
    cur = d.get("currency", "stars")
    if cur not in ("stars", "gram"): return jsonify({"error": "Валюта"}), 400
    amount = int(d.get("amount") or 0)
    if amount <= 0 or u["stars" if cur == "stars" else "gram"] < amount:
        return jsonify({"error": "Недостаточно средств"}), 400
    change_balance(u["id"], cur, -amount)
    change_balance(to["id"], cur, amount)
    tx(u["id"], to["id"], amount, cur, "transfer", d.get("note", ""))
    return jsonify({"ok": True})

@app.post("/api/exchange")
def exchange():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    direction = d.get("direction")
    amount = int(d.get("amount") or 0)
    if amount <= 0: return jsonify({"error": "Сумма"}), 400
    if direction == "gram_to_stars":
        if u["gram"] < amount * BOT_STAR_PRICE:
            return jsonify({"error": f"Нужно {amount * BOT_STAR_PRICE} GRAM"}), 400
        change_balance(u["id"], "gram", -amount * BOT_STAR_PRICE)
        change_balance(u["id"], "stars", amount)
        tx(u["id"], u["id"], amount, "stars", "exchange", f"Обмен {amount * BOT_STAR_PRICE} GRAM")
    else:
        if u["stars"] < amount: return jsonify({"error": "Недостаточно звёзд"}), 400
        change_balance(u["id"], "stars", -amount)
        change_balance(u["id"], "gram", amount * BOT_STAR_PRICE)
        tx(u["id"], u["id"], amount, "gram", "exchange", f"Обмен {amount} звёзд")
    return jsonify({"ok": True})

@app.post("/api/request")
def payment_request():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    to = one("SELECT * FROM users WHERE username=? OR display_id=?",
             ((d.get("to") or "").lower(), d.get("to") if str(d.get("to", "")).isdigit() else -1))
    if not to: return jsonify({"error": "Не найден"}), 404
    amount = int(d.get("amount") or 0)
    cur = d.get("currency", "stars")
    tx(to["id"], u["id"], amount, cur, "request", d.get("note", ""))
    return jsonify({"ok": True})

@app.post("/api/buy_stars")
def buy_stars():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    amount = int(d.get("amount") or 0)
    cost = amount * BOT_STAR_PRICE
    if amount <= 0 or u["gram"] < cost:
        return jsonify({"error": f"Нужно {cost} GRAM"}), 400
    change_balance(u["id"], "gram", -cost)
    change_balance(u["id"], "stars", amount)
    tx(u["id"], u["id"], amount, "stars", "purchase", f"Покупка ({cost} GRAM)")
    return jsonify({"ok": True, "stars": u["stars"] + amount})

# ---------------- GIFTS ----------------
@app.get("/api/gifts/catalog")
def gift_catalog():
    return jsonify({"models": GIFT_MODELS, "backgrounds": GIFT_BGS,
                    "rarities": {"common": 50, "rare": 200, "epic": 500, "legendary": 1500, "nft": 5000}})

@app.get("/api/gifts")
def my_gifts():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    return jsonify({"gifts": all_("SELECT * FROM gifts WHERE owner_id=? ORDER BY id DESC", (u["id"],))})

@app.post("/api/gifts/send")
def send_gift():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    to = one("SELECT * FROM users WHERE username=? OR display_id=?",
             ((d.get("to") or "").lower(), d.get("to") if str(d.get("to", "")).isdigit() else -1))
    if not to: return jsonify({"error": "Не найден"}), 404
    rarity = d.get("rarity", "common")
    price = {"common": 50, "rare": 200, "epic": 500, "legendary": 1500, "nft": 5000}.get(rarity, 50)
    if u["stars"] < price: return jsonify({"error": "Недостаточно звёзд"}), 400
    change_balance(u["id"], "stars", -price)
    gift = make_gift(to["id"], u["id"], d.get("name"), rarity, rarity == "nft", price)
    run("UPDATE users SET gift_level=gift_level+?, level=level+? WHERE id=?",
        (price // 100, price // 200, to["id"]), commit=True)
    tx(u["id"], to["id"], price, "stars", "gift", f"Подарок {gift['name']}")
    return jsonify({"gift": gift})

@app.post("/api/gifts/<int:gid>/upgrade")
def upgrade_gift(gid):
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    gft = one("SELECT * FROM gifts WHERE id=? AND owner_id=?", (gid, u["id"]))
    if not gft or not gft["is_nft"]: return jsonify({"error": "NFT не найден"}), 404
    level = gft["upgrade_level"]
    cost = 500 * (level + 1)
    if u["stars"] < cost: return jsonify({"error": f"Нужно {cost} звёзд"}), 400
    d = request.get_json(force=True) or {}
    change_balance(u["id"], "stars", -cost)
    run("UPDATE gifts SET upgrade_level=?, model=?, bg=? WHERE id=?",
        (level + 1, d.get("model", gft["model"]),
         d.get("bg", GIFT_BGS[(level + 1) % len(GIFT_BGS)]), gid), commit=True)
    tx(u["id"], u["id"], cost, "stars", "upgrade", f"Апгрейд #{gid}")
    return jsonify({"gift": one("SELECT * FROM gifts WHERE id=?", (gid,))})

@app.post("/api/gifts/craft")
def craft():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    ids = request.get_json(force=True).get("ids", [])[:4]
    if len(ids) != 4: return jsonify({"error": "Нужно 4 NFT"}), 400
    nfts = all_("SELECT * FROM gifts WHERE id IN (?,?,?,?) AND owner_id=? AND is_nft=1",
                (*ids, u["id"]))
    if len(nfts) != 4: return jsonify({"error": "Проверьте владение"}), 400
    for i in ids:
        run("DELETE FROM gifts WHERE id=?", (i,))
    unique = make_gift(u["id"], 0, "Уникальный " + secrets.token_hex(3).upper(),
                       "legendary", True, 20000)
    run("UPDATE gifts SET unique_key=? WHERE id=?", ("UNIQ-" + secrets.token_hex(8).upper(), unique["id"]), commit=True)
    tx(u["id"], u["id"], 0, "stars", "craft", "Крафт")
    return jsonify({"gift": one("SELECT * FROM gifts WHERE id=?", (unique["id"],))})

@app.get("/api/market")
def market_list():
    rows = all_("""SELECT m.*, g.name, g.rarity, g.model, g.bg, g.is_nft, g.upgrade_level, u.nickname, u.username
                   FROM market m JOIN gifts g ON g.id=m.gift_id JOIN users u ON u.id=m.seller_id
                   WHERE m.sold=0 ORDER BY m.id DESC""")
    return jsonify({"items": rows})

@app.post("/api/market/sell")
def market_sell():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    gft = one("SELECT * FROM gifts WHERE id=? AND owner_id=?", (int(d.get("gift_id")), u["id"]))
    if not gft: return jsonify({"error": "Не найден"}), 404
    price = int(d.get("price") or 0)
    if price <= 0: return jsonify({"error": "Цена"}), 400
    run("UPDATE gifts SET owner_id=0 WHERE id=?", (gft["id"],), commit=True)
    run("INSERT INTO market(gift_id,seller_id,price,created_at) VALUES(?,?,?,?)",
        (gft["id"], u["id"], price, NOW()), commit=True)
    return jsonify({"ok": True})

@app.post("/api/market/<int:mid>/buy")
def market_buy(mid):
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    m = one("SELECT * FROM market WHERE id=? AND sold=0", (mid,))
    if not m: return jsonify({"error": "Лот не найден"}), 404
    if u["stars"] < m["price"]: return jsonify({"error": "Недостаточно звёзд"}), 400
    change_balance(u["id"], "stars", -m["price"])
    change_balance(m["seller_id"], "stars", m["price"])
    run("UPDATE gifts SET owner_id=? WHERE id=?", (u["id"], m["gift_id"]))
    run("UPDATE market SET sold=1 WHERE id=?", (mid,))
    db().commit()
    tx(u["id"], m["seller_id"], m["price"], "stars", "market", f"Лот #{mid}")
    return jsonify({"ok": True})

# ---------------- CHATS ----------------
def chat_dict(c):
    d = dict(c)
    d["admins"] = json.loads(d.get("admins") or "[]")
    return d

@app.get("/api/chats")
def chats_list():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    mine = all_("""SELECT c.* FROM chats c JOIN chat_members m ON m.chat_id=c.id
                    WHERE m.user_id=? ORDER BY c.id DESC""", (u["id"],))
    public = all_("SELECT * FROM chats WHERE public=1 AND id NOT IN (SELECT chat_id FROM chat_members WHERE user_id=?) ORDER BY boosts DESC LIMIT 20", (u["id"],))
    return jsonify({"mine": [chat_dict(c) for c in mine], "public": [chat_dict(c) for c in public]})

@app.post("/api/chats")
def chat_create():
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    d = request.get_json(force=True)
    ctype = d.get("type", "group")
    if ctype not in ("group", "channel", "bot"): return jsonify({"error": "Тип"}), 400
    link = secrets.token_urlsafe(6)
    run("""INSERT INTO chats(type,title,username,owner_id,public,about,link_key,created_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        (ctype, (d.get("title") or "Чат")[:64], (d.get("username") or "").lower()[:32],
         u["id"], 1 if d.get("public", True) else 0, d.get("about", "")[:200], link, NOW()), commit=True)
    c = one("SELECT * FROM chats ORDER BY id DESC LIMIT 1")
    run("INSERT OR IGNORE INTO chat_members(chat_id,user_id) VALUES(?,?)", (c["id"], u["id"]), commit=True)
    return jsonify({"chat": chat_dict(one("SELECT * FROM chats WHERE id=?", (c["id"],)))})

@app.get("/api/chats/<int:cid>")
def chat_get(cid):
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    c = one("SELECT * FROM chats WHERE id=?", (cid,))
    if not c: return jsonify({"error": "Не найден"}), 404
    member = one("SELECT * FROM chat_members WHERE chat_id=? AND user_id=?", (cid, u["id"]))
    if not c["public"] and not member:
        return jsonify({"error": "Приватный чат"}), 403
    msgs = all_("""SELECT m.*, us.nickname, us.avatar_color FROM messages m
                   JOIN users us ON us.id=m.user_id WHERE m.chat_id=? ORDER BY m.id DESC LIMIT 100""", (cid,))
    return jsonify({"chat": chat_dict(c), "messages": list(reversed(msgs)), "member": bool(member)})

@app.post("/api/chats/<int:cid>/join")
def chat_join(cid):
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    c = one("SELECT * FROM chats WHERE id=? OR link_key=?", (cid, str(cid)))
    if not c: return jsonify({"error": "Не найден"}), 404
    if not c["public"] and request.get_json(force=True).get("key") != c["link_key"]:
        return jsonify({"error": "Нужна ссылка"}), 403
    run("INSERT OR IGNORE INTO chat_members(chat_id,user_id) VALUES(?,?)", (c["id"], u["id"]), commit=True)
    return jsonify({"ok": True})

@app.post("/api/chats/<int:cid>/message")
def chat_message(cid):
    u, _ = get_user_by_token()
    if not u: return jsonify({"error": "Не авторизован"}), 401
    c = one("SELECT * FROM chats WHERE id=?", (cid,))
    if not c: return jsonify({"error": "Не найден"}), 404
    member = one("SELECT * FROM chat_members WHERE chat_id=? AND user_id=?", (cid, u["id"]))
    is_admin = u["id"] == c["owner_id"] or u["id"] in json.loads(c.get("admins") or "[]")
    if not member and not is_admin: return jsonify({"error": "Вы не участник"}), 403
    if c["type"] == "channel" and not is_admin:
        return jsonify({"error": "Только админы"}), 403
    if c["slow_mode"] > 0 and not is_admin:
        last = one("SELECT created_at FROM messages WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT 1", (
