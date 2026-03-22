# NVDA (Nvidia) - PROFETA Setup Guide

## 📋 Panoramica

**Nvidia Corporation (NVDA)** è uno stock US quotato al NASDAQ.

| Parametro | Valore |
|-----------|--------|
| **Mercato** | NASDAQ (US Stocks) |
| **Orari** | 14:30-21:00 UTC (Lun-Ven) |
| **Festività** | US Market Holidays |
| **Valuta** | USD |
| **Min Deal Size** | ~0.001 (verificare su Capital.com) |

---

## ⚙️ Configurazione

### **1. File Config**

Il file `BKTEST/config-lstm-NVDA.ini` è già stato creato con:
- `epic = NVDA`
- Parametri ereditati da backtest config

### **2. Parametri Consigliati**

Per NVDA, consigliamo di modificare:

```ini
# BKTEST/config-lstm-NVDA.ini

[FUSION]
; NVDA è più volatile di EURUSD
delta_threshold_pct = 0.002    ; 0.2% (vs 0.05% di EURUSD)
min_confidence = 0.35
signal_threshold = 0.55

[CAPITAL_DEMO]
epic = NVDA
trade_size = 10.0          ; Size appropriata per NVDA
sl_pts = 5000              ; Stop loss in punti (5%)
tp_pts = 15000             ; Take profit in punti (15%)
activation_threshold = 0.002  ; 0.2% minimo per trade
```

---

## 🕐 Orari di Trading

### **Mercato Aperto**
- **Lun-Ven**: 14:30-21:00 UTC
- **Sab-Dom**: CHIUSO

### **Esempio (Orario Italiano)**
- **Apertura**: 15:30 CET (Lun-Ven)
- **Chiusura**: 22:00 CET (Lun-Ven)

---

## 📅 Festività US (Mercato Chiuso)

NVDA segue il calendario NYSE/NASDAQ:

### **2026**
| Data | Festività |
|------|-----------|
| 1 Gen | Capodanno |
| 19 Gen | MLK Day |
| 16 Feb | Presidents Day |
| 3 Apr | Good Friday |
| 25 Mag | Memorial Day |
| 19 Giu | Juneteenth |
| 3 Lug | Independence Day (observed) |
| 7 Set | Labor Day |
| 26 Nov | Thanksgiving |
| 27 Nov | Day after Thanksgiving |
| 24 Dic | Christmas Eve |
| 25 Dic | Natale |

### **2027**
| Data | Festività |
|------|-----------|
| 1 Gen | Capodanno |
| 18 Gen | MLK Day |
| 15 Feb | Presidents Day |
| 26 Mar | Good Friday |
| 31 Mag | Memorial Day |
| 18 Giu | Juneteenth |
| 5 Lug | Independence Day (observed) |
| 6 Set | Labor Day |
| 25 Nov | Thanksgiving |
| 26 Nov | Day after Thanksgiving |
| 24 Dic | Christmas Eve |
| 27 Dic | Natale (observed) |

---

## 🚀 Avvio Trading

### **1. Scarica Dati**

```bash
wsl -d Ubuntu-24.04
cd ~/Profeta

# Scarica 8000 ore di training data (~1 anno)
python capital_data_download.py ./Trading_live_data/dati-training_NVDA.csv 8000

# Scarica 1500 ore di trading data
python capital_data_download.py ./Trading_live_data/dati-trading_NVDA.csv 1500
```

### **2. Training Iniziale**

```bash
# Esegui training (prima volta: 30-60 min)
python profeta-universal.py BKTEST/config-lstm-NVDA.ini --epic NVDA
```

### **3. Avvia Servizi**

