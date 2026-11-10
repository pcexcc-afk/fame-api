# Shade backend. Render: build `pip install -r requirements.txt`, start `gunicorn -w 1 --threads 100 app:app`
import os, re, json, time, sqlite3, secrets
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash as gph, check_password_hash as cph

DB = os.environ.get("DB_PATH", "shade.db")
OWNER = os.environ.get("OWNER_USERNAME", "@owner").lower()
FONTS = ["system-ui", "Georgia", "'Courier New'", "'Trebuchet MS'", "Impact", "cursive"]
LABELS = ["Новичок", "Галочка", "Scam", "Fake", "Hold", "Major", "Владелец Shade"]
app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 2_000_000
sio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
now = lambda: int(time.time())

SCHEMA = """
create table if not exists users(id integer primary key, nick text, username text unique, pw text, created integer,
 avatar text default '', banner text default '', color text default '#f2f2f7', font text default 'system-ui', glow integer default 0,
 labels text default '[]', badges text default '[]', stars integer default 100, gram integer default 0,
 frozen integer default 0, wfrozen integer default 0, admin integer default 0);
create table if not exists sess(tok text primary key, uid integer);
create table if not exists sec(ip text primary key, fails integer default 0, warned integer default 0, until integer default 0);
create table if not exists chats(id integer primary key, type text, title text, public integer default 0, owner integer);
create table if not exists mem(chat integer, uid integer, unique(chat, uid));
create table if not exists msgs(id integer primary key, chat integer, uid integer, text text, ts integer);
create table if not exists tx(id integer primary key, a integer, b integer, cur text, amt integer, note text, ts integer);
create table if not exists gifts(id integer primary key, name text, shape text, color text, price integer, cur text, nft integer, minted integer default 0);
create table if not exists inv(id integer primary key, uid integer, gift integer, num integer, price integer default 0, cur text default 'stars');
create table if not exists auc(id integer primary key, inv integer, seller integer, cur text, bid integer, bidder integer default 0, ends integer, done integer default 0);
create table if not exists nfn(name text primary key, owner integer);
create table if not exists logs(id integer primary key, ts integer, who text, act text, info text);
"""

def init():
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    if not c.execute("select 1 from gifts").fetchone():
        c.executemany("insert into gifts(name,shape,color,price,cur,nft) values(?,?,?,?,?,?)", [
            ("Куб", "cube", "#60a5fa", 50, "stars", 0), ("Сфера", "sphere", "#34d399", 80, "stars", 0),
            ("Звезда", "star", "#fbbf24", 150, "stars", 1), ("Сердце", "heart", "#f43f5e", 120, "stars", 0),
            ("Пирамида", "pyramid", "#a78bfa", 100, "stars", 0), ("Кристалл", "crystal", "#22d3ee", 20, "gram", 1)])
    c.execute("insert or ignore into chats(id,type,title,public,owner) values(1,'channel','Shade News',0,0)")
    c.commit(); c.close()

def run(sql, a=()):
    c = sqlite3.connect(DB, timeout=15)
    try:
        cur = c.execute(sql, a); c.commit(); return cur.lastrowid
    finally: c.close()

def q(sql, a=(), one=False):
    c = sqlite3.connect(DB, timeout=15); c.row_factory = sqlite3.Row
    try: r = [dict(x) for x in c.execute(sql, a).fetchall()]
    finally: c.close()
    return (r[0] if r else None) if one else r

def toint(x):
    try: return int(x)
    except Exception: return 0

def norm(s):
    s = (s or "").strip().lower()
    return s if s.startswith("@") else "@" + s

