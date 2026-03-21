# PROFETA - Market Status Check (Hybrid System)

## 📋 Panoramica

Il **Market Status Check Ibrido** verifica automaticamente se un mercato è aperto prima di eseguire training e trading, usando:

1. **TradingHours API** (primario)
2. **Fallback locale** con festività per mercato (fallback)
3. **Procedi comunque** (ultimo fallback)

---

## 🎯 Come Funziona

### **Flusso Ibrido**

```
┌─────────────────────────────────────┐
│  Start ciclo trading/training       │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Check: TradingHours API            │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
    OK            FALLITO
       │               │
       ▼               ▼
┌─────────────┐ ┌──────────────────┐
│ Usa risultato│ │ Fallback:        │
└─────────────┘ │ Check locale     │
                │ (festività)      │
                └────────┬─────────┘
                         │
                 ┌───────┴───────┐
                 │               │
              APERTO         CHIUSO
                 │               │
                 ▼               ▼
          ┌──────────┐   ┌──────────────┐
          │ Esegui   │   │ Skip ciclo,  │
          │ training │   │ log motivo   │
          └──────────┘   └──────────────┘
```

---

## 📁 File Utilizzati

### **1. check_market_hybrid.py**

Script principale con:
- **MarketHolidays**: Database festività per mercato (2026-2027)
- **check_market_local()**: Check locale (no API)
- **check_market_tradinghours()**: Check con API
- **check_market_status()**: Funzione ibrida principale

### **2. Integrazioni**

- **Run_profeta_real_time.py**: Check prima di training
- **profeta_trading_bot.py**: Check prima di trading

---

## 🎯 Mercati Supportati

### **Forex (EURUSD, GBPUSD, etc.)**
- **Orari**: Domenica 22:00 - Venerdì 22:00 UTC
- **Weekend**: Chiuso Sabato/Domenica
- **Festività**: Natale, Capodanno, Venerdì Santo

### **Crypto (BTCUSD, ETHUSD, etc.)**
- **Sempre aperto**: 24/7
- **Nessuna festività**

### **US Stocks (AAPL, TSLA, etc.)**
- **Orari**: Lun-Ven 14:30-21:00 UTC
- **Festività US**: MLK Day, Thanksgiving, Natale, etc.

### **UK Stocks (VODL, BP, etc.)**
- **Orari**: Lun-Ven 08:00-16:30 UTC
- **Festività UK**: Boxing Day, Early May, Summer Bank Holiday

---

## 📊 Festività Incluse (2026-2027)

### **Forex**
```
2026:
- 1 Gen: Capodanno
- 3 Apr: Venerdì Santo
- 1 Mag: Labour Day
- 25 Dic: Natale
- 26 Dic: Boxing Day
```

### **US Stocks**
```
2026:
- 1 Gen: Capodanno
- 19 Gen: MLK Day
- 16 Feb: Presidents Day
- 3 Apr: Good Friday
- 25 Mag: Memorial Day
- 19 Giu: Juneteenth
- 3 Lug: Independence Day
- 7 Set: Labor Day
- 26 Nov: Thanksgiving
- 27 Nov: Day after Thanksgiving
- 24 Dic: Christmas Eve
- 25 Dic: Natale
```

### **UK Stocks**
```
2026:
- 1 Gen: Capodanno
- 3 Apr: Good Friday
- 6 Apr: Easter Monday
- 4 Mag: Early May
- 25 Mag: Spring Bank Holiday
- 31 Ago: Summer Bank Holiday
- 25 Dic: Natale
- 28 Dic: Boxing Day (observed)
```

---

## 🚀 Utilizzo

### **Test Singolo**

```bash
wsl -d Ubuntu-24.04
cd ~/Profeta

# Test EURUSD (Forex)
~/miniconda3/envs/profeta/bin/python check_market_hybrid.py EURUSD

# Test BTCUSD (Crypto)
~/miniconda3/envs/profeta/bin/python check_market_hybrid.py BTCUSD

# Test AAPL (US Stocks)
~/miniconda3/envs/profeta/bin/python check_market_hybrid.py AAPL
```

### **Output Tipico (Weekend)**

