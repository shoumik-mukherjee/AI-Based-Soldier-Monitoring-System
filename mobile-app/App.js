// ─────────────────────────────────────────────────────────────
//  WARTECH INNOVATORS — Soldier Health Monitoring Mobile App
//  React Native + Expo
//
//  Install deps before running:
//    npx create-expo-app SoldierApp
//    cd SoldierApp
//    npm install @react-native-async-storage/async-storage expo-notifications
//    Replace App.js with this file
//    npx expo start
//
//  Default credentials:
//    commander / commander123
//    admin     / admin123
// ─────────────────────────────────────────────────────────────

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, StatusBar, Animated, Dimensions, Modal,
  Alert, ActivityIndicator, FlatList, RefreshControl,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// ── Change to your PC's local IP when testing on physical device ──
const API_BASE = 'http://127.0.0.1:5000';

const { width: SW, height: SH } = Dimensions.get('window');

// ─── THEME ────────────────────────────────────────────────────
const C = {
  bg:      '#0a0c0f',
  bg2:     '#111418',
  bg3:     '#181c22',
  border:  'rgba(255,255,255,0.07)',
  border2: 'rgba(255,255,255,0.15)',
  green:   '#00ff9d',
  greenDim:'rgba(0,255,157,0.12)',
  amber:   '#f5a623',
  amberDim:'rgba(245,166,35,0.12)',
  red:     '#ff3b3b',
  redDim:  'rgba(255,59,59,0.12)',
  purple:  '#bf5fff',
  purpleDim:'rgba(191,95,255,0.12)',
  text:    '#c8cdd8',
  textDim: '#4a5060',
  textBright:'#e8ecf4',
  mono:    'monospace',
};

const STATE_COLORS = {
  normal:   { fg: C.green,  bg: C.greenDim,  border: 'rgba(0,255,157,0.3)' },
  warning:  { fg: C.amber,  bg: C.amberDim,  border: 'rgba(245,166,35,0.3)' },
  fatigue:  { fg: C.amber,  bg: C.amberDim,  border: 'rgba(245,166,35,0.3)' },
  injury:   { fg: C.purple, bg: C.purpleDim, border: 'rgba(191,95,255,0.3)' },
  critical: { fg: C.red,    bg: C.redDim,    border: 'rgba(255,59,59,0.3)' },
};

// ─── MOCK CREDENTIALS (used in demo mode) ────────────────────
const MOCK_USERS = [
  { id: 'CMD-001', username: 'commander', password: 'commander123', role: 'Commander', clearance: 'ALPHA' },
  { id: 'ADM-001', username: 'admin',     password: 'admin123',     role: 'Admin',     clearance: 'OMEGA' },
];

// ─── MOCK SOLDIER DATA ────────────────────────────────────────
function makeSoldiers() {
  const t = Date.now() / 1000;
  const w = Math.sin(t * 0.3) * 0.5;
  const jit = (v, a) => +(v + (Math.random() - 0.5) * 2 * a).toFixed(2);

  return [
    {
      id: 'S001', name: 'Alpha Unit', initials: 'AU', channel: '3358625',
      hr: jit(72 + w * 4, 3), spo2: jit(98, 0.5), temp: jit(36.8, 0.1),
      acc: jit(0.6, 0.05), prediction: 'NORMAL', color: 'normal',
      alert: 'NORMAL ✅', risk_score: 12,
      lat: 12.9272 + Math.sin(t * 0.05) * 0.002,
      lon: 77.5020 + Math.cos(t * 0.04) * 0.002,
    },
    {
      id: 'S002', name: 'Bravo Unit', initials: 'BU', channel: '3358626',
      hr: jit(130 + w * 8, 4), spo2: jit(94, 0.4), temp: jit(38.3, 0.15),
      acc: jit(1.2, 0.1), prediction: 'FATIGUE', color: 'fatigue',
      alert: 'FATIGUE ⚠️', risk_score: 45,
      lat: 12.9800, lon: 77.6100,
    },
    {
      id: 'S003', name: 'Charlie Unit', initials: 'CU', channel: '3358627',
      hr: jit(160 + w * 10, 6), spo2: jit(88, 0.8), temp: jit(39.8, 0.2),
      acc: jit(3.5, 0.3), prediction: 'CRITICAL', color: 'critical',
      alert: 'CRITICAL 🚨', risk_score: 87,
      lat: 12.9650, lon: 77.5800,
    },
    {
      id: 'S004', name: 'Delta Unit', initials: 'DU', channel: '3358628',
      hr: jit(145 + w * 6, 4), spo2: jit(96, 0.3), temp: jit(36.6, 0.1),
      acc: jit(0.8, 0.08), prediction: 'FATIGUE', color: 'fatigue',
      alert: 'FATIGUE ⚠️', risk_score: 42,
      lat: 12.9900, lon: 77.6200,
    },
    {
      id: 'S005', name: 'Echo Unit', initials: 'EU', channel: '3358629',
      hr: jit(132 + w * 10, 5), spo2: jit(92, 0.6), temp: jit(37.6, 0.2),
      acc: jit(3.0, 0.3), prediction: 'INJURY', color: 'injury',
      alert: 'INJURY 🩹', risk_score: 63,
      lat: 12.9750, lon: 77.5850,
    },
  ];
}