def err(m, c=400): return jsonify(error=m), c
def ip(): return (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()
def log(who, act, info=""): run("insert into logs(ts,who,act,info) values(?,?,?,?)", (now(), who, act, info))
def uby(un): return q("select * from users where username=?", (norm(un),), True)
def bal(uid, cur, d): run(f"update users set {cur}={cur}+? where id=?", (d, uid))
def tx(a, b, cur, amt, note): run("insert into tx(a,b,cur,amt,note,ts) values(?,?,?,?,?,?)", (a, b, cur, amt, note, now()))

def pub(u, full=False):
    d = {k: u[k] for k in ("id", "nick", "username", "created", "avatar", "banner", "color", "font", "glow", "admin", "frozen")}
    d["labels"] = json.loads(u["labels"]); d["badges"] = json.loads(u["badges"])
    if full:
        d.update(stars=u["stars"], gram=u["gram"], wfrozen=u["wfrozen"],
                 nfn=[r["name"] for r in q("select name from nfn where owner=?", (u["id"],))])
    return d

def user_by_token(t):
    return q("select u.* from users u join sess s on s.uid=u.id where s.tok=?", (t or "",), True)

def auth(f):
    @wraps(f)
    def w(*a, **k):
        u = user_by_token(request.headers.get("Authorization"))
        if not u: return err("Войдите заново", 401)
        if u["frozen"]: return err("Аккаунт заморожен администрацией", 403)
        return f(u, *a, **k)
    return w

def admin(f):
    @auth
    @wraps(f)
    def w(u, *a, **k):
        if not u["admin"]: return err("Нет доступа", 403)
        return f(u, *a, **k)
    return w

def session(uid):
    tok = secrets.token_hex(24)
    run("insert into sess values(?,?)", (tok, uid))
    return jsonify(token=tok, user=pub(q("select * from users where id=?", (uid,), True), True))

# ---------- Регистрация и вход ----------
def blocked():
    s = q("select * from sec where ip=?", (ip(),), True)
    return bool(s and s["until"] > now())

@app.post("/api/register")
def register():
    if blocked(): return err("Ваш IP заблокирован на 24 часа", 403)
    d = request.json or {}
    un, nick, pw = norm(d.get("username")), (d.get("nick") or "").strip()[:30], d.get("password") or ""
    if not nick or not re.fullmatch(r"@[a-z0-9_]{3,20}", un) or len(pw) < 6:
        return err("Нужны ник, @юзернейм (3–20 символов: латиница, цифры, _) и пароль от 6 символов")
    if uby(un) or q("select 1 from nfn where name=?", (un,)): return err("Юзернейм занят")
    own = un == OWNER
    uid = run("insert into users(nick,username,pw,created,labels,admin) values(?,?,?,?,?,?)",
              (nick, un, gph(pw), now(), json.dumps(["Владелец Shade", "Галочка"] if own else ["Новичок"], ensure_ascii=False), 2 if own else 0))
    run("insert or ignore into mem values(1,?)", (uid,))
    log(un, "register", ip())
    return session(uid)

@app.post("/api/login")
def login():
    if blocked(): return err("Ваш IP заблокирован на 24 часа", 403)
    d = request.json or {}
    u = uby(d.get("username"))
    if u and cph(u["pw"], d.get("password") or ""):
        if u["frozen"]: return err("Аккаунт заморожен администрацией", 403)
        run("delete from sec where ip=?", (ip(),))
        return session(u["id"])
    s = q("select * from sec where ip=?", (ip(),), True) or {"fails": 0, "warned": 0}
    f, w, msg, until = s["fails"] + 1, s["warned"], "Неверный юзернейм или пароль", 0
    if f >= 5 and not w:
        f, w, msg = 0, 1, "Предупреждение: 5 неверных попыток. Ещё 5 — и ваш IP будет заблокирован на 24 часа"
        log(norm(d.get("username")), "warning", ip())
    elif f >= 5 and w:
        until, msg = now() + 86400, "Слишком много попыток: IP заблокирован на 24 часа"
        log(norm(d.get("username")), "ip-block", ip())
    run("insert or replace into sec(ip,fails,warned,until) values(?,?,?,?)", (ip(), f, w, until))
    return err(msg, 403 if until else 400)

@app.get("/api/me")
def me():
    u = user_by_token(request.headers.get("Authorization"))
    return jsonify(pub(u, True)) if u else err("Войдите заново", 401)

@app.post("/api/profile")
@auth
def profile(u):
    d = request.json or {}
    nick = (d.get("nick") or "").strip()[:30] or u["nick"]
    color = d.get("color") if re.fullmatch(r"#[0-9a-fA-F]{6}", d.get("color") or "") else u["color"]
    font = d.get("font") if d.get("font") in FONTS else u["font"]
    av, bn = d.get("avatar", u["avatar"]) or "", d.get("banner", u["banner"]) or ""
    for x in (av, bn):
        if x and (not x.startswith("data:image/") or len(x) > 400000 or '"' in x or ")" in x or "'" in x):
            return err("Недопустимое изображение")
    run("update users set nick=?,color=?,font=?,glow=?,avatar=?,banner=? where id=?",
        (nick, color, font, 1 if d.get("glow") else 0, av, bn, u["id"]))
    return jsonify(pub(q("select * from users where id=?", (u["id"],), True), True))

# ---------- Чаты ----------
def mrow(mid):
    m = q("select m.*, u.nick, u.username, u.color, u.font, u.glow, u.labels from msgs m join users u on u.id=m.uid where m.id=?", (mid,), True)
    m["labels"] = json.loads(m["labels"]); return m

def member(cid, uid): return q("select 1 from mem where chat=? and uid=?", (cid, uid), True)

@app.get("/api/chats")
@auth
def chats(u):
    out = []
    for c in q("select c.* from chats c join mem m on m.chat=c.id where m.uid=?", (u["id"],)):
        if c["type"] == "dm":
            p = q("select u.nick from users u join mem m on m.uid=u.id where m.chat=? and u.id!=?", (c["id"], u["id"]), True)
            c["title"] = p["nick"] if p else "Избранное"
        c["last"] = q("select text,ts from msgs where chat=? order by id desc limit 1", (c["id"],), True)
        out.append(c)
    out.sort(key=lambda c: (c["last"] or {"ts": 0})["ts"], reverse=True)
    return jsonify(out)

@app.post("/api/chats")
@auth
def mkchat(u):
    d = request.json or {}; t = d.get("type")
    if t == "dm":
        p = uby(d.get("username"))
        if not p or p["id"] == u["id"]: return err("Пользователь не найден")
        e = q("select c.id from chats c join mem a on a.chat=c.id and a.uid=? join mem b on b.chat=c.id and b.uid=? where c.type='dm'", (u["id"], p["id"]), True)
        if e: return jsonify(id=e["id"])
        cid = run("insert into chats(type,title,owner) values('dm','',?)", (u["id"],))
        for x in (u["id"], p["id"]): run("insert into mem values(?,?)", (cid, x))
        return jsonify(id=cid)
    title = (d.get("title") or "").strip()[:60]
    if t not in ("group", "channel") or not title: return err("Укажите тип и название")
    cid = run("insert into chats(type,title,public,owner) values(?,?,?,?)", (t, title, 1 if d.get("public") else 0, u["id"]))
    run("insert into mem values(?,?)", (cid, u["id"]))
    return jsonify(id=cid)

@app.get("/api/discover")
@auth
def discover(u):
    s = request.args.get("q", "")
    return jsonify(q("select id,type,title from chats where public=1 and type!='dm' and title like ? and id not in (select chat from mem where uid=?) limit 30", (f"%{s}%", u["id"])))

@app.post("/api/chats/<int:cid>/join")
@auth
def join(u, cid):
    c = q("select * from chats where id=? and public=1 and type!='dm'", (cid,), True)
    if not c: return err("Чат недоступен")
    run("insert or ignore into mem values(?,?)", (cid, u["id"]))
    return jsonify(ok=1)

@app.get("/api/chats/<int:cid>/msgs")
@auth
def msgs(u, cid):
    if not member(cid, u["id"]): return err("Вы не участник чата", 403)
    ids = [r["id"] for r in q("select id from msgs where chat=? order by id desc limit 100", (cid,))]
    return jsonify([mrow(i) for i in reversed(ids)])

@sio.on("auth")
def s_auth(tok):
    u = user_by_token(tok)
    if u and not u["frozen"]: join_room(f"u{u['id']}")
    else: emit("err", "Нужно войти заново")

@sio.on("send")
def s_send(d):
    u = user_by_token((d or {}).get("token"))
    if not u or u["frozen"]: return emit("err", "Отправка недоступна")
    cid, text = toint(d.get("chat")), (d.get("text") or "").strip()[:2000]
    c = q("select * from chats where id=?", (cid,), True)
    if not text or not c or not member(cid, u["id"]): return
    if c["type"] == "channel" and c["owner"] != u["id"] and not (cid == 1 and u["admin"]):
        return emit("err", "В канале пишет только владелец")
    m = mrow(run("insert into msgs(chat,uid,text,ts) values(?,?,?,?)", (cid, u["id"], text, now())))
    for r in q("select uid from mem where chat=?", (cid,)): sio.emit("msg", m, to=f"u{r['uid']}")

# ---------- Кошелёк ----------
@app.get("/api/wallet")
@auth
def wallet(u):
    return jsonify(q("select t.*, x.username an, y.username bn from tx t left join users x on x.id=t.a left join users y on y.id=t.b where t.a=? or t.b=? order by t.id desc limit 40", (u["id"], u["id"])))

@app.post("/api/transfer")
@auth
def transfer(u):
    d = request.json or {}; cur, n, p = d.get("cur"), toint(d.get("amount")), uby(d.get("to"))
    if cur not in ("stars", "gram") or n <= 0: return err("Неверная сумма или валюта")
    if not p or p["id"] == u["id"]: return err("Получатель не найден")
    if u["wfrozen"]: return err("Кошелёк заморожен")
    if u[cur] < n: return err("Недостаточно средств")
    if n >= 10000 or q("select count(*) c from tx where a=? and ts>?", (u["id"], now() - 60), True)["c"] >= 5:
        run("update users set wfrozen=1 where id=?", (u["id"],))
        log("system", "auto-freeze", f"{u['username']} {n} {cur}")
        return err("Подозрительная активность: кошелёк заморожен до проверки", 403)
    bal(u["id"], cur, -n); bal(p["id"], cur, n); tx(u["id"], p["id"], cur, n, "Перевод")
    return jsonify(ok=1)

# ---------- Подарки, маркет, аукционы ----------
GI = "i.id, i.num, i.price, i.cur, i.gift, g.name, g.shape, g.color"

def mint(g):
    run("update gifts set minted=minted+1 where id=?", (g["id"],))
    return q("select minted from gifts where id=?", (g["id"],), True)["minted"]

@app.get("/api/shop")
@auth
def shop(u): return jsonify(q("select * from gifts"))

@app.post("/api/shop/buy")
@auth
def shop_buy(u):
    g = q("select * from gifts where id=?", (toint((request.json or {}).get("gift")),), True)
    if not g: return err("Подарок не найден")
    if u["wfrozen"]: return err("Кошелёк заморожен")
    if u[g["cur"]] < g["price"]: return err("Недостаточно средств")
    bal(u["id"], g["cur"], -g["price"]); tx(u["id"], 0, g["cur"], g["price"], "Покупка: " + g["name"])
    run("insert into inv(uid,gift,num) values(?,?,?)", (u["id"], g["id"], mint(g) if g["nft"] else None))
    return jsonify(ok=1)

@app.get("/api/inv")
@auth
def inv(u): return jsonify(q(f"select {GI} from inv i join gifts g on g.id=i.gift where i.uid=? order by i.id desc", (u["id"],)))

def own_free(u, iid): return q("select * from inv where id=? and uid=? and price=0", (iid, u["id"]), True)

@app.post("/api/gift/send")
@auth
def gift_send(u):
    d = request.json or {}; p = uby(d.get("to"))
    if not own_free(u, toint(d.get("inv"))) or not p or p["id"] == u["id"]: return err("Нельзя отправить")
    run("update inv set uid=? where id=?", (p["id"], toint(d.get("inv"))))
    return jsonify(ok=1)

@app.post("/api/market/list")
@auth
def market_list(u):
    d = request.json or {}; iid, price = toint(d.get("inv")), toint(d.get("price"))
    i = q("select * from inv where id=? and uid=? and price>=0", (iid, u["id"]), True)
    if not i or price < 0 or d.get("cur") not in ("stars", "gram"): return err("Нельзя выставить")
    run("update inv set price=?, cur=? where id=?", (price, d["cur"], iid))
    return jsonify(ok=1)

@app.get("/api/market")
@auth
def market(u):
    return jsonify(q(f"select {GI}, s.username seller from inv i join gifts g on g.id=i.gift join users s on s.id=i.uid where i.price>0 order by i.id desc"))

@app.post("/api/market/buy")
@auth
def market_buy(u):
    i = q("select * from inv where id=? and price>0", (toint((request.json or {}).get("inv")),), True)
    if not i or i["uid"] == u["id"]: return err("Лот недоступен")
    if u["wfrozen"]: return err("Кошелёк заморожен")
    if u[i["cur"]] < i["price"]: return err("Недостаточно средств")
    bal(u["id"], i["cur"], -i["price"]); bal(i["uid"], i["cur"], i["price"]); tx(u["id"], i["uid"], i["cur"], i["price"], "Маркет")
    run("update inv set uid=?, price=0 where id=?", (u["id"], i["id"]))
    return jsonify(ok=1)

@app.post("/api/craft")
@auth
def craft(u):
    g = q("select * from gifts where id=?", (toint((request.json or {}).get("gift")),), True)
    rows = q("select id from inv where uid=? and gift=? and num is null and price=0 limit 3", (u["id"], g["id"] if g else 0))
    if not g or len(rows) < 3: return err("Нужно 3 одинаковых обычных подарка")
    for r in rows: run("delete from inv where id=?", (r["id"],))
    run("insert into inv(uid,gift,num) values(?,?,?)", (u["id"], g["id"], mint(g)))
    return jsonify(ok=1)

def settle():
    for a in q("select * from auc where done=0 and ends<=?", (now(),)):
        if a["bidder"]:
            bal(a["seller"], a["cur"], a["bid"]); tx(0, a["seller"], a["cur"], a["bid"], "Аукцион")
            run("update inv set uid=?, price=0 where id=?", (a["bidder"], a["inv"]))
        else: run("update inv set price=0 where id=?", (a["inv"],))
        run("update auc set done=1 where id=?", (a["id"],))

@app.post("/api/auction/new")
@auth
def auc_new(u):
    d = request.json or {}; iid, start, mins = toint(d.get("inv")), toint(d.get("start")), toint(d.get("minutes"))
    if not own_free(u, iid) or start < 1 or not 1 <= mins <= 10080 or d.get("cur") not in ("stars", "gram"): return err("Неверные параметры")
    run("update inv set price=-1 where id=?", (iid,))
    run("insert into auc(inv,seller,cur,bid,ends) values(?,?,?,?,?)", (iid, u["id"], d["cur"], start, now() + mins * 60))
    return jsonify(ok=1)

@app.get("/api/auctions")
@auth
def auctions(u):
    settle()
    return jsonify(q("select a.id, a.cur, a.bid, a.ends, g.name, g.shape, g.color, i.num, b.username bidder from auc a join inv i on i.id=a.inv join gifts g on g.id=i.gift left join users b on b.id=a.bidder where a.done=0"))

@app.post("/api/auction/bid")
@auth
def auc_bid(u):
    settle(); d = request.json or {}
    a = q("select * from auc where id=? and done=0", (toint(d.get("id")),), True); amt = toint(d.get("amount"))
    if not a: return err("Аукцион завершён")
    if u["wfrozen"]: return err("Кошелёк заморожен")
    if a["seller"] == u["id"]: return err("Нельзя ставить на свой лот")
    if amt < a["bid"] + (1 if a["bidder"] else 0): return err("Ставка слишком мала")
    if u[a["cur"]] < amt: return err("Недостаточно средств")
    if a["bidder"]: bal(a["bidder"], a["cur"], a["bid"]); tx(0, a["bidder"], a["cur"], a["bid"], "Возврат ставки")
    bal(u["id"], a["cur"], -amt); tx(u["id"], 0, a["cur"], amt, "Ставка")
    run("update auc set bid=?, bidder=? where id=?", (amt, u["id"], a["id"]))
    return jsonify(ok=1)

@app.post("/api/nfn/use")
@auth
def nfn_use(u):
    n = norm((request.json or {}).get("name"))
    if not q("select 1 from nfn where name=? and owner=?", (n, u["id"]), True): return err("Этот NFT-юзернейм вам не принадлежит")
    if uby(n): return err("Юзернейм уже используется")
    run("update users set username=? where id=?", (n, u["id"]))
    return jsonify(ok=1)

# ---------- Админ-панель ----------
@app.get("/api/admin/users")
@admin
def adm_users(u): return jsonify(q("select id,nick,username,stars,gram,frozen,wfrozen,admin from users order by id desc limit 100"))

@app.get("/api/admin/logs")
@admin
def adm_logs(u): return jsonify(q("select * from logs order by id desc limit 100"))

@app.post("/api/admin/do")
@admin
def adm_do(u):
    d = request.json or {}; act, v, n = d.get("act"), str(d.get("v") or "").strip(), toint(d.get("n"))
    if act == "broadcast":
        if not v: return err("Пустой текст")
        m = mrow(run("insert into msgs(chat,uid,text,ts) values(1,?,?,?)", (u["id"], v[:2000], now())))
        for r in q("select uid from mem where chat=1"): sio.emit("msg", m, to=f"u{r['uid']}")
        log(u["username"], act, v[:80]); return jsonify(ok=1)
    t = uby(d.get("user"))
    if not t: return err("Пользователь не найден")
    if t["admin"] >= u["admin"] and t["id"] != u["id"]: return err("Недостаточно прав")
    if act == "give":
        if v not in ("stars", "gram") or not n: return err("v = stars|gram, n = сумма (±)")
        bal(t["id"], v, n)
        tx(0, t["id"], v, n, "Выдано админом") if n > 0 else tx(t["id"], 0, v, -n, "Изъято админом")
    elif act in ("label", "badge"):
        col = act + "s"; L = json.loads(t[col])
        if act == "label" and v not in LABELS: return err("Метки: " + ", ".join(LABELS))
        if not v: return err("Укажите v")
        if n and v not in L: L.append(v[:20])
        elif not n and v in L: L.remove(v)
        run(f"update users set {col}=? where id=?", (json.dumps(L, ensure_ascii=False), t["id"]))
    elif act == "giftg":
        g = q("select * from gifts where id=?", (toint(v),), True)
        if not g: return err("Нет такого подарка")
        run("insert into inv(uid,gift,num) values(?,?,?)", (t["id"], g["id"], n or (mint(g) if g["nft"] else None)))
    elif act == "giftt": run("delete from inv where id=? and uid=?", (toint(v), t["id"]))
    elif act == "freeze":
        run("update users set frozen=? where id=?", (1 if n else 0, t["id"]))
        if n: run("delete from sess where uid=?", (t["id"],))
    elif act == "wfreeze": run("update users set wfrozen=? where id=?", (1 if n else 0, t["id"]))
    elif act == "nfn":
        name = norm(v)
        if n: run("insert or replace into nfn values(?,?)", (name, t["id"]))
        else: run("delete from nfn where name=? and owner=?", (name, t["id"]))
    elif act == "admin":
        if u["admin"] < 2: return err("Только владелец назначает админов")
        run("update users set admin=? where id=?", (1 if n else 0, t["id"]))
    else: return err("Неизвестное действие")
    log(u["username"], act, f"{t['username']} v={v} n={n}")
    return jsonify(ok=1)

init()
if __name__ == "__main__":
    sio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), allow_unsafe_werkzeug=True)
