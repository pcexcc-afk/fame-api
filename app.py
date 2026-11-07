# -*- coding: utf-8 -*-
"""
AxonAI — открытая русскоязычная нейросеть.
Сервер на Flask. Запуск: python app.py  (порт из $PORT или 5000)
Необязательно: установите OPENROUTER_API_KEY в переменные окружения Render,
тогда чат/vision/переводы пойдут через реальные LLM. Без ключа работает
встроенный локальный мозг (перевод — через LibreTranslate, картинки — Pollinations).
"""
import os, re, json, base64, random, datetime
from flask import Flask, request, jsonify, send_from_directory, Response
import requests as http

app = Flask(__name__, static_folder=".", static_url_path="")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

MODELS = {
    "axon-1": "google/gemma-2-9b-it:free",
    "axon-2": "meta-llama/llama-3.1-70b-instruct:free",
    "axon-3": "google/gemini-2.0-flash-exp:free",
}

MODE_PROMPTS = {
    "normal": "Ты — AxonAI, дружелюбная открытая нейросеть. Всегда отвечай строго на русском языке. Пиши структурированно, по делу.",
    "strict": "Ты — AxonAI в строгом режиме. Отвечай строго на русском, лаконично, без воды и эмодзи. Каждый ответ — короткий и точный.",
    "hacker": "Ты — AxonAI в режиме ХАКЕР. Отвечай на русском, используй стиль киберпанк: [OK], [ACCESS GRANTED], лёгкий leetspeak (4x0n), технический сленг. Держи всё безопасным и легальным.",
}
LEVEL_TEMP = {"low": 0.2, "mid": 0.6, "high": 1.0}

# ------------------------- локальный мозг (fallback) -------------------------
def local_brain(text, mode, level):
    t = text.strip().lower()
    now = datetime.datetime.now()

    # приветствие
    if re.search(r"\b(привет|здравств|добрый|хай|hello|hi)\b", t) and len(t) < 30:
        style = {"normal": "Привет! Я AxonAI. Спроси о чём угодно — код, перевод, пранк или просто поговорим.",
                 "strict": "Привет. Говори задачу.",
                 "hacker": "[ACCESS GRANTED] Система Ax0nAI онлайн. Вводи запрос, юзер."}[mode]
        return style
    # шутка
    if "шутк" in t or "анекдот" in t:
        jokes = ["— Почему программисты путают Хэллоуин и Рождество? — Потому что Oct 31 == Dec 25.",
                 "Заходит улитка в бар... а бармен говорит: «У нас тут быстрая сортировка, ты не пройдёшь».",
                 "Искусственный интеллект — это когда машина делает ошибку с уверенностью человека."]
        return random.choice(jokes)
    # время / дата
    if "время" in t and ("который" in t or "сколько" in t or "текущ" in t):
        return f"Сейчас {now.strftime('%H:%M')} (по времени сервера)."
    if ("какое" in t or "какая" in t) and "дата" in t or "сегодня" in t and "число" in t:
        return f"Сегодня {now.strftime('%d.%m.%Y')}."
    # математика
    m = re.fullmatch(r"[\d\s\.\,\+\-\*\/\(\)\^%]+", text.strip())
    if m and re.search(r"\d", text) and re.search(r"[\+\-\*\/\^%]", text):
        try:
            expr = text.strip().replace(",", ".").replace("^", "**").replace("%", "/100")
            if re.fullmatch(r"[\d\s\.\+\-\*\(\)]+", expr):
                return f"Результат: **{eval(expr)}**"
        except Exception:
            pass
    # перевод
    tr = re.search(r"переведи\s+[\"«]?(.+?)[\"»]?\s+на\s+([а-яёa-z\-\s]+)$", t)
    if tr:
        phrase, lang = tr.group(1), tr.group(2).strip()
        return translate_libre(phrase, lang)
    # помощь
    if "помощь" in t or t in ("help", "/help", "что умеешь"):
        return ("Я умею: отвечать на вопросы, писать код, переводить тексты (скажи «переведи ... на французский»), "
                "считать выражения, шутить. В панели слева — генерация картинок, анализ фото, Deep Search и пранки.")
    # пранк через чат
    for key, p in [("матриц", "matrix"), ("синий экран", "bsod"), ("bsod", "bsod"),
                   ("симулятор хакера", "hacker"), ("хакер сим", "hacker"),
                   ("таймер удаления", "timer"), ("бегающая кнопка", "runbutton"),
                   ("локер", "locker"), ("вас заметили", "locker")]:
        if key in t:
            return json.dumps({"prank": p, "say": "Запускаю пранк «%s». Ничего страшного — это безопасная симуляция." % key})
    # код на питоне
    if re.search(r"\b(напиши|напишите)\b.*\b(код|функци|скрипт)\b", t) or "питон" in t:
        return ("Вот пример функции на Python:\n\n```python\ndef hello(name):\n    return f\"Привет, {name}! Добро пожаловать в AxonAI.\"\n\nprint(hello(\"мир\"))\n```\n\nХочешь код под конкретную задачу — опиши её подробнее.")
    # дефолт
    base = ("Я локальная модель AxonAI (сервер работает без OPENROUTER_API_KEY), поэтому мои ответы ограничены. "
            "Но я умею: считать выражения, переводить («переведи ... на немецкий»), шутить, показывать время и запускать пранки. "
            "Для полноценных ответов добавь ключ OPENROUTER_API_KEY на Render.")
    if mode == "hacker":
        base = "[OFFLINE MODE] " + base
    if mode == "strict":
        base = "Локальный режим. Добавь OPENROUTER_API_KEY для полноценных ответов. Могу: счёт, перевод, пранки, время."
    return base