// ─── NOTIFICATION HELPER ──────────────────────────────────────
// Uses in-app modal alerts (Expo push needs device token in prod)
function useAlerts(soldiers) {
  const prevRef = useRef({});
  useEffect(() => {
    if (!soldiers) return;
    soldiers.forEach(s => {
      const prev = prevRef.current[s.id];
      if (prev && prev !== s.color && s.color === 'critical') {
        Alert.alert(
          '🚨 CRITICAL ALERT',
          `${s.name} (${s.id}) has entered CRITICAL status!\nHR: ${s.hr} bpm | SpO₂: ${s.spo2}%`,
          [{ text: 'ACKNOWLEDGE', style: 'destructive' }]
        );
      }
      prevRef.current[s.id] = s.color;
    });
  }, [soldiers]);
}

// ═══════════════════════════════════════════════════════════════
//  LOGIN SCREEN
// ═══════════════════════════════════════════════════════════════
function LoginScreen({ onLogin }) {
  const [uid, setUid]       = useState('');
  const [pass, setPass]     = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');
  const [showPass, setShowPass] = useState(false);

  const shakeAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim  = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 900, useNativeDriver: true }).start();
  }, []);

  const shake = () => {
    Animated.sequence([
      Animated.timing(shakeAnim, { toValue: 10,  duration: 60, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: -10, duration: 60, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: 8,   duration: 60, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: -8,  duration: 60, useNativeDriver: true }),
      Animated.timing(shakeAnim, { toValue: 0,   duration: 60, useNativeDriver: true }),
    ]).start();
  };

  const handleLogin = async () => {
    if (!uid.trim() || !pass.trim()) {
      setError('Enter credentials to proceed.');
      shake(); return;
    }
    setLoading(true); setError('');

    // Try real backend first
    try {
      const res = await fetch(`${API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: uid.trim(), password: pass }),
        signal: AbortSignal.timeout(4000),
      });
      const data = await res.json();
      if (res.ok && data.token) {
        await AsyncStorage.setItem('jwt', data.token);
        await AsyncStorage.setItem('user', JSON.stringify(data.user || { username: uid }));
        onLogin(data.user || { username: uid, role: 'Commander' }, false);
        setLoading(false); return;
      }
    } catch (_) { /* backend offline — fall through to demo mode */ }

    // Demo mode — check mock credentials
    const user = MOCK_USERS.find(
      u => u.username.toLowerCase() === uid.trim().toLowerCase() && u.password === pass
    );
    if (user) {
      await AsyncStorage.setItem('user', JSON.stringify(user));
      onLogin(user, true);
    } else {
      setError('Invalid credentials. Access denied.');
      shake();
    }
    setLoading(false);
  };

  return (
    <View style={s.loginBg}>
      <StatusBar barStyle="light-content" backgroundColor={C.bg} />

      {/* Grid lines background */}
      <View style={s.gridOverlay} pointerEvents="none">
        {[...Array(8)].map((_, i) => (
          <View key={i} style={[s.gridLine, { top: i * (SH / 8) }]} />
        ))}
      </View>

      <Animated.View style={[s.loginCard, { opacity: fadeAnim,
        transform: [{ translateX: shakeAnim }] }]}>

        {/* Logo */}
        <View style={s.logoRow}>
          <View style={s.shield} />
          <View style={s.logoText}>
            <Text style={s.brand}>WARTECH <Text style={s.brandAccent}>INNOVATORS</Text></Text>
            <Text style={s.brandSub}>SOLDIER HEALTH MONITORING SYSTEM</Text>
          </View>
        </View>

        <View style={s.divider} />

        <Text style={s.loginTitle}>COMMAND ACCESS</Text>
        <Text style={s.loginSub}>Authorised Personnel Only · RV College of Engineering</Text>

        {/* User ID */}
        <View style={s.fieldWrap}>
          <Text style={s.fieldLabel}>COMMANDER ID / USERNAME</Text>
          <View style={s.inputWrap}>
            <Text style={s.inputIcon}>◈</Text>
            <TextInput
              style={s.input}
              value={uid}
              onChangeText={setUid}
              placeholder="Enter username"
              placeholderTextColor={C.textDim}
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>
        </View>

        {/* Password */}
        <View style={s.fieldWrap}>
          <Text style={s.fieldLabel}>ACCESS CODE</Text>
          <View style={s.inputWrap}>
            <Text style={s.inputIcon}>◉</Text>
            <TextInput
              style={[s.input, { flex: 1 }]}
              value={pass}
              onChangeText={setPass}
              placeholder="Enter password"
              placeholderTextColor={C.textDim}
              secureTextEntry={!showPass}
              autoCapitalize="none"
            />
            <TouchableOpacity onPress={() => setShowPass(p => !p)} style={s.eyeBtn}>
              <Text style={s.eyeText}>{showPass ? '🙈' : '👁'}</Text>
            </TouchableOpacity>
          </View>
        </View>

        {error ? (
          <View style={s.errorBox}>
            <Text style={s.errorText}>⛔ {error}</Text>
          </View>
        ) : null}

        <TouchableOpacity
          style={[s.loginBtn, loading && { opacity: 0.6 }]}
          onPress={handleLogin}
          disabled={loading}
          activeOpacity={0.8}
        >
          {loading
            ? <ActivityIndicator color={C.bg} size="small" />
            : <Text style={s.loginBtnText}>▶  AUTHENTICATE &amp; ENTER</Text>
          }
        </TouchableOpacity>

        <Text style={s.hint}>Demo: commander / commander123</Text>
      </Animated.View>
    </View>
  );
}

// ═══════════════════════════════════════════════════════════════
//  SOLDIER DETAIL MODAL
// ═══════════════════════════════════════════════════════════════
function DetailModal({ soldier: s, visible, onClose, onSOS }) {
  if (!s) return null;
  const col = STATE_COLORS[s.color] || STATE_COLORS.normal;
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (s.color === 'critical' || s.color === 'injury') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulse, { toValue: 1.06, duration: 600, useNativeDriver: true }),
          Animated.timing(pulse, { toValue: 1,    duration: 600, useNativeDriver: true }),
        ])
      ).start();
    }
    return () => pulse.stopAnimation();
  }, [s.color]);

  const VitalBar = ({ label, value, max, color }) => (
    <View style={sd.vitalRow}>
      <Text style={sd.vitalLabel}>{label}</Text>
      <View style={sd.barTrack}>
        <View style={[sd.barFill, { width: `${Math.min((value / max) * 100, 100)}%`, backgroundColor: color }]} />
      </View>
      <Text style={[sd.vitalVal, { color }]}>{value}</Text>
    </View>
  );

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={sd.overlay}>
        <View style={sd.sheet}>

          {/* Header */}
          <View style={[sd.sheetHeader, { borderBottomColor: col.border }]}>
            <View style={[sd.bigAvatar, { backgroundColor: col.bg, borderColor: col.border }]}>
              <Text style={[sd.bigAvatarText, { color: col.fg }]}>{s.initials}</Text>
            </View>
            <View style={{ flex: 1, marginLeft: 14 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Text style={sd.soldierName}>{s.name}</Text>
                {s.id === 'S001'
                  ? <View style={ds.liveTag}><Text style={ds.liveTagTxt}>● LIVE</Text></View>
                  : <View style={ds.simTag}><Text style={ds.simTagTxt}>SIM</Text></View>
                }
              </View>
              <Text style={sd.soldierId}>{s.id} · CH {s.channel}</Text>
              <Animated.View style={[sd.alertBadge, { backgroundColor: col.bg, borderColor: col.border,
                transform: [{ scale: pulse }] }]}>
                <Text style={[sd.alertText, { color: col.fg }]}>{s.alert}</Text>
              </Animated.View>
            </View>
            <TouchableOpacity onPress={onClose} style={sd.closeBtn}>
              <Text style={sd.closeTxt}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator={false}>

            {/* Risk Score */}
            <View style={sd.section}>
              <Text style={sd.secTitle}>EDGE AI RISK SCORE</Text>
              <View style={sd.riskRow}>
                <Text style={[sd.riskNum, {
                  color: s.risk_score >= 70 ? C.red : s.risk_score >= 55 ? C.purple
                       : s.risk_score >= 40 ? C.amber : C.green
                }]}>{s.risk_score}</Text>
                <Text style={sd.riskOf}>/100</Text>
              </View>
              <View style={sd.riskTrack}>
                <View style={[sd.riskFill, {
                  width: `${s.risk_score}%`,
                  backgroundColor: s.risk_score >= 70 ? C.red : s.risk_score >= 55 ? C.purple
                                 : s.risk_score >= 40 ? C.amber : C.green,
                }]} />
              </View>
              <View style={sd.aiRow}>
                <Text style={sd.aiLabel}>🧠 Decision Tree Prediction:</Text>
                <Text style={[sd.aiVal, { color: col.fg }]}>{s.prediction}</Text>
              </View>
            </View>

            {/* Vitals */}
            <View style={sd.section}>
              <Text style={sd.secTitle}>VITAL SIGNS</Text>
              <VitalBar label="Heart Rate" value={`${Math.round(s.hr)} bpm`}
                max={200} color={s.hr > 150 ? C.red : s.hr > 120 ? C.amber : C.green} />
              <VitalBar label="SpO₂" value={`${s.spo2}%`}
                max={100} color={s.spo2 < 90 ? C.red : s.spo2 < 94 ? C.amber : C.green} />
              <VitalBar label="Temperature" value={`${s.temp}°C`}
                max={41} color={s.temp > 39 ? C.red : s.temp > 38 ? C.amber : C.green} />
              <VitalBar label="Acceleration" value={`${s.acc}g`}
                max={5} color={s.acc > 3 ? C.red : s.acc > 2 ? C.purple : s.acc > 1.5 ? C.amber : C.green} />
            </View>

            {/* GPS */}
            <View style={sd.section}>
              <Text style={sd.secTitle}>LAST KNOWN POSITION</Text>
              <View style={sd.gpsBox}>
                <View style={sd.gpsRow}>
                  <Text style={sd.gpsKey}>Latitude</Text>
                  <Text style={sd.gpsVal}>{s.lat.toFixed(6)}° N</Text>
                </View>
                <View style={sd.gpsRow}>
                  <Text style={sd.gpsKey}>Longitude</Text>
                  <Text style={sd.gpsVal}>{s.lon.toFixed(6)}° E</Text>
                </View>
                <View style={sd.gpsRow}>
                  <Text style={sd.gpsKey}>GPS Status</Text>
                  <Text style={[sd.gpsVal, { color: C.green }]}>FIXED ●</Text>
                </View>
                <View style={sd.gpsRow}>
                  <Text style={sd.gpsKey}>Data Source</Text>
                  <Text style={[sd.gpsVal, { color: s.id === 'S001' ? C.green : C.textDim }]}>
                    {s.id === 'S001' ? 'ThingSpeak · LIVE' : 'Simulated · SIM'}
                  </Text>
                </View>
                <View style={sd.gpsRow}>
                  <Text style={sd.gpsKey}>Region</Text>
                  <Text style={sd.gpsVal}>Bengaluru, KA</Text>
                </View>
              </View>
            </View>

            {/* SOS Button */}
            <View style={sd.section}>
              <Text style={sd.secTitle}>EMERGENCY ACTIONS</Text>
              <TouchableOpacity
                style={sd.sosBtn}
                onPress={() => onSOS(s)}
                activeOpacity={0.75}
              >
                <Text style={sd.sosBtnIcon}>🆘</Text>
                <View>
                  <Text style={sd.sosBtnText}>SEND SOS ALERT</Text>
                  <Text style={sd.sosBtnSub}>Dispatches emergency to command center</Text>
                </View>
              </TouchableOpacity>
            </View>

            <View style={{ height: 32 }} />
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

// ═══════════════════════════════════════════════════════════════
//  MAIN DASHBOARD SCREEN
// ═══════════════════════════════════════════════════════════════
function DashboardScreen({ user, demoMode, onLogout }) {
  const [soldiers, setSoldiers]     = useState(makeSoldiers());
  const [selected, setSelected]     = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [sosLog, setSosLog]         = useState([]);
  const [showSosLog, setShowSosLog] = useState(false);
  const timerRef = useRef(null);

  useAlerts(soldiers);

  const fetchData = useCallback(async () => {
    if (demoMode) {
      setSoldiers(makeSoldiers());
      setLastUpdate(new Date());
      return;
    }
    try {
      const token = await AsyncStorage.getItem('jwt');
      const res = await fetch(`${API_BASE}/api/soldiers`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(5000),
      });
      if (res.ok) {
        const data = await res.json();
        setSoldiers(data);
        setLastUpdate(new Date());
      }
    } catch (_) {
      setSoldiers(makeSoldiers());
    }
  }, [demoMode]);

  useEffect(() => {
    fetchData();
    timerRef.current = setInterval(fetchData, 10000);
    return () => clearInterval(timerRef.current);
  }, [fetchData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const handleSOS = (soldier) => {
    const entry = {
      id: Date.now(),
      soldier: soldier.name,
      sid: soldier.id,
      time: new Date().toLocaleTimeString(),
      status: soldier.prediction,
      risk: soldier.risk_score,
    };
    setSosLog(prev => [entry, ...prev]);
    Alert.alert(
      '🆘 SOS DISPATCHED',
      `Emergency alert sent for ${soldier.name} (${soldier.id})\n\nRisk: ${soldier.risk_score}/100\nStatus: ${soldier.prediction}\n\nCommand center notified.`,
      [{ text: 'CONFIRMED', style: 'default' }]
    );
  };

  const critical = soldiers.filter(s => s.color === 'critical').length;
  const injury   = soldiers.filter(s => s.color === 'injury').length;
  const fatigue  = soldiers.filter(s => s.color === 'fatigue' || s.color === 'warning').length;
  const avgHr    = Math.round(soldiers.reduce((a, s) => a + s.hr, 0) / soldiers.length);
  const avgSpo2  = (soldiers.reduce((a, s) => a + s.spo2, 0) / soldiers.length).toFixed(1);

  const SoldierCard = ({ item: s }) => {
    const col = STATE_COLORS[s.color] || STATE_COLORS.normal;
    const pulse = useRef(new Animated.Value(1)).current;

    useEffect(() => {
      if (s.color === 'critical') {
        const loop = Animated.loop(
          Animated.sequence([
            Animated.timing(pulse, { toValue: 1.03, duration: 700, useNativeDriver: true }),
            Animated.timing(pulse, { toValue: 1,    duration: 700, useNativeDriver: true }),
          ])
        );
        loop.start();
        return () => loop.stop();
      }
    }, [s.color]);

    return (
      <TouchableOpacity onPress={() => setSelected(s)} activeOpacity={0.85}>
        <Animated.View style={[ds.card, { borderColor: col.border,
          transform: [{ scale: pulse }] }]}>
          {/* Left accent bar */}
          <View style={[ds.accentBar, { backgroundColor: col.fg }]} />

          <View style={ds.cardInner}>
            {/* Top row */}
            <View style={ds.cardTop}>
              <View style={[ds.avatar, { backgroundColor: col.bg, borderColor: col.border }]}>
                <Text style={[ds.avatarText, { color: col.fg }]}>{s.initials}</Text>
              </View>
              <View style={{ flex: 1, marginLeft: 10 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Text style={ds.soldierName}>{s.name}</Text>
                  {s.id === 'S001' && !demoMode
                    ? <View style={ds.liveTag}><Text style={ds.liveTagTxt}>● LIVE</Text></View>
                    : <View style={ds.simTag}><Text style={ds.simTagTxt}>SIM</Text></View>
                  }
                </View>
                <Text style={ds.soldierId}>{s.id} · CH {s.channel}</Text>
              </View>
              <View style={[ds.badge, { backgroundColor: col.bg, borderColor: col.border }]}>
                <Text style={[ds.badgeText, { color: col.fg }]}>{s.prediction}</Text>
              </View>
            </View>

            {/* Vitals row */}
            <View style={ds.vitalsRow}>
              <View style={ds.vitalBox}>
                <Text style={ds.vLabel}>HR</Text>
                <Text style={[ds.vVal, { color: s.hr > 150 ? C.red : s.hr > 120 ? C.amber : C.green }]}>
                  {Math.round(s.hr)}
                </Text>
                <Text style={ds.vUnit}>bpm</Text>
              </View>
              <View style={ds.vDivider} />
              <View style={ds.vitalBox}>
                <Text style={ds.vLabel}>SpO₂</Text>
                <Text style={[ds.vVal, { color: s.spo2 < 90 ? C.red : s.spo2 < 94 ? C.amber : C.green }]}>
                  {s.spo2}
                </Text>
                <Text style={ds.vUnit}>%</Text>
              </View>
              <View style={ds.vDivider} />
              <View style={ds.vitalBox}>
                <Text style={ds.vLabel}>TEMP</Text>
                <Text style={[ds.vVal, { color: s.temp > 39 ? C.red : s.temp > 38 ? C.amber : C.green }]}>
                  {s.temp}
                </Text>
                <Text style={ds.vUnit}>°C</Text>
              </View>
              <View style={ds.vDivider} />
              <View style={ds.vitalBox}>
                <Text style={ds.vLabel}>ACC</Text>
                <Text style={[ds.vVal, { color: s.acc > 3 ? C.red : s.acc > 1.5 ? C.amber : C.green }]}>
                  {s.acc}
                </Text>
                <Text style={ds.vUnit}>g</Text>
              </View>
            </View>

            {/* Risk bar */}
            <View style={ds.riskWrap}>
              <View style={ds.riskHeader}>
                <Text style={ds.riskLabel}>RISK SCORE</Text>
                <Text style={[ds.riskNum, { color: col.fg }]}>{s.risk_score}/100</Text>
              </View>
              <View style={ds.riskTrack}>
                <View style={[ds.riskFill, {
                  width: `${s.risk_score}%`,
                  backgroundColor: s.risk_score >= 70 ? C.red : s.risk_score >= 55 ? C.purple
                                 : s.risk_score >= 40 ? C.amber : C.green,
                }]} />
              </View>
            </View>

            {/* GPS */}
            <View style={ds.gpsRow}>
              <Text style={ds.gpsIcon}>◎</Text>
              <Text style={ds.gpsTxt}>{s.lat.toFixed(5)}°N  {s.lon.toFixed(5)}°E</Text>
              <Text style={[ds.gpsFixed, { color: C.green }]}>GPS FIXED</Text>
            </View>
          </View>
        </Animated.View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <StatusBar barStyle="light-content" backgroundColor={C.bg} />

      {/* Top Bar */}
      <View style={ds.topbar}>
        <View style={ds.topLeft}>
          <View style={ds.shieldSmall} />
          <View>
            <Text style={ds.brandSmall}>WARTECH <Text style={{ color: C.green }}>INNOVATORS</Text></Text>
            <Text style={ds.userLine}>
              {user.role || 'Commander'} · {user.username?.toUpperCase()}
              {demoMode ? '  [DEMO]' : ''}
            </Text>
          </View>
        </View>
        <View style={ds.topRight}>
          {sosLog.length > 0 && (
            <TouchableOpacity onPress={() => setShowSosLog(true)} style={ds.sosCountBtn}>
              <Text style={ds.sosCountTxt}>🆘 {sosLog.length}</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity onPress={onLogout} style={ds.logoutBtn}>
            <Text style={ds.logoutTxt}>EXIT</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Summary Strip */}
      <View style={ds.strip}>
        <View style={[ds.stripCard, { borderLeftColor: C.green }]}>
          <Text style={ds.stripLabel}>ONLINE</Text>
          <Text style={ds.stripVal}>{soldiers.length}</Text>
        </View>
        <View style={[ds.stripCard, { borderLeftColor: C.red }]}>
          <Text style={ds.stripLabel}>CRITICAL</Text>
          <Text style={[ds.stripVal, { color: critical > 0 ? C.red : C.textDim }]}>{critical}</Text>
        </View>
        <View style={[ds.stripCard, { borderLeftColor: C.purple }]}>
          <Text style={ds.stripLabel}>INJURY</Text>
          <Text style={[ds.stripVal, { color: injury > 0 ? C.purple : C.textDim }]}>{injury}</Text>
        </View>
        <View style={[ds.stripCard, { borderLeftColor: C.amber }]}>
          <Text style={ds.stripLabel}>FATIGUE</Text>
          <Text style={[ds.stripVal, { color: fatigue > 0 ? C.amber : C.textDim }]}>{fatigue}</Text>
        </View>
        <View style={[ds.stripCard, { borderLeftColor: C.green }]}>
          <Text style={ds.stripLabel}>AVG HR</Text>
          <Text style={ds.stripVal}>{avgHr}</Text>
        </View>
        <View style={[ds.stripCard, { borderLeftColor: C.green }]}>
          <Text style={ds.stripLabel}>AVG SpO₂</Text>
          <Text style={ds.stripVal}>{avgSpo2}</Text>
        </View>
      </View>

      {/* Update bar */}
      <View style={ds.updateBar}>
        <View style={ds.liveDot} />
        <Text style={ds.updateTxt}>
          LIVE · Updated {lastUpdate.toLocaleTimeString()} · Auto-refresh 10s
        </Text>
      </View>

      {/* Soldier Cards */}
      <FlatList
        data={soldiers}
        keyExtractor={s => s.id}
        renderItem={({ item }) => <SoldierCard item={item} />}
        contentContainerStyle={{ padding: 14, paddingBottom: 30 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh}
            tintColor={C.green} colors={[C.green]} />
        }
      />

      {/* Soldier Detail Modal */}
      <DetailModal
        soldier={selected}
        visible={!!selected}
        onClose={() => setSelected(null)}
        onSOS={handleSOS}
      />

      {/* SOS Log Modal */}
      <Modal visible={showSosLog} animationType="fade" transparent onRequestClose={() => setShowSosLog(false)}>
        <View style={sl.overlay}>
          <View style={sl.sheet}>
            <View style={sl.header}>
              <Text style={sl.title}>🆘 SOS LOG</Text>
              <TouchableOpacity onPress={() => setShowSosLog(false)}>
                <Text style={sl.close}>✕</Text>
              </TouchableOpacity>
            </View>
            <ScrollView>
              {sosLog.length === 0
                ? <Text style={sl.empty}>No SOS alerts dispatched.</Text>
                : sosLog.map(e => (
                  <View key={e.id} style={sl.entry}>
                    <Text style={sl.eTime}>{e.time}</Text>
                    <Text style={sl.eName}>{e.soldier} ({e.sid})</Text>
                    <Text style={sl.eStat}>Status: {e.status} · Risk: {e.risk}/100</Text>
                  </View>
                ))
              }
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// ═══════════════════════════════════════════════════════════════
//  ROOT APP
// ═══════════════════════════════════════════════════════════════
export default function App() {
  const [user, setUser]         = useState(null);
  const [demoMode, setDemoMode] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    (async () => {
      const stored = await AsyncStorage.getItem('user');
      if (stored) { setUser(JSON.parse(stored)); }
      setChecking(false);
    })();
  }, []);

  const handleLogin = (u, demo) => { setUser(u); setDemoMode(demo); };

  const handleLogout = async () => {
    await AsyncStorage.removeItem('jwt');
    await AsyncStorage.removeItem('user');
    setUser(null);
  };

  if (checking) {
    return (
      <View style={{ flex: 1, backgroundColor: C.bg, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator color={C.green} size="large" />
        <Text style={{ color: C.textDim, marginTop: 12, fontFamily: C.mono, fontSize: 11 }}>
          INITIALISING SYSTEM...
        </Text>
      </View>
    );
  }

  return user
    ? <DashboardScreen user={user} demoMode={demoMode} onLogout={handleLogout} />
    : <LoginScreen onLogin={handleLogin} />;
}

// ═══════════════════════════════════════════════════════════════
//  STYLES
// ═══════════════════════════════════════════════════════════════

// Login Screen styles
const s = StyleSheet.create({
  loginBg: { flex: 1, backgroundColor: C.bg, justifyContent: 'center', paddingHorizontal: 24 },
  gridOverlay: { ...StyleSheet.absoluteFillObject },
  gridLine: { position: 'absolute', left: 0, right: 0, height: 1, backgroundColor: 'rgba(0,255,157,0.04)' },
  loginCard: { backgroundColor: C.bg2, borderWidth: 1, borderColor: C.border2, borderRadius: 4, padding: 28 },
  logoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  shield: { width: 36, height: 36, backgroundColor: C.green,
    // clip-path not available in RN; use borderRadius trick
    borderRadius: 4, transform: [{ rotate: '45deg' }], marginRight: 14 },
  logoText: {},
  brand: { fontSize: 16, fontWeight: '700', color: C.textBright, letterSpacing: 2, fontFamily: C.mono },
  brandAccent: { color: C.green },
  brandSub: { fontSize: 8, color: C.textDim, letterSpacing: 1.5, marginTop: 2, fontFamily: C.mono },
  divider: { height: 1, backgroundColor: C.border, marginBottom: 20 },
  loginTitle: { fontSize: 20, fontWeight: '700', color: C.textBright, letterSpacing: 3, marginBottom: 4, fontFamily: C.mono },
  loginSub: { fontSize: 10, color: C.textDim, marginBottom: 24, letterSpacing: 0.5 },
  fieldWrap: { marginBottom: 16 },
  fieldLabel: { fontSize: 9, color: C.textDim, letterSpacing: 2, marginBottom: 6, fontFamily: C.mono },
  inputWrap: { flexDirection: 'row', alignItems: 'center', backgroundColor: C.bg3,
    borderWidth: 1, borderColor: C.border, borderRadius: 3, paddingHorizontal: 12, height: 46 },
  inputIcon: { color: C.green, fontSize: 14, marginRight: 10 },
  input: { flex: 1, color: C.textBright, fontSize: 14, fontFamily: C.mono },
  eyeBtn: { padding: 4 },
  eyeText: { fontSize: 16 },
  errorBox: { backgroundColor: 'rgba(255,59,59,0.1)', borderWidth: 1, borderColor: 'rgba(255,59,59,0.3)',
    borderRadius: 3, padding: 10, marginBottom: 14 },
  errorText: { color: C.red, fontSize: 12, fontFamily: C.mono },
  loginBtn: { backgroundColor: C.green, borderRadius: 3, height: 50,
    justifyContent: 'center', alignItems: 'center', marginTop: 4 },
  loginBtnText: { color: C.bg, fontSize: 13, fontWeight: '700', letterSpacing: 2, fontFamily: C.mono },
  hint: { textAlign: 'center', color: C.textDim, fontSize: 10, marginTop: 16, fontFamily: C.mono },
});

// Dashboard styles
const ds = StyleSheet.create({
  topbar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 10, backgroundColor: C.bg2,
    borderBottomWidth: 1, borderBottomColor: C.border },
  topLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  shieldSmall: { width: 24, height: 24, backgroundColor: C.green, borderRadius: 3, transform: [{ rotate: '45deg' }] },
  brandSmall: { fontSize: 13, fontWeight: '700', color: C.textBright, letterSpacing: 1.5, fontFamily: C.mono },
  userLine: { fontSize: 9, color: C.textDim, fontFamily: C.mono, marginTop: 1 },
  topRight: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  sosCountBtn: { backgroundColor: 'rgba(255,59,59,0.15)', borderWidth: 1, borderColor: 'rgba(255,59,59,0.4)',
    borderRadius: 3, paddingHorizontal: 8, paddingVertical: 4 },
  sosCountTxt: { color: C.red, fontSize: 11, fontFamily: C.mono, fontWeight: '700' },
  logoutBtn: { backgroundColor: C.bg3, borderWidth: 1, borderColor: C.border,
    borderRadius: 3, paddingHorizontal: 10, paddingVertical: 5 },
  logoutTxt: { color: C.textDim, fontSize: 10, fontFamily: C.mono, letterSpacing: 1 },

  strip: { flexDirection: 'row', backgroundColor: C.bg2, borderBottomWidth: 1, borderBottomColor: C.border },
  stripCard: { flex: 1, borderLeftWidth: 2, paddingVertical: 8, paddingHorizontal: 6, alignItems: 'center' },
  stripLabel: { fontSize: 7, color: C.textDim, fontFamily: C.mono, letterSpacing: 1, marginBottom: 2 },
  stripVal: { fontSize: 16, fontWeight: '700', color: C.textBright, fontFamily: C.mono },

  updateBar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 5,
    backgroundColor: C.bg3 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: C.green, marginRight: 8 },
  updateTxt: { fontSize: 9, color: C.textDim, fontFamily: C.mono, letterSpacing: 0.5 },

  card: { backgroundColor: C.bg2, borderWidth: 1, borderRadius: 4, marginBottom: 12,
    flexDirection: 'row', overflow: 'hidden' },
  accentBar: { width: 3 },
  cardInner: { flex: 1, padding: 14 },
  cardTop: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  avatar: { width: 38, height: 38, borderRadius: 4, borderWidth: 1,
    justifyContent: 'center', alignItems: 'center' },
  avatarText: { fontSize: 13, fontWeight: '700', fontFamily: C.mono },
  soldierName: { fontSize: 14, fontWeight: '700', color: C.textBright },
  soldierId: { fontSize: 10, color: C.textDim, fontFamily: C.mono, marginTop: 1 },
  badge: { borderWidth: 1, borderRadius: 3, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontSize: 9, fontWeight: '700', letterSpacing: 1, fontFamily: C.mono },

  vitalsRow: { flexDirection: 'row', backgroundColor: C.bg3, borderRadius: 3,
    paddingVertical: 10, marginBottom: 10 },
  vitalBox: { flex: 1, alignItems: 'center' },
  vDivider: { width: 1, backgroundColor: C.border },
  vLabel: { fontSize: 8, color: C.textDim, fontFamily: C.mono, letterSpacing: 1, marginBottom: 3 },
  vVal: { fontSize: 18, fontWeight: '700', fontFamily: C.mono },
  vUnit: { fontSize: 8, color: C.textDim, marginTop: 1 },

  riskWrap: { marginBottom: 10 },
  riskHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  riskLabel: { fontSize: 9, color: C.textDim, fontFamily: C.mono, letterSpacing: 1 },
  riskNum: { fontSize: 9, fontFamily: C.mono, fontWeight: '700' },
  riskTrack: { height: 4, backgroundColor: C.bg3, borderRadius: 2, overflow: 'hidden' },
  riskFill: { height: '100%', borderRadius: 2 },

  liveTag: { backgroundColor: 'rgba(0,255,157,0.15)', borderWidth: 1,
    borderColor: 'rgba(0,255,157,0.5)', borderRadius: 3, paddingHorizontal: 5, paddingVertical: 1 },
  liveTagTxt: { color: C.green, fontSize: 8, fontFamily: C.mono, fontWeight: '700', letterSpacing: 1 },
  simTag: { backgroundColor: 'rgba(74,80,96,0.3)', borderWidth: 1,
    borderColor: 'rgba(74,80,96,0.6)', borderRadius: 3, paddingHorizontal: 5, paddingVertical: 1 },
  simTagTxt: { color: C.textDim, fontSize: 8, fontFamily: C.mono, letterSpacing: 1 },

  gpsRow: { flexDirection: 'row', alignItems: 'center' },
  gpsIcon: { color: C.textDim, fontSize: 11, marginRight: 6 },
  gpsTxt: { flex: 1, fontSize: 10, color: C.textDim, fontFamily: C.mono },
  gpsFixed: { fontSize: 9, fontFamily: C.mono, letterSpacing: 1 },
});

// Detail Modal styles
const sd = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.75)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: C.bg2, borderTopLeftRadius: 12, borderTopRightRadius: 12,
    maxHeight: SH * 0.9, borderTopWidth: 1, borderColor: C.border2 },
  sheetHeader: { flexDirection: 'row', alignItems: 'center', padding: 18,
    borderBottomWidth: 1 },
  bigAvatar: { width: 52, height: 52, borderRadius: 6, borderWidth: 1.5,
    justifyContent: 'center', alignItems: 'center' },
  bigAvatarText: { fontSize: 18, fontWeight: '700', fontFamily: C.mono },
  soldierName: { fontSize: 17, fontWeight: '700', color: C.textBright },
  soldierId: { fontSize: 10, color: C.textDim, fontFamily: C.mono, marginTop: 2 },
  alertBadge: { alignSelf: 'flex-start', borderWidth: 1, borderRadius: 3,
    paddingHorizontal: 8, paddingVertical: 3, marginTop: 6 },
  alertText: { fontSize: 11, fontWeight: '700', fontFamily: C.mono },
  closeBtn: { padding: 8 },
  closeTxt: { color: C.textDim, fontSize: 18 },

  section: { paddingHorizontal: 18, paddingTop: 18 },
  secTitle: { fontSize: 9, color: C.textDim, fontFamily: C.mono, letterSpacing: 2,
    marginBottom: 12, borderBottomWidth: 1, borderBottomColor: C.border, paddingBottom: 6 },

  riskRow: { flexDirection: 'row', alignItems: 'baseline', marginBottom: 8 },
  riskNum: { fontSize: 40, fontWeight: '700', fontFamily: C.mono },
  riskOf: { fontSize: 16, color: C.textDim, marginLeft: 4 },
  riskTrack: { height: 6, backgroundColor: C.bg3, borderRadius: 3, overflow: 'hidden', marginBottom: 12 },
  riskFill: { height: '100%', borderRadius: 3 },
  aiRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  aiLabel: { fontSize: 11, color: C.textDim },
  aiVal: { fontSize: 12, fontWeight: '700', fontFamily: C.mono },

  vitalRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  vitalLabel: { width: 90, fontSize: 11, color: C.textDim },
  barTrack: { flex: 1, height: 6, backgroundColor: C.bg3, borderRadius: 3, overflow: 'hidden', marginHorizontal: 8 },
  barFill: { height: '100%', borderRadius: 3 },
  vitalVal: { width: 65, fontSize: 11, fontFamily: C.mono, textAlign: 'right', fontWeight: '700' },

  gpsBox: { backgroundColor: C.bg3, borderRadius: 4, padding: 12, borderWidth: 1, borderColor: C.border },
  gpsRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5,
    borderBottomWidth: 1, borderBottomColor: C.border },
  gpsKey: { fontSize: 11, color: C.textDim },
  gpsVal: { fontSize: 11, color: C.textBright, fontFamily: C.mono },

  sosBtn: { flexDirection: 'row', alignItems: 'center', gap: 14, backgroundColor: 'rgba(255,59,59,0.12)',
    borderWidth: 1.5, borderColor: 'rgba(255,59,59,0.5)', borderRadius: 4, padding: 16 },
  sosBtnIcon: { fontSize: 28 },
  sosBtnText: { color: C.red, fontSize: 14, fontWeight: '700', fontFamily: C.mono, letterSpacing: 1 },
  sosBtnSub: { color: C.textDim, fontSize: 10, marginTop: 2 },
});

// SOS Log Modal styles
const sl = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', padding: 24 },
  sheet: { backgroundColor: C.bg2, borderWidth: 1, borderColor: 'rgba(255,59,59,0.4)',
    borderRadius: 6, maxHeight: SH * 0.6, padding: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  title: { color: C.red, fontSize: 14, fontWeight: '700', fontFamily: C.mono, letterSpacing: 2 },
  close: { color: C.textDim, fontSize: 18 },
  empty: { color: C.textDim, fontFamily: C.mono, fontSize: 11, textAlign: 'center', paddingVertical: 20 },
  entry: { borderBottomWidth: 1, borderBottomColor: C.border, paddingVertical: 10 },
  eTime: { color: C.textDim, fontSize: 9, fontFamily: C.mono, marginBottom: 3 },
  eName: { color: C.textBright, fontSize: 13, fontWeight: '700' },
  eStat: { color: C.amber, fontSize: 10, fontFamily: C.mono, marginTop: 2 },
});