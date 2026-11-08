import os
import re
import json
import time
import sqlite3
import requests
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_file, Response, stream_with_context
from deep_translator import GoogleTranslator
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "woxai.db")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "woxai-secret")

# --- Настройки ---
SYSTEM = "Ты woxAI — умный помощник. Отвечай на любые вопросы."
MODELS = {
    "Anox-Core": {"url": "https://api.openai.com/v1/chat/completions", "key": os.getenv("OPENAI_API_KEY"), "model": "gpt-4o"},
    "Onyx-Brain": {"url": "https://api.anthropic.com/v1/messages", "key": os.getenv("ANTHROPIC_API_KEY"), "model": "claude-3-5-sonnet-20240620"},
    "Troll-Fast": {"url": "https://api.groq.com/openai/v1/chat/completions", "key": os.getenv("GROQ_API_KEY"), "model": "llama-3.3-70b-versatile"},
}

# --- База данных ---
def q(sql, args=(), write=False):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.execute(sql, args)
    out = cur.lastrowid if write else [dict(r) for r in cur.fetchall()]
    con.commit()
    con.close()
    return out

def init_db():
    q("CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, created REAL)", write=True)
    q("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, role TEXT, model TEXT, content TEXT, created REAL)", write=True)
    q("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, created REAL)", write=True)

# --- Бесплатные генераторы (без ключей) ---
def generate_image(prompt):
    """Генерация картинки через Pollinations (бесплатно)"""
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    return {"url": url, "prompt": prompt}

def search_duckduckgo(query):
    """Поиск картинок через DuckDuckGo (бесплатно)"""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().images(query, max_results=5))
        return [{"title": r.get("title"), "image": r.get("image")} for r in results]
    except Exception:
        return []

# --- Парсинг и перевод ---
def parse_website(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]): tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        return text[:5000]
    except Exception:
        return ""

def translate_text(text, target="en"):
    try:
        return GoogleTranslator(source="auto", target=target).translate(text[:4000])
    except Exception:
        return text

# --- API ИИ ---
def ask_ai(name, messages):
    cfg = MODELS.get(name)
    if not cfg or not cfg["key"]:
        return f"⚠️ {name}: нет ключа"
    try:
        if name == "Onyx-Brain":
            r = requests.post(cfg["url"], headers={"x-api-key": cfg["key"], "anthropic-version": "2023-06-01"},
                              json={"model": cfg["model"], "max_tokens": 2048, "system": SYSTEM, "messages": messages}, timeout=60)
            return "".join(b.get("text", "") for b in r.json().get("content", []))
        else:
            r = requests.post(cfg["url"], headers={"Authorization": f"Bearer {cfg['key']}"},
                              json={"model": cfg["model"], "messages": [{"role": "system", "content": SYSTEM}] + messages}, timeout=60)
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ {name}: {e}"

# --- Маршруты ---
@app.get("/")
def index():
    return send_file(os.path.join(BASE, "index.html"))

@app.post("/api/register")
def register():
    d = request.get_json()
    username, password = d.get("username"), d.get("password")
    if not username or not password: return jsonify(error="Заполни все поля"), 400
    if q("SELECT id FROM users WHERE username=?", (username,)): return jsonify(error="Ник занят"), 409
    q("INSERT INTO users(username, password_hash, created) VALUES(?,?,?)", (username, generate_password_hash(password), time.time()), write=True)
    return jsonify(ok=True)

@app.post("/api/login")
def login():
    d = request.get_json()
    user = q("SELECT * FROM users WHERE username=?", (d.get("username"),))
    if not user or not check_password_hash(user[0]["password_hash"], d.get("password", "")):
        return jsonify(error="Неверный логин или пароль"), 401
    return jsonify(ok=True, username=user[0]["username"])

@app.post("/api/chat")
def chat():
    d = request.get_json()
    text = d.get("message", "").strip()
    model = d.get("model", "Troll-Fast")
    if not text: return jsonify(error="Пустое сообщение"), 400
    
    # Проверка на генерацию картинки
    if text.lower().startswith("нарисуй"):
        prompt = text[7:].strip()
        img = generate_image(prompt)
        return jsonify(reply=f"![{prompt}]({img['url']})")
    
    # Иначе — обычный ответ ИИ
    reply = ask_ai(model, [{"role": "user", "content": text}])
    return jsonify(reply=reply)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