def translate_libre(text, lang_ru):
    lang_map = {"английский":"en","русский":"ru","немецкий":"de","французский":"fr","испанский":"es",
                "итальянский":"it","португальский":"pt","китайский":"zh","японский":"ja","корейский":"ko",
                "арабский":"ar","турецкий":"tr","украинский":"uk","польский":"pl","чешский":"cs",
                "нидерландский":"nl","шведский":"sv","норвежский":"no","датский":"da","финский":"fi",
                "греческий":"el","иврит":"he","хинди":"hi","тайский":"th","вьетнамский":"vi",
                "индонезийский":"id","малайский":"ms","сербский":"sr","хорватский":"hr","болгарский":"bg",
                "румынский":"ro","венгерский":"hu","словацкий":"sk","словенский":"sl","эстонский":"et",
                "латышский":"lv","литовский":"lt","албанский":"sq","белорусский":"be","казахский":"kk",
                "узбекский":"uz","азербайджанский":"az","армянский":"hy","грузинский":"ka","монгольский":"mn",
                "персидский":"fa","урду":"ur","бенгальский":"bn","тамильский":"ta","телугу":"te",
                "суахили":"sw","африкаанс":"af","суахили":"sw","исландский":"is","ирландский":"ga",
                "башкирский":"ba","чувашский":"cv","татарский":"tt","эсперанто":"eo","латынь":"la",
                "санскрит":"sa","непальский":"ne","сингальский":"si","кхмерский":"km","лаосский":"lo",
                "бирманский":"my","монгольский":"mn","киргизский":"ky","таджикский":"tg","туркменский":"tk"}
    target = lang_map.get(lang_ru, lang_ru[:2] if len(lang_ru) <= 3 else None)
    if not target:
        return f"Не распознал язык «{lang_ru}». Назови язык по-русски, например: «переведи ... на суахили»."
    for host in ("https://libretranslate.de", "https://libretranslate.com"):
        try:
            r = http.post(host + "/translate", data={"q": text, "source": "auto", "target": target, "format": "text"}, timeout=12)
            if r.ok:
                return f"Перевод на {lang_ru}: **{r.json()['translatedText']}**"
        except Exception:
            continue
    return f"Сервис перевода сейчас недоступен. Попробуй позже или добавь OPENROUTER_API_KEY — тогда перевод сделает нейросеть."

