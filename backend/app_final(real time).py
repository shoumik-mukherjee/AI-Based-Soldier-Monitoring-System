from flask import Flask, render_template_string, session, redirect, url_for, request
import random
import math
import time
import pickle
import pandas as pd
import requests

app = Flask(__name__)
app.secret_key = 'wartech-innovators-rvce-2024'

# ─── CREDENTIALS ─────────────────────────────────────────────
USERS = {
    'commander': {'password': 'commander123', 'role': 'Commander',  'clearance': 'ALPHA'},
    'admin':     {'password': 'admin123',     'role': 'Admin',      'clearance': 'OMEGA'},
}

# ─── LOAD REAL AI MODEL ──────────────────────────────────────
# Place model_large.pkl in the same folder as this script
model = pickle.load(open("model_large.pkl", "rb"))
print("✅ AI Model loaded. Classes:", model.classes_)

# ─── SOLDIER PROFILES ────────────────────────────────────────
SOLDIERS = [
    {"id": "S001", "name": "Alpha Unit",   "channel": "3358625", "state": "normal",   "lat": 12.9716, "lon": 77.5946, "initials": "AU"},
    {"id": "S002", "name": "Bravo Unit",   "channel": "3358626", "state": "warning",  "lat": 12.9800, "lon": 77.6100, "initials": "BU"},
    {"id": "S003", "name": "Charlie Unit", "channel": "3358627", "state": "critical", "lat": 12.9650, "lon": 77.5800, "initials": "CU"},
    {"id": "S004", "name": "Delta Unit",   "channel": "3358628", "state": "fatigue",  "lat": 12.9900, "lon": 77.6200, "initials": "DU"},
    {"id": "S005", "name": "Echo Unit",    "channel": "3358629", "state": "injury",   "lat": 12.9750, "lon": 77.5850, "initials": "EU"},
]

# ─── HELPERS ─────────────────────────────────────────────────
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

# ─── FAKE DATA GENERATOR WITH REAL AI MODEL ──────────────────
def generate_vitals(soldier):
    state = soldier["state"]
    t     = time.time()
    wave  = math.sin(t * 0.3) * 0.5

    if state == "normal":
        hr   = jitter(72  + wave * 4,   3)
        spo2 = jitter(98  + wave * 0.5, 0.5)
        temp = jitter(36.8 + wave * 0.1, 0.1)
        acc  = jitter(0.6  + abs(wave) * 0.1, 0.05)

    elif state == "warning":
        hr   = jitter(130 + wave * 8,   4)
        spo2 = jitter(94  + wave * 0.5, 0.4)
        temp = jitter(38.3 + wave * 0.2, 0.15)
        acc  = jitter(1.2  + abs(wave) * 0.3, 0.1)

    elif state == "critical":
        hr   = jitter(160 + wave * 10,  6)
        spo2 = jitter(88  + wave * 1,   0.8)
        temp = jitter(39.8 + wave * 0.3, 0.2)
        acc  = jitter(3.5  + abs(wave) * 0.5, 0.3)

    elif state == "fatigue":
        hr   = jitter(145 + wave * 6,   4)
        spo2 = jitter(96  + wave * 0.5, 0.3)
        temp = jitter(36.6 + wave * 0.15, 0.1)
        acc  = jitter(0.8  + abs(wave) * 0.2, 0.08)

    elif state == "injury":
        hr   = jitter(132 + wave * 10,  5)
        spo2 = jitter(92  + wave * 1,   0.6)
        temp = jitter(37.6 + wave * 0.3, 0.2)
        acc  = jitter(3.0  + abs(wave) * 0.5, 0.3)

    # Clamp to dataset bounds
    hr   = round(max(50,  min(200, hr)),  1)
    spo2 = round(max(80,  min(100, spo2)), 1)
    temp = round(max(33,  min(41,  temp)), 2)
    acc  = round(max(0.1, min(5.0, acc)),  3)

    # ── REAL AI PREDICTION ──────────────────────────────────
    input_df = pd.DataFrame([[hr, spo2, temp, acc]],
                            columns=["HR", "SpO2", "temp", "acc"])
    prediction = model.predict(input_df)[0]

    # Map prediction → alert + color
    if prediction == "critical":
        alert = "CRITICAL 🚨"
        color = "critical"
    elif prediction == "injury":
        alert = "INJURY 🩹"
        color = "injury"
    elif prediction == "fatigue":
        alert = "FATIGUE ⚠️"
        color = "fatigue"
    else:
        alert = "NORMAL ✅"
        color = "normal"

    # Smooth GPS patrol movement
    lat = round(soldier["lat"] + math.sin(t * 0.05) * 0.002, 6)
    lon = round(soldier["lon"] + math.cos(t * 0.04) * 0.002, 6)

    return {
        "id":         soldier["id"],
        "name":       soldier["name"],
        "initials":   soldier["initials"],
        "channel":    soldier["channel"],
        "hr":         hr,
        "spo2":       spo2,
        "temp":       temp,
        "acc":        acc,
        "prediction": prediction.upper(),
        "alert":      alert,
        "color":      color,
        "lat":        lat,
        "lon":        lon,
        "risk_score": compute_risk(hr, spo2, temp, acc),
    }

