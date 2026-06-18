# 🪖 AI-Based Soldier Health Monitoring System

> Real-time IoT + ML system for monitoring soldier vitals in the field — built by Wartech Innovators @ RVCE

---

## 📌 Problem Statement

Modern warfare demands continuous real-time health monitoring of soldiers. Delayed medical response due to lack of awareness costs lives. This system provides an intelligent, automated solution that tracks vital signs and instantly alerts command units during emergencies.

---

## 🧠 How It Works
Sensors (ESP32) → Edge AI Risk Score → ThingSpeak Cloud → Flask Backend → ML Prediction → Dashboard + Mobile App

4-layer architecture:
- **Sensor Layer** — MAX30102, MPU6050, DS18B20, NEO-6M GPS
- **Edge Intelligence** — On-device risk scoring (0–100) without internet
- **Cloud AI Layer** — ThingSpeak + Decision Tree Classifier
- **Presentation Layer** — Web dashboard + React Native mobile app

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Microcontroller | ESP32 (30-pin) |
| Sensors | MAX30102, MPU6050, DS18B20, NEO-6M GPS |
| Firmware | C++ / Arduino IDE 2.3.8 |
| Cloud | ThingSpeak |
| Backend | Python Flask |
| AI Model | Scikit-learn Decision Tree (99% accuracy) |
| Web UI | HTML5, CSS3, Jinja2, Chart.js |
| Mobile App | React Native + Expo SDK 54 |
| Auth | Flask Sessions + JWT |

---

## 🎯 Features

- ✅ Real-time vitals: Heart Rate, SpO2, Body Temperature, Acceleration
- ✅ GPS tracking for rescue coordination
- ✅ 4-class AI prediction: **Normal / Fatigue / Injury / Critical**
- ✅ Edge AI risk score (0–100) — works offline
- ✅ Multi-soldier dashboard (LIVE + SIM tagged cards)
- ✅ React Native mobile app with SOS dispatch
- ✅ Role-based login for command personnel

---

## 📊 AI Model Performance

| Metric | Score |
|---|---|
| Accuracy | 99% |
| Precision | 99% |
| Recall | 99% |
| Recall | 99% |
| F1-Score | 99% |
| Training Samples | 3200 |
| Test Samples | 800 |

---

## 🔌 Hardware Wiring

| Sensor | Connection | Protocol |
|---|---|---|
| MAX30102 | SDA→GPIO21, SCL→GPIO22 | I²C (0x57) |
| MPU6050 | SDA→GPIO21, SCL→GPIO22 | I²C (0x68) |
| DS18B20 | DATA→GPIO4 (4.7kΩ pull-up) | One-Wire |
| NEO-6M GPS | TX→GPIO16, RX→GPIO17 | UART2 |

---

## 🚀 Running the Project

**Flask Dashboard:**
```bash
pip install flask scikit-learn pandas numpy requests
python app_final_real_time_.py
# Open http://localhost:5000
```

**ESP32 Firmware:**
- Open `soldier_monitor_v2.ino` in Arduino IDE 2.3.8
- Install libraries: MAX30105, FastIMU, DallasTemperature, TinyGPSPlus
- Flash to ESP32

**Mobile App:**
```bash
cd SoldierApp2
npm install
npx expo start
```

---

## 👥 Team name — Wartech Innovators

Built as part of the Experiential Learning of semester 2 @ RV College of Engineering, Bengaluru (2025–26)

---

## 📄 License

MIT License
