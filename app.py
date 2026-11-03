@app.route('/api/customize', methods=['POST'])
def customize():
    data = request.json or {}
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET name_color = ?, avatar_frame = ? WHERE user_id = ?", 
              (data.get('color', '#ffffff'), data.get('frame', 'none'), data.get('user_id')))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})
