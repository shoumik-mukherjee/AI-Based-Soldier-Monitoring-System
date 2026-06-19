// ============================================================
//   AI-Based Soldier Health Monitoring System
//   ESP32 + MAX30102 + DS18B20 + MPU6050 (FastIMU) + NEO-6M GPS
//   ThingSpeak Fields: HR | SpO2 | Temp | Acc | Lat | Lon
//   Board: ESP32 Dev Module | Upload Speed: 115200
//   Press BOOT button when "Connecting..." appears
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <math.h>

// MAX30102 (Heart Rate + SpO2)
#include "MAX30105.h"
#include "spo2_algorithm.h"

// DS18B20 (Temperature)
#include <OneWire.h>
#include <DallasTemperature.h>

// MPU6050 via FastIMU
#include <FastIMU.h>

// GPS (NEO-6M)
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>

// ─── USER CONFIG ─────────────────────────────────────────────
const char* WIFI_SSID     = "SMG M31";
const char* WIFI_PASS     = "vczo6943";
const char* TS_API_KEY    = "QK2ANNCNKJ14IOK9";
const char* TS_SERVER     = "https://api.thingspeak.com/update";
const int   SEND_INTERVAL = 15000;  // ms (min 15s for ThingSpeak free)
// ─────────────────────────────────────────────────────────────

// ─── PIN DEFINITIONS ─────────────────────────────────────────
#define DS18B20_PIN   4    // DS18B20 data pin (with 4.7kΩ pull-up)
#define GPS_RX_PIN    16   // ESP32 RX2 ← GPS TX
#define GPS_TX_PIN    17   // ESP32 TX2 → GPS RX
#define GPS_BAUD      9600
// MAX30102 and MPU6050 share I2C: SDA=GPIO21, SCL=GPIO22
// ─────────────────────────────────────────────────────────────

// ─── SENSOR OBJECTS ──────────────────────────────────────────
MAX30105          particleSensor;
OneWire           oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);

// FastIMU — using MPU6500 class (compatible with MPU6050)
MPU6500           mpu;
calData           calib = {0};
AccelData         accelData;

TinyGPSPlus       gps;
HardwareSerial    gpsSerial(2);  // UART2

// ─── MAX30102 BUFFERS ─────────────────────────────────────────
#define BUFFER_LENGTH 100
uint32_t irBuffer[BUFFER_LENGTH];
uint32_t redBuffer[BUFFER_LENGTH];
int32_t  spo2Val;
int8_t   spo2Valid;
int32_t  heartRate;
int8_t   hrValid;

// ─── EDGE AI: RISK SCORE ─────────────────────────────────────
int computeRiskScore(float hr, float spo2, float temp, float acc) {
  int score = 0;

  // Heart Rate
  if      (hr > 150) score += 40;
  else if (hr > 120) score += 25;
  else if (hr > 100) score += 10;
  else if (hr < 50)  score += 30;

  // SpO2
  if      (spo2 < 90) score += 40;
  else if (spo2 < 94) score += 20;
  else if (spo2 < 96) score += 10;

  // Temperature
  if      (temp > 39.5) score += 30;
  else if (temp > 38.5) score += 20;
  else if (temp > 38.0) score += 10;
  else if (temp < 35.0) score += 25;

  // Acceleration (fall/impact)
  if      (acc > 4.0) score += 40;
  else if (acc > 2.5) score += 20;
  else if (acc > 1.5) score += 10;

  return min(score, 100);
}

String getRiskLabel(int score) {
  if      (score >= 70) return "CRITICAL";
  else if (score >= 55) return "INJURY";
  else if (score >= 40) return "FATIGUE";
  else                  return "NORMAL";
}

// ─── SETUP ───────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Soldier Monitor Booting ===");

  // WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi failed — will retry on upload");
  }

  // I2C
  Wire.begin(21, 22);

  // MAX30102
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("ERROR: MAX30102 not found! Check SDA/SCL wiring.");
  } else {
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeGreen(0);
    Serial.println("MAX30102 OK");
  }

  // DS18B20
  ds18b20.begin();
  int deviceCount = ds18b20.getDeviceCount();
  if (deviceCount == 0) {
    Serial.println("ERROR: DS18B20 not found! Check GPIO4 wiring and pull-up resistor.");
  } else {
    Serial.println("DS18B20 OK (" + String(deviceCount) + " device found)");
  }

  // MPU6050 via FastIMU
  int err = mpu.init(calib, 0x68);
  if (err != 0) {
    Serial.println("ERROR: MPU6050 init failed: " + String(err));
  } else {
    Serial.println("MPU6050 OK (FastIMU)");
  }

  // GPS
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("GPS ready (UART2 — RX:16, TX:17)");

  Serial.println("=== All sensors initialised ===\n");
}

