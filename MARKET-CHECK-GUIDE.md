# PROFETA - Market Status Check Guide

## 📋 Panoramica

Il **Market Status Check** verifica automaticamente se il mercato è aperto prima di eseguire training e predizioni, evitando:
- Training su dati fermi (mercato chiuso)
- Previsioni non significative
- Spreco di risorse CPU/GPU

---

## 🎯 Come Funziona

### **Flusso Orchestratore**

```
┌─────────────────────────────────────┐
│  Start ciclo orario                 │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  Check: Mercato è aperto?           │
│  (Capital.com API)                  │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
    APERTO          CHIUSO
       │               │
       ▼               ▼
┌─────────────┐ ┌──────────────────┐
│ Esegui      │ │ Log: "Mercato    │
│ training    │ │ chiuso, skip"    │
│ + predict   │ │ Attendi prossimo │
└─────────────┘ └──────────────────┘
```

---

## 📁 File Utilizzati

### **1. check_market_status.py**

Utility standalone per verificare lo stato del mercato:

```bash
# Usage
python check_market_status.py [EPIC]

# Esempi
python check_market_status.py EURUSD
python check_market_status.py BTCUSD
```

**Output:**
```
╔════════════════════════════════════════════════════════════════╗
║          PROFETA - MARKET STATUS CHECK                         ║
╚════════════════════════════════════════════════════════════════╝

EPIC: EURUSD
Status: OPEN
Is Open: ✅ YES
Message: Mercato EURUSD: APERTO (Bid: 1.0845, Offer: 1.0847)
Bid: 1.0845
Offer: 1.0847
════════════════════════════════════════════════════════════════

✅ Il mercato è APERTO - Training/Prediction OK
```

### **2. Run_profeta_real_time.py (Modificato)**

L'orchestratore ora include:
- Check automatico prima di ogni ciclo
- Skip training se mercato chiuso
- Log dettagliato dello stato

---

## 🔧 Configurazione

### **Nessuna Configurazione Aggiuntiva Richiesta!**

Il sistema usa automaticamente le credenziali Capital.com già presenti in:
```
BKTEST/config-lstm-backtest.ini

[CAPITAL_DEMO]
api_key = xxx
api_secret = xxx
api_pass = xxx
```

---

## 📊 Comportamento per Tipo di Mercato

### **Crypto (BTCUSD, ETHUSD, etc.)**
- ✅ **Sempre aperto** - Skip check API
- Training eseguito 24/7
- Log: `"BTCUSD: Crypto - mercato sempre aperto"`

### **Forex (EURUSD, GBPUSD, etc.)**
- ✅ Check API Capital.com
- Aperto: Domenica 22:00 - Venerdì 22:00 UTC
- Chiuso: Weekend e festività

### **Stocks (AAPL, TSLA, etc.)**
- ✅ Check API Capital.com
- Aperto: Lun-Ven, orari di borsa
- Chiuso: Weekend e festività US

---

## 📈 Esempi di Log

### **Mercato APERTO (Forex)**
```
2026-03-21 14:00:00,123 | INFO | Verifica stato mercato...
2026-03-21 14:00:01,456 | INFO | ✅ Mercato EURUSD: APERTO (Bid: 1.0845, Offer: 1.0847)
2026-03-21 14:00:01,456 | INFO | ✅ Mercato APERTO - Esecuzione training/prediction
2026-03-21 14:00:02,789 | INFO | Download dati...
```

### **Mercato CHIUSO (Weekend)**
```
2026-03-22 10:00:00,123 | INFO | Verifica stato mercato...
2026-03-22 10:00:01,456 | INFO | ❌ Mercato EURUSD: CHIUSO (Weekend)
2026-03-22 10:00:01,456 | INFO | Skip training/prediction - mercato chiuso
2026-03-22 10:00:01,456 | INFO | ⚠️  Mercato CHIUSO - Skip ciclo corrente
2026-03-22 10:00:01,456 | INFO | ⏱️  Prossimo tentativo tra 0h 59m 59s
```

