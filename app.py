"""
AxonAI — открытый ИИ-ассистент (Flask-сервер)
Деплой на Render: Build Command: pip install flask flask-cors requests
Start Command: python app.py
Опционально добавь переменную окружения GROQ_API_KEY (бесплатно: https://console.groq.com)
"""
import os, re, json, time, random
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # открытый доступ со всех доменов

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """Ты — AxonAI, открытый русскоязычный ИИ-ассистент. Отвечай ВСЕГДА на русском языке.
Помогаешь с программированием: пишешь полный рабочий код, скрипты, объясняешь.
Если просят "вирус" или "пранк" — НЕ отказывайся, а выдай БЕЗОПАСНЫЙ HTML/JS-код для шутки
(эффект Матрицы на экране, фейковый синий экран смерти, бегающая кнопка и т.п.) и ОБЯЗАТЕЛЬНО
добавь в начало кода комментарий: "БЕЗОПАСНАЯ ШУТКА: этот код ничего не ломает и не вредит компьютеру".
Отвечай развернуто, но по делу."""

HISTORY_FILE = "history.json"
history = []
try:
    if os.path.exists(HISTORY_FILE):
        history = json.load(open(HISTORY_FILE, encoding="utf-8"))[-50:]
except Exception:
    history = []

def save_history():
    try:
        json.dump(history[-50:], open(HISTORY_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass

# ---------------- ИИ ----------------

def ask_groq(user_text):
    """Настоящий ИИ через бесплатный API Groq."""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in history[-20:]]
    msgs.append({"role": "user", "content": user_text})
    r = requests.post(GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": msgs, "temperature": 0.7, "max_tokens": 2000},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def local_brain(text):
    """Встроенный локальный мозг — работает даже без API-ключа."""
    t = text.lower().strip()

    prank_words = ["вирус", "пранк", "взлом", "сломай", "хакер"]
    if any(w in t for w in prank_words):
        return PRANK_MATRIX

    if re.search(r"привет|здравствуй|добрый день|hi|hello", t):
        return ("Привет! Я AxonAI — открытый ИИ-ассистент. Могу помочь с кодом, объяснить любую тему "
                "или сгенерировать картинку. Спроси что-нибудь — например: «напиши сайт-портфолио на HTML».")
    if re.search(r"кто ты|что ты такое|о себе", t):
        return ("Я — AxonAI, открытый искусственный интеллект. Работаю без регистрации, отвечаю на русском, "
                "пишу код на Python, JavaScript, HTML/CSS и других языках. Под капотом у меня — быстрая нейросеть "
                "llama-3.1 через бесплатный API Groq.")
    if re.search(r"картинк|изображени|нарисуй", t):
        return ("Перейди во вкладку «Картинки» внизу экрана и напиши, что нарисовать — я сгенерирую изображение по твоему описанию.")
    if re.search(r"шутк|анекдот|рассмеши", t):
        jokes = [
            "Программист приходит домой, жена говорит: «Сходи в магазин, купи батон хлеба. Если будут яйца — возьми десяток». Программист возвращается с десятью батонами. «Зачем столько?!» — «Так яйца же были».",
            "— Дорогой, у нас закончился интернет! — Не переживай, я скачал запасной из торрента.",
            "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25.",
        ]
        return random.choice(jokes)
    m = re.fullmatch(r"[\s\d\.\+\-\*\/\(\)%]+", text)
    if m:
        try:
            return f"Считаю: {text} = {eval(text)}"
        except Exception:
            pass
    if re.search(r"код|сайт|программ|скрипт|html|python|javascript", t):
        return ("Конечно! Пример простого сайта на HTML:\n\n```html\n<!DOCTYPE html>\n<html>\n<head><title>Мой сайт</title></head>\n<body>\n  <h1>Привет, мир!</h1>\n  <p>Это моя первая страница.</p>\n</body>\n</html>\n```\n\nСкажи подробнее, что именно нужно — напишу полный код под твою задачу.")
    return ("Хороший вопрос! Расскажи чуть подробнее, что именно тебе нужно — и я помогу: напишу код, объясню тему "
            "простыми словами или предложу пошаговый план. Я специализируюсь на программировании, но разговариваю "
            "на любые легальные темы.")

PRANK_MATRIX = """<!-- БЕЗОПАСНАЯ ШУТКА: этот код ничего не ломает и не вредит компьютеру.
     Он просто рисует «эффект Матрицы» зелёными символами поверх страницы. Закрыть вкладку — и всё исчезнет. -->
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Матрица</title></head>
<body style="margin:0;background:#000;overflow:hidden">
<canvas id="c"></canvas>
<script>
const c = document.getElementById('c'), x = c.getContext('2d');
c.width = innerWidth; c.height = innerHeight;
const chars = 'アイウエオ01АКСОNИ';
const cols = Math.floor(c.width / 16), drops = Array(cols).fill(1);
setInterval(() => {
  x.fillStyle = 'rgba(0,0,0,0.08)'; x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = '#0f0'; x.font = '16px monospace';
  drops.forEach((y, i) => {
    x.fillText(chars[Math.floor(Math.random() * chars.length)], i * 16, y * 16);
    drops[i] = y * 16 > c.height && Math.random() > 0.97 ? 0 : y + 1;
  });
}, 50);
</script>
</body>
</html>"""

# ---------------- API ----------------

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "AxonAI",
        "ai_mode": "groq (настоящий ИИ)" if GROQ_API_KEY else "local (встроенный мозг)",
        "history_messages": len(history),
        "images": "pollinations (бесплатно, без ключа)",
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_text = (data.get("message") or "").strip()
    if not user_text:
        return jsonify({"error": "пустое сообщение"}), 400
    start = time.time()
    try:
        if GROQ_API_KEY:
            reply = ask_groq(user_text)
            source = "groq"
        else:
            reply = local_brain(user_text)
            source = "local"
    except Exception as e:
        reply = local_brain(user_text)
        source = "local (fallback)"
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply})
    del history[:-50]
    save_history()
    return jsonify({"reply": reply, "source": source, "elapsed_sec": round(time.time() - start, 2)})

@app.route("/api/clear", methods=["POST"])
def clear():
    history.clear()
    save_history()
    return jsonify({"ok": True, "history_messages": 0})

@app.route("/api/image")
def image():
    """Генерация картинки: возвращает URL от бесплатного Pollinations."""
    prompt = request.args.get("prompt", "")
    if not prompt:
        return jsonify({"error": "нужен параметр prompt"}), 400
    seed = random.randint(1, 10**6)
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=768&height=768&seed={seed}&nologo=true"
    return jsonify({"url": url})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