// ─── READ MAX30102 ────────────────────────────────────────────
void readMAX30102() {
  Serial.println("Collecting MAX30102 samples (takes ~4 seconds)...");
  for (byte i = 0; i < BUFFER_LENGTH; i++) {
    while (!particleSensor.available())
      particleSensor.check();
    redBuffer[i] = particleSensor.getRed();
    irBuffer[i]  = particleSensor.getIR();
    particleSensor.nextSample();
  }
  maxim_heart_rate_and_oxygen_saturation(
    irBuffer, BUFFER_LENGTH, redBuffer,
    &spo2Val, &spo2Valid, &heartRate, &hrValid
  );
}

// ─── READ GPS ────────────────────────────────────────────────
void readGPS(float &lat, float &lon) {
  unsigned long start = millis();
  lat = 0.0;
  lon = 0.0;
  while (millis() - start < 2000) {
    while (gpsSerial.available())
      gps.encode(gpsSerial.read());
    if (gps.location.isUpdated()) {
      lat = gps.location.lat();
      lon = gps.location.lng();
      return;
    }
  }
  // Use last known fix if available
  if (gps.location.isValid()) {
    lat = gps.location.lat();
    lon = gps.location.lng();
  }
}

// ─── SEND TO THINGSPEAK ───────────────────────────────────────
void sendToThingSpeak(float hr, float spo2, float temp, float acc,
                      float lat, float lon) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected — reconnecting...");
    WiFi.reconnect();
    delay(3000);
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("Reconnect failed, skipping upload.");
      return;
    }
  }

  HTTPClient http;
  String url = String(TS_SERVER) +
    "?api_key="  + TS_API_KEY  +
    "&field1="   + String(hr,   1) +
    "&field2="   + String(spo2, 1) +
    "&field3="   + String(temp, 2) +
    "&field4="   + String(acc,  3) +
    "&field5="   + String(lat,  6) +
    "&field6="   + String(lon,  6);

  http.begin(url);
  int code = http.GET();
  if (code > 0)
    Serial.println("ThingSpeak OK → HTTP " + String(code));
  else
    Serial.println("ThingSpeak FAIL → " + http.errorToString(code));
  http.end();
}

// ─── MAIN LOOP ───────────────────────────────────────────────
unsigned long lastSend = 0;

void loop() {
  // Keep feeding GPS parser continuously
  while (gpsSerial.available())
    gps.encode(gpsSerial.read());

  if (millis() - lastSend < SEND_INTERVAL) return;
  lastSend = millis();

  Serial.println("\n========== READING SENSORS ==========");

  // 1. Heart Rate + SpO2 (MAX30102)
  readMAX30102();
  float hr   = (hrValid   && heartRate > 30 && heartRate < 220) ? (float)heartRate : 0.0;
  float spo2 = (spo2Valid && spo2Val   > 70 && spo2Val   < 101) ? (float)spo2Val   : 0.0;

  // 2. Temperature (DS18B20)
  ds18b20.requestTemperatures();
  float temp = ds18b20.getTempCByIndex(0);
  if (temp == DEVICE_DISCONNECTED_C || temp < 0 || temp > 50) temp = 0.0;

  // 3. Acceleration (MPU6050 via FastIMU)
  mpu.update();
  mpu.getAccel(&accelData);
  float acc = sqrt(
    accelData.accelX * accelData.accelX +
    accelData.accelY * accelData.accelY +
    accelData.accelZ * accelData.accelZ
  );

  // 4. GPS (NEO-6M)
  float lat = 0.0, lon = 0.0;
  readGPS(lat, lon);

  // 5. Edge AI Risk Score
  int    riskScore = computeRiskScore(hr, spo2, temp, acc);
  String riskLabel = getRiskLabel(riskScore);

  // Print to Serial Monitor
  Serial.println("---------- VITALS ----------");
  Serial.println("HR:    " + (hr   > 0 ? String(hr,   1) + " bpm"  : "-- (no finger detected)"));
  Serial.println("SpO2:  " + (spo2 > 0 ? String(spo2, 1) + " %"    : "-- (no finger detected)"));
  Serial.println("Temp:  " + (temp > 0 ? String(temp, 2) + " C"    : "-- (sensor error)"));
  Serial.println("Acc:   " + String(acc, 3) + " g");
  Serial.println("GPS:   " + (lat != 0 ? String(lat, 6) + ", " + String(lon, 6) : "No fix yet (move near window)"));
  Serial.println("---------- EDGE AI ----------");
  Serial.println("Risk Score: " + String(riskScore) + "/100 → " + riskLabel);
  Serial.println("-----------------------------");

  // 6. Upload to ThingSpeak
  sendToThingSpeak(hr, spo2, temp, acc, lat, lon);
}