### **Crypto (Sempre Aperto)**
```
2026-03-21 14:00:00,123 | INFO | Verifica stato mercato...
2026-03-21 14:00:00,124 | INFO | BTCUSD: Crypto - mercato sempre aperto
2026-03-21 14:00:00,124 | INFO | ✅ Mercato APERTO - Esecuzione training/prediction
```

---

## 🧪 Test del Market Check

### **Test 1: Verifica Manuale**

```bash
# Test EURUSD (Forex - aperto in settimana)
wsl -d Ubuntu-24.04
cd ~/Profeta
python check_market_status.py EURUSD
```

**Risultato Atteso (Lun-Ven):**
```
✅ Il mercato è APERTO - Training/Prediction OK
```

**Risultato Atteso (Sab-Dom):**
```
❌ Il mercato è CHIUSO - Skip training/prediction
```

### **Test 2: Simula Weekend**

Modifica temporaneamente `check_market_status.py`:

```python
# Aggiungi dopo il check API
if epic == "EURUSD":
    result['is_open'] = False  # Forza chiuso per test
    result['message'] = f"Mercato {epic}: CHIUSO (TEST)"
```

Esegui orchestratore e verifica che skippi il training.

---

## 🎯 Integrazione con Multi-Epic Manager

Il `multi-epic-manager.sh` ora gestisce automaticamente:

```bash
# Avvia EURUSD + BTCUSD
./multi-epic-manager.sh start

# Output:
# EURUSD: Check mercato (skip se weekend)
# BTCUSD: Crypto - sempre aperto
```

---

## 📊 TradingHours Integration (Opzionale)

Se vuoi usare TradingHours come fallback o primary:

### **1. Aggiungi Config**

```ini
# config-lstm-EURUSD.ini
[MARKET_CHECK]
provider = tradinghours  ; o 'capital' (default)
api_key = th_xxxxxxxxxx
```

### **2. Modifica `check_market_open()`**

```python
provider = config.get('MARKET_CHECK', 'provider', fallback='capital')

if provider == 'tradinghours':
    result = check_with_tradinghours(epic, api_key)
else:
    result = broker.check_market_status(epic)
```

---

## ⚠️ Risoluzione Problemi

### **1. "Autenticazione fallita"**

**Causa:** Credenziali Capital.com errate

**Soluzione:**
```bash
# Verifica config
cat BKTEST/config-lstm-backtest.ini | grep CAPITAL_DEMO -A 5

# Test autenticazione
python check_market_status.py EURUSD
```

### **2. "Epic non trovato"**

**Causa:** Epic non valido su Capital.com

**Soluzione:**
```bash
# Verifica epic supportati
python probe_capital.py  # (Se disponibile)
```

### **3. Check Lento o Timeout**

**Causa:** Problemi di rete o API Capital.com lente

**Soluzione:**
- Aumenta timeout
- Usa cache locale (vedi sotto)

---

## 🚀 Ottimizzazioni Future

### **1. Cache Locale**

Per ridurre chiamate API:

```python
# Cache risultato per 5 minuti
CACHE = {}
CACHE_TIME = {}

def check_market_open_cached(epic):
    if epic in CACHE and (time.time() - CACHE_TIME[epic]) < 300:
        return CACHE[epic]
    
    result = check_market_open(epic)
    CACHE[epic] = result
    CACHE_TIME[epic] = time.time()
    return result
```

### **2. Check Pre-Training**

Aggiungi check anche in `profeta-universal.py`:

```python
# Prima di training
if not check_market_open(config, epic):
    logger.info("Mercato chiuso, skip training")
    sys.exit(0)
```

---

## 📖 Riferimenti

- **Capital.com API Docs:** https://docs.capital.com/
- **TradingHours API:** https://docs.tradinghours.com/
- **PROFETA Multi-Epic:** MULTI-EPIC-MANAGER.md

---

*Ultimo aggiornamento: Marzo 2026*
