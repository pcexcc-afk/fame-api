from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import hashlib
import os

app = Flask(__name__)
CORS(app)
DB_FILE = 'crushgram.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Таблица юзеров (с паролем)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT, password TEXT, is_admin INTEGER DEFAULT 0
    )""")
    # Таблица кодов для входа
    c.execute("""CREATE TABLE IF NOT EXISTS auth_codes (
        phone TEXT PRIMARY KEY, code TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# --- 1. ЗАПРОС КОДА ---
@app.route('/api/auth/request_code', methods=['POST'])
def request_code():
    data = request.json
    phone = data.get('phone')
    if not phone: return jsonify({"success": False, "error": "Введите номер"}), 400
    
    code = str(random.randint(1000, 9999))
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO auth_codes (phone, code) VALUES (?, ?)", (phone, code))
    conn.commit()
    conn.close()
    
    # ВРЕМЕННО: Отдаем код на сайт (потом уберем в бота)
    return jsonify({"success": True, "test_code": code})

# --- 2. ПРОВЕРКА КОДА И ВХОД ---
@app.route('/api/auth/verify_code', methods=['POST'])
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
        
    # Проверяем, есть ли юзер с паролем
    c.execute("SELECT * FROM users WHERE id = ?", (phone,))
    user = c.fetchone()
    
    if user and user['password']:
        # Если пароль есть - просим его ввести
        conn.close()
        return jsonify({"success": True, "require_password": True})
    else:
        # Если пароля нет - просим создать
        conn.close()
        return jsonify({"success": True, "require_password": False})

# --- 3. СОЗДАНИЕ ПАРОЛЯ (Первый раз) ---
@app.route('/api/auth/create_password', methods=['POST'])
def create_password():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    
    # Хэшируем пароль (для безопасности)
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (id, name, password) VALUES (?, ?, ?)", (phone, "Игрок", hashed_pw))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Пароль создан"})

# --- 4. ВХОД ПО ПАРОЛЮ (Второй раз) ---
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    password = data.get('password')
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ? AND password = ?", (phone, hashed_pw))
    user = c.fetchone()
    conn.close()
    
    if user:
        return jsonify({"success": True, "user": {"id": user['id'], "name": user['name']}})
    else:
        return jsonify({"success": False, "error": "Неверный пароль (или пишите в поддержку)"}), 401

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
