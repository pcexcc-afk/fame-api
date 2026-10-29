from flfrom flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import whois
import phonenumbers
from phonenumbers import geocoder, carrier
import re

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "API работает!"

# 1. WHOIS (Информация о домене)
@app.route('/api/whois', methods=['POST'])
def get_whois():
    data = request.json or {}
    domain = data.get('domain', '').strip()
    if not domain: return jsonify({"error": "Пустой домен"}), 400
    
    try:
        w = whois.whois(domain)
        return jsonify({
            "domain": domain,
            "registrar": w.registrar or "Скрыто",
            "creation_date": str(w.creation_date) if w.creation_date else "Неизвестно",
            "expiration_date": str(w.expiration_date) if w.expiration_date else "Неизвестно",
            "country": w.country or "Неизвестно"
        })
    except Exception as e:
        return jsonify({"error": "Не удалось получить данные WHOIS"}), 500

# 2. Анализ IP (Геолокация)
@app.route('/api/ip', methods=['POST'])
def get_ip():
    data = request.json or {}
    ip = data.get('ip', '').strip()
    if not ip: return jsonify({"error": "Пустой IP"}), 400
    
    try:
        # Используем бесплатный API ip-api.com
        r = requests.get(f"http://ip-api.com/json/{ip}?lang=ru", timeout=5)
        res = r.json()
        if res.get('status') == 'success':
            return jsonify({
                "ip": ip,
                "country": res.get('country', 'Неизвестно'),
                "city": res.get('city', 'Неизвестно'),
                "isp": res.get('isp', 'Неизвестно'),
                "timezone": res.get('timezone', 'Неизвестно')
            })
        else:
            return jsonify({"error": "IP не найден"}), 404
    except Exception as e:
        return jsonify({"error": "Ошибка запроса"}), 500

# 3. Анализ Номера Телефона
@app.route('/api/phone', methods=['POST'])
def get_phone():
    data = request.json or {}
    phone = data.get('phone', '').strip()
    if not phone: return jsonify({"error": "Пустой номер"}), 400

    try:
        # Добавляем плюс, если его нет
        if not phone.startswith('+'):
            phone = '+' + phone
            
        parsed = phonenumbers.parse(phone, None)
        
        if not phonenumbers.is_valid_number(parsed):
            return jsonify({"error": "Неверный формат номера"}), 400

        return jsonify({
            "phone": phone,
            "country": geocoder.description_for_number(parsed, "ru") or "Неизвестно",
            "operator": carrier.name_for_number(parsed, "ru") or "Неизвестно",
            "type": "Мобильный" if phonenumbers.number_type(parsed) == 1 else "Другой"
        })
    except Exception as e:
        return jsonify({"error": "Ошибка обработки номера"}), 500

# 4. Проверка Email (Имитация утечек, т.к. HIBP требует платный ключ)
@app.route('/api/email', methods=['POST'])
def get_email():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Неверный формат email"}), 400

    # Тут мы просто имитируем базу утечек для примера
    leaks = []
    if "test" in email or "admin" in email:
        leaks = ["Adobe (2013)", "Canva (2019)", "LinkedIn (2021)"]
    elif "mail.ru" in email:
        leaks = ["База mail.ru (2022)"]
    
    return jsonify({
        "email": email,
        "status": "Найден в утечках" if leaks else "Утечек не найдено",
        "leaks": leaks
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