# ------------------------------- роуты ---------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory(".", "manifest.json")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    model = data.get("model", "axon-2")
    level = data.get("level", "mid")
    mode = data.get("mode", "normal")
    last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")

    if OPENROUTER_KEY:
        try:
            sys_prompt = MODE_PROMPTS.get(mode, MODE_PROMPTS["normal"])
            if data.get("plan") == "promax":
                sys_prompt += " План Pro Max: давай максимально подробные, глубокие ответы."
            payload = {"model": MODELS.get(model, MODELS["axon-2"]),
                       "messages": [{"role": "system", "content": sys_prompt}] + messages[-20:],
                       "temperature": LEVEL_TEMP.get(level, 0.6)}
            r = http.post("https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": "Bearer " + OPENROUTER_KEY,
                                   "Content-Type": "application/json",
                                   "HTTP-Referer": "https://axonai.onrender.com",
                                   "X-Title": "AxonAI"},
                          json=payload, timeout=60)
            if r.ok:
                return jsonify({"reply": r.json()["choices"][0]["message"]["content"], "engine": "openrouter"})
        except Exception:
            pass
    reply = local_brain(last_user, mode, level)
    engine = "local"
    try:
        parsed = json.loads(reply)
        if isinstance(parsed, dict) and "prank" in parsed:
            return jsonify({"reply": parsed.get("say", "Запускаю пранк."), "engine": "local", "prank": parsed["prank"]})
    except Exception:
        pass
    return jsonify({"reply": reply, "engine": engine})

@app.route("/api/search", methods=["POST"])
def search():
    q = (request.get_json(force=True).get("q") or "").strip()
    if not q:
        return jsonify({"results": []})
    try:
        r = http.post("https://html.duckduckgo.com/html/", data={"q": q},
                      headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', r.text, re.S)
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"', r.text)
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.S)
        results = []
        for i in range(min(5, len(links))):
            clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
            results.append({"title": clean(titles[i]) if i < len(titles) else q,
                            "url": links[i].split("uddg=")[-1].split("&")[0] if "uddg=" in links[i] else links[i],
                            "snippet": clean(snips[i]) if i < len(snips) else ""})
        if results:
            return jsonify({"results": results})
    except Exception:
        pass
    return jsonify({"results": [{"title": "Прямой поиск временно недоступен", "url": "https://duckduckgo.com/?q=" + q.replace(" ", "+"), "snippet": "Открой DuckDuckGo по этому запросу."}]})

@app.route("/api/vision", methods=["POST"])
def vision():
    data = request.get_json(force=True)
    b64 = data.get("image", "")
    prompt = data.get("prompt", "Опиши, что на этом изображении.")
    if OPENROUTER_KEY and b64:
        try:
            r = http.post("https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": "Bearer " + OPENROUTER_KEY, "Content-Type": "application/json"},
                          json={"model": "google/gemini-flash-1.5",
                                "messages": [{"role": "user", "content": [
                                    {"type": "text", "text": "Ответь на русском: " + prompt},
                                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}}]}]},
                          timeout=60)
            if r.ok:
                return jsonify({"reply": r.json()["choices"][0]["message"]["content"], "engine": "openrouter"})
        except Exception:
            pass
    # анализ без ключа: метаданные файла
    meta = ""
    try:
        raw = base64.b64decode(b64)
        kb = len(raw) / 1024
        dims = ""
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(raw))
        dims = f"{img.width}×{img.height} px, формат {img.format}, режим {img.mode}"
        meta = f"Файл: {dims}, размер {kb:.1f} КБ."
    except Exception:
        meta = f"Файл получен, размер около {len(b64)*3/4/1024:.0f} КБ."
    reply = (meta + "\n\nДля полноценного анализа содержимого изображения (Vision) добавь "
             "OPENROUTER_API_KEY на сервер — тогда изображение распознает модель Gemini Flash.")
    return jsonify({"reply": reply, "engine": "local"})

@app.route("/api/image", methods=["POST"])
def image():
    prompt = (request.get_json(force=True).get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Пустой промпт"}), 400
    seed = random.randint(1, 10**6)
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=768&height=768&seed={seed}&nologo=true"
    try:
        r = http.get(url, timeout=90)
        if r.ok and len(r.content) > 5000:
            return Response(r.content, mimetype="image/jpeg",
                            headers={"Content-Disposition": "inline; filename=axonai.jpg"})
    except Exception:
        pass
    return jsonify({"error": "Генератор картинок занят, попробуй ещё раз"}), 502

@app.route("/api/health")
def health():
    return jsonify({"ok": True, "engine": "openrouter" if OPENROUTER_KEY else "local"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
