# ============================================================
#  WAR TECH INNOVATORS — Flask Backend API
#  Add these routes to your existing app_final.py
#  Install: pip install flask-jwt-extended bcrypt
# ============================================================

from flask import Flask, request, jsonify, render_template_string
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt
import sqlite3
import os
import random
import math
import time
import pickle
import pandas as pd

app = Flask(__name__)

# ─── JWT CONFIG ───────────────────────────────────────────────
app.config['JWT_SECRET_KEY'] = 'wti-secret-key-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Set timedelta for expiry in prod
jwt = JWTManager(app)

# ─── LOAD AI MODEL ────────────────────────────────────────────
model = pickle.load(open("model_large.pkl", "rb"))

# ─── DATABASE SETUP ───────────────────────────────────────────
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'operator'
    )''')
    # Create default admin user (username: admin, password: admin123)
    try:
        hashed = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  ('admin', hashed, 'admin'))
        # Create a commander user
        hashed2 = bcrypt.hashpw('commander'.encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  ('commander', hashed2, 'admin'))
    except sqlite3.IntegrityError:
        pass  # Users already exist
    conn.commit()
    conn.close()

init_db()

# ─── SOLDIER PROFILES ─────────────────────────────────────────
SOLDIERS = [
    {"id": "S001", "name": "Alpha Unit",   "channel": "3358625", "state": "normal",   "lat": 12.9716, "lon": 77.5946, "initials": "AU"},
    {"id": "S002", "name": "Bravo Unit",   "channel": "3358626", "state": "warning",  "lat": 12.9800, "lon": 77.6100, "initials": "BU"},
    {"id": "S003", "name": "Charlie Unit", "channel": "3358627", "state": "critical", "lat": 12.9650, "lon": 77.5800, "initials": "CU"},
    {"id": "S004", "name": "Delta Unit",   "channel": "3358628", "state": "fatigue",  "lat": 12.9900, "lon": 77.6200, "initials": "DU"},
    {"id": "S005", "name": "Echo Unit",    "channel": "3358629", "state": "injury",   "lat": 12.9750, "lon": 77.5850, "initials": "EU"},
]

def jitter(val, amount):
    return round(val + random.uniform(-amount, amount), 2)

def compute_risk(hr, spo2, temp, acc):
    score = 0
    if hr > 150:      score += 40
    elif hr > 120:    score += 25
    elif hr > 100:    score += 10
    elif hr < 50:     score += 30
    if spo2 < 90:     score += 40
    elif spo2 < 94:   score += 20
    elif spo2 < 96:   score += 10
    if temp > 39.5:   score += 30
    elif temp > 38.5: score += 20
    elif temp > 38.0: score += 10
    if acc > 4.0:     score += 40
    elif acc > 2.5:   score += 20
    elif acc > 1.5:   score += 10
    return min(score, 100)

def generate_vitals(soldier):
    state = soldier["state"]
    t     = time.time()
    wave  = math.sin(t * 0.3) * 0.5

    if state == "normal":
        hr, spo2, temp, acc = jitter(72+wave*4,3), jitter(98+wave*0.5,0.5), jitter(36.8+wave*0.1,0.1), jitter(0.6+abs(wave)*0.1,0.05)
    elif state == "warning":
        hr, spo2, temp, acc = jitter(130+wave*8,4), jitter(94+wave*0.5,0.4), jitter(38.3+wave*0.2,0.15), jitter(1.2+abs(wave)*0.3,0.1)
    elif state == "critical":
        hr, spo2, temp, acc = jitter(160+wave*10,6), jitter(88+wave*1,0.8), jitter(39.8+wave*0.3,0.2), jitter(3.5+abs(wave)*0.5,0.3)
    elif state == "fatigue":
        hr, spo2, temp, acc = jitter(145+wave*6,4), jitter(96+wave*0.5,0.3), jitter(36.6+wave*0.15,0.1), jitter(0.8+abs(wave)*0.2,0.08)
    elif state == "injury":
        hr, spo2, temp, acc = jitter(132+wave*10,5), jitter(92+wave*1,0.6), jitter(37.6+wave*0.3,0.2), jitter(3.0+abs(wave)*0.5,0.3)

    hr   = round(max(50,  min(200, hr)),  1)
    spo2 = round(max(80,  min(100, spo2)), 1)
    temp = round(max(33,  min(41,  temp)), 2)
    acc  = round(max(0.1, min(5.0, acc)),  3)

    input_df = pd.DataFrame([[hr, spo2, temp, acc]], columns=["HR", "SpO2", "temp", "acc"])
    prediction = model.predict(input_df)[0]

    color_map = { "critical": ("CRITICAL 🚨", "critical"), "injury": ("INJURY 🩹", "injury"),
                  "fatigue": ("FATIGUE ⚠️", "warning"), "normal": ("NORMAL ✅", "normal") }
    alert, color = color_map.get(prediction, ("NORMAL ✅", "normal"))

    lat = round(soldier["lat"] + math.sin(t * 0.05) * 0.002, 6)
    lon = round(soldier["lon"] + math.cos(t * 0.04) * 0.002, 6)

    return {
        "id": soldier["id"], "name": soldier["name"], "initials": soldier["initials"],
        "channel": soldier["channel"], "hr": hr, "spo2": spo2, "temp": temp, "acc": acc,
        "prediction": prediction.upper(), "alert": alert, "color": color,
        "lat": lat, "lon": lon, "risk_score": compute_risk(hr, spo2, temp, acc),
    }

# ─── AUTH ROUTES ──────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'message': 'Invalid credentials'}), 401

    password_hash, role = row
    if not bcrypt.checkpw(password.encode(), password_hash.encode()):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = create_access_token(identity={'username': username, 'role': role})
    return jsonify({'token': token, 'username': username, 'role': role}), 200


@app.route('/api/register', methods=['POST'])
@jwt_required()
def register():
    """Only admins can register new users"""
    identity = get_jwt_identity()
    if identity.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role     = data.get('role', 'operator')

    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  (username, hashed, role))
        conn.commit()
        conn.close()
        return jsonify({'message': f'User {username} created'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Username already exists'}), 409


@app.route('/api/me', methods=['GET'])
@jwt_required()
def me():
    identity = get_jwt_identity()
    return jsonify(identity), 200


# ─── SOLDIER DATA ROUTES ──────────────────────────────────────

@app.route('/api/soldiers', methods=['GET'])
@jwt_required()
def get_soldiers():
    """Returns live soldier data — protected by JWT"""
    data = [generate_vitals(s) for s in SOLDIERS]
    return jsonify(data), 200


@app.route('/api/soldiers/<soldier_id>', methods=['GET'])
@jwt_required()
def get_soldier(soldier_id):
    """Returns data for a single soldier"""
    soldier = next((s for s in SOLDIERS if s['id'] == soldier_id), None)
    if not soldier:
        return jsonify({'message': 'Soldier not found'}), 404
    return jsonify(generate_vitals(soldier)), 200


# ─── WEB DASHBOARD (existing) ─────────────────────────────────
# Keep your existing dashboard route here — it still works in browser
# The API routes above are the new additions for the mobile app

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'online', 'model': str(model.classes_.tolist())}), 200


if __name__ == '__main__':
    # host='0.0.0.0' makes it accessible on your local network
    # so the mobile app can connect when on same WiFi
    app.run(debug=True, host='0.0.0.0', port=5000)
