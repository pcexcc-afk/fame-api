from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "AxonAI Server is running!"

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "AxonAI backend is alive"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
