# TradingHours API - Setup Guide

## 🔑 Configurazione API Key

### **1. Aggiungi al File di Configurazione**

Modifica `BKTEST/config-lstm-backtest.ini`:

```ini
[MARKET_CHECK]
; TradingHours API Configuration
provider = tradinghours
api_key = th_xxxxxxxxxxxxxxxx  ; La tua API key

; Opzionale: fallback su Capital.com se TradingHours fallisce
fallback = capital
```

### **2. Ottieni API Key (Se Non Ce L'hai)**

1. Vai su: https://tradinghours.com/api
2. Clicca "Get API Key" o "Sign Up"
3. Registrati con email
4. Ricevi la key via email
5. Copia nel file di configurazione

---

## 📋 Test del Setup

### **Test 1: Verifica Configurazione**

```bash
wsl -d Ubuntu-24.04
cd ~/Profeta

# Test EURUSD (Forex)
~/miniconda3/envs/profeta/bin/python check_market_th.py EURUSD
```

**Output Atteso (Mercato Aperto):**
```
EPIC: EURUSD
Market Type: forex
Status: OPEN
Is Open: ✅ YES
Message: Mercato EURUSD (forex): APERTO
Provider: TradingHours

✅ Il mercato è APERTO - Training/Prediction OK
```

**Output Atteso (Mercato Chiuso - Weekend):**
```
EPIC: EURUSD
Market Type: forex
Status: CLOSED
Is Open: ❌ NO
Message: Mercato EURUSD (forex): CHIUSO (Weekend)
Reason: Weekend
Next Open: 2026-03-23T22:00:00Z
Provider: TradingHours

❌ Il mercato è CHIUSO - Skip training/prediction
```

### **Test 2: Verifica BTCUSD (Crypto)**

```bash
~/miniconda3/envs/profeta/bin/python check_market_th.py BTCUSD
```

**Output Atteso:**
```
EPIC: BTCUSD
Market Type: crypto
Status: OPEN
Is Open: ✅ YES
Message: Mercato BTCUSD (crypto): APERTO
Provider: TradingHours

✅ Il mercato è APERTO - Training/Prediction OK
```

---

## 🎯 Integrazione con PROFETA

### **Orchestratore (Run_profeta_real_time.py)**

Il check TradingHours viene chiamato automaticamente prima di ogni ciclo:

```python
# Check mercato prima di training
if not check_market_open(config_path, epic, logger):
    logger.info("Mercato CHIUSO - Skip ciclo")
    # Attendi prossima ora
else:
    logger.info("Mercato APERTO - Esegui training")
    run_scripts(...)
```

### **Trading Bot**

Il trading bot usa TradingHours per:
- Verificare se eseguire trade
- Evitare ordini a mercato chiuso
- Loggare stato mercato

---

## 📊 Market Types Supportati

| Market Type | Epic Examples | Orari |
|-------------|---------------|-------|
| **forex** | EURUSD, GBPUSD, USDJPY | Dom 22:00 - Ven 22:00 UTC |
| **crypto** | BTCUSD, ETHUSD, XRPUSD | 24/7 Sempre aperto |
| **stocks** | AAPL, TSLA, NVDA | Lun-Ven 14:30-21:00 UTC |

---

## ⚠️ Risoluzione Problemi

### **"API key non trovata"**

**Soluzione:**
```ini
# Aggiungi a BKTEST/config-lstm-backtest.ini
[MARKET_CHECK]
api_key = th_xxxxxxxxxxxxxxxx
```

### **"Errore HTTP 401"**

**Causa:** API key non valida

**Soluzione:**
1. Verifica key nel config
2. Contatta support@tradinghours.com
3. Rigenera nuova key

### **"Errore HTTP 429" (Rate Limit)**

**Causa:** Troppe richieste

**Soluzione:**
- Free tier: 1000 richieste/giorno
- Upgrade a piano Pro se necessario

### **Timeout**

**Causa:** API TradingHours lenta o down

**Soluzione:**
- Il fallback automatico usa Capital.com
- Oppure procedi comunque (safe mode)

---

## 🚀 Best Practices

### **1. Cache Locale**

Per ridurre chiamate API:

```python
# Cache risultato per 5 minuti
CACHE = {}
CACHE_TIME = {}

def check_market_cached(epic):
    if epic in CACHE and (time.time() - CACHE_TIME[epic]) < 300:
        return CACHE[epic]
    
    result = check_market_tradinghours(epic)
    CACHE[epic] = result
    CACHE_TIME[epic] = time.time()
    return result
```

### **2. Fallback Chain**

```python
# 1. Prova TradingHours
result = check_market_th(epic)
if result['success']:
    return result

# 2. Fallback: Capital.com
result = check_market_capital(epic)
if result['success']:
    return result

# 3. Fallback: Procedi comunque
return {'is_open': True, 'status': 'UNKNOWN'}
```

### **3. Log Dettagliato**

```python
logger.info(f"Market check: {epic} → {result['status']}")
if not result['is_open']:
    logger.info(f"Reason: {result.get('reason', 'Unknown')}")
    logger.info(f"Next open: {result.get('next_open', 'N/A')}")
```

---

## 📖 Riferimenti

- **TradingHours Docs:** https://docs.tradinghours.com/
- **API Status:** https://status.tradinghours.com/
- **Support:** support@tradinghours.com

---

*Ultimo aggiornamento: Marzo 2026*
