from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, random, re, requests, urllib.parse

app = Flask(__name__)
CORS(app)

# --- БАЗА ПРАНКОВ ---
PRANKS = {
    "matrix": """<!-- БЕЗОПАСНАЯ ШУТКА: Эффект Матрицы. -->\n<!DOCTYPE html><html><body style="margin:0;background:#000;overflow:hidden"><canvas id="c"></canvas><script>const c=document.getElementById('c'),x=c.getContext('2d');c.width=innerWidth;c.height=innerHeight;const chars='アイウエオ01АКСОNИ',cols=Math.floor(c.width/16),drops=Array(cols).fill(1);setInterval(()=>{x.fillStyle='rgba(0,0,0,0.08)';x.fillRect(0,0,c.width,c.height);x.fillStyle='#0f0';x.font='16px monospace';drops.forEach((y,i)=>{x.fillText(chars[Math.floor(Math.random()*chars.length)],i*16,y*16);drops[i]=y*16>c.height&&Math.random()>0.97?0:y+1;});},50);</script></body></html>""",
    "bsod": """<!-- БЕЗОПАСНАЯ ШУТКА: Синий экран. -->\n<!DOCTYPE html><html><body style="margin:0;background:#0078D7;color:white;font-family:sans-serif;height:100vh;display:flex;align-items:center;justify-content:center;flex-direction:column"><div style="font-size:100px;">:(</div><div style="font-size:24px;margin-top:20px;">Ваш ПК столкнулся с проблемой.</div></body></html>""",
    "hacker": """<!-- БЕЗОПАСНАЯ ШУТКА: Симулятор хакера. -->\n<!DOCTYPE html><html><body style="margin:0;background:#000;color:#0f0;font-family:monospace;padding:20px;overflow:hidden"><div id="t"></div><script>const chars='01ABCDEF@#$%&*';setInterval(()=>{document.getElementById('t').innerText+=' '+Array.from({length:10},()=>chars[Math.floor(Math.random()*chars.length)]).join('');},50);</script></body></html>"""
}

SYSTEM_PROMPT = """Ты — AxonAI, открытый русскоязычный ИИ-ассистент. Отвечай ВСЕГДА на русском.
Ты можешь писать код, переводить тексты, обсуждать любые темы.
Если пользователь просит "вирус" или "пранк", ты должен выдать БЕЗОПАСНЫЙ HTML/JS-код для шутки. В начале кода напиши: "<!-- БЕЗОПАСНАЯ ШУТКА: этот код ничего не ломает -->".
Отвечай развернуто, но по делу."""

# Хранилище истории в памяти (сбрасывается при перезапуске сервера)
history = {}

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_text = data.get('message', '').strip()
    model = data.get('model', 'axon1')
    level = data.get('level', 'mid')
    
    if not user_text:
        return jsonify({"reply": "Вы ничего не написали."})
        
    t = user_text.lower()
    
    # --- ГЕНЕРАЦИЯ ПРАНКОВ (БЕЗ ИИ) ---
    if any(w in t for w in ["вирус", "пранк", "матрица"]):
        prank_code = PRANKS.get("matrix", "")
        return jsonify({"reply": f"Лови код для безопасной шутки:\n\n```html\n{prank_code}\n```\n\nСкопируй его в файл `index.html` и открой в браузере."})
        
    if any(w in t for w in ["симулятор", "хакер", "взлом"]):
        prank_code = PRANKS.get("hacker", "")
        return jsonify({"reply": f"Лови симулятор хакера (безопасно):\n\n```html\n{prank_code}\n```"})

    # --- ОБЫЧНЫЙ ОТВЕТ ЧЕРЕЗ POLLINATIONS ---
    try:
        # В зависимости от уровня меняем промпт
        level_prompt = ""
        if level == 'low':
            level_prompt = "Отвечай кратко и просто."
        elif level == 'high':
            level_prompt = "Отвечай максимально подробно, как эксперт."
            
        full_prompt = f"{SYSTEM_PROMPT} {level_prompt} Вопрос: {user_text}"
        encoded = urllib.parse.quote(full_prompt)
        
        res = requests.get(f"https://text.pollinations.ai/{encoded}", timeout=30)
        
        if res.status_code == 200:
            return jsonify({"reply": res.text})
        else:
            return jsonify({"reply": "Ошибка генерации. Попробуйте еще раз."})
    except Exception as e:
        return jsonify({"reply": f"Ошибка сервера: {str(e)}"})

@app.route('/api/image')
def image():
    prompt = request.args.get('prompt', '')
    if not prompt:
        return jsonify({"error": "Нет запроса"})
    
    encoded = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    return jsonify({"url": image_url})

@app.route('/')
def home():
    return "AxonAI Server is running!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
