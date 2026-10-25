from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Список сайтов для проверки
SITES = {
    "GitHub": "https://github.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "YouTube": "https://www.youtube.com/@{}",
    "Telegram": "https://t.me/{}"
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

    # ТУТ ПОКА ЗАГЛУШКА (потом заменишь на свою базу)
    is_scam = False
    is_fake = False
    scam_reason = ""
    fake_reason = ""

    if username in ["bad_user", "scammer"]:
        is_scam = True
        scam_reason = "Кинул на 500 звезд"
    elif username in ["0ksy", "bully_fake"]:
        is_fake = True
        fake_reason = "Копия профиля"

    return jsonify({
        "username": username,
        "is_scam": is_scam,
        "scam_reason": scam_reason,
        "is_fake": is_fake,
        "fake_reason": fake_reason,
        "found_sites": found_sites
    })

if __name__ == '__main__':
    # Render сам подставит нужный порт
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