```
╔════════════════════════════════════════════════════════════════╗
║     PROFETA - MARKET STATUS (Hybrid)                           ║
╚════════════════════════════════════════════════════════════════╝

2026-03-21 17:37:10 | INFO | Market check per EURUSD...
2026-03-21 17:37:10 | INFO | Uso fallback locale...
2026-03-21 17:37:10 | INFO | ✅ Local: EURUSD: Weekend

════════════════════════════════════════════════════════════════
EPIC: EURUSD
Status: CLOSED
Is Open: ❌ NO
Message: EURUSD: Weekend
Reason: Weekend
Provider: local
════════════════════════════════════════════════════════════════

❌ Il mercato è CHIUSO - Skip training/prediction
```

### **Output Tipico (Crypto)**

```
EPIC: BTCUSD
Status: OPEN
Is Open: ✅ YES
Message: BTCUSD: Crypto - mercato sempre aperto
Provider: local

✅ Il mercato è APERTO - Training/Prediction OK
```

---

## ⚙️ Configurazione TradingHours API (Opzionale)

Se vuoi usare TradingHours come primary:

### **1. Ottieni API Key**

1. Vai su: https://tradinghours.com/api
2. Registrati
3. Ricevi API key via email

### **2. Aggiungi al Config**

```ini
# BKTEST/config-lstm-backtest.ini

[MARKET_CHECK]
provider = tradinghours
api_key = th_xxxxxxxxxxxxxxxx
```

### **3. Testa**

```bash
python check_market_hybrid.py EURUSD
```

Se TradingHours funziona, vedrai `Provider: TradingHours` invece di `Provider: local`.

---

## 📈 Log Esempi

### **Orchestratore (Training)**

```
2026-03-23 09:00:00,123 | INFO | Verifica stato mercato...
2026-03-23 09:00:00,456 | INFO | ✅ EURUSD: Forex - mercato aperto (Provider: local)
2026-03-23 09:00:00,456 | INFO | ✅ Mercato APERTO - Esecuzione training/prediction
```

### **Trading Bot**

```
2026-03-23 10:30:00,789 | INFO | ❌ Mercato EURUSD: CHIUSO (Weekend) - Skip trading cycle
```

---

## ⚠️ Risoluzione Problemi

### **"API key non trovata"**

**Normale**: Il fallback locale funziona senza API key.

Se vuoi TradingHours:
```ini
[MARKET_CHECK]
api_key = th_xxxxxxxxxxxxxxxx
```

### **"401 Unauthorized"**

**Causa**: API key TradingHours non valida per v3

**Soluzione**: Usa fallback locale (già automatico)

### **Festività Mancanti**

**Soluzione**: Aggiungi a `MarketHolidays` in `check_market_hybrid.py`:

```python
FOREX_HOLIDAYS = {
    2027: [
        date(2027, 1, 1),
        # Aggiungi altre festività
    ],
    2028: [
        # ...
    ]
}
```

---

## 🎯 Best Practices

### **1. Aggiorna Festività Annualmente**

A fine anno, aggiungi festività per anno nuovo:

```python
FOREX_HOLIDAYS = {
    2026: [...],
    2027: [...],
    2028: [  # Aggiungi a Dicembre
        date(2028, 1, 1),
        date(2028, 12, 25),
        date(2028, 12, 26),
    ]
}
```

### **2. Testa Prima di Lunedì**

Verifica che il check funzioni:

```bash
# Domenica: dovrebbe essere CHIUSO
python check_market_hybrid.py EURUSD

# Lunedì: dovrebbe essere APERTO
python check_market_hybrid.py EURUSD
```

### **3. Log Monitor**

Monitora i log per verificare check:

```bash
tail -f ~/Profeta/logs/orchestrator-EURUSD.log | grep "Mercato"
```

---

## 📖 Riferimenti

- **TradingHours Docs**: https://docs.tradinghours.com/
- **Market Holidays**: Aggiornare annualmente
- **PROFETA Docs**: MARKET-CHECK-GUIDE.md, MULTI-EPIC-MANAGER.md

---

*Ultimo aggiornamento: Marzo 2026*
