from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SITES = {
    "GitHub": "https://github.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "YouTube": "https://www.youtube.com/@{}",
    "Telegram": "https://t.me/{}"
}

# Временная база в памяти (пока сервер работает)
# Для постоянного хранения нужна настоящая база данных, но для теста сойдет
fake_db = {
    "scam": ["bad_user", "scammer"],
    "fake": ["0ksy", "bully_fake"],
    "fame": ["doctor", "admin"],
    "balances": {}
}

@app.route('/')
def home():
    return "API работает!"

@app.route('/api/check', methods=['POST'])
def check():
    data = request.json
    username = data.get('username', '').lower().replace('@', '')
    
    if not username:
        return jsonify({"error": "Введи ник"}), 400

    found_sites = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for name, url in SITES.items():
        try:
            r = requests.get(url.format(username), headers=headers, timeout=3)
            if r.status_code == 200 and "Page not found" not in r.text:
                found_sites.append(name)
        except:
            pass

    is_scam = username in fake_db["scam"]
    is_fake = username in fake_db["fake"]

    return jsonify({
        "username": username,
        "is_scam": is_scam,
        "scam_reason": "Найден в базе" if is_scam else "",
        "is_fake": is_fake,
        "fake_reason": "Найден в базе" if is_fake else "",
        "found_sites": found_sites
    })

# ==================== АДМИНСКИЕ КОМАНДЫ С САЙТА ====================

@app.route('/api/admin/action', methods=['POST'])
def admin_action():
    data = request.json
    action = data.get('action')
    target = data.get('target', '').lower().replace('@', '')
    value = data.get('value')

    if action == 'add_mark':
        if value not in fake_db:
            fake_db[value] = []
        if target not in fake_db[value]:
            fake_db[value].append(target)
        return jsonify({"status": "ok", "msg": f"Метка {value} добавлена для {target}"})

    elif action == 'remove_mark':
        if value in fake_db and target in fake_db[value]:
            fake_db[value].remove(target)
        return jsonify({"status": "ok", "msg": f"Метка {value} убрана у {target}"})

    elif action == 'balance':
        fake_db["balances"][target] = fake_db["balances"].get(target, 0) + int(value)
        return jsonify({"status": "ok", "msg": f"Баланс {target} увеличен на {value}"})

    elif action == 'ban':
        if target not in fake_db["scam"]:
            fake_db["scam"].append(target)
        return jsonify({"status": "ok", "msg": f"Пользователь {target} забанен"})

    return jsonify({"status": "error", "msg": "Неизвестное действие"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