# ─── DASHBOARD HTML ───────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WARTECH INNOVATORS — Soldier Monitoring</title>
<meta http-equiv="refresh" content="10">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:#0a0c0f; --bg2:#111418; --bg3:#181c22;
    --border:rgba(255,255,255,0.07); --border2:rgba(255,255,255,0.13);
    --green:#00ff9d; --green-dim:rgba(0,255,157,0.08);
    --amber:#f5a623; --amber-dim:rgba(245,166,35,0.08);
    --red:#ff3b3b;   --red-dim:rgba(255,59,59,0.09);
    --purple:#bf5fff; --purple-dim:rgba(191,95,255,0.09);
    --text:#c8cdd8; --text-dim:#4a5060; --text-bright:#e8ecf4;
    --mono:'Share Tech Mono',monospace; --head:'Rajdhani',sans-serif;
  }
  body { background:var(--bg); color:var(--text); font-family:var(--head); min-height:100vh; }

  /* TOP BAR */
  .topbar { display:flex; align-items:center; justify-content:space-between; padding:12px 28px; background:var(--bg2); border-bottom:1px solid var(--border); position:sticky; top:0; z-index:100; }
  .topbar-left { display:flex; align-items:center; gap:14px; }
  .shield { width:34px; height:34px; background:var(--green); clip-path:polygon(50% 0%,95% 20%,95% 60%,50% 100%,5% 60%,5% 20%); }
  .brand { font-size:17px; font-weight:700; letter-spacing:3px; color:var(--text-bright); text-transform:uppercase; }
  .brand span { color:var(--green); }
  .ai-badge { font-family:var(--mono); font-size:10px; color:var(--green); background:var(--green-dim); border:1px solid rgba(0,255,157,0.3); padding:3px 9px; border-radius:3px; letter-spacing:1px; }
  .topbar-right { display:flex; align-items:center; gap:18px; }
  .live-badge { display:flex; align-items:center; gap:6px; font-family:var(--mono); font-size:10px; color:var(--green); background:var(--green-dim); border:1px solid rgba(0,255,157,0.25); padding:4px 10px; border-radius:3px; letter-spacing:1px; }
  .live-dot { width:6px; height:6px; border-radius:50%; background:var(--green); animation:blink 1.4s infinite; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
  .clock { font-family:var(--mono); font-size:12px; color:var(--text-dim); letter-spacing:1px; }
  .user-badge { font-family:var(--mono); font-size:10px; color:var(--text-dim); letter-spacing:1px; }
  .user-badge span { color:var(--green); }
  .logout-btn { font-family:var(--mono); font-size:10px; color:var(--text-dim); background:var(--bg3);
    border:1px solid var(--border); border-radius:3px; padding:4px 12px; text-decoration:none;
    letter-spacing:1px; transition:color .2s,border-color .2s; }
  .logout-btn:hover { color:var(--red); border-color:rgba(255,59,59,0.4); }

  .live-tag { font-family:var(--mono); font-size:9px; font-weight:700; color:var(--green); background:rgba(0,255,157,0.12); border:1px solid rgba(0,255,157,0.4); border-radius:3px; padding:2px 6px; letter-spacing:1px; }
  .sim-tag  { font-family:var(--mono); font-size:9px; color:var(--text-dim); background:rgba(74,80,96,0.2); border:1px solid rgba(74,80,96,0.4); border-radius:3px; padding:2px 6px; letter-spacing:1px; }

  /* PAGE */
  .page { padding:22px 28px; }

  /* SUMMARY STRIP */
  .summary-strip { display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:22px; }
  .sum-card { background:var(--bg2); border:1px solid var(--border); border-radius:4px; padding:12px 16px; position:relative; overflow:hidden; }
  .sum-card::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--green); }
  .sum-card.warn::before  { background:var(--amber); }
  .sum-card.crit::before  { background:var(--red); }
  .sum-card.injr::before  { background:var(--purple); }
  .sum-label { font-family:var(--mono); font-size:9px; color:var(--text-dim); letter-spacing:2px; text-transform:uppercase; margin-bottom:5px; }
  .sum-val { font-size:24px; font-weight:700; color:var(--text-bright); }
  .sum-val span { font-size:11px; font-weight:400; color:var(--text-dim); margin-left:3px; }

  /* SOLDIER GRID — 3 cols top, 2 cols bottom */
  .soldiers { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }
  .soldiers .scard:nth-child(4) { grid-column: 1 / 2; }
  .soldiers .scard:nth-child(5) { grid-column: 2 / 3; }

  .scard { background:var(--bg2); border:1px solid var(--border); border-radius:6px; overflow:hidden; }
  .scard.state-critical { border-color:rgba(255,59,59,0.35); }
  .scard.state-warning  { border-color:rgba(245,166,35,0.3); }
  .scard.state-injury   { border-color:rgba(191,95,255,0.35); }

  .scard-header { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-bottom:1px solid var(--border); background:var(--bg3); }
  .sid-block { display:flex; align-items:center; gap:10px; }
  .avatar { width:38px; height:38px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-family:var(--mono); font-size:12px; font-weight:700; border:1px solid; flex-shrink:0; }
  .avatar.normal   { background:var(--green-dim);  border-color:rgba(0,255,157,0.3);   color:var(--green); }
  .avatar.warning,
  .avatar.fatigue  { background:var(--amber-dim);  border-color:rgba(245,166,35,0.3);  color:var(--amber); }
  .avatar.critical { background:var(--red-dim);    border-color:rgba(255,59,59,0.35);  color:var(--red); }
  .avatar.injury   { background:var(--purple-dim); border-color:rgba(191,95,255,0.3);  color:var(--purple); }
  .sname { font-size:15px; font-weight:700; color:var(--text-bright); letter-spacing:1px; }
  .suid  { font-family:var(--mono); font-size:10px; color:var(--text-dim); letter-spacing:1px; margin-top:2px; }

  .alert-badge { display:flex; align-items:center; gap:6px; padding:5px 12px; border-radius:3px; font-family:var(--mono); font-size:10px; font-weight:700; letter-spacing:2px; }
  .alert-badge.normal   { background:var(--green-dim);  border:1px solid rgba(0,255,157,0.3);   color:var(--green); }
  .alert-badge.warning,
  .alert-badge.fatigue  { background:var(--amber-dim);  border:1px solid rgba(245,166,35,0.3);  color:var(--amber); }
  .alert-badge.critical { background:var(--red-dim);    border:1px solid rgba(255,59,59,0.35);  color:var(--red);    animation:flash 0.9s infinite; }
  .alert-badge.injury   { background:var(--purple-dim); border:1px solid rgba(191,95,255,0.3);  color:var(--purple); animation:flash 1.2s infinite; }
  @keyframes flash { 0%,100%{opacity:1} 50%{opacity:.4} }
  .badge-dot { width:6px; height:6px; border-radius:50%; background:currentColor; }

  /* CARD BODY */
  .scard-body { padding:14px 16px; }
  .vitals { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-bottom:12px; }
  .vbox { background:var(--bg3); border:1px solid var(--border); border-radius:4px; padding:10px 12px; }
  .vlabel { font-family:var(--mono); font-size:9px; color:var(--text-dim); letter-spacing:2px; text-transform:uppercase; margin-bottom:6px; }
  .vval { font-family:var(--mono); font-size:18px; font-weight:700; color:var(--text-bright); }
  .vunit { font-size:10px; color:var(--text-dim); font-weight:400; }
  .vbar { height:2px; background:var(--border2); border-radius:2px; margin-top:7px; overflow:hidden; }
  .vfill { height:100%; border-radius:2px; }
  .g { background:var(--green); } .o { background:var(--amber); } .r { background:var(--red); } .p { background:var(--purple); }

  /* AI ROW */
  .meta-row { display:flex; align-items:center; gap:8px; background:var(--bg3); border:1px solid var(--border); border-radius:4px; padding:8px 12px; margin-bottom:12px; }
  .meta-tag { font-family:var(--mono); font-size:9px; color:var(--text-dim); letter-spacing:2px; text-transform:uppercase; white-space:nowrap; }
  .meta-sep { flex:1; height:1px; background:var(--border2); }
  .meta-val { font-family:var(--mono); font-size:12px; font-weight:700; letter-spacing:1px; }
  .meta-val.normal   { color:var(--green); }
  .meta-val.warning,
  .meta-val.fatigue  { color:var(--amber); }
  .meta-val.critical { color:var(--red); }
  .meta-val.injury   { color:var(--purple); }

  /* RISK BAR */
  .risk-row { margin-bottom:12px; }
  .risk-header { display:flex; justify-content:space-between; margin-bottom:5px; }
  .risk-label { font-family:var(--mono); font-size:9px; color:var(--text-dim); letter-spacing:2px; text-transform:uppercase; }
  .risk-num   { font-family:var(--mono); font-size:9px; color:var(--text-dim); }
  .risk-track { height:4px; background:var(--border2); border-radius:2px; overflow:hidden; }
  .risk-fill  { height:100%; border-radius:2px; }

  /* LOWER: MAP + GPS */
  .lower { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
  .sec-label { font-family:var(--mono); font-size:9px; color:var(--text-dim); letter-spacing:3px; text-transform:uppercase; margin-bottom:7px; }
  .map-wrap { background:var(--bg3); border:1px solid var(--border); border-radius:4px; overflow:hidden; position:relative; }
  .map-wrap iframe { display:block; width:100%; height:170px; border:none; filter:invert(0.88) hue-rotate(170deg) saturate(0.5); opacity:0.85; }
  .map-coords { position:absolute; bottom:6px; left:6px; font-family:var(--mono); font-size:9px; color:var(--green); background:rgba(10,12,15,0.85); border:1px solid rgba(0,255,157,0.2); padding:3px 7px; border-radius:2px; letter-spacing:1px; }
  .gps-info { background:var(--bg3); border:1px solid var(--border); border-radius:4px; padding:10px 12px; }
  .gps-row { display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid var(--border); }
  .gps-row:last-child { border-bottom:none; }
  .gps-key { font-family:var(--mono); font-size:9px; color:var(--text-dim); letter-spacing:1px; text-transform:uppercase; }
  .gps-val { font-family:var(--mono); font-size:11px; color:var(--text-bright); }

  @media(max-width:900px) {
    .soldiers { grid-template-columns:1fr 1fr; }
    .soldiers .scard:nth-child(4),
    .soldiers .scard:nth-child(5) { grid-column: auto; }
    .summary-strip { grid-template-columns:repeat(3,1fr); }
  }
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-left">
    <div class="shield"></div>
    <div class="brand">WARTECH <span>INNOVATORS</span></div>
    <div class="ai-badge">🧠 AI MODEL ACTIVE</div>
  </div>
  <div class="topbar-right">
    <div class="live-badge"><div class="live-dot"></div> REFRESH IN <span id="countdown">10</span>s</div>
    <div class="clock" id="clk">--:--:--</div>
    <div class="user-badge">{{ session.role }} · <span>{{ session.username|upper }}</span></div>
    <a href="/logout" class="logout-btn">⏏ EXIT</a>
  </div>
</div>

<div class="page">

  <!-- SUMMARY STRIP -->
  <div class="summary-strip">
    <div class="sum-card">
      <div class="sum-label">Online</div>
      <div class="sum-val">{{ data|length }}<span>units</span></div>
    </div>
    <div class="sum-card {% if data|selectattr('color','eq','critical')|list|length > 0 %}crit{% endif %}">
      <div class="sum-label">Critical</div>
      <div class="sum-val">{{ data|selectattr('color','eq','critical')|list|length }}<span>units</span></div>
    </div>
    <div class="sum-card {% if data|selectattr('color','eq','injury')|list|length > 0 %}injr{% endif %}">
      <div class="sum-label">Injury</div>
      <div class="sum-val">{{ data|selectattr('color','eq','injury')|list|length }}<span>units</span></div>
    </div>
    <div class="sum-card {% if data|selectattr('color','eq','fatigue')|list|length > 0 %}warn{% endif %}">
      <div class="sum-label">Fatigue</div>
      <div class="sum-val">{{ data|selectattr('color','eq','fatigue')|list|length }}<span>units</span></div>
    </div>
    <div class="sum-card">
      <div class="sum-label">Avg HR</div>
      <div class="sum-val">{{ (data|sum(attribute='hr') / data|length)|round(0)|int }}<span>bpm</span></div>
    </div>
    <div class="sum-card">
      <div class="sum-label">Avg SpO₂</div>
      <div class="sum-val">{{ (data|sum(attribute='spo2') / data|length)|round(1) }}<span>%</span></div>
    </div>
  </div>

  <!-- SOLDIER CARDS -->
  <div class="soldiers">
  {% for s in data %}
    <div class="scard state-{{ s.color }}">
      <div class="scard-header">
        <div class="sid-block">
          <div class="avatar {{ s.color }}">{{ s.initials }}</div>
          <div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div class="sname">{{ s.name }}</div>
              {% if s.id == 'S001' %}
                <div class="live-tag">● LIVE</div>
              {% else %}
                <div class="sim-tag">SIM</div>
              {% endif %}
            </div>
            <div class="suid">{{ s.id }} · CH {{ s.channel }}</div>
          </div>
        </div>
        <div class="alert-badge {{ s.color }}">
          <div class="badge-dot"></div>{{ s.alert }}
        </div>
      </div>

      <div class="scard-body">

        <div class="vitals">
          <div class="vbox">
            <div class="vlabel">Heart Rate</div>
            <div class="vval">{{ s.hr|round(0)|int }}<span class="vunit"> bpm</span></div>
            <div class="vbar"><div class="vfill {{ 'r' if s.hr > 150 else 'o' if s.hr > 120 else 'g' }}" style="width:{{ [s.hr/2,100]|min }}%"></div></div>
          </div>
          <div class="vbox">
            <div class="vlabel">SpO₂</div>
            <div class="vval">{{ s.spo2|round(1) }}<span class="vunit"> %</span></div>
            <div class="vbar"><div class="vfill {{ 'r' if s.spo2 < 90 else 'o' if s.spo2 < 94 else 'g' }}" style="width:{{ s.spo2 }}%"></div></div>
          </div>
          <div class="vbox">
            <div class="vlabel">Temp</div>
            <div class="vval">{{ s.temp|round(1) }}<span class="vunit"> °C</span></div>
            <div class="vbar"><div class="vfill {{ 'r' if s.temp > 39 else 'o' if s.temp > 38 else 'g' }}" style="width:{{ [(s.temp-33)/8*100,100]|min|round }}%"></div></div>
          </div>
          <div class="vbox">
            <div class="vlabel">Accel</div>
            <div class="vval">{{ s.acc|round(2) }}<span class="vunit"> g</span></div>
            <div class="vbar"><div class="vfill {{ 'r' if s.acc > 3 else 'p' if s.acc > 2 else 'o' if s.acc > 1.5 else 'g' }}" style="width:{{ [s.acc/5*100,100]|min|round }}%"></div></div>
          </div>
        </div>

        <div class="meta-row">
          <div class="meta-tag">🧠 Decision Tree</div>
          <div class="meta-sep"></div>
          <div class="meta-val {{ s.color }}">{{ s.prediction }}</div>
        </div>

        <div class="risk-row">
          <div class="risk-header">
            <div class="risk-label">Edge AI Risk Score</div>
            <div class="risk-num">{{ s.risk_score }}/100</div>
          </div>
          <div class="risk-track">
            <div class="risk-fill {{ 'r' if s.risk_score >= 70 else 'p' if s.risk_score >= 55 else 'o' if s.risk_score >= 40 else 'g' }}" style="width:{{ s.risk_score }}%"></div>
          </div>
        </div>

        <div class="lower">
          <div>
            <div class="sec-label">Last Position</div>
            <div class="map-wrap">
              <iframe src="https://maps.google.com/maps?q={{ s.lat }},{{ s.lon }}&z=15&output=embed" loading="lazy"></iframe>
              <div class="map-coords">{{ s.lat }}° · {{ s.lon }}°</div>
            </div>
          </div>
          <div>
            <div class="sec-label">GPS + Status</div>
            <div class="gps-info">
              <div class="gps-row"><span class="gps-key">Latitude</span><span class="gps-val">{{ s.lat }}° N</span></div>
              <div class="gps-row"><span class="gps-key">Longitude</span><span class="gps-val">{{ s.lon }}° E</span></div>
              <div class="gps-row"><span class="gps-key">GPS</span><span class="gps-val" style="color:var(--green)">FIXED</span></div>
              <div class="gps-row"><span class="gps-key">Data Source</span>
                {% if s.id == 'S001' %}
                  <span class="gps-val" style="color:var(--green)">ThingSpeak · LIVE</span>
                {% else %}
                  <span class="gps-val" style="color:var(--text-dim)">Simulated · SIM</span>
                {% endif %}
              </div>
              <div class="gps-row"><span class="gps-key">AI Result</span>
                <span class="gps-val" style="color:var(--{{ 'red' if s.color=='critical' else 'purple' if s.color=='injury' else 'amber' if s.color=='warning' else 'green' }})">{{ s.prediction }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  {% endfor %}
  </div>
</div>

<script>
  // ── Clock ──
  function tick() {
    document.getElementById('clk').textContent = new Date().toTimeString().slice(0,8) + ' UTC';
  }
  tick(); setInterval(tick, 1000);

  // ── Countdown ──
  var count = 10;
  var cdEl  = document.getElementById('countdown');
  setInterval(function() {
    count--;
    if (count <= 0) { count = 10; }
    cdEl.textContent = count;
    // Turn red in last 3 seconds
    if (count <= 3) {
      cdEl.style.color = 'var(--red)';
      cdEl.parentElement.style.color = 'var(--red)';
      cdEl.parentElement.style.borderColor = 'rgba(255,59,59,0.4)';
      cdEl.parentElement.style.background  = 'rgba(255,59,59,0.08)';
    } else {
      cdEl.style.color = '';
      cdEl.parentElement.style.color = '';
      cdEl.parentElement.style.borderColor = '';
      cdEl.parentElement.style.background  = '';
    }
  }, 1000);
</script>
</body>
</html>
"""

# ─── REAL THINGSPEAK DATA FETCHER (S001) ─────────────────────
def fetch_real_data(soldier):
    try:
        url = (f"https://api.thingspeak.com/channels/{soldier['channel']}"
               f"/feeds.json?api_key=OQXIONJMGF8PIUUY&results=1")
        response = requests.get(url, timeout=5)
        feed = response.json()['feeds'][0]

        hr   = float(feed.get('field1') or 0)
        spo2 = float(feed.get('field2') or 0)
        temp = float(feed.get('field3') or 0)
        acc  = float(feed.get('field4') or 0)
        lat  = float(feed.get('field5') or soldier['lat'])
        lon  = float(feed.get('field6') or soldier['lon'])

        # Run real AI model
        input_df = pd.DataFrame([[hr, spo2, temp, acc]],
                                columns=["HR", "SpO2", "temp", "acc"])
        prediction = model.predict(input_df)[0]

        color_map = {
            "critical": ("CRITICAL 🚨", "critical"),
            "injury":   ("INJURY 🩹",   "injury"),
            "fatigue":  ("FATIGUE ⚠️",  "fatigue"),
            "normal":   ("NORMAL ✅",   "normal"),
        }
        alert, color = color_map.get(prediction, ("NORMAL ✅", "normal"))

        return {
            "id":         soldier["id"],
            "name":       soldier["name"],
            "initials":   soldier["initials"],
            "channel":    soldier["channel"],
            "hr":         round(hr,   1),
            "spo2":       round(spo2, 1),
            "temp":       round(temp, 2),
            "acc":        round(acc,  3),
            "prediction": prediction.upper(),
            "alert":      alert,
            "color":      color,
            "lat":        lat,
            "lon":        lon,
            "risk_score": compute_risk(hr, spo2, temp, acc),
        }
    except Exception as e:
        print(f"ThingSpeak fetch error for {soldier['id']}: {e}")
        return generate_vitals(soldier)  # fallback to simulated


# ─── LOGIN PAGE HTML ──────────────────────────────────────────
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WARTECH INNOVATORS — Command Access</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:#0a0c0f; --bg2:#111418; --bg3:#181c22;
    --border:rgba(255,255,255,0.07); --border2:rgba(255,255,255,0.15);
    --green:#00ff9d; --green-dim:rgba(0,255,157,0.10);
    --red:#ff3b3b; --red-dim:rgba(255,59,59,0.10);
    --text:#c8cdd8; --text-dim:#4a5060; --text-bright:#e8ecf4;
    --mono:'Share Tech Mono',monospace; --head:'Rajdhani',sans-serif;
  }
  body { background:var(--bg); color:var(--text); font-family:var(--head);
    min-height:100vh; display:flex; align-items:center; justify-content:center;
    overflow:hidden; }

  /* grid lines */
  body::before {
    content:''; position:fixed; inset:0; pointer-events:none;
    background-image:
      repeating-linear-gradient(0deg, transparent, transparent 79px, rgba(0,255,157,0.03) 80px),
      repeating-linear-gradient(90deg, transparent, transparent 79px, rgba(0,255,157,0.03) 80px);
  }

  .login-wrap { width:100%; max-width:420px; padding:24px; }

  .logo-row { display:flex; align-items:center; gap:14px; margin-bottom:28px; }
  .shield { width:40px; height:40px; background:var(--green);
    clip-path:polygon(50% 0%,95% 20%,95% 65%,50% 100%,5% 65%,5% 20%); flex-shrink:0; }
  .brand { font-size:18px; font-weight:700; letter-spacing:3px; color:var(--text-bright);
    text-transform:uppercase; font-family:var(--mono); }
  .brand span { color:var(--green); }
  .brand-sub { font-size:9px; color:var(--text-dim); letter-spacing:2px; margin-top:3px;
    font-family:var(--mono); }

  .card { background:var(--bg2); border:1px solid var(--border2); border-radius:4px; padding:32px; }

  .card-title { font-size:22px; font-weight:700; letter-spacing:4px; color:var(--text-bright);
    margin-bottom:4px; font-family:var(--mono); }
  .card-sub { font-size:10px; color:var(--text-dim); letter-spacing:1px; margin-bottom:28px; }
  .divider { height:1px; background:var(--border); margin-bottom:28px; }

  .field { margin-bottom:18px; }
  .field label { display:block; font-family:var(--mono); font-size:9px; color:var(--text-dim);
    letter-spacing:2px; margin-bottom:7px; text-transform:uppercase; }
  .input-wrap { display:flex; align-items:center; background:var(--bg3); border:1px solid var(--border);
    border-radius:3px; padding:0 14px; height:48px; transition:border-color .2s; }
  .input-wrap:focus-within { border-color:rgba(0,255,157,0.4); }
  .input-icon { color:var(--green); font-size:14px; margin-right:10px; }
  .input-wrap input { flex:1; background:none; border:none; outline:none; color:var(--text-bright);
    font-family:var(--mono); font-size:14px; }
  .input-wrap input::placeholder { color:var(--text-dim); }

  .error-box { background:var(--red-dim); border:1px solid rgba(255,59,59,0.35);
    border-radius:3px; padding:10px 14px; margin-bottom:16px; font-family:var(--mono);
    font-size:11px; color:var(--red); }

  .login-btn { width:100%; height:52px; background:var(--green); border:none; border-radius:3px;
    color:#0a0c0f; font-family:var(--mono); font-size:13px; font-weight:700; letter-spacing:2px;
    cursor:pointer; transition:opacity .2s; margin-top:4px; }
  .login-btn:hover { opacity:0.85; }

  .hint { text-align:center; font-family:var(--mono); font-size:10px; color:var(--text-dim);
    margin-top:20px; }
  .hint span { color:var(--green); }
</style>
</head>
<body>
<div class="login-wrap">
  <div class="logo-row">
    <div class="shield"></div>
    <div>
      <div class="brand">WARTECH <span>INNOVATORS</span></div>
      <div class="brand-sub">SOLDIER HEALTH MONITORING SYSTEM · RVCE</div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">COMMAND ACCESS</div>
    <div class="card-sub">Authorised Personnel Only — Enter Credentials to Proceed</div>
    <div class="divider"></div>

    {% if error %}
    <div class="error-box">⛔ {{ error }}</div>
    {% endif %}

    <form method="POST" action="/login">
      <div class="field">
        <label>Commander ID / Username</label>
        <div class="input-wrap">
          <span class="input-icon">◈</span>
          <input type="text" name="username" placeholder="Enter username" autocomplete="off" required>
        </div>
      </div>
      <div class="field">
        <label>Access Code</label>
        <div class="input-wrap">
          <span class="input-icon">◉</span>
          <input type="password" name="password" placeholder="Enter password" required>
        </div>
      </div>
      <button type="submit" class="login-btn">▶ &nbsp; AUTHENTICATE &amp; ENTER</button>
    </form>
  </div>

  <div class="hint">Demo: <span>commander</span> / <span>commander123</span></div>
</div>
</body>
</html>
"""

# ─── AUTH HELPERS & ROUTES ───────────────────────────────────
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user = USERS.get(username)
        if user and user['password'] == password:
            session['logged_in'] = True
            session['username']  = username
            session['role']      = user['role']
            session['clearance'] = user['clearance']
            return redirect(url_for('dashboard'))
        error = 'Invalid credentials. Access denied.'
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/login', methods=['POST'])
def api_login():
    from flask import jsonify, request as req
    data = req.get_json(silent=True) or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    user = USERS.get(username)
    if user and user['password'] == password:
        # Return user info — mobile app stores this as 'user' in AsyncStorage
        return jsonify({
            'ok': True,
            'user': {
                'id': f'CMD-{username[:3].upper()}',
                'username': username,
                'role': user['role'],
                'clearance': user['clearance'],
            }
        })
    return jsonify({'ok': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/soldiers')

def api_soldiers():
    from flask import jsonify
    all_data = []
    for s in SOLDIERS:
        if s["id"] == "S001":
            all_data.append(fetch_real_data(s))
        else:
            all_data.append(generate_vitals(s))
    return jsonify(all_data)

@app.route('/')
@login_required
def dashboard():
    all_data = []
    for s in SOLDIERS:
        if s["id"] == "S001":
            all_data.append(fetch_real_data(s))   # ← real sensor data
        else:
            all_data.append(generate_vitals(s))   # ← simulated
    return render_template_string(HTML, data=all_data)

if __name__ == '__main__':
    app.run(debug=True)