```bash
# Opzione A: Avvia tutto (EURUSD, BTCUSD, NVDA)
./start-epic-services.sh

# Opzione B: Avvia solo NVDA
nohup ~/miniconda3/envs/profeta/bin/python Run_profeta_real_time.py \
  --config BKTEST/config-lstm-NVDA.ini --epic NVDA \
  > ~/Profeta/logs/orchestrator-NVDA-live.log 2>&1 &

nohup ~/miniconda3/envs/profeta/bin/python profeta_trading_bot.py \
  --config BKTEST/config-lstm-NVDA.ini --epic NVDA \
  > ~/Profeta/logs/trading-bot-NVDA-live.log 2>&1 &
```

---

## 📊 Monitoraggio

### **Log Files**

```bash
# Orchestratore NVDA
tail -f ~/Profeta/logs/orchestrator-NVDA-live.log

# Trading Bot NVDA
tail -f ~/Profeta/logs/trading-bot-NVDA-live.log

# Previsioni
tail -f ~/Profeta/logs/profeta-v5.log | grep NVDA
```

### **Stato Mercato**

```bash
# Verifica se mercato è aperto
python check_market_hybrid.py NVDA

# Output (mercato aperto):
# ✅ Local: NVDA: Stocks - mercato aperto

# Output (mercato chiuso):
# ❌ Local: NVDA: CHIUSO (After hours)
```

---

## ⚠️ Note Importanti

### **1. Volatilità**

NVDA è **molto più volatile** di EURUSD:
- **EURUSD**: ~0.05% al giorno
- **NVDA**: ~2-5% al giorno

**Implicazioni:**
- Aumenta `delta_threshold_pct` a 0.002 (0.2%)
- Aumenta `activation_threshold` a 0.002
- Usa stop loss più ampi (5000+ punti)

### **2. After Hours**

Fuori orario di mercato (14:30-21:00 UTC):
- ❌ Trading bot skipa cicli
- ✅ Orchestratore può fare training
- ✅ Previsioni vengono generate

### **3. Earnings Date**

Gli earnings di Nvidia (4 volte/anno) causano:
- Alta volatilità
- Gap di prezzo all'apertura

**Consiglio:** Monitora date earnings su [Nvidia IR](https://investor.nvidia.com/)

---

## 📈 Esempio di Trading

### **Scenario Tipico**

```
2026-03-24 15:30:00 | INFO | Market check: NVDA - APERTO
2026-03-24 15:30:05 | INFO | SEGNALE LONG SCATTATO: Esecuzione ordine di BUY
2026-03-24 15:30:06 | INFO | Ordine eseguito: BUY NVDA, Size: 10.0
2026-03-24 16:00:00 | INFO | STATUS TRADES: [BUY 10.0 NVDA -> P/L: +25.50 $ (+1.2%)]
2026-03-24 18:00:00 | INFO | STATUS TRADES: [BUY 10.0 NVDA -> P/L: +150.00 $ (+7.5%)]
2026-03-24 18:30:00 | INFO | Take Profit raggiunto (+15%)
2026-03-24 18:30:01 | INFO | Posizione chiusa automaticamente
```

---

## 🔧 Risoluzione Problemi

### **"Mercato chiuso" durante il giorno**

**Causa:** After hours o festività

**Soluzione:**
```bash
python check_market_hybrid.py NVDA
# Verifica se è festività US
```

### **"Min deal size" errore**

**Causa:** Size troppo piccola per NVDA

**Soluzione:**
```ini
[CAPITAL_DEMO]
trade_size = 10.0  ; Aumenta size
```

### **Training troppo lento**

**Causa:** Troppi dati o GPU occupata

**Soluzione:**
```ini
[ENSEMBLE]
num_models = 10  ; Riduci da 20 a 10
```

---

## 📖 Riferimenti

- **Nvidia Investor Relations:** https://investor.nvidia.com/
- **NASDAQ NVDA:** https://www.nasdaq.com/market-activity/stocks/nvda
- **US Market Holidays:** https://www.nyse.com/markets/hours-calendars

---

*Ultimo aggiornamento: Marzo 2026*